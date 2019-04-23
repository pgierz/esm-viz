#!/bin/bash -e
# Set up where the directories are. If you store this script in a folder:
# ${EXP_BASE_DIR}/analysis/script everything will work automatically, also for
# different experiments. ESM-runscript style directory trees are assumed.

module load cdo
CURRENT_DIR=$(cd $(dirname $0) && pwd)
EXP_BASE_DIR=$(cd $(dirname $0)/../../ && pwd)
case $(basename $EXP_BASE_DIR) in
        # NOTE: For iterative coupling; if you land in a "model" folder; you need to
        # go up one more
        # FIXME: This is dependent on how Dirk has set up iterative coupling
        # for now; and might change in the future....
        'awicm' | 'mpiesm' | 'pism_standalone' | 'cosmos' )
                EXP_ID=$(basename $(cd $(dirname $0)/../../../ && pwd))
                ;;
        * )
                EXP_ID=$(basename ${EXP_BASE_DIR})
                ;;
esac

# Define parameters that define filenames
MODEL=echam
VARNAME=$1
eval FILENAME=$2

OUTDATA_DIR_ECHAM=${EXP_BASE_DIR}/outdata/echam
ANALYSIS_DIR_ECHAM=${EXP_BASE_DIR}/analysis/echam

# Make sure an analysis directory exists
if [ ! -d $ANALYSIS_DIR_ECHAM ]; then
        mkdir -p ${ANALYSIS_DIR_ECHAM}
fi


# Define filenames for the processed data
FILENAME_RAW=${EXP_ID}_${VARNAME}_${MODEL}_catted.nc
FILENAME_AVG=${EXP_ID}_${MODEL}_${VARNAME}_global_timeseries.nc

# Remove old files if you want to recreate them (probably a good idea to keep
# monitoring up to date)
RECREATE_ANALYSIS_FILE_DURING_RUN=1
if [ "${RECREATE_ANALYSIS_FILE_DURING_RUN}" == 1 ]; then
        if [ -f "${ANALYSIS_DIR_ECHAM}"/"${FILENAME_AVG}" ]; then
                rm -v "${ANALYSIS_DIR_ECHAM}"/"${FILENAME_AVG}"
        fi
fi

# Get all data files from the outdata
cdo -f nc -t echam6 \
        select,name="${VARNAME}" "${OUTDATA_DIR_ECHAM}"/"${FILENAME}" \
        "${ANALYSIS_DIR_ECHAM}"/"${FILENAME_RAW}" || echo "something went wrong, we continue anyway ..."

# FIXME: This should only be removed if it is the last timeseries being made:
rmlist="${ANALYSIS_DIR_ECHAM}/${FILENAME_RAW} $rmlist"

# Make a yearmean and a fldmean
cdo -f nc -fldmean -yearmean \
        "${ANALYSIS_DIR_ECHAM}"/"${FILENAME_RAW}" \
        "${ANALYSIS_DIR_ECHAM}"/"${FILENAME_AVG}"

# NOTE: This is done on the python side; so we can remove it here. I just
# commented it for now in case we need something like this in the future...
#
# Make a running mean if the file is long enough
#NUMBER_OF_YEARS=$(cdo nyear "${ANALYSIS_DIR_ECHAM}/${FILENAME_AVG}")
#if [ "${NUMBER_OF_YEARS}" -gt 30 ]; then
#        cdo -runmean,30 "${ANALYSIS_DIR_ECHAM}/${FILENAME_AVG}" "${ANALYSIS_DIR_ECHAM}/${FILENAME_AVG%.*}_runmean30.nc"
#fi

# Cleanup any files you might not need anymore
for f in $rmlist; do
        rm -v $f
done
