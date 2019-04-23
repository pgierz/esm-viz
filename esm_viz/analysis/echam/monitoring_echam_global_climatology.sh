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
FILENAME_AVG=${EXP_ID}_${MODEL}_${VARNAME}_global_climatology.nc

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

rmlist="${ANALYSIS_DIR_ECHAM}/${FILENAME_RAW} $rmlist"

# Make a timmean of the last 30 years
# NOTES:
#
# This will not work for variables that need specific weighting; e.g. oxygen
# isotopes.
#
# For reasons I don't fully understand, this needs to be broken up into a few
# different commands; since seltimestep messes up otherwise
cdo -f nc -yearmean \
        "${ANALYSIS_DIR_ECHAM}"/"${FILENAME_RAW}" \
        tmp
rmlist="tmp $rmlist"
cdo -f nc -timmean -seltimestep,-30/-1 \
        tmp \
        "${ANALYSIS_DIR_ECHAM}"/"${FILENAME_AVG}"

# Cleanup any files you might not need anymore
for f in $rmlist; do
        rm -v $f
done
