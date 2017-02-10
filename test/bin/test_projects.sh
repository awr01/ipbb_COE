#!/usr/bin/env bash

if [ "$(basename $PWD)" != "myarea" ]; then
    echo "$(basename $BASH_SOURCE) must be run in 'myarea' test area"
    exit -1
fi


if [ "$#" -ne 1 ]; then
    echo "Usage $(basename $0) <project>"
    exit
fi

IPBB_TEST_PROJ="$1"
FW_ROOT=$(pwd)
set -e

if [ "${IPBB_TEST_PROJ}" == "kc705" ]; then
    cd ${FW_ROOT}
    ipbb proj create vivado kc705 dummy-fw-proj:projects/example -t top_kc705_gmii.dep
    cd work/kc705
    ipbb vivado project 
    ipbb vivado build
    ipbb vivado bitfile

elif [[ "${IPBB_TEST_PROJ}" == "mp7xe_690_minimal" ]]; then
    cd ${FW_ROOT}
    ipbb proj create vivado mp7xe_690_minimal cactusupgrades:projects/examples/mp7xe_690_minimal 
    cd work/mp7xe_690_minimal
    ipbb vivado project
    ipbb vivado build
    ipbb vivado bitfile

elif [[ "${IPBB_TEST_PROJ}" == "mp7_sim" ]]; then
    cd ${FW_ROOT}
    ipbb proj create sim mp7_sim cactusupgrades:projects/examples/mp7_sim 
    cd work/mp7_sim
    ipbb sim ipcores
    ipbb sim fli 
    ipbb sim project
    ./vsim -c work.top -do "run 10 us; quit"
    set +x
else
    echo "Unknow project ${IPBB_TEST_PROJ}."
    echo "  Available projects: kc705, mp7xe_690_minimal, mp7_sim"
    exit -1
fi