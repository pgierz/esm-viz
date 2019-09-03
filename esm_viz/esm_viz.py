# -*- coding: utf-8 -*-
"""Main module."""
import os
import shutil

import yaml

MODEL_COMPONENTS = {
    "AWICM": ["echam", "jsbach", "hdmodel", "fesom"],
    "MPIESM": ["echam", "jsbach", "hdmodel", "mpiom"],
    "COSMOS": ["echam", "jsbach,", "hdmodel", "mpiom"],
    "PISM_STANDALONE": ["pism"],
}

COUPLED_SETUPS = {"awicm pism_standalone": ["awicm", "pism_standalone"]}


def read_simulation_config(config_file):
    """
    Reads a simulation monitoring file and returns a parsed dictionary.

    Parameters:
    -----------
    config_file : str
        Which file to read to set up the simulation monitoring
    """
    config_dir = os.environ.get("HOME") + "/.config/monitoring/"

    if not os.path.isdir(config_dir):
        os.makedirs(config_dir)

    if os.path.isfile(config_file):
        if not os.path.isfile(config_dir+config_file+".yaml"):
            shutil.copyfile(config_file, config_dir+os.path.basename(config_file)+".yaml")
    elif os.path.isfile(config_dir+config_file+".yaml"):
        config_file = config_dir+config_file+".yaml"

    with open(config_file) as cfg:
        sim_monitoring_dict = yaml.load(cfg, Loader=yaml.FullLoader)

    return sim_monitoring_dict
