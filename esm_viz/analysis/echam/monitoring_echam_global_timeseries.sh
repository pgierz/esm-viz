#!/bin/bash -e
# Set up where the directories are. If you store this script in a folder:
# ${EXP_BASE_DIR}/analysis/script everything will work automatically, also for
# different experiments. ESM-runscript style directory trees are assumed.

#module load cdo
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

if [ ! -d .aux ]; then
        mkdir .aux
fi

if [ ! -f .aux/monitoring_echam_global_timeseries_${VARNAME}.dat ]; then
        files_to_process=$(find ${OUTDATA_DIR_ECHAM} -name ${FILENAME} | sort | tr -s ' ' '\n')
        echo $files_to_process | tr -s ' ' '\n' > .aux/monitoring_echam_global_timeseries_${VARNAME}.dat
else
        all_files=$(find ${OUTDATA_DIR_ECHAM} -name ${FILENAME} | sort | tr -s ' ' '\n')
        echo $all_files | tr -s ' ' '\n' > .aux/monitoring_echam_global_timeseries_${VARNAME}_newfiles.dat
        files_to_process=$(comm -13 .aux/monitoring_echam_global_timeseries_${VARNAME}.dat .aux/monitoring_echam_global_timeseries_${VARNAME}_newfiles.dat)
        mv .aux/monitoring_echam_global_timeseries_${VARNAME}_newfiles.dat .aux/monitoring_echam_global_timeseries_${VARNAME}.dat
fi


# Define filenames for the processed data
FILENAME_RAW=${EXP_ID}_${VARNAME}_${MODEL}_catted.nc
FILENAME_AVG=${EXP_ID}_${MODEL}_${VARNAME}_global_timeseries.nc

# TODO: This needs to be a bit different, this is something like "force mode"
# Remove old files if you want to recreate them (probably a good idea to keep
# monitoring up to date)
FORCE=0
if [[ x"$FORCE" == "x1" ]]; then
        RECREATE_ANALYSIS_FILE_DURING_RUN=1
else
        RECREATE_ANALYSIS_FILE_DURING_RUN=0
fi
if [ "${RECREATE_ANALYSIS_FILE_DURING_RUN}" == 1 ]; then
        if [ -f "${ANALYSIS_DIR_ECHAM}"/"${FILENAME_AVG}" ]; then
                rm -v "${ANALYSIS_DIR_ECHAM}"/"${FILENAME_AVG}"
        fi
fi

if [[ "x${files_to_process}" != "x" ]]; then
        # PG: This is somehow on the right track
        cdo -f nc -t echam6 \
                select,name="${VARNAME}" ${files_to_process} \
                        ${ANALYSIS_DIR_ECHAM}/${EXP_ID}_${VARNAME}_${MODEL}_newfiles.nc || echo "something went wrong, sorry!"

        cdo -f nc -fldmean -yearmean \
                ${ANALYSIS_DIR_ECHAM}/${EXP_ID}_${VARNAME}_${MODEL}_newfiles.nc \
                ${ANALYSIS_DIR_ECHAM}/${EXP_ID}_${VARNAME}_${MODEL}_newfiles_processed.nc
        rmlist="$rmlist ${ANALYSIS_DIR_ECHAM}/${EXP_ID}_${VARNAME}_${MODEL}_newfiles.nc ${ANALYSIS_DIR_ECHAM}/${EXP_ID}_${VARNAME}_${MODEL}_newfiles_processed.nc"
        # Check if a processed file already exists, otherwise it's the first run:
        if [ -f "${ANALYSIS_DIR_ECHAM}"/"${FILENAME_AVG}" ]; then
                cdo cat "${ANALYSIS_DIR_ECHAM}"/"${FILENAME_AVG}" ${ANALYSIS_DIR_ECHAM}/${EXP_ID}_${VARNAME}_${MODEL}_newfiles_processed.nc tmp
                echo "mv command --> Will rename tmp to ${ANALYSIS_DIR_ECHAM}/${FILENAME_AVG}"
                mv tmp "${ANALYSIS_DIR_ECHAM}"/"${FILENAME_AVG}"
        else
                echo "mv command --> Will rename ${ANALYSIS_DIR_ECHAM}/${EXP_ID}_${VARNAME}_${MODEL}_newfiles_processed.nc to ${ANALYSIS_DIR_ECHAM}/${FILENAME_AVG}"
                mv ${ANALYSIS_DIR_ECHAM}/${EXP_ID}_${VARNAME}_${MODEL}_newfiles_processed.nc "${ANALYSIS_DIR_ECHAM}"/"${FILENAME_AVG}"
        fi

else
        echo "No new files to process! The checked variable was: files_to_process=${files_to_process}"
        echo "Proceed with cleanup!"
fi

# Cleanup any files you might not need anymore
for f in $rmlist; do
        echo "rm command --> $f will be deleted"
        rm -v $f
done
