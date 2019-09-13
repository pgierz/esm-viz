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


def yaml_to_dict(f):
    with open(f) as cfg:
        config = yaml.load(cfg, Loader=yaml.FullLoader)
    return config


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

    # User gave the a file, which might or might not be in the right directory at this point:
    if os.path.isfile(config_file):
        if not os.path.isfile(os.path.join(config_dir, os.path.basename(config_file))):
            print("Copying file to config folder")
            shutil.copyfile(config_file, config_dir + os.path.basename(config_file))
        return yaml_to_dict(config_file)
    elif os.path.isfile(os.path.join(config_dir, config_file)):
        return read_simulation_config(os.path.join(config_dir, config_file))
    else:  # Not a file, probably just experiment name
        return read_simulation_config(config_file + ".yaml")
