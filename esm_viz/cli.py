#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""Console script for esm_viz."""

import os
import sys

# This could be prettier and sorted. but whatever
sys.path.append("..")
import inspect
import logging
import datetime
import time

# First thing before any pf the specific modules are imported, set up a working
# mpl backend:
import matplotlib

matplotlib.use("AGG")


import click
from crontab import CronTab


# For nbconvert programatically:
# import nbconvert
# import nbformat
# from nbconvert.preprocessors import ExecutePreprocessor
import importlib
import panel as pn

import esm_viz
from .deployment import Simulation_Monitor
from .esm_viz import read_simulation_config, MODEL_COMPONENTS, get_bindir
from .visualization import general

module_path = os.path.dirname(inspect.getfile(esm_viz))


def autocomplete_yamls(ctx, args, incomplete):
    flist = []
    for f in os.listdir(os.environ.get("HOME") + ".config/monitoring"):
        if f.endswith(".yaml"):
            flist.append(f)
    return flist


@click.group(invoke_without_command=True)
@click.version_option()
@click.pass_context
@click.option(
    "--expid", default="example", help="The YAML file found in ~/.config/monitoring"
)
@click.option(
    "--frequency",
    default=2,
    help="How often to run monitoring for this experiment (Default is every 2 hours)",
)
@click.option("--quiet", default=False, is_flag=True)
def main(ctx, expid, frequency, quiet):
    if ctx.invoked_subcommand is None:
        click.echo("Scheduling...")
        ctx.invoke(schedule, expid=expid, frequency=frequency)
        click.echo("Deploying...")
        ctx.invoke(deploy, expid=expid, quiet=quiet)
        click.echo("Combining...")
        ctx.invoke(combine, expid=expid, quiet=quiet)


@main.command()
@click.option(
    "--expid", default="example", help="The YAML file found in ~/.config/monitoring"
)
@click.option(
    "--frequency",
    default=2,
    help="How often to run monitoring for this experiment (Default is every 2 hours)",
)
def schedule(expid, frequency):
    """
    Schedule a job for automatic monitoring

    Parameters
    ----------
    expid : str
        The experiment that will be monitored
    frequency : int
        How often to monitor your job (in hours, minimum is 1)
    """
    cron = CronTab(user=True)
    job = cron.new(
        command="esm_viz deploy --expid "
        + expid
        + " && esm_viz combine --expid "
        + expid,
        comment="Monitoring for " + expid,
    )
    job.env["PATH"] = get_bindir() + ":" + os.environ["PATH"]
    job.every(frequency).hours()
    if job.is_valid():
        job.enable()
        cron.write()
        click.echo(
            "Successfully scheduled automatic monitoring of %s every %s hours"
            % (expid, frequency)
        )


@main.command()
@click.option("--quiet", default=False, is_flag=True)
@click.argument(
    "expid", type=click.STRING, autocompletion=autocomplete_yamls, default="example"
)
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

    config = read_simulation_config(expid)

    monitor = Simulation_Monitor(
        config.get("user"),
        config.get("host"),
        config.get("basedir"),
        config.get("coupling", False),
        config.get("storagedir"),
        config.get("required_modules", ["anaconda3", "cdo"]),
    )

    analysis_script_path = module_path + "/analysis"

    for component in MODEL_COMPONENTS.get(config["model"]):
        if component in config:
            for monitoring_part in [
                "Global Timeseries",
                "Global Climatology",
                "Timeseries",
            ]:
                monitoring_part_script_string = monitoring_part.replace(
                    " ", "_"
                ).lower()
                if monitoring_part in config[component]:
                    # In YAML, the variable vairable_container comes back as a
                    # dictionary, so we need to unpack a bit:
                    #
                    # FIXME: This is all very echam specific right now...
                    for variable in config[component][monitoring_part]:
                        container = config[component][monitoring_part][variable]
                        logging.debug(container)
                        file_pattern = container["file pattern"]
                        args = [variable, file_pattern]
                        if "analysis script" in container:
                            specialized_script = container["analysis script"][0]
                            if len(container["analysis script"]) > 1:
                                args = args + container["analysis script"][1:]
                            if os.path.isfile(specialized_script):
                                script_to_run = specialized_script
                        else:
                            script_to_run = (
                                analysis_script_path
                                + "/"
                                + component
                                + "/monitoring_"
                                + component
                                + "_"
                                + monitoring_part_script_string
                                + ".sh"
                            )
                        if not os.path.isfile(script_to_run):
                            logging.error(
                                "The analysis script you want to copy to the computer server does not exist!"
                            )
                            logging.error("It was %s", script_to_run)
                            sys.exit(1)
                        monitor.copy_analysis_script_for_component(
                            component, script_to_run
                        )
                        monitor.run_analysis_script_for_component(
                            component, script_to_run, args
                        )
                        monitor.copy_results_from_analysis_script(
                            component, variable, monitoring_part
                        )
                        # Sleep for 1 second to avoid timeout errors:
                        time.sleep(1)
            for monitoring_part in ["Special Timeseries"]:
                if monitoring_part in config[component]:
                    for special_timeseries in config[component][monitoring_part]:
                        # Did the user give a full path?
                        if "script" in special_timeseries:
                            if os.path.isfile(special_timeseries.get("script")):
                                special_timeseries_script = special_timeseries.get(
                                    "script"
                                )
                        else:  # we assume its in the analysis/component directory
                            special_timeseries_script = (
                                analysis_script_path
                                + "/"
                                + component
                                + "/monitoring_"
                                + component
                                + "_"
                                + monitoring_part.replace(" ", "_").lower()
                                + ".py"
                            )
                        # Did we get args?
                        if "args" in special_timeseries:
                            special_timeseries_args = special_timeseries.get("args")
                        else:
                            special_timeseries_args = []
                        monitor.copy_analysis_script_for_component(
                            component, special_timeseries_script
                        )
                        monitor.run_analysis_script_for_component(
                            component,
                            special_timeseries_script,
                            special_timeseries_args,
                        )


@main.command()
@click.option("--quiet", default=False, is_flag=True)
@click.option(
    "--expid", default="example", help="The YAML file found in ~/.config/monitoring"
)
def combine(expid, quiet):
    if not os.path.isdir(os.path.join(os.environ.get("HOME"), "public_html")):
        os.makedirs(os.path.join(os.environ.get("HOME"), "public_html"))
    if quiet:
        logging.basicConfig(level=logging.ERROR)
    else:
        logging.basicConfig(level=logging.INFO)
    config = read_simulation_config(
        os.environ.get("HOME") + "/.config/monitoring/" + expid + ".yaml"
    )

    tab_list = []
    if "general" in config:
        logging.info("Setting up general monitoring")
        general_mon = general.GeneralPanel.from_config(config)
        pane = general_mon.render_pane(config)
        tab_list.append(("General", pane))
    for component in MODEL_COMPONENTS.get(config["model"]):
        if component in config:
            logging.info("Setting up monitoring for %s", component)
            module_for_component = importlib.import_module(
                "esm_viz.visualization." + component
            )
            Panel_for_component = getattr(
                module_for_component, component.capitalize() + "Panel"
            )
            comp_mod = Panel_for_component.from_config(config)
            tab_list.append((component.capitalize(), comp_mod.render_pane(config)))
    heading = pn.pane.Markdown("# Monitoring: " + config.get("basedir").split("/")[-1])
    footing = pn.pane.Markdown(
        "Last update of your monitoring was %s."
        % datetime.datetime.now().strftime("%c")
    )
    # Figure out when the next update will be:
    # cron = CronTab(user=True)

    recognition = pn.pane.Markdown("This is `esm-viz`, developed by Dr. Paul Gierz.")
    my_mon = pn.Column(heading, pn.Tabs(*tab_list), footing, recognition)
    my_mon.save(
        os.path.join(
            os.environ.get("HOME"),
            "public_html",
            config.get("basedir").split("/")[-1] + ".html",
        )
    )


@main.command()
def template():
    click.echo(
        "Hi, this is the template command. It's being built, please be patient and pet the owl."
    )


@main.command()
def configure():
    click.echo(
        "Hi, this is the configure command. It's being built, please be patient and pet the owl."
    )
    return
    config_dir = os.environ["HOME"] + "./config/monitoring"
    if not os.path.isdir(config_dir):
        os.makedirs(config_dir)
    if not os.path.isfile("known_supercomputers.yaml"):
        known_computers = {}
        print(known_computers)
        # Not yet done....


@click.option("--expid", default="example", help="The experiment ID you wish to edit")
@main.command()
def edit(expid):
    """Opens the YAML config for ``expid`` in your $EDITOR"""
    click.edit(
        filename=os.environ.get("HOME") + "/.config/monitoring/" + expid + ".yaml"
    )


@main.command()
@click.option("--debug", default=False, is_flag=True)
def show_paths(debug):
    click.echo("A small utility to show where the esm_viz binary is")
    click.echo("Code is here: %s" % module_path)

    if debug:
        logging.basicConfig(level=logging.DEBUG)
    else:
        logging.basicConfig(level=logging.INFO)
    bin_dir = get_bindir(debug=debug)
    click.echo("Bin could be here: %s" % os.path.normpath(os.path.join(bin_dir)))


if __name__ == "__main__":
    sys.exit(main())  # pragma: no cover
