#!/usr/bin/env bash

#PBS -P vy72
#PBS -q  normal
#PBS -l walltime=8:00:00,mem=128GB,ncpus=64,jobfs=50GB
#PBS -l wd
#PBS -j oe

module load python3/3.6.2
module load hdf5/1.8.14p openmpi/1.8
module load geos/3.5.0 netcdf/4.4.1.1

# setup environment
export LC_ALL=en_AU.UTF-8
export LANG=en_AU.UTF-8


# User please modify the below INSTALL_DIR, where pstvenv is installed (see install_venv.sh)
INSTALL_DIR=/g/data/ha3/PST2

# ELLIPCORR env variable should point to `passive-seismic/ellip-corr` dir
export ELLIPCORR=/g/data/ha3/fxz547/Githubz/passive-seismic/ellip-corr

# start the virtualenv workon seismic
source $INSTALL_DIR/pstvenv/bin/activate

# gather
# mpirun --mca mpi_warn_on_fork 0 cluster gather /g/data/ha3/events_xmls_sc3ml -w "P S"
#0.25 mpirun --mca mpi_warn_on_fork 0 cluster gather /g/data1a/ha3/fxz547/travel_time_tomography/run6_events_0.25deg/pbs_events_paths.txt  -w "P S"

mpirun --mca mpi_warn_on_fork 0 cluster gather /g/data1a/ha3/fxz547/travel_time_tomography/run7_events_0.5deg/pbs_events_paths.txt  -x 720 -y 360 -w "P S"


# sort
cluster sort outfile_P.csv 5. -s sorted_P.csv
cluster sort outfile_S.csv 10. -s sorted_S.csv

# match
# matching is an optional step as we can simply do P or S wave inversion
# cluster match sorted_P.csv sorted_S.csv -p matched_P.csv -s matched_S.csv

# zones
# if matching is not performed, replace matched_P.csv by sorted_P.csv and
# matched_S.csv by sorted_P.csv
cluster zone sorted_S.csv -z '0 -50.0 100 190' -r sorted_region_S.csv -g sorted_global_S.csv
cluster zone sorted_P.csv -z '0 -50.0 100 190' -r sorted_region_P.csv -g sorted_global_P.csv
#cluster zone matched_P.csv -z '0 -50.0 100 190' -r region_P.csv -g global_P.csv
#cluster zone matched_S.csv -z '0 -50.0 100 190' -r region_S.csv -g global_S.csv


# alternative zone command using the param2x2, the parameter file used during
# inversion
# cluster zone -p /path/to/param2x2 matched_S.csv -r region_S.csv -g global_S.csv

# cluster diagnostics plot
#cluster plot matched_P.csv '0 -50.0 100 190'
#cluster plot matched_S.csv '0 -50.0 100 190'
cluster plot sorted_P.csv '0 -50.0 100 190'
cluster plot sorted_S.csv '0 -50.0 100 190'