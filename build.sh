#!/bin/bash

source envs/derecho_env_gnu.sh
rm -rf build install
ESMX_Builder -v --build-jobs=4 --build-args="-DCMAKE_Fortran_FLAGS=-I${ESMF_ROOT}/include" --cmake-args="-DCMAKE_Fortran_FLAGS=-I${PWD}/build/roms/module"
