#!/bin/bash -e
# Set up where the directories are. If you store this script in a folder:
# ${EXP_BASE_DIR}/analysis/script everything will work automatically, also for
# different experiments. ESM-runscript style directory trees are assumed.

module load cdo
CURRENT_DIR=$(cd $(dirname $0) && pwd)
EXP_BASE_DIR=$(cd $(dirname $0)/../../ && pwd)
EXP_ID=$(basename ${EXP_BASE_DIR})

OUTDATA_DIR_ECHAM=${EXP_BASE_DIR}/outdata/echam
ANALYSIS_DIR_ECHAM=${EXP_BASE_DIR}/analysis/echam

# Make sure an analysis directory exists
if [ ! -d $ANALYSIS_DIR_ECHAM ]; then
        mkdir -p ${ANALYSIS_DIR_ECHAM}
fi

#define parameters that define filenames
MODEL=echam6
VARNAME=$1
eval FILENAME=$2

#define filenames for the processed data
FILENAME_RAW=${EXP_ID}_${VARNAME}_${MODEL}_catted.nc
FILENAME_AVG=${EXP_ID}_${VARNAME}_${MODEL}_catted_yearmean_fldmean.nc

# Remove old files if you want to recreate them (probably a good idea to keep
# monitoring up to date)
RECREATE_ANALYSIS_FILE_DURING_RUN=1
if [ ${RECREATE_ANALYSIS_FILE_DURING_RUN} == 1 ]; then
        if [ -f ${ANALYSIS_DIR_ECHAM}/${FILENAME_AVG} ]; then
                rm -v ${ANALYSIS_DIR_ECHAM}/${FILENAME_AVG}
        fi
fi

# Get all data files from the outdata
cdo -f nc -t echam6 \
        select,name=${VARNAME} ${OUTDATA_DIR_ECHAM}/"${FILENAME}" \
        ${ANALYSIS_DIR_ECHAM}/${FILENAME_RAW} || echo "something went wrong, we continue anyway ..."

rmlist="${ANALYSIS_DIR_ECHAM}/${FILENAME_RAW} $rmlist"

# Make a yearmean and a fldmean
cdo -f nc -fldmean -yearmean \
        ${ANALYSIS_DIR_ECHAM}/${FILENAME_RAW} \
        ${ANALYSIS_DIR_ECHAM}/${FILENAME_AVG}

# Cleanup any files you might not need anymore
rm -v $rmlist
