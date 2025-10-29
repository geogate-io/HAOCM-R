import os
import sys
import xarray as xr
import numpy as np
from conduit import Node 
import earth2studio
from earth2studio.models.px import GraphCastOperational
from earth2studio.data import WB2ERA5
from earth2studio.io import XarrayBackend
from earth2studio.run import deterministic as run
from datetime import datetime, timedelta

# Arguments
state = "export"
channel = "atm"
nx_atm = 416
ny_atm = 196
debug = True 
method = "linear"

# Access to channel
my_channel = my_node["channels/{}/{}".format(state, channel)]

# Model specific parameters
forecast = my_node['state/time_str']
time = datetime.strptime(forecast, "%Y-%m-%dT%H:%M:%S")
step = 2 # lead time is 12h

# Find closest forecast time in 6 hour interval
def find_closest_6h_interval(time):
    # Find distance based on midnight
    seconds_since_midnight = (
        time - time.replace(hour=0, minute=0, second=0, microsecond=0)
    ).total_seconds()
    interval_seconds = 6 * 3600
    floor_intervals = int(seconds_since_midnight / interval_seconds)
    ceil_intervals = floor_intervals + 1

    # Find lower and upper time
    floor_time = time.replace(hour=0, minute=0, second=0, microsecond=0)+timedelta(seconds=floor_intervals * interval_seconds)
    ceil_time = time.replace(hour=0, minute=0, second=0, microsecond=0)+timedelta(seconds=ceil_intervals * interval_seconds)

    # Return bound
    return [floor_time, ceil_time]

# Find lower and upper bound or requested time
time_lb, time_ub = find_closest_6h_interval(time)

# Set new forecast time
forecast_new = time_lb.strftime("%Y-%m-%dT%H:%M:%S")
time_new = time_lb

# Redirect stdout - DO NOT USE WITH earth2studio
# This is interfering with earth2studio and prevent to run the model
#with open('output.txt', 'w') as f:
#    sys.stdout = f
#    print(f"Time lower bound: {time_lb} -> upper bound: {time_ub}")

# Create model, dataset for input and also io object for output
package = GraphCastOperational.load_default_package()
model = GraphCastOperational.load_model(package)
ds_input = WB2ERA5(cache=True)
io = XarrayBackend()

# Run model
run([forecast_new], step, model, ds_input, io)

# Perform temporal interpolation, lower -> forecast -> upper
ds_interp = io.root.isel(time=0, drop=True).rename({'lead_time': 'time'})
ds_interp['time'] = io.root['time'].values[0]+ds_interp['time']
ds_interp = ds_interp.interp(time=time, method=method)

# Define bounding box limits
min_lat, max_lat = 12.25, 61
min_lon, max_lon = 207, 310.75
ds_interp_subset = ds_interp.sel(lat=slice(min_lat, max_lat), lon=slice(min_lon, max_lon))

# Save results
if debug:
    ds_interp_subset.to_netcdf("graphcast_operational_{}_{}_{}_sub.nc".format(state, channel, forecast))

# Read flux data from file
ds_frc = xr.open_dataset("Data/FRC/era5_IRENE.nc")
ds_frc_interp = ds_frc.interp(time=time, method=method)

# Save selected time
if debug:
    ds_frc_interp.to_netcdf("forcing_era5_{}.nc".format(forecast))

# Return node with data
lead_time = 1
my_node_return = Node()
my_node_return.update(my_channel)
my_node_return['data/fields/Sa_u10m/values'] = ds_interp_subset.u10m.values.reshape(-1)
my_node_return['data/fields/Sa_v10m/values'] = ds_interp_subset.v10m.values.reshape(-1)
my_node_return['data/fields/Sa_pslv/values'] = ds_interp_subset.msl.values.reshape(-1)/100.0 # Pa -> hPa
my_node_return['data/fields/Sa_t2m/values'] = ds_interp_subset.t2m.values.reshape(-1)-273.15 # K -> C
my_node_return['data/fields/Faxa_rain/values']  = ds_interp_subset.tp06.values.reshape(-1)/6.0 # 6h -> 1h
# Get flux components humidity from forcing file since Grapcast does not provide them
my_node_return['data/fields/Sa_q2m/values'] = ds_frc_interp.Qair.values.reshape(-1)
my_node_return['data/fields/Faxa_lwdn/values']  = ds_frc_interp.lwrad_down.values.reshape(-1)
my_node_return['data/fields/Faxa_swnet/values'] = ds_frc_interp.swrad.values.reshape(-1)
if debug:
    my_node_return.save("my_node_return_{}".format(forecast))
