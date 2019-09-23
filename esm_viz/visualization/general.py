"""
This module contains a couple of things that might be needed in the "general"
section of an experiment montioring:

    1. queue information
    2. disk usage
    3. throughput
    4. progress bar

These do basically what they say they do, but, since we want to be explicit:

1. Functions that display the queue status for a particular machine as a pandas
   dataframe.
2. How much space you're using
3. How many runs per day you're getting
4. When you'll be done.
"""
# Python Standard Library
import datetime
import re
import os

# Third-Party Packages
from IPython.core.display import display, HTML
from IPython.display import display_html

# PG: Not sure if I like importing matplotlib so often, could probably be
# simpler..
from matplotlib import cm
from matplotlib import pyplot as plt
from matplotlib.patches import Circle, Wedge, Rectangle

import matplotlib.dates as mdates
import numpy as np
import pandas as pd
import paramiko

import panel as pn

from tqdm.auto import tqdm


# Import from this class (please let this work)
from ..deployment import Simulation_Monitor
from .logfile import Logfile

SLURM_QUEUE_COMMAND = (
    r"squeue -u `whoami` -o '%.18i %.9P %.50j %.8u %.8T %.10M  %.6D %R %Z'"
)


PBS_QUEUE_COMMAND = r"qstat -l"


BATCH_SYSTEMS = {
    "mistral.dkrz.de": SLURM_QUEUE_COMMAND,
    "ollie0.awi.de": SLURM_QUEUE_COMMAND,
    "ollie1.awi.de": SLURM_QUEUE_COMMAND,
    "juwels.fz-juelich.de": SLURM_QUEUE_COMMAND,
    "stan0.awi.de": PBS_QUEUE_COMMAND,
    "stan1.awi.de": PBS_QUEUE_COMMAND,
}


QUOTA_COMMANDS = {
    "mistral.dkrz.de": None,
    "ollie0.awi.de": "sudo quota.sh",
    "ollie1.awi.de": "sudo quota.sh",
    "juwels.fz-juelich.de": None,
    "stan0.awi.de": None,
    "stan1.awi.de": None,
}


def quota_parser_ollie(quota_output):
    """ A specialized quota parser for ollie. Has hopefully sensible error handling"""
    try:
        used = [l.split(":")[-1].strip().split(" ") for l in quota_output]
        quota_used_TB = float(used[1][0])
        quota_available_TB = float(used[1][4])
        return quota_used_TB * 10 ** 12, quota_available_TB * 10 ** 12
    # PG: I'd like to have a more general error here:
    except IndexError:
        # Something probably changed with Malte's quota program. You get
        # nothing back, twice; the "normal" behaviour also gives you back
        # a 2-element tuple.
        return (None, None)


QUOTA_PARSERS = {
    "mistral.dkrz.de": None,
    "ollie0.awi.de": quota_parser_ollie,
    "ollie1.awi.de": quota_parser_ollie,
    "juwels.fz-juelich.de": None,
    "stan0.awi.de": None,
    "stan1.awi.de": None,
}


def stripComments(code):
    code = str(code)
    return re.sub(r"(?m) *#.*\n?", "", code)


def bytes2human(n):
    symbols = ("K", "M", "G", "T", "P", "E", "Z", "Y")
    prefix = {}
    for i, s in enumerate(symbols):
        prefix[s] = 1 << (i + 1) * 10
    for s in reversed(symbols):
        if n >= prefix[s]:
            value = float(n) / prefix[s]
            return "%.3f%s" % (value, s)
    return "%sB" % n


class GeneralPanel(Simulation_Monitor):
    def render_pane(self, config, use_password=True):
        general = General.from_config(config, use_password)
        log = Logfile(general.get_log_output(config))

        General_Tabs = []
        if "queue info" in config["general"]:
            queue_info = ("Queue Information", general.queue_info())
            General_Tabs.append(queue_info)
        if "run efficiency" in config["general"]:
            run_efficiency = (
                "Run Statistics",
                pn.Row(log.run_stats(), log.run_gauge()),
            )
            General_Tabs.append(run_efficiency)
        if "disk usage" in config["general"]:
            disk_usage = ("Disk Usage", general.plot_usage(config))
            General_Tabs.append(disk_usage)
        if "simulation timeline" in config["general"]:
            pass  # NotYetImplemented
        if "progress bar" in config["general"]:
            progress_bar = ("Progress Bar", general.progress_bar(config, log))
            General_Tabs.append(progress_bar)
        if "newest log" in config["general"]:
            pass  # NotYetImplemented

        return pn.Tabs(("General", pn.Tabs(*General_Tabs)))


class General(Simulation_Monitor):
    def queue_info(self, verbose=True):
        """
        Gets Batch Scheduler queueing information

        Parameters
        ----------
        config : dict
            A dictionary containing the configuration used for your experiment,
            read from the YAML file.

        Returns
        -------
        queue_df or None : pd.DataFrame
            A DataFrame containing the queue information, or None if the queue for
            your user is empty.
        """
        queue_check_cmd = BATCH_SYSTEMS[self.host]
        self._connect()
        _, stdout, _ = self.ssh.exec_command(queue_check_cmd)
        queue_status = stdout.readlines()
        # Either we have just the header, or nothing at all, so nothing is running,
        # probably.
        if len(queue_status) <= 1:
            if verbose:
                print("No jobs running on", self.host)
            return None
        queue_status = [l.split() for l in queue_status]
        queue_df = pd.DataFrame(queue_status[1:])
        queue_df.columns = queue_status[0]
        return queue_df

    def get_log_output(self, config, esm_style=True):
        exp_path = self.basedir  # config["basedir"]
        model_name = config["model"].lower()
        self._connect()
        expid = exp_path.split("/")[-1]
        if esm_style:
            log_file = (
                exp_path + "/scripts/" + expid + "_" + model_name + "_compute.log"
            )
        else:
            log_file = exp_path + "/scripts/" + expid + ".log"
        stdin, stdout, stderr = self.ssh.exec_command("cat " + log_file)
        return stdout.readlines()

    def disk_usage(self, config):
        """
        Gets disk usage of a particular experiment, and if possible, quota
        information.

        Parameters
        ----------
        config : dict
            A dictionary containing the configuration used for your experiment,
            read from the YAML file.

        Returns
        -------
        exp_usage, total_usage, total_available : tuple of ints
            Three numbers, for the usage of your particular experiment, the total
            usage in your account or project, and the total available. The latter
            two elements default to None if they cannot be easily determined.
        """
        disk_check_command = "du -sb"
        # This part should be replaced with the self
        self._connect()
        _, stdout, _ = self.ssh.exec_command(
            "cd " + config["basedir"] + ";" + disk_check_command
        )
        currently_used_space = float(stdout.readlines()[0].strip().replace("\t", ""))
        if QUOTA_COMMANDS[config["host"]]:
            _, stdout, stderr = self.ssh.exec_command(QUOTA_COMMANDS[config["host"]])
            try:
                errors = stderr.readlines()
                # Dump module output. This is also idioitcally dangerous.
                errors = [e for e in errors if ("module" not in e.lower())]
            except:
                # Errors couldn't be read. We will idiotically assume there were
                # none. This is probably very dangerous and will bite me in the ass
                # at some point.
                errors = []
            if errors:
                print(errors)
                # There were errors; you probably can't get the whole quota
                return (currently_used_space, None, None)
            # Let's just hope this breaks loudly:
            quota_output = stdout.readlines()
            return (currently_used_space,) + QUOTA_PARSERS[config["host"]](quota_output)
        return (currently_used_space, None, None)

    def plot_usage(self, config):
        exp_usage, total_usage, total_quota = self.disk_usage(config)
        if total_usage and total_quota:
            total_free = total_quota - total_usage
            total_not_this_exp = total_usage - exp_usage
            f, ax = plt.subplots(1, 1, dpi=150, figsize=(2.5, 2.5))
            ax.pie(
                [exp_usage, total_not_this_exp, total_free],
                colors=["lightblue", "lightgray", "white"],
                labels=["This Exp", "Other Storage", "Free"],
                autopct="%1.1f%%",
                shadow=True,
                startangle=90,
                explode=(0.1, 0, 0),
                textprops={"fontsize": 5},
            )
            plt.close(f)
            return f
        else:
            return "This experiment uses %s space" % bytes2human(exp_usage)

    def progress_bar(self, config, log):
        _, throughput, _ = log.compute_throughput()

        exp = config["basedir"]
        model = config["model"].lower()
        self._connect()
        date_filename = exp.split("/")[-1] + "_" + model + ".date"
        remote_command = (
            "cd "
            + config["basedir"]
            + "/scripts/; cat "
            + date_filename
            + " |awk '{ print $1 }'"
        )
        stdin, stdout, stderr = self.ssh.exec_command(remote_command)
        # stdout is now something like 19500101
        # Assume that you get something like Y*YMMDD; so cut off the last 4 digits
        # (note that we dont know how many places the year has; so we need to cut
        # from the end)
        current_date = int(stdout.readlines()[0][:-5])

        remote_command = (
            "cd "
            + config["basedir"]
            + "/scripts/; cat "
            + date_filename
            + " |awk '{ print $2 }'"
        )
        stdin, stdout, stderr = self.ssh.exec_command(remote_command)
        current_run = int(stdout.readlines()[0])

        runscript_file = config.get("runscript", config["basedir"] + "/scripts/*run")
        # POTENTIAL BUG: These things are all very dependent on the runscript's way
        # of defining time control. It might be better to do this somehow
        # differently
        start_year = self.ssh.exec_command(
            "grep INITIAL_DATE_" + model + " " + runscript_file
        )[1].readlines()[0]
        final_year = self.ssh.exec_command(
            "grep FINAL_DATE_" + model + " " + runscript_file
        )[1].readlines()[0]
        # POTENTIAL BUG: What about people who run on monthly basis?
        run_size = self.ssh.exec_command("grep NYEAR_" + model + " " + runscript_file)[
            1
        ].readlines()[0]
        # Reformat to get just the years and run sizes
        start_year = int(start_year.split("=")[1].split("-")[0])
        final_year = int(final_year.split("=")[1].split("-")[0])
        run_size = int(stripComments(" ".join(run_size.split("=")[1].split())))

        total_number_of_runs = int((final_year - start_year) / run_size)
        years_per_day = throughput

        years_left = final_year - current_date
        days_left = years_left / years_per_day
        finishing_date = datetime.datetime.now() + datetime.timedelta(days=days_left)
        r_bar = (
            " "
            + str(current_run)
            + "/"
            + str(total_number_of_runs)
            + ", Throughput ~"
            + str(np.round(years_per_day, 2))
            + "runs/day"
        )

        pbar = tqdm(
            total=total_number_of_runs,
            desc="Done on: " + finishing_date.strftime("%d %b, %Y"),
            bar_format="{n}/|/{l_bar} " + r_bar,
        )
        pbar.update(current_run)
        return pbar


# TODO:
# def simulation_timeline(config):
#    log = get_log_output(config)
#    log_df = generate_dataframe_from_esm_logfile(log)
#    # Drop the last entry if it's start
#    if "start" in log_df.iloc[-1]["State"]:
#        end_of_log = log_df.iloc[:-1].tail(30)
#    else:
#        end_of_log = log_df.tail(30)
#    end_groups = end_of_log.groupby("Run Number")
#    f, ax = plt.subplots(1, 1, dpi=150, figsize=(15, 1.5))
#    for name, group in end_groups:
#        try:
#            bdate = group.index[0]
#            edate = group.index[1]
#        except IndexError:
#            print("Sorry, couldn't make a timeline")
#            plt.close(f)
#            return
#        edate, bdate = [mdates.date2num(item) for item in (edate, bdate)]
#        # The color is the same as the progressbar below, use the colormeter to figure it out.
#        ax.barh(
#            0,
#            edate - bdate,
#            left=bdate,
#            height=0.2,
#            color=(217.0 / 255.0, 83.0 / 255.0, 79.0 / 255.0),
#            edgecolor="black",
#        )
#    ax.set_ylim(-0.5, 0.5)
#    for direction in ["top", "left", "right"]:
#        ax.spines[direction].set_visible(False)
#    ax.yaxis.set_visible(False)
#    ax.xaxis_date()
#    ax.xaxis.set_major_formatter(mdates.DateFormatter("%H:%M %d.%m.%y"))
