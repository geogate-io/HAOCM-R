import os, sys
import time
import xarray as xr
import pandas as pd
import numpy as np
import argparse
import glob
from metpy.units import units
from metpy.calc import specific_humidity_from_dewpoint
from metpy.calc import relative_humidity_from_dewpoint

if __name__ == "__main__":
    # Arguments
    parser = argparse.ArgumentParser(description="Split ERA5 data into individual time steps.")
    parser.add_argument("--data_path", type=str, default='.', help="Path to the data directory")
    args = parser.parse_args()
    data_path = args.data_path

    # Load datasets
    start_time = time.time()
    files = sorted(glob.glob(os.path.join(data_path, '*_surface-level-instant.nc')))
    ds_surf_ins = xr.open_mfdataset(files, chunks='auto', engine="netcdf4").rename({'valid_time': 'time'})
    files = sorted(glob.glob(os.path.join(data_path, '*_surface-level-accum.nc')))
    ds_surf_acc = xr.open_mfdataset(files, chunks='auto', engine="netcdf4").rename({'valid_time': 'time'})
    files = sorted(glob.glob(os.path.join(data_path, '*_atmospheric.nc')))
    ds_atmos = xr.open_mfdataset(files, chunks='auto', engine="netcdf4").rename({'valid_time': 'time', 'pressure_level': 'level'})
    ds_static = xr.open_dataset(os.path.join(data_path, 'static.nc'), engine="netcdf4").rename({'z': 'hgt'}).squeeze("valid_time")
    ds = xr.merge([ds_atmos, ds_surf_ins, ds_surf_acc, ds_static], compat='override').drop_vars(['number', 'expver', 'valid_time'])
    ds = ds.chunk({'time': 10, 'level': -1, 'latitude': -1, 'longitude': -1})
    end_time = time.time()
    print(f"Datasets loaded in {end_time - start_time} seconds")

    # Output directory
    output_dir = os.path.join(data_path, 'split_files')
    os.makedirs(output_dir, exist_ok=True)

    # Loop over time steps and save individual files
    i = 0
    for t in ds.time:
        # Generate output file name
        time_str = pd.to_datetime(t.values).strftime('%Y-%m-%dT%H:%M:%S')
        output_file = os.path.join(output_dir, f'data_{time_str}.nc')
        # Check if file already exists
        if os.path.exists(output_file):
            print(f'Skipping {output_file}, already exists.')
            i += 1
            continue
        else:
            start_time = time.time()
            # Select time slice
            ds_local = ds.isel(time=slice(i,i+1))
            # Calculate relative humidity and specific humidity at 2 meters
            t2 = ds['t2m']-273.15 # Convert from Kelvin to Celsius
            msl = ds['msl']/100.0  # Convert from Pa to hPa
            d2 = ds['d2m'].sel(time=ds.time) # Convert from Kelvin to Celsius
            rh2 = relative_humidity_from_dewpoint(t2 * units.degC, (d2-273.16) * units.degC).compute().values
            q2 = specific_humidity_from_dewpoint(msl * units.hPa, (d2-273.16) * units.degC).compute().values
            # Create DataArrays for rh2 and q2
            relative_humidity = xr.DataArray(
                rh2,
                dims=('time', 'latitude', 'longitude'),
                coords=ds.coords.drop_vars('level'),
                name='rh2',
                attrs={'units': 'fraction', 'description': '2 metre relative humidity'}
            )
            specific_humidity = xr.DataArray(
                q2,
                dims=('time', 'latitude', 'longitude'),
                coords=ds.coords.drop_vars('level'),
                name='q2',
                attrs={'units': 'kg/kg', 'description': '2 metre specific humidity'}
            )
            # Add new variables to dataset
            ds_local['rh2'] = relative_humidity
            ds_local['q2'] = specific_humidity
            ds_local['d2m'] = d2
            # Handle missing values for 'sst' variable, based on approach used in Google's FGN model (https://arxiv.org/abs/2506.10772)
            # sst_min = ds_local.sst.min().load()
            sst_min = 269.12622  # Pre-computed minimum value for 2012-2018 period that covers training and validation data
            ds_local["sst"] = ds_local["sst"].fillna(sst_min)
            # Add w10 variable
            ds_local['w10'] = np.sqrt(ds_local['u10']**2 + ds_local['v10']**2)
            # Save the dataset
            ds_local.to_netcdf(output_file)
            i += 1
            end_time = time.time()
            print(f'Saved {output_file} in {end_time - start_time} seconds.')