# -*- coding: utf-8 -*-
"""Main module."""
import inspect
import logging
import os
import shutil

import esm_viz
import yaml

MODEL_COMPONENTS = {
    "AWICM": ["echam", "jsbach", "hdmodel", "fesom"],
    "MPIESM": ["echam", "jsbach", "hdmodel", "mpiom"],
    "COSMOS": ["echam", "jsbach,", "hdmodel", "mpiom"],
    "AWICM_PISM": ["echam", "jsbach", "hdmodel", "fesom", "pism"],
    "PISM_STANDALONE": ["pism"],
}

COUPLED_SETUPS = {"awicm pism_standalone": ["awicm", "pism_standalone"]}


module_path = os.path.dirname(inspect.getfile(esm_viz))


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


def walk_up(bottom):
    """
    mimic os.walk, but walk 'up' instead of down the directory tree

    Parameters
    ----------
    bottom: str
        Where to start walking up from

    Yields
    ------
    Tuple of (bottom, dirs, nondirs)
    """
    bottom = os.path.realpath(bottom)

    # Get files in current dir
    try:
        names = os.listdir(bottom)
    except Exception as e:
        print(e)
        return

    dirs, nondirs = [], []
    for name in names:
        if os.path.isdir(os.path.join(bottom, name)):
            dirs.append(name)
        else:
            nondirs.append(name)
    yield bottom, dirs, nondirs

    new_path = os.path.realpath(os.path.join(bottom, ".."))

    # See if we are at the top
    if new_path == bottom:
        return

    for x in walk_up(new_path):
        yield x


def get_bindir(debug=False):
    bin_dir = None

    PATH = os.environ.get("PATH").split(":")
    for path_dir in PATH:
        logging.debug("Checking %s", path_dir)
        logging.debug("%s is a dir? %s", path_dir, os.path.isdir(path_dir))
        if os.path.isdir(path_dir) and "esm_viz" in os.listdir(path_dir):
            logging.debug("Found esm_viz in %s", path_dir)
            bin_dir = path_dir
            break

    if not bin_dir:
        for root, dirs, files in walk_up(module_path):
            if "bin" in dirs:
                new_root = root
                break

        for root, dirs, files in os.walk(new_root):
            if "esm_viz" in files:
                bin_dir = root
                break
    return bin_dir
