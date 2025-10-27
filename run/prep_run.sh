#!/bin/bash
# Arguments
nPETsX=3
nPETsY=4
OuterLoop=1
Phase4DVAR=1

# Clean existing configuration files
rm -f roms_irene.in rbl4dvar.in roms_data.yaml

# Download config files
wget -c -O roms_irene.in https://raw.githubusercontent.com/myroms/roms_test/refs/heads/main/IRENE/Coupling/roms_data_cdeps/roms_irene.tmpl
wget -c -O rbl4dvar.in https://raw.githubusercontent.com/myroms/roms_test/refs/heads/main/IRENE/Coupling/roms_data_cdeps/rbl4dvar.tmpl
wget -c -O roms_data.yaml https://raw.githubusercontent.com/myroms/roms_test/refs/heads/main/IRENE/Coupling/roms_data_cdeps/roms_cdeps_era5.yaml
cp ../src/ROMS/ROMS/External/varinfo.yaml .

# Parse config files
perl -p0777 -i -e "s|MyNtileI|${nPETsX}|g" roms_irene.in
perl -p0777 -i -e "s|MyNtileJ|${nPETsY}|g" roms_irene.in
perl -p0777 -i -e "s|MyIRENEdir|.|g" roms_irene.in
perl -p0777 -i -e "s|Hout\(idPair\) \=\= F|Hout\(idPair\) \=\= T|g" roms_irene.in 
perl -p0777 -i -e "s|Hout\(idTair\) \=\= F|Hout\(idTair\) \=\= T|g" roms_irene.in
perl -p0777 -i -e "s|Hout\(idUair\) \=\= F|Hout\(idUair\) \=\= T|g" roms_irene.in
perl -p0777 -i -e "s|Hout\(idVair\) \=\= F|Hout\(idVair\) \=\= T|g" roms_irene.in
perl -p0777 -i -e "s|Hout\(idUaiE\) \=\= F|Hout\(idUaiE\) \=\= T|g" roms_irene.in
perl -p0777 -i -e "s|Hout\(idVaiN\) \=\= F|Hout\(idVaiN\) \=\= T|g" roms_irene.in
perl -p0777 -i -e "s|Hout\(idTsur\) \=\= F F|Hout\(idTsur\) \=\= T T|g" roms_irene.in
perl -p0777 -i -e "s|Hout\(idLhea\) \=\= F|Hout\(idLhea\) \=\= T|g" roms_irene.in
perl -p0777 -i -e "s|Hout\(idShea\) \=\= F|Hout\(idShea\) \=\= T|g" roms_irene.in
perl -p0777 -i -e "s|Hout\(idLrad\) \=\= F|Hout\(idLrad\) \=\= T|g" roms_irene.in
perl -p0777 -i -e "s|Hout\(idSrad\) \=\= F|Hout\(idSrad\) \=\= T|g" roms_irene.in
perl -p0777 -i -e "s|Hout\(idEmPf\) \=\= F|Hout\(idEmPf\) \=\= T|g" roms_irene.in
perl -p0777 -i -e "s|Hout\(idevap\) \=\= F|Hout\(idevap\) \=\= T|g" roms_irene.in
perl -p0777 -i -e "s|Hout\(idrain\) \=\= F|Hout\(idrain\) \=\= T|g" roms_irene.in
perl -p0777 -i -e "s|NHIS == 180|NHIS == 60 |g" roms_irene.in
perl -p0777 -i -e "s|MyOuterLoop|${OuterLoop}|g" rbl4dvar.in
perl -p0777 -i -e "s|MyPhase4DVAR|${Phase4DVAR}|g" rbl4dvar.in
perl -p0777 -i -e "s|MyIRENEdir|.|g" rbl4dvar.in

perl -p0777 -i -e "s|CouplingType:    1|CouplingType:    2|g" roms_data.yaml

# Download ROMS input 
RUN_DIR=$PWD
mkdir -p Data/ROMS
cd Data/ROMS
wget -c https://github.com/myroms/roms_test/raw/refs/heads/main/IRENE/Data/ROMS/irene_roms_grid.nc
wget -c https://github.com/myroms/roms_test/raw/refs/heads/main/IRENE/Data/ROMS/irene_roms_ini_20110827_06.nc
wget -c https://github.com/myroms/roms_test/raw/refs/heads/main/IRENE/Data/ROMS/irene_roms_bry.nc
wget -c https://github.com/myroms/roms_test/raw/refs/heads/main/IRENE/Data/ROMS/irene_roms_clm.nc 
wget -c https://github.com/myroms/roms_test/raw/refs/heads/main/IRENE/Data/ROMS/irene_roms_nudgcoef.nc
wget -c https://github.com/myroms/roms_test/raw/refs/heads/main/IRENE/Data/ROMS/irene_roms_rivers.nc
wget -c https://github.com/myroms/roms_test/raw/refs/heads/main/IRENE/Data/ROMS/irene_roms_tides.nc
cd $RUN_DIR
mkdir -p Data/OBS
cd Data/OBS
wget -c https://github.com/myroms/roms_test/raw/refs/heads/main/IRENE/Data/OBS/irene_obs_20110827.nc
cd $RUN_DIR

# Download forcing
mkdir -p Data/ESMF
cd Data/ESMF
wget -c https://github.com/myroms/roms_test/raw/refs/heads/main/IRENE/Data/ESMF/era5_IRENE_ESMFmesh.nc
nccopy -k 5 era5_IRENE_ESMFmesh.nc era5_IRENE_ESMFmesh_cdf5.nc
rm -f era5_IRENE_ESMFmesh.nc
cd $RUN_DIR
mkdir -p Data/FRC
cd Data/FRC
wget -c https://github.com/myroms/roms_test/raw/refs/heads/main/IRENE/Data/FRC/era5_IRENE.nc
cd $RUN_DIR
