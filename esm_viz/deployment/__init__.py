#!/bin/python
"""
The deployment submodule contain functionality to log in to a remote supercomputer, run analysis jobs, and copy back the results.

This portion of the package contains the following pieces:

    + a class to contain deployment infrastructure; copying analysis scripts to
      the other computer and running them
    + Some helper function do deal with paramiko remote paths easily.

.. note::

     ESM-style directory structures are assumed.
     
The following functions are defined here:

``rexists``
    A remote path exists check
    
``mkdir_p``
    A remote version of recursive directory creation

The following classes are defined here:

``Simulation_Monitor``
    An object to deploy, run, and copy results on a supercomputer.

Specific documentation is shown below


-------
"""
import logging
import os
import sys

import paramiko

from esm_viz import esm_viz

__author__ = "Danek, Gierz, Stepanek"
__version__ = "0.1.0" 


def rexists(sftp, path):
    """
    os.path.exists for paramiko's SCP object
    
    Parameters
    ----------
    sftp : :class:`paramiko.sftp_client.SFTPClient`
        The SFTP connection to use
    path: :class:`str`
        The remote filesystem path that should be checked
        
    Returns
    -------
    :class:`bool`
        ``True`` if the remote path exists; ``False`` otherwise.
    """
    try:
        sftp.stat(path)
        return True
    except FileNotFoundError:
        return False

def mkdir_p(sftp, remote_directory):
    """
    Change to this directory, recursively making new folders if needed.
    Returns True if any folders were created.
    
    This uses recursion. We split up the directory 
    
    Parameters
    ----------
    sftp : :class:`paramiko.sftp_client.SFTPClient`
        The Paramiko SFTP connection to use
    remote_directory : :class:`str`
        The remote directory to create
        
    Returns
    -------
    :class:`bool`
        ``True`` if remote directories needed to be made
    """
    if remote_directory == '/':
        # absolute path so change directory to root
        sftp.chdir('/')
        return
    if remote_directory == '':
        # top-level relative directory must exist
        return
    try:
        sftp.chdir(remote_directory) # sub-directory exists
    except IOError:
        dirname, basename = os.path.split(remote_directory.rstrip('/'))
        mkdir_p(sftp, dirname) # make parent directories
        sftp.mkdir(basename) # sub-directory missing, so created it
        sftp.chdir(basename)
        return True

class Simulation_Monitor(object):
    """
    ``Simulation_Monitor`` can deploy and run simulation monitoring scripts.

    The idea here is to automatically deploy certain scripts to a
    production machine, run them with some arguments, and copy the results
    to the local machine. In principle, we need three methods for this:

    #. something that copies the script
    #. something that runs the script.
    #. something that copies the results back to this computer.

    These are defined here:
    """
    def __init__(self, user, host, basedir, coupling, storage_prefix):
        """
        Initializes a new monitoring object.

        Parameters
        ----------
        user : :class:`str`
            The username you will use to connect to the computing host
        host : :class:`str`
            The machine name you will connect to
        basedir : :class:`str`
            The base directory of the experiment you will monitory
        coupling : :class:`str` or :class:`bool`
            A string denoting which iteratively coupled setup is being
            monitored, or ``False``
        storage_prefix : :class:`str`
            A string pointing to where results should be stored on the local computer

        Attributes
        ----------
        basedir : :class:`str`
            The directory where the experiment is running. Should point to the
            top of the experiment
        host : :class:`str`
            The compute host
        user : :class:`str`
            The username
        ssh : :class:`paramiko.client.SSHClient`
            A ssh client which you can use to connect to the host (maybe this
            should be automatically connected)
        storagedir : :class:`str`
            The location where analyzed data should be stored on this computer
            after copying
        """
        self.basedir = basedir
        self.host = host
        self.user = user
        self.coupling_setup = coupling

        self.storagedir = "/".join(storage_prefix.split("/") + basedir.split("/")[1+basedir.split("/").index(self.user):])

        self.ssh = paramiko.SSHClient()
        self.ssh.load_system_host_keys()
        self.ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
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
        :class:`bool`
            ``True`` if you can log in to the instance's ``host`` without a
            password. Otherwise, ``False``.
        """
        try:
            self.ssh.connect(self.host, username=self.user)
            self.ssh.close()
            return True
        except paramiko.ssh_exception.AuthenticationException:
            return False

    def _determine_this_setup(self, component):
        """
        This determines which setup a particular component belongs to in
        iteratively coupled experiments.

        Using the attribute ``self.coupling_setup``; we check which of the
        setups ``component`` belongs to. A key assumption isn't that you aren't
        coupling something that contains the same component twice.

        Parameters
        ----------
        component : :class:`str`
            The component to look for in ``self.coupling_setup``

        Returns
        -------
        :class:`str`
            The setup for ``component``
        """
        logging.info("Determing what model %s belongs to", component)
        for setup in esm_viz.COUPLED_SETUPS[self.coupling_setup]:
            logging.info("Checking %s", setup)
            for components_in_setup in esm_viz.MODEL_COMPONENTS[setup.upper()]:
                logging.info("It has %s", components_in_setup)
                if component == components_in_setup:
                    return setup


    def _determine_remote_analysis_dir(self, component):
        """
        Finds out where the analysis directory is on the computing host

        Given a component; uses ``self.coupling_setup`` information to figure
        out where the analysis directory should be located.

        Parameters
        ----------
        component : :class:`str`
            The component to look for

        Returns
        -------
        :class:`str`
            The location of the remote analysis directory
        """
        if self.coupling_setup:
            # FIXME: This is specific to Dirk's version of esm-tools...
            this_setup = self._determine_this_setup(component)
            return self.basedir + "/" + this_setup + "/analysis/" + component
        else:
            return self.basedir + "/analysis/" + component

    def copy_analysis_script_for_component(self, component, analysis_script):
        """
        Copies a specified analysis script to a folder ``${EXPBASE}/analysis/<component>``
        
        Example:
        --------
            Let's assume you've initialized a ``Simulation_Monitor`` object like this:
        
            >>> monitor = Simulation_Monitor(
                    user='pgierz',
                    host='ollie1.awi.de',
                    basedir='/work/ollie/pgierz/AWICM/PI',
                    coupling=False,
                    storage_prefix='/scratch/work/pgierz'
                    )
        
            Given a ``component``, e.g. ``echam``, and an ``analysis_script``, e.g. 
            ``/home/csys/pgierz/example_script.sh``, this method would do the following:
        
            >>> monitor.copy_analysis_script_for_component(
                    'echam',
                    '/home/csys/pgierz/example_script.sh'
                    )
            The analysis script will be copied to: /work/ollie/pgierz/AWICM/PI/analysis/echam/example_script.sh
            Copying: 
                /home/csys/pgierz/example_script 
            to 
                pgierz@ollie1.awi.de:/work/ollie/pgierz/AWICM/PI/analysis/echam/     
            Ensuring script is executable...
                chmod 755 /work/ollie/pgierz/AWICM/PI/analysis/echam/example_script.sh
            Done!
            
        .. note::
            
            The copying is only performed if the script is not already there!
        
        Parameters:
        -----------
        component : :class:`str`
            The component that will be automatically monitored
        analysis_script : :class:`str`
            The script that will automatically analyze this component
        """
        self.ssh.connect(self.host, username=self.user)
        with self.ssh.open_sftp() as sftp:
            remote_analysis_script_directory = self._determine_remote_analysis_dir(component)
            remote_script = remote_analysis_script_directory + "/" + os.path.basename(analysis_script)
            logging.info("The analysis script will be copied to: %s", remote_script)
            if not rexists(sftp, remote_analysis_script_directory):
                mkdir_p(sftp, remote_analysis_script_directory)
            if not rexists(sftp, remote_script):
                logging.info(
                        "Copying \n\t%s \nto \n\t%s",
                        os.path.basename(analysis_script),
                        remote_analysis_script_directory
                        )
                sftp.put(
                        analysis_script,
                        remote_script
                        )
            # TODO: A check here if the script is already executable
            logging.info("Ensuring script is executable...")
            logging.info("\t chmod 755 %s", remote_script)
            sftp.chmod(remote_script, 0o755)
            logging.debug(sftp.stat(remote_script))
        self.ssh.close()
        logging.info("Done!")

    def run_analysis_script_for_component(self, component, analysis_script, args=[]):
        """
        Runs a script with arguments for a specific component

        Parameters:
        -----------
        component : :class:`str`
            Which component to run scripts for
        analysis_script : :class:`str`
            Which script to run
        args : :class:`list`
            A list of strings for the arguments. If the arguments need flags,
            they should get ``'-<FLAG NAME>'`` as one of the strings. The default
            is to assume no arguments are needed.
        """
        # Ensure that analysis_script is a basename and not a full path:
        analysis_script = os.path.basename(analysis_script)
        remote_analysis_script_directory = self._determine_remote_analysis_dir(component)
        self.ssh.connect(self.host, username=self.user)
        logging.info("Executing %s...", analysis_script)
        self.ssh.invoke_shell()
        args = [arg.replace("$", "\$").replace("{", "\{").replace("}", "\}") for arg in args]
        logging.info("With arguments %s...", args)
        
        stdin, stdout, stderr = self.ssh.exec_command("bash -l -c 'cd "+remote_analysis_script_directory+"; "+" ".join(["./"+analysis_script] + args + ["'"]),
                get_pty=True)
        for stream, tag in zip([stdin, stdout, stderr], ["stdin", "stdout", "stderr"]):
            try:
                logging.info(tag)
                for line in stream.readlines():
                    logging.info(line)
            except OSError:
                logging.info("Couldn't open %s", tag)
        self.ssh.close()

    def copy_results_from_analysis_script(self, component, variable, tag, copy_running_means=True):
        """
        Copies results from an analysis script back to this computer

        Parameters:
        -----------
        component : :class:`str`
            The component to be copied from
        variable : :class:`str`
            The variable name to look for
        tag : :class:`str`
            A unique tag to label the data. The remote file uses this to built
            it's filename. The default construction of the remote filename
            looks like this: ``${EXP_ID}_${component}_${variable}_${tag}.nc``
        copy_running_means : :class:`bool`
            Default is True. If set; a second file is also copied with
            ``_runmean30.nc`` at the end.
        """
        fname = self.basedir.split("/")[-1]+"_"+component+"_"+variable+"_"+tag.lower().replace(" ", "_")+".nc"
        destination_dir = self.storagedir+"/analysis/"+component
        if not os.path.exists(destination_dir):
            os.makedirs(destination_dir)
        self.ssh.connect(self.host, username=self.user)
        with self.ssh.open_sftp() as sftp:
            remote_analysis_script_directory = self._determine_remote_analysis_dir(component)
            lfile = destination_dir + "/" + fname
            rfile = remote_analysis_script_directory + "/" + fname
            logging.info("Copying from %s to %s", rfile, lfile)
            sftp.get(rfile, lfile)
        self.ssh.close()
        if copy_running_means:
            send_tag = tag + "_runmean30"
            # NOTE: Set this to copy_running_means to False to avoid endless recursion...
            self.copy_results_from_analysis_script(component, variable, send_tag, copy_running_means=False)
