import os
import sys
sys.path.append("..")
import inspect

import click

import esm_viz
from esm_viz.deployment import Simulation_Monitor
from esm_viz.esm_viz import read_simulation_config, MODEL_COMPONENTS

module_path = os.path.dirname(inspect.getfile(esm_viz))

@click.command()
@click.option('--expid', default="example", help="The YAML file found in ~/.config/monitoring")
def deploy(expid):
    config = read_simulation_config(os.environ.get("HOME")+"/.config/monitoring/"+expid+".yaml")
    monitor = Simulation_Monitor(config['user'], config['host'], config['basedir'])
    for component in MODEL_COMPONENTS.get(config["model"]):
        if component in config:
            if "Global Timeseries" in config[component]:
                # TODO: The analysis script here should point to something
                # actually useful...
                # TODO: Here, we need some way to actually get the scripts in,
                # regardless of where this tool is installed.
                print(module_path)
                #monitor.copy_analysis_script_for_component(
                #    component,
                #    "/home/csys/pgierz/esm-viz/analysis/general/say_hello.sh")

if __name__ == "__main__":
    deploy()
