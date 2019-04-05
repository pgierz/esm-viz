# -*- coding: utf-8 -*-

"""Console script for esm_viz."""

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


@click.group()
def main(args=None):
    """Console script for esm_viz."""
    click.echo("Replace this message by putting your code into "
               "esm_viz.cli.main")
    click.echo("See click documentation at http://click.pocoo.org/")
    return 0


@main.command()
@click.option('--quiet', default=False, is_flag=True)
@click.option('--expid', default="example", help="The YAML file found in ~/.config/monitoring")
def deploy(expid, quiet):
    """
    Deploys a script to a computation host (supercompute) and runs it.

    Parameters
    ----------
    expid : str
        The experiment that will be monitored
    quiet : bool
        Turn off more verbose logging
    """
    if quiet:
        logging.basicConfig(level=logging.ERROR)
    else:
        logging.basicConfig(level=logging.INFO)

    config = read_simulation_config(
        os.environ.get("HOME")+"/.config/monitoring/"+expid+".yaml"
        )
    monitor = Simulation_Monitor(
        config.get('user'),
        config.get('host'),
        config.get('basedir'),
        config.get("coupling", False)
        )

    analysis_script_path = module_path+"/analysis"

    for component in MODEL_COMPONENTS.get(config["model"]):
        if component in config:
            if "Global Timeseries" in config[component]:
                # In YAML, the variable vairable_container comes back as a
                # dictionary, so we need to unpack a bit:
                for variable_container in config[component]['Global Timeseries']:
                    for var in variable_container:
                        variable = var
                        file_pattern = variable_container[var]
                        specialized_script = analysis_script_path+"/"+component+"/monitoring_"+component+"_global_timeseries_"+variable+".sh"
                        if os.path.isfile(specialized_script):
                            script_to_run = specialized_script
                        else:
                            script_to_run = "montoring_"+component+"_global_timeseries.sh"
                        # TODO: How to include arguments here?
                        monitor.copy_analysis_script_for_component(
                            component,
                            script_to_run
                            )
                        monitor.run_analysis_script_for_component(
                            component,
                            script_to_run,
                            [variable, file_pattern]
                            )

if __name__ == "__main__":
    sys.exit(main())  # pragma: no cover
