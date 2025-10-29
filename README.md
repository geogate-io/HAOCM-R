## DLROMS

The DLROMS modeling system is a hybrid modeling application that combines a DL weather model with a physical model (Regional Ocean Modeling System)

## Configuration

The predefined configuration uses the ROMS Hurricane Irene configuration. The detailed information about configuration can be found in the [ROMS Idealized and Realistic Test Cases](https://github.com/myroms/roms_test/blob/main/IRENE/Coupling/roms_data_cdeps/Readme.md) repository. More information about the Regional Ocean Modeling System (ROMS) can be found on its [wiki page](https://github.com/myroms/roms/wiki).

<img width="512" height="359" alt="Fig01" src="https://github.com/user-attachments/assets/9be9e2a6-e0ad-4520-9f63-9a2747320a21" />

## Usage

### Cloning Repository

The DLROMS modeling system includes two sub-components: (1) GeoGate (as data producer) and (2) the Regional Ocean Modeling System (ROMS) ocean model component. To clone the repository, the following command can be used:

```console
$ git clone --recursive https://github.com/geogate-io/DLROMS
```

### Installing Dependencies

The software dependencies to run the DLROMS application can be installed using [Conda](https://conda-forge.org) and [Spack](https://spack.io) package managers. The dependencies are already installed on [NCAR's Derecho](https://ncar-hpc-docs.readthedocs.io/en/latest/compute-systems/derecho/) HPC platform and can be accessed in the `/glade/work/turuncu/ML/envs/spack-1.0.2/var/spack/environments/myenv` directory. More information about creating a run environment from scratch can be found in the [GeoGateApps](https://github.com/geogate-io/GeoGateApps) prototype application repository, specifically in the [PythonSendCatalystRecv readme file](https://github.com/geogate-io/GeoGateApps/blob/main/PythonSendCatalystRecv/README.md).

### Building Model

To build the Hurricane Irene configuration on NCAR's Derecho machine, the [build.sh](https://github.com/geogate-io/DLROMS/blob/main/build.sh) script can be used. The script relies on a pre-installed Spack environment and uses the [derecho_env_gnu.sh](https://github.com/geogate-io/DLROMS/blob/main/envs/derecho_env_gnu.sh) file to load required modules.

```console
$ cd DLROMS
$ ./build.sh
```
Once it is successfully built, the executable for the coupled application (`esmx_app`) can be found in the `install/bin` directory.

### Supported Configurations

#### One-way Coupled

The one-way coupled configurations are used to force the underlying ocean component (ROMS) without receiving any feedback from it.

##### a. ERA5 (0.25 deg)

This configuration uses ERA5 data found in the [ROMS Idealized and Realistic Test Cases](https://github.com/myroms/roms_test/blob/main/IRENE/Coupling/roms_data_cdeps/Readme.md) repository. The GeoGate Python plugin is used to trigger [data_era5.py](https://github.com/geogate-io/DLROMS/blob/main/run/data_era5.py) to populate GeoGate's export state and pass the information to the ROMS ocean model.

##### b. GraphCast Operational (0.25 deg)

The [GraphCastOperational](https://nvidia.github.io/earth2studio/modules/generated/models/px/earth2studio.models.px.GraphCastOperational.html#earth2studio.models.px.GraphCastOperational) model is a high-resolution model (0.25 degree resolution, 13 pressure levels) pre-trained on ERA5 data from 1979 to 2017 and fine-tuned on HRES data from 2016 to 2021.

The GraphCastOperational model does not provide all the variables needed to force the ROMS ocean model. Therefore, variables such as `net shortwave radiation`, `downwelling longwave radiation`, and `surface relative humidity` are sourced directly from the ERA5 dataset to meet these requirements. There are plans to enhance GraphCast by incorporating the missing variables, either through fine-tuning or by utilizing another AI/ML-based weather model that supplies all necessary variables and interacts with the ocean component by exchanging sea surface temperature (SST) data as well.

To run this configuration, the `PythonScripts` and `ExportMeshFile` options need to be set as follows in the [esmxRun.yaml](https://github.com/geogate-io/DLROMS/blob/main/run/esmxRun.yaml) configuration file.

```
PythonScripts: data_graphcast_operational.py
```

#### Two-way Coupled

In this configuration, the interactions between model components (DL Weather and ROMS Ocean models) are two-way. The DL Weather provides atmospheric forcing to the ocean component (ROMS) and receives sea surface temperature (SST) to use it to make more accurate predictions. This configuration represents the complex and non-linear two-way interaction.

[...]

### Running Model

Once the configuration is compiled successfully, it can be run by using the job submission script (NCAR Derecho, [job_card.derecho](https://github.com/geogate-io/DLROMS/blob/main/run/job_card.derecho)). The job can be submitted by using following command,

```console
$ qsub job_card.derecho
```

To run GraphCast models on GPU, the job submission script can be modified to request GPU resources as follows:

```
...
#PBS -q main
#PBS -l select=1:ncpus=2:mpiprocs=2:ompthreads=1:ngpus=1
#PBS -l walltime=03:00:00
...
```

### References

The GraphCast configurations use NVIDIA's [Earth2Studio](https://nvidia.github.io/earth2studio/index.html) toolkit to run available GraphCast models ([Lam et al., 2023](https://www.science.org/doi/10.1126/science.adi2336)).
