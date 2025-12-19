import xarray as xr

# Load dataset
ds = xr.open_dataset("../run_cdeps/Data/merged_1h_with_humidity.nc")
ds = ds.reindex(latitude=ds.latitude[::-1])

# Define bounding box limits
min_lat, max_lat = 25, 55
min_lon, max_lon = 270, 310

# Subset it and write to disk
ds = ds.sel(longitude=slice(min_lon, max_lon), latitude=slice(min_lat, max_lat))
print(ds)
ds.to_netcdf("merged_1h_with_humidity_sub.nc")
