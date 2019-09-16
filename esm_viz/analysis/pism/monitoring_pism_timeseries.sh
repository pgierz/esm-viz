#!/bin/bash -e

this_script_path=$(readlink -f $(dirname $0))
this_script=$(basename $0)
root_path=$(readlink -f $(dirname ${this_script_path})"/../")
ANALYSIS_DIR=${root_path}/analysis
OUTDATA_DIR=${root_path}/outdata
VIZ_PATH=${root_path}/viz

EXP_ID=$(basename $root_path)

varname=${1:-sea_level_rise_potential}


ANALYSIS_DIR_pism=${root_path}/analysis/pism
OUTDATA_DIR_pism=${root_path}/outdata/pism
VIZ_PATH_pism=${root_path}/viz/pism


echo -e "\t\t * ANALYSIS of $EXP_ID\n"
echo -e "\t\t   This script ($this_script) will get timeseries for PISM\n"
echo -e "\t\t - Selected variable: $varname"

if [ -f ${ANALYSIS_DIR_pism}/${EXP_ID}_pismr_timeseries_${varname}.nc ]; then
        rm -fr ${ANALYSIS_DIR_pism}/${EXP_ID}_pismr_timeseries_${varname}.nc
fi

cdo select,name=$varname \
        $(ls -rt ${OUTDATA_DIR_pism}/${EXP_ID}_pismr_timeseries*nc)\
        ${ANALYSIS_DIR_pism}/${EXP_ID}_pism_${varname}_timeseries.nc
