import sys
from pathlib import Path
import cdsapi
import yaml
import pandas as pd

if __name__ == "__main__":
    # Load config from YAML file
    with open("/glade/work/turuncu/ML/runs/DLROMS/run/config.yaml", "r") as f:
        settings = yaml.safe_load(f)
    prediction_settings = settings["aurora_config"]["prediction"]

    # Data will be downloaded here.
    download_path = Path("./")

    # Open client
    c = cdsapi.Client()

    # Download data
    # Create a time array from start to end with 6-hour intervals
    time_array = pd.date_range(prediction_settings["start"], prediction_settings["end"], freq="6h")

    # Loop over each time and download data
    for t in time_array:
        # Extract year, month, day, hour
        year = t.year
        month = t.month
        day = t.day
        hour = t.strftime("%H:%M")

        # Download the static variables
        if t == time_array[0]:
            if not (download_path / "static.nc").exists():
                c.retrieve(
                    "reanalysis-era5-single-levels",
                    {
                        "product_type": "reanalysis",
                        "variable": [
                            "geopotential",
                            "land_sea_mask",
                            "soil_type",
                        ],
                        "year": year,
                        "month": "01",
                        "day": "01",
                        "time": "00:00",
                        "format": "netcdf",
                    },
                    str(download_path / "static.nc"),
                )
            print("Static variables downloaded!")

        # Download the surface-level instantaneous variables
        if not (download_path / f"data_{year:04d}-{month:02d}-{day:02d}T{hour}:00:00_surface-level-instant.nc").exists():
            print(f"Downloading datafile data_{year:04d}-{month:02d}-{day:02d}T{hour}:00:00_surface-level-instant.nc")
            c.retrieve(
                "reanalysis-era5-single-levels",
                {
                    "product_type": "reanalysis",
                    "variable": [
                        "2m_temperature",
                        "2m_dewpoint_temperature",
                        "10m_u_component_of_wind",
                        "10m_v_component_of_wind",
                        "mean_sea_level_pressure",
                        "sea_surface_temperature",
                        "total_cloud_cover",
                    ],
                    "year": year,
                    "month": f"{month:02d}",
                    "day": f"{day:02d}",
                    "time": [hour],
                    "data_format": "netcdf",
                    "download_format": "unarchived"
                },
                str(download_path / f"data_{year:04d}-{month:02d}-{day:02d}T{hour}:00:00_surface-level-instant.nc"),
            )
        else:
            print(f"File data_{year:04d}-{month:02d}-{day:02d}T{hour}:00:00_surface-level-instant.nc already exists. Skipping download.")

        # Download the surface-level accumulated variables
        if not (download_path / f"data_{year:04d}-{month:02d}-{day:02d}T{hour}:00:00_surface-level-accum.nc").exists():
            print(f"Downloading datafile data_{year:04d}-{month:02d}-{day:02d}T{hour}:00:00_surface-level-accum.nc")
            c.retrieve(
                "reanalysis-era5-single-levels",
                {
                    "product_type": "reanalysis",
                    "variable": [
                        "total_precipitation",
                        "surface_net_solar_radiation",
                        "surface_net_thermal_radiation",
                        "surface_solar_radiation_downwards",
                        "surface_thermal_radiation_downwards",
                    ],
                    "year": year,
                    "month": f"{month:02d}",
                    "day": f"{day:02d}",
                    "time": [hour],
                    "data_format": "netcdf",
                    "download_format": "unarchived"
                },
                str(download_path / f"data_{year:04d}-{month:02d}-{day:02d}T{hour}:00:00_surface-level-accum.nc"),
            )
        else:
            print(f"File data_{year:04d}-{month:02d}-{day:02d}T{hour}:00:00_surface-level-accum.nc already exists. Skipping download.")

        # Download the atmospheric variables at pressure levels
        if not (download_path / f"data_{year:04d}-{month:02d}-{day:02d}T{hour}:00:00_atmospheric.nc").exists():
            print(f"Downloading datafile data_{year:04d}-{month:02d}-{day:02d}T{hour}:00:00_atmospheric.nc")
            c.retrieve(
                "reanalysis-era5-pressure-levels",
                {
                    "product_type": "reanalysis",
                    "variable": [
                        "temperature",
                        "u_component_of_wind",
                        "v_component_of_wind",
                        "specific_humidity",
                        "geopotential",
                    ],
                    "pressure_level": [
                        "50",
                        "100",
                        "150",
                        "200",
                        "250",
                        "300",
                        "400",
                        "500",
                        "600",
                        "700",
                        "850",
                        "925",
                        "1000",
                    ],
                    "year": year,
                    "month": f"{month:02d}",
                    "day": f"{day:02d}",
                    "time": [hour],
                    "data_format": "netcdf",
                    "download_format": "unarchived"
                },
                str(download_path / f"data_{year:04d}-{month:02d}-{day:02d}T{hour}:00:00_atmospheric.nc"),
            )