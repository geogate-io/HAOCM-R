import os
import sys
import time
from datetime import datetime, timedelta
from typing import Dict, List, Tuple
import yaml
import pandas as pd
import xarray as xr
import numpy as np
import torch
from torch.utils.data import DataLoader, Dataset
from aurora import rollout
from aurora import AuroraPretrained
from aurora import Batch, Metadata
from aurora.normalisation import locations, scales
from conduit import Node

class AuroraDataset(Dataset):
    """
    Aurora Dataset class for loading ERA5 data for training, validation and testing.
    Provides paired batches: input (t-6h, t) and target (t+6h).
    """
    def __init__(self, data_path: str, start_date: str, end_date: str, time_delta: int, variables: Dict[str, Dict[str, str]], timing: bool=False):
        self.data_path = data_path
        self.variables = variables
        self.start_indx = 1 # Because we need t-6h for input
        self.start_date = datetime.strptime(start_date, "%Y-%m-%dT%H:%M:%S")
        self.end_date = datetime.strptime(end_date, "%Y-%m-%dT%H:%M:%S")
        self.time_delta = timedelta(hours=time_delta)
        self.time_array = pd.date_range(self.start_date, self.end_date, freq=self.time_delta).strftime('%Y-%m-%dT%H:%M:%S').to_list()
        self.len = len(self.time_array) - 2

    def __len__(self) -> int:
        return self.len

    def __getbatch__(self, idxs: List[int], remove_south_pole=False) -> Batch:
        # Define required dictionaries
        surf_vars = {}
        static_vars = {}
        atmos_vars = {}

        # Load datasets
        file_list = []
        for idx in idxs:
            time_str = self.time_array[idx]
            file_name = f"data_{time_str}.nc"
            file_list.append(os.path.join(self.data_path, file_name))
        ds = xr.open_mfdataset(file_list, data_vars="all", chunks='auto', engine="netcdf4")

        # Fix for target tensors since Aurora model does not return data for the south pole
        if remove_south_pole:
            ds = ds.isel(latitude=slice(None, -1))

        # Batch
        for section in self.variables.keys():
            if section == "surf":
                for key, val in self.variables[section].items():
                    # Accumulated variables
                    if key in ["swnet", "lwnet", "swdn", "lwdn", "tp"]:
                        surf_vars[key] = torch.from_numpy((ds[val]/3600.0).values[None])  # Convert from per hour to per second
                    else:
                        surf_vars[key] = torch.from_numpy(ds[val].values[None])
            elif section == "static":
                for key, val in self.variables[section].items():
                    if len(idxs) > 1:
                        static_vars[key] = torch.from_numpy(ds[val].isel(time=0).values)
                    else:
                        static_vars[key] = torch.from_numpy(ds[val].values)
            elif section == "atmos":
                for key, val in self.variables[section].items():
                    atmos_vars[key] = torch.from_numpy(ds[val].values[None])

        _batch = Batch(
            surf_vars=surf_vars,
            static_vars=static_vars,
            atmos_vars=atmos_vars,
            metadata=Metadata(
                lat=torch.from_numpy(ds.latitude.values),
                lon=torch.from_numpy(ds.longitude.values),
                time=(ds.time.values.astype("datetime64[s]").tolist()[-1],),
                atmos_levels=tuple(int(level) for level in ds.level.values)
            ),
        )

        return _batch

    def __getitem__(self, idx: int) -> Tuple[Batch, Batch]:
        # Update index since we need t-6h for input
        idx = idx + self.start_indx

        # Get input batch
        input_idx = [idx-1, idx]
        input_batch = self.__getbatch__(input_idx)

        # Get target batch
        target_idx = [idx+1]
        target_batch = self.__getbatch__(target_idx, remove_south_pole=True)
        
        return input_batch, target_batch

def aurora_collate_fn(batches: List[Tuple[Batch, Batch]]) -> Tuple[Batch, Batch]:
    """
    Custom collate function to combine a list of Aurora Batch objects into a single batch.
    """
    inputs, targets = zip(*batches)
    return(batch_collate_fn(inputs), batch_collate_fn(targets))

def batch_collate_fn(batches: List[Batch]) -> Batch:
    """
    This function takes a list of Aurora Batch objects and combines them into a single batch of tensors
    """
    # Initialize result Batch
    result = Batch(
        atmos_vars=batches[0].atmos_vars,
        surf_vars=batches[0].surf_vars,
        static_vars=batches[0].static_vars,
        metadata=batches[0].metadata
    )
    # Merge tensors for surfface variables
    for key in result.surf_vars.keys():
        for idx in range(1, len(batches)):
            result.surf_vars[key] = torch.cat([result.surf_vars[key], batches[idx].surf_vars[key]], dim=0)
    
    # Merge tensors for atmospheric variables
    for key in result.atmos_vars.keys():
        for idx in range(1, len(batches)):
            result.atmos_vars[key] = torch.cat([result.atmos_vars[key], batches[idx].atmos_vars[key]], dim=0)    
    
    # Merge tensors for static variables
    result.static_vars = batches[0].static_vars

    # Add metadata, this is not working since Aurora fails with metadata as list
    #result.metadata = [t for item in batches for t in item.metadata.time]

    return result

def _np(x: torch.Tensor) -> np.ndarray:
    return x.detach().cpu().numpy()

def batch_to_dataset(batch) -> xr.Dataset:
    ds = xr.Dataset(
        data_vars = {
            **{key: (("latitude", "longitude"), _np(value)) for key, value in batch.static_vars.items()},
            **{key: (("batch", "time", "latitude", "longitude"), _np(value)) for key, value in batch.surf_vars.items()},
            **{key: (("batch", "time", "level", "latitude", "longitude"), _np(value)) for key, value in batch.atmos_vars.items()},
        },
        coords={
            "rollout_step": batch.metadata.rollout_step,
            "time": list(batch.metadata.time),
            "level": list(batch.metadata.atmos_levels),
            "latitude": _np(batch.metadata.lat),
            "longitude": _np(batch.metadata.lon),
        },
    )
    return ds

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

if __name__ == "__main__":
    # Arguments
    state = "export"
    channel = "atm"
    nx_atm = 1440
    ny_atm = 720
    debug = True
    perform_temporal_interpolation = True
    temporal_interpolation_method = "linear"
    update_sst = False

    # Set epoch date
    epoch_date = pd.Timestamp("1970-01-01")

    # Access to channel
    my_channel = my_node["channels/{}/{}".format(state, channel)]
    forecast_time_str = my_node['state/time_str'] # e.g., "2011-08-27T06:00:00"
    forecast_time = datetime.strptime(forecast_time_str, "%Y-%m-%dT%H:%M:%S")
    
    # Find lower and upper bound or requested time
    time_delta = 6 # hours
    time_lb, time_ub = find_closest_6h_interval(forecast_time)

    # Start and end date for data loading, need to cover t-6h, t and t+6h
    duration = timedelta(hours=time_delta)
    start_date = (time_lb - 2*duration).strftime("%Y-%m-%dT%H:%M:%S")
    end_date =  time_lb.strftime("%Y-%m-%dT%H:%M:%S")
    print(f"Forecast time: {forecast_time}, lower bound: {start_date}, upper bound: {end_date}", flush=True)

    # Load config from YAML file
    with open("config.yaml", "r") as f:
        settings = yaml.safe_load(f)
    generic_settings = settings["aurora_config"]["generic"]
    prediction_settings = settings["aurora_config"]["prediction"]

    # Variables downloaded from (ECMWF's cds.climate.copernicus.eu)
    # lat = 90 to -90 (721 points)
    # lon = 0 to 359.75 (1440 points)
    # lev = 1000, 925, 850, 700, 600, 500, 400, 300, 250, 200, 150, 100, 50
    variables = {
        "surf": {
            "2t" : "t2m",
            "10u": "u10",
            "10v": "v10",
            "msl": "msl",
        },
        "static": {
            "z"  : "hgt",
            "slt": "slt",
            "lsm": "lsm"
        },
        "atmos": {
            "t"  : "t",
            "u"  : "u",
            "v"  : "v",
            "q"  : "q",
            "z"  : "z"
        }
    }

    # Include additional surface variables
    if "new_surf_vars" in generic_settings and generic_settings["new_surf_vars"] is not None:
        for key, val in generic_settings["new_surf_vars"].items():
            variables["surf"][key] = val["name"]

    # List of variables
    surf_vars = tuple(variables["surf"].keys())
    static_vars = tuple(variables["static"].keys())
    atmos_vars = tuple(variables["atmos"].keys())

    # Set device
    device_type = torch.accelerator.current_accelerator()
    device = torch.device(f"{device_type}")

    # Initialize model
    model = AuroraPretrained(
        surf_vars=surf_vars,
        static_vars=static_vars,
        atmos_vars=atmos_vars
    )

    # Load pretrained weights
    model.load_checkpoint_local(prediction_settings["checkpoint_file"], strict=False)

    # Set model to evaluation mode
    model.eval()

    # Move model to device
    model.to(device)

    # Prepare Aurora dataset that provides paired batches: input, target
    data_path = generic_settings["data_path"]
    dataset = AuroraDataset(data_path, start_date, end_date, time_delta, variables)

    # Create DataLoader
    data_loader = DataLoader(
       dataset,
       batch_size=int(prediction_settings["batch_size"]), # Number of samples per batch - Use 1 for coupling since GeoGate provides one time step at a time
       num_workers=int(prediction_settings["num_workers"]), # Use multiple processes for faster data loading (adjust based on system)
       pin_memory=True, # Use pinned memory for faster GPU transfer (if using a GPU)
       persistent_workers=True if int(prediction_settings["num_workers"]) > 0 else False, # Keep workers alive for multiple epochs
       shuffle=False, # Shuffle data every epoch
       sampler=None, # No distributed sampler
       collate_fn=aurora_collate_fn,
    )

    # Set the normalisation statistics for the new variables
    if "new_surf_vars" in generic_settings.keys():
        for key, val in generic_settings["new_surf_vars"].items():
            print(f"Setting normalisation statistics for {key} ({val['name']}): mean={val['mean']}, std={val['std']}", flush=True)
            locations[key] = float(val["mean"])
            scales[key] = float(val["std"])

    # Output file path
    ofile_path = prediction_settings["output_path"]
    os.makedirs(ofile_path, exist_ok=True)

    # Loop over the data loader and make predictions    
    for batch, (input, target) in enumerate(data_loader):
        # Print input and target times
        print(f"Input time: {input.metadata.time[0].strftime('%Y-%m-%dT%H:%M:%S')}", flush=True)
        print(f"Target time: {target.metadata.time[0].strftime('%Y-%m-%dT%H:%M:%S')}", flush=True)

        with torch.inference_mode():
            # Output file
            ofile = os.path.join(ofile_path, f"pred_{target.metadata.time[0].strftime('%Y-%m-%dT%H:%M:%S')}.nc")

            # Check if output file already exists
            if os.path.exists(ofile):
                print(f"File {ofile} already exists. Use existing prediction...", flush=True)
                # Load existing dataset
                ds = xr.open_dataset(ofile, engine="netcdf4")
            else:
                # Get start time
                start_time = time.time()

                # Make prediction
                preds = [pred.to("cpu") for pred in rollout(model, input.to(device), steps=prediction_settings["steps"])]

                # Create dataset from predictions
                ds = xr.concat([batch_to_dataset(pred) for pred in preds], dim="time", data_vars='all', coords='different', compat='equals')
                
                # Save predictions to netCDF files
                ds.to_netcdf(ofile, engine="netcdf4")

                # Get end time
                end_time = time.time()

                # Measure estimated time for the batch
                batch_time = end_time - start_time

                # Print info
                print(f"Made {int(prediction_settings['steps'])*time_delta}h prediction for batch {batch+1}/{len(data_loader)} with time {target.metadata.time[0].strftime('%Y-%m-%d %H:%M:%S')} in {batch_time:.4f} seconds.", flush=True)

            # Keep only coupling variables
            ds = ds[['10u', '10v', 'msl', '2t', '2rh', 'lwdn', 'swnet', 'time']].drop_vars('rollout_step').isel(batch=0)

            # Perform temporal interpolation to forecast time, two rollout step is needed to perform: t+0h -> ? -> t+6h
            # Since Aurora output is in float32, we need to convert to float64 to be compatible with GeoGate - TODO: Fix this in GeoGate to allow float32
            if perform_temporal_interpolation:
                if forecast_time != time_lb:
                    print(f"Interpolating data using {temporal_interpolation_method} method to forecast time: {forecast_time_str}", flush=True)
                    ds_interp = ds.interp(time=forecast_time_str, method=temporal_interpolation_method).drop_vars('time').astype(np.float64)
                    if debug:
                        ds_interp.to_netcdf(os.path.join(ofile_path, f"pred_{forecast_time_str}_interp.nc"), engine="netcdf4")
                else:
                    print("No temporal interpolation needed since forecast time matches the model output time.", flush=True)
                    ds_interp = ds.isel(time=0).astype(np.float64)
            else:
                print("No temporal interpolation requested.", flush=True)
                ds_interp = ds.isel(time=0).astype(np.float64)

            # Return Conduit node with data
            my_node_return = Node()
            my_node_return.update(my_channel)
            my_node_return['data/fields/Sa_u10m/values'] = ds_interp['10u'].values.reshape(-1) # m/s
            my_node_return['data/fields/Sa_v10m/values'] = ds_interp['10v'].values.reshape(-1) # m/s
            my_node_return['data/fields/Sa_pslv/values'] = ds_interp['msl'].values.reshape(-1)/100.0 # Pa -> hPa
            my_node_return['data/fields/Sa_t2m/values'] = ds_interp['2t'].values.reshape(-1)-273.15 # K -> C
            my_node_return['data/fields/Faxa_rain/values']  = np.zeros_like(ds_interp['2t'].values).reshape(-1) # No precipitation data from Aurora
            my_node_return['data/fields/Sa_q2m/values'] = ds_interp['2rh'].values.reshape(-1)*100.0 # fraction -> percentage
            my_node_return['data/fields/Faxa_lwdn/values']  = ds_interp['lwdn'].values.reshape(-1) # W/m2
            my_node_return['data/fields/Faxa_swnet/values'] = ds_interp['swnet'].values.reshape(-1) # W/m2
            if debug:
                my_node_return.save("pred_{}".format(forecast_time_str))