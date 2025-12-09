#!/bin/bash

source envs/derecho_env_gnu.sh
rm -rf build install esmxBuild.yaml
echo "application:" >> esmxBuild.yaml 
echo "  disable_comps: ESMX_Data" >> esmxBuild.yaml
echo "  link_libraries: piof conduit catalyst catalyst_fortran python3.12" >> esmxBuild.yaml
echo "components:" >> esmxBuild.yaml
echo "  datm:" >> esmxBuild.yaml
echo "    source_dir: src/CDEPS" >> esmxBuild.yaml
echo "    build_type: cmake.external" >> esmxBuild.yaml
echo "    build_args: \"-DDISABLE_FoX=ON -DCPRGNU=ON -DPIO_C_LIBRARY=$PIO_C_LIBRARY -DPIO_C_INCLUDE_DIR=$PIO_C_INCLUDE_DIR -DPIO_Fortran_LIBRARY=$PIO_Fortran_LIBRARY -DPIO_Fortran_INCLUDE_DIR=$PIO_Fortran_INCLUDE_DIR -DCMAKE_Fortran_FLAGS=-ffree-line-length-none\"" >> esmxBuild.yaml
echo "    fort_module: cdeps_datm_comp.mod" >> esmxBuild.yaml
echo "    libraries: datm dshr streams cdeps_share" >> esmxBuild.yaml
echo "  geogate:" >> esmxBuild.yaml
echo "    source_dir: src/GeoGate/src" >> esmxBuild.yaml
echo "    build_type: cmake.external" >> esmxBuild.yaml
echo "    build_args: \"-DGEOGATE_USE_PYTHON=ON -DGEOGATE_USE_CATALYST=ON -DCMAKE_Fortran_FLAGS=-ffree-line-length-none\"" >> esmxBuild.yaml
echo "    fort_module: geogate_nuopc.mod" >> esmxBuild.yaml
echo "    libraries: geogate geogate_io geogate_python geogate_catalyst geogate_shared" >> esmxBuild.yaml
echo "  roms:" >> esmxBuild.yaml
echo "    source_dir: src/ROMS" >> esmxBuild.yaml
echo "    build_type: cmake.external" >> esmxBuild.yaml
echo "    build_args: \"-DROMS_EXECUTABLE=OFF -DLIBTYPE=STATIC -DROMS_SRC_DIR=src/ROMS -DMY_HEADER_DIR=../../../apps -DROMS_APP=IRENE -DMPI=ON\"" >> esmxBuild.yaml
echo "    fort_module: cmeps_roms_mod" >> esmxBuild.yaml
echo "    libraries: ROMS" >> esmxBuild.yaml
ESMX_Builder -v --build-jobs=4 --build-args="-DCMAKE_Fortran_FLAGS=-I${ESMF_ROOT}/include" --cmake-args="-DCMAKE_Fortran_FLAGS=-I${PWD}/build/roms/module"
