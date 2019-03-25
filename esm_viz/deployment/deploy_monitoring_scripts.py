#!/bin/python
"""
This script reads a "namelist", since Chris really, really wanted one. It then
deploys a series of analysis scripts to a remote host, and combines several
jupyter notebooks together to achieve a monitoring system for any
particular experiment.

Note: ESM-style directory structures are assumed. Otherwise, I'm just at a
loss...

Dr. Paul Gierz
March 2019
"""
import logging
import os
import sys

import paramiko
import yaml

__author__ = "Dr. Paul Gierz"
__version__ = "0.1.0"  # FIXME: Bump this to 1.0.0 once it works


def read_json_simulation_config(config_file):
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


def rexists(sftp, path):
    """os.path.exists for paramiko's SCP object"""
    try:
        sftp.stat(path)
    except IOError as error:
        if error[0] == 2:
            return False
        raise
    else:
        return True


class Simulation_Monitor(object):
    """
    ``Simulation_Monitor`` can deploy and run simulation monitoring scripts.

    The golden idea here is to automatically deploy certain scripts to a
    production machine, and run them with some (ideally useful) arguments. In
    principle, we need two methods for this:

    1. something that copies the script
    1. something that runs the script.

    Methods
    -------
    + copy_analysis_script_for_component : Copies a specified analysis script to a folder EXPBASE/analysis/<component>
    + run_analysis_script_for_component : Runs an analysis script with a passed set of arguments.
    """
    def __init__(self, user, host, basedir):
        """
        Initializes a new monitoring object.

        Attributes
        ----------
        basedir : str
            The directory where the experiment is running. Should point to the top of the experiment
        host : str
            The compute host
        user : str
            The username
        ssh : paramiko.SSHClient
            A ssh client which you can use to connect to the host (maybe this should be automatically connected
        """
        self.basedir = basedir
        self.host = host
        self.user = user
        self.ssh = paramiko.SSHClient()
        self.ssh.load_system_host_keys()
        if not self._can_login_to_host_without_password():
            with open(os.environ["HOME"]+"/simulation_monitoring_errors", "a") as error_file:
                error_file.write("Hey, you should setup ssh keys for %s. Try using esm-viz/deployment/generate_automatic_ssh_key.sh" % host)
                error_file.write("Cowardly refusing to do anything until you get your keys figured out. Goodbye.")
                logging.error("Hey, you can't log on to this computer: %s. Set up your keys!!! See also the error message in your home folder!", self.host)
                sys.exit()

    def _can_login_to_host_without_password(self):
        """
        Tries to figure out if you can log into the host without a password.

        Returns
        -------
        bool
            ``True`` if you can log in to the instance's ``host`` without a
            password. Otherwise, ``False``.
        """
        try:
            self.ssh.connect(self.host, username=self.user)
            return True
        # Maybe we really just need a general except here...
        except paramiko.ssh_exception.AuthenticationException:
            return False

    def copy_analysis_script_for_component(self, component, analysis_script):
        """
        Copies a specific analysis script to the correct folder.

        Parameters:
        -----------
        component : str
            The component that will be automatically monitored
        analysis_script : str
            The script that will automatically analyze this component
        """
        with self.ssh.open_sftp() as sftp:
            remote_analysis_script_directory = self.basedir + "/analysis/" + component
            if not rexists(sftp, remote_analysis_script_directory):
                sftp.mkdir(remote_analysis_script_directory)
            sftp.put(analysis_script, remote_analysis_script_directory+"/"+os.path.basename(analysis_script))


MODEL_COMPONENTS = {
    "AWICM": ["echam", "jsbach", "hdmodel", "fesom",],
    "MPIESM": ["echam", "jsbach", "hdmodel", "mpiom",],
    "COSMOS": ["echam", "jsbach,", "hdmodel", "mpiom",],
    "PISM": ["pism",],
    }


if __name__ == "__main__":
    config = read_json_simulation_config(os.environ.get("HOME")+"/.config/monitoring/example.yaml")
    monitor = Simulation_Monitor(config['user'], config['host'], config['basedir']) 
    for component in MODEL_COMPONENTS.get(config["model"]):
        if component in config:
            if "Global Timeseries" in config[component]:
                # TODO: The analysis script here should point to something
                # actually useful...
                monitor.copy_analysis_script_for_component(
                    component,
                    "/home/csys/pgierz/esm-viz/README.md")