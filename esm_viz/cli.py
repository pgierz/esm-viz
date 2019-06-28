# -*- coding: utf-8 -*-

"""Console script for esm_viz."""

import os
import sys

sys.path.append("..")
import inspect
import logging

import click
from crontab import CronTab

import esm_viz
from esm_viz.deployment import Simulation_Monitor
from esm_viz.esm_viz import read_simulation_config, MODEL_COMPONENTS
from esm_viz.visualization.nbmerge import merge_notebooks

module_path = os.path.dirname(inspect.getfile(esm_viz))


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
    print(ctx, expid, frequency, quiet)
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
        command="/scratch/work/pgierz/anaconda3/bin/esm_viz deploy "
        + expid
        + "; /scratch/work/pgierz/anaconda3/bin/esm_viz combine "
        + expid,
        comment="Monitoring for " + expid,
    )
    job.hour.every(frequency)
    if job.is_valid():
        job.enable()
        cron.write()
        click.echo(
            "Successfully scheduled automatic monitoring of %s every %s hours"
            % (expid, frequency)
        )


@main.command()
@click.option("--quiet", default=False, is_flag=True)
@click.option(
    "--expid", default="example", help="The YAML file found in ~/.config/monitoring"
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

    config = read_simulation_config(
        os.environ.get("HOME") + "/.config/monitoring/" + expid + ".yaml"
    )
    monitor = Simulation_Monitor(
        config.get("user"),
        config.get("host"),
        config.get("basedir"),
        config.get("coupling", False),
        config.get("storagedir"),
    )

    analysis_script_path = module_path + "/analysis"

    for component in MODEL_COMPONENTS.get(config["model"]):
        if component in config:
            for monitoring_part in ["Global Timeseries", "Global Climatology"]:
                monitoring_part_script_string = monitoring_part.replace(
                    " ", "_"
                ).lower()
                if monitoring_part in config[component]:
                    # In YAML, the variable vairable_container comes back as a
                    # dictionary, so we need to unpack a bit:
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


@main.command()
@click.option("--quiet", default=False, is_flag=True)
@click.option(
    "--expid", default="example", help="The YAML file found in ~/.config/monitoring"
)
def combine(expid, quiet):
    if quiet:
        logging.basicConfig(level=logging.ERROR)
    else:
        logging.basicConfig(level=logging.INFO)
    config = read_simulation_config(
        os.environ.get("HOME") + "/.config/monitoring/" + expid + ".yaml"
    )
    # Remove stuff from the config that we probably won't need:
    for bad_chapter in ["user", "host", "basedir", "coupling"]:
        if bad_chapter in config:
            del config[bad_chapter]
    viz_path = module_path + "/visualization/"
    notebooks_to_merge = [viz_path + "read_config.ipynb"]
    for monitoring_element in config["general"]:
        if os.path.isfile(
            viz_path
            + "general_"
            + monitoring_element.lower().replace(" ", "_")
            + ".ipynb"
        ):
            notebooks_to_merge.append(
                viz_path
                + "general_"
                + monitoring_element.lower().replace(" ", "_")
                + ".ipynb"
            )
    for component in MODEL_COMPONENTS.get(config["model"]):
        if component in config:
            for monitoring_part in ["Global Timeseries", "Global Climatology"]:
                if monitoring_part in config[component]:
                    notebooks_to_merge.append(
                        viz_path
                        + component
                        + "_"
                        + monitoring_part.replace(" ", "_").lower()
                        + ".ipynb"
                    )
    print(notebooks_to_merge)
    with open(expid + ".ipynb", "w") as notebook_merged:
        notebook_merged.write(merge_notebooks(notebooks_to_merge))
    with open(".config_ipynb", "w") as config_file:
        config_file.write(
            " ".join(
                [
                    "test_args.py",
                    os.environ.get("HOME") + "/.config/monitoring/" + expid + ".yaml",
                ]
            )
        )
    if not quiet:
        click.echo("Combined notebook; executing and converting to HTML")
    os.system("jupyter nbconvert --execute {:s} --to html".format(expid + ".ipynb"))
    os.rename(
        expid + ".html", os.environ.get("HOME") + "/public_html/" + expid + ".html"
    )
    if not quiet:
        click.echo("Cleaning up...")
    os.remove(".config_ipynb")


@main.command()
def template():
    print(
        "Hi, this is the template command. It's being built, please be patient and pet the owl."
    )


if __name__ == "__main__":
    sys.exit(main())  # pragma: no cover
