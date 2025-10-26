import sys
#import logging
from conduit import Node
import numpy as np
import xarray as xr
#import pandas as pd

# Class for logging
#class StreamToLogger(object):
#    """
#    Fake file-like stream object that redirects writes to a logger instance.
#    """
#    def __init__(self, logger, level):
#       self.logger = logger
#       self.level = level
#       self.linebuf = ''
#
#    def write(self, buf):
#       for line in buf.rstrip().splitlines():
#          self.logger.log(self.level, line.rstrip())
#
#    def flush(self):
#        pass
#
## Redirect stdout and stderr to log file
#logging.basicConfig(
#        level=logging.DEBUG,
#        format='%(asctime)s:%(levelname)s:%(name)s:%(message)s',
#        filename='{}.log'.format(sys.argv[0].replace('py', '')),
#        filemode='a'
#)
#
#log = logging.getLogger(sys.argv[0])
#sys.stdout = StreamToLogger(log,logging.INFO)
#sys.stderr = StreamToLogger(log,logging.ERROR)

# Arguments
state = "export"
channel = "atm"
nx_atm = 416
ny_atm = 196
debug = True

# Access to channel
my_channel = my_node["channels/{}/{}".format(state, channel)]

# Save the data in the channel
#if debug:
#    my_channel.save('my_channel_{}_{}_{}'.format(state, channel, tstr))

# Read data from file
tstr = my_node['state/time_str']
ds = xr.open_dataset("Data/FRC/era5_IRENE.nc").sel(time=tstr, method="nearest")

# Data is converted to double since GeoGate Conduit interface is designed to expect double
# GeoGate TODO: Allow other data types without type conversion
for var in ds.data_vars:
    if np.issubdtype(ds[var].dtype, np.number):
        ds[var] = ds[var].astype(np.float64)

# Redirect stdout
with open('output.txt', 'w') as f:
    sys.stdout = f
    print("Time = {}".format(tstr))
    for vn, da in ds.data_vars.items():
        print(f"{vn} min, max = {da.min().item():.3f}, {da.max().item():.3f}")
        
# Save data for debugging
if debug:
    ds.to_netcdf("{}_{}_{}.nc".format(state, channel, tstr))

# Return new node with modified data
my_node_return = Node()
my_node_return.update(my_channel)
my_node_return['data/fields/Sa_u10m/values']    = ds['Uwind'].values.reshape(-1)
my_node_return['data/fields/Sa_v10m/values']    = ds['Vwind'].values.reshape(-1)
my_node_return['data/fields/Sa_pslv/values']    = ds['Pair'].values.reshape(-1)
my_node_return['data/fields/Sa_t2m/values']     = ds['Tair'].values.reshape(-1)
my_node_return['data/fields/Sa_q2m/values']     = ds['Qair'].values.reshape(-1)
my_node_return['data/fields/Faxa_rain/values']  = ds['rain'].values.reshape(-1)
my_node_return['data/fields/Faxa_lwdn/values']  = ds['lwrad_down'].values.reshape(-1)
my_node_return['data/fields/Faxa_swnet/values'] = ds['swrad'].values.reshape(-1)
#if debug:
#    my_node_return.save("my_node_return_{}".format(tstr))
