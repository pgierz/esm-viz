import os
import sys
sys.path.append("..")
import inspect
import logging

import click

import esm_viz
from esm_viz.deployment import Simulation_Monitor
from esm_viz.esm_viz import read_simulation_config, MODEL_COMPONENTS

module_path = os.path.dirname(inspect.getfile(esm_viz))

@click.command()
@click.option('--quiet', default=False, is_flag=True)
@click.option('--expid', default="example", help="The YAML file found in ~/.config/monitoring")
def deploy(expid, quiet):
    if quiet:
        logging.basicConfig(level=logging.ERROR)
    else:
        logging.basicConfig(level=logging.INFO)
    config = read_simulation_config(os.environ.get("HOME")+"/.config/monitoring/"+expid+".yaml")
    monitor = Simulation_Monitor(config['user'], config['host'], config['basedir'])
    analysis_script_path = module_path+"/analysis"
    for component in MODEL_COMPONENTS.get(config["model"]):
        if component in config:
            if "Global Timeseries" in config[component]:
                logging.info(analysis_script_path+"/echam/monitoring_echam_global_timeseries.sh")
                monitor.copy_analysis_script_for_component(
                    component,
                    analysis_script_path+"/echam/monitoring_echam6_temp2.sh")
                # In YAML, the variable: file_pattern comes back as a
                # dictionary, so we need to unpack a bit:
                for variable_container in config[component]['Global Timeseries']:
                    for var in variable_container:
                        variable = var
                        file_pattern = variable_container[var]
                    monitor.run_analysis_script_for_component(
                        component,
                        "monitoring_echam_global_timeseries.sh", [variable, file_pattern])

if __name__ == "__main__":
    deploy()
