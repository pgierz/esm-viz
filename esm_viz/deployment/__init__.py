#!/bin/python
"""
The deployment submodule contain functionality to log in to a remote
supercomputer, run analysis jobs, and copy back the results.

This portion of the package contains the following pieces:

    + a class to contain deployment infrastructure; copying analysis scripts to
      the other computer and running them
    + Some helper function do deal with paramiko remote paths easily.

.. note::

     ESM-style directory structures are assumed.

The following classes are defined here:

``Simulation_Monitor``
    An object to deploy, run, and copy results on a supercomputer.

The following functions are defined here:

``rexists``
    A remote path exists check

``mkdir_p``
    A remote version of recursive directory creation

``get_password_for_machine``
    Asks for your remote password

``generate_keypair``
    Generates a specific key for ``esm_viz`` to use

``deploy_keypair``
    Copies the ``esm_viz`` key to the supercomputer


Specific documentation is shown below

-------
"""
import getpass
import logging
import os
import sys

import paramiko

# wat?
from esm_viz import esm_viz

# Py2 Py3 Fix: this has implications for the actual type of IO error, but...OK
try:
    FileNotFoundError
except NameError:
    FileNotFoundError = IOError


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
    if remote_directory == "/":
        # absolute path so change directory to root
        sftp.chdir("/")
        return
    if remote_directory == "":
        # top-level relative directory must exist
        return
    try:
        sftp.chdir(remote_directory)  # sub-directory exists
    except IOError:
        dirname, basename = os.path.split(remote_directory.rstrip("/"))
        mkdir_p(sftp, dirname)  # make parent directories
        sftp.mkdir(basename)  # sub-directory missing, so created it
        sftp.chdir(basename)
        return True


def get_password_for_machine(user, host):
    """
    Asks for your password

    Parameters
    ----------
    user :
        The user to ask for
    host :
        The machine to log in to

    Notes
    -----
        Uses f strings, might be Python 3 specific
    """
    print("Could not find existing public key for %s in ~/.ssh/." % host)
    print("To set up simulation monitoring for %s, I need to know your password." % host)
    print("Don't worry, it will not be stored to disk.")
    passprompt = "Please enter the password for %s@%s: " % (user, host)
    return getpass.getpass(prompt=passprompt)


def generate_keypair(user, host):
    """
    Makes a key for ``esm_viz`` to use

    Parameters
    ----------
    user :
        The user to ask for
    host :
        The machine to log in to

    Notes
    -----
        Uses f strings, might be Python 3 specific
    """
    print("Generating a specific key for esm_viz to use for %s" % host)
    priv = paramiko.RSAKey.generate(2048)
    keypath = os.path.join(
        os.environ.get("HOME"), ".config", "esm_viz", "keys", "%s_%s" % (user, host)
    )
    if not os.path.isdir(os.path.join(os.environ.get("HOME"), ".config", "esm_viz", "keys")):
        os.makedirs(os.path.join(os.environ.get("HOME"), ".config", "esm_viz", "keys"))
    # Private Key:
    priv.write_private_key_file(keypath)
    # Public Key
    pub = paramiko.RSAKey(filename=keypath)
    with open(keypath + ".pub", "w") as pub_key_file:
        pub_key_file.write("%s %s" % (pub.get_name(), pub.get_base64()))


def deploy_keypair(user, host):
    """
    Puts the ``esm_viz`` key onto the remote machine

    Parameters
    ----------
    user :
        The user to ask for
    host :
        The machine to log in to

    Notes
    -----
        Uses f strings, might be Python 3 specific

    Returns
    -------
        The public key filepath on **this** computer
    """
    priv_file = os.path.join(
        os.environ.get("HOME"), ".config", "esm_viz", "keys", "%s_%s" % (user, host)
    )
    if not os.path.isfile(priv_file):
        generate_keypair(user, host)
    client = paramiko.SSHClient()
    client.load_system_host_keys()
    # TODO: get user preference for the policy
    client.set_missing_host_key_policy(paramiko.WarningPolicy)
    remote_password = get_password_for_machine(user, host)
    client.connect(host, username=user, password=remote_password)
    sftp = client.open_sftp()
    # If HOME isn't set....oh well...
    _, stdout, _ = client.exec_command("echo $HOME")
    remote_home = stdout.readlines()[0].strip()
    known_hosts_remote = os.path.join(remote_home, ".ssh/known_hosts")
    with sftp.open(known_hosts_remote, "w") as r_known_hosts:
        with open(priv_file + ".pub", "r") as esm_viz_pub_key:
            r_known_hosts.write(esm_viz_pub_key.readlines())
    print("Deleting your password from memory...")
    del remote_password
    # Give back the path of the public key for further use:
    return priv_file + ".pub"


class Simulation_Monitor(object):
    """
    ``Simulation_Monitor`` can deploy and run simulation monitoring scripts.

    The idea here is to automatically deploy certain scripts to a
    production machine, run them with some arguments, and copy the results
    to the local machine. In principle, we need three methods for this:

    #. something that copies the script
    #. something that runs the script.
    #. something that copies the results back to this computer.

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

    def __init__(
        self, user, host, basedir, coupling, storage_prefix, required_modules=[]
    ):
        """
        Initializes a new monitoring object.

        Class documentation is shown above.
        """
        self.basedir = basedir
        self.host = host
        self.user = user
        self.coupling_setup = coupling

        self.storagedir = "/".join(
            storage_prefix.split("/")
            + basedir.split("/")[1 + basedir.split("/").index(self.user) :]
        )

        self.required_modules = required_modules

        self.ssh = paramiko.SSHClient()
        self.ssh.load_system_host_keys()
        self.ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        self._using_esm_viz_key = False
        if not self._can_login_to_host_without_password():
            generate_keypair(self.user, self.host)
            self.public_keyfile = deploy_keypair(self.user, self.host)
            self._using_esm_viz_key = True

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
        # PG: This next line probably has implications I am not considering...
        except paramiko.ssh_exception.SSHException:
            return False

    def _connect(self):
        if self._using_esm_viz_key:
            self.ssh.connect(
                self.host, user=self.user, key_filename=self.public_keyfile
            )
        else:
            self.ssh.connect(self.host, username=self.user)

    def _determine_this_setup(self, component):
        """
        This determines which setup a particular component belongs to in
        iteratively coupled experiments.

        Using the attribute ``self.coupling_setup``; we check which of the
        setups ``component`` belongs to. A key assumption is that you aren't
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
            ...     user='pgierz',
            ...     host='ollie1.awi.de',
            ...     basedir='/work/ollie/pgierz/AWICM/PI',
            ...     coupling=False,
            ...     storage_prefix='/scratch/work/pgierz'
            ...     )

            Given a ``component``, e.g. ``echam``, and an ``analysis_script``, e.g.
            ``/home/csys/pgierz/example_script.sh``, this method would do the following:

            >>> monitor.copy_analysis_script_for_component(
            ...     'echam',
            ...     '/home/csys/pgierz/example_script.sh'
            ...     )
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
        self._connect()
        with self.ssh.open_sftp() as sftp:
            remote_analysis_script_directory = self._determine_remote_analysis_dir(
                component
            )
            # FIXME: Chris wants this to be a user defined option
            remote_script = (
                remote_analysis_script_directory
                + "/"
                + os.path.basename(analysis_script)
            )
            logging.info("The analysis script will be copied to: %s", remote_script)
            # FIXME: Chris wants confirmation for this
            if not rexists(sftp, remote_analysis_script_directory):
                mkdir_p(sftp, remote_analysis_script_directory)
            if not rexists(sftp, remote_script):
                logging.info(
                    "Copying \n\t%s \nto \n\t%s",
                    os.path.basename(analysis_script),
                    remote_analysis_script_directory,
                )
                sftp.put(analysis_script, remote_script)
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
        remote_analysis_script_directory = self._determine_remote_analysis_dir(
            component
        )
        self._connect()
        logging.info("Executing %s...", analysis_script)
        self.ssh.invoke_shell()
        args = [
            arg.replace("$", "\$").replace("{", "\{").replace("}", "\}") for arg in args
        ]
        logging.info("With arguments %s...", args)
        if self.required_modules:
            logging.info("Loading modules %s...", self.required_modules)
            module_command = "module purge; module load " + " ".join(
                self.required_modules
            )
        else:
            module_command = ""
        stdin, stdout, stderr = self.ssh.exec_command(
            "bash -l -c '"
            + module_command
            + "; cd "
            + remote_analysis_script_directory
            + "; "
            + " ".join(["./" + analysis_script] + args + ["'"]),
            get_pty=True,
        )
        for stream, tag in zip([stdin, stdout, stderr], ["stdin", "stdout", "stderr"]):
            try:
                logging.info(tag)
                for line in stream.readlines():
                    logging.info(line)
            except (OSError, IOError):
                logging.info("Couldn't open %s", tag)
        self.ssh.close()

    def copy_results_from_analysis_script(self, component, variable, tag):
        """
        Copies results from an analysis script back to this computer

        Parameters:
        -----------
        component : :class:`str`
            The component to be copied from
        variable : :class:`str`
            The variable name to look for
        tag : :class:`str`
            A unique tag to label the data. The remote file uses this to build
            it's filename. The default construction of the remote filename
            looks like this: ``${EXP_ID}_${component}_${variable}_${tag}.nc``
        """
        fname = (
            self.basedir.split("/")[-1]
            + "_"
            + component
            + "_"
            + variable
            + "_"
            + tag.lower().replace(" ", "_")
            + ".nc"
        )
        destination_dir = self.storagedir + "/analysis/" + component
        if not os.path.exists(destination_dir):
            os.makedirs(destination_dir)
        self._connect()
        with self.ssh.open_sftp() as sftp:
            remote_analysis_script_directory = self._determine_remote_analysis_dir(
                component
            )
            lfile = destination_dir + "/" + fname
            rfile = remote_analysis_script_directory + "/" + fname
            logging.info("Copying from %s to %s", rfile, lfile)
            sftp.get(rfile, lfile)
        self.ssh.close()
