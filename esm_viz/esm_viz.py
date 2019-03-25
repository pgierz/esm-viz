# -*- coding: utf-8 -*-
"""Main module."""

import yaml

MODEL_COMPONENTS = {
    "AWICM": ["echam", "jsbach", "hdmodel", "fesom",],
    "MPIESM": ["echam", "jsbach", "hdmodel", "mpiom",],
    "COSMOS": ["echam", "jsbach,", "hdmodel", "mpiom",],
    "PISM": ["pism",],
    }


def read_simulation_config(config_file):
    """
    Reads a simulation monitoring file and returns a parsed dictionary.

    Parameters:
    -----------
    json_file : str
        Which file to read to set up the simulation monitoring
    """
    config_file = open(config_file, 'r')
    sim_monitoring_dict = yaml.load(config_file)
    return sim_monitoring_dict
