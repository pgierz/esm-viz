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
import json
import logging
import os
import sys

import paramiko


def read_json_simulation_config(json_file):
    """
    Reads a simulation monitoring file and returns a parsed dictionary.

    Parameters:
    -----------
    json_file : str
        Which file to read to set up the simulation monitoring
    """
    sim_monitoring_dict = json.loads(json_file)
    return sim_monitoring_dict


class Simulation_Monitor(object):
    """
    A thing.

    This thing monitors similations for you. Or rather, it sets up everything.
    """
    def __init__(self, user, host, basedir):
        self.basedir = basedir
        self.host = host
        self.user = user
        self.ssh = paramiko.SSHClient()
        self.ssh.load_system_host_keys()
        if not self._can_login_to_host_without_password():
            with open(os.environ["HOME"]+"/simulation_monitoring_errors", "a") as error_file:
                error_file.write("Hey, you should setup ssh keys for %s" % host)
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
        with self.ssh.open_sftp(self.host, username=self.user) as sftp:
            remote_analysis_script_directory = self.basedir + "/analysis/" + component
            sftp.mkdir(remote_analysis_script_directory)
            sftp.put(analysis_script, remote_analysis_script_directory+"/"+ analysis_script)
