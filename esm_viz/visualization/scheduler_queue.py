"""
Deals with queues
"""
import getpass
import logging
import os
import sys

import paramiko
import pandas as pd

from esm_viz.deployment import generate_keypair, deploy_keypair



PBS_QUEUE_COMMAND = r"qstat -l"

class RemoteMixin(object):
    """
    A mixin class used for adding remote execution functionality
    """
    def __init__(
        self,
        user,
        host,
        use_password=False,
    ):
        """
        Initializes a new monitoring object.

        Class documentation is shown above.
        """
        self.host = host
        self.user = user

        self.ssh = paramiko.SSHClient()
        self.ssh.load_system_host_keys()
        self.ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        self._using_esm_viz_key = False
        self._use_password = use_password

        if not self._use_password:
            if not self._can_login_to_host_without_password():
                priv_file = os.path.join(
                    os.environ.get("HOME"),
                    ".config",
                    "esm_viz",
                    "keys",
                    "%s_%s" % (user, host),
                )
                if not os.path.isfile(priv_file):
                    generate_keypair(self.user, self.host)
                    self.pkey = deploy_keypair(self.user, self.host)
                else:
                    self.pkey = priv_file
                self._using_esm_viz_key = True
                logging.info("Using esm_viz specific keys")
            else:
                logging.info("You can already log in without a password")
        else:
            logging.info("You will be prompted for your password!")

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
            actual_pkey = paramiko.RSAKey.from_private_key_file(self.pkey)
            self.ssh.connect(self.host, username=self.user, pkey=actual_pkey)
            del actual_pkey  # PG: Might be safe. Dunno. I'm not a network expert.
        elif self._use_password:
            rpass = getpass.getpass(
                prompt="Password for %s@%s: " % (self.user, self.host)
            )
            self.ssh.connect(self.host, username=self.user, password=rpass)
            del rpass
        else:
            self.ssh.connect(self.host, username=self.user)

    def __enter__(self):
        self._connect()
        return self.ssh

    def __exit__(self, exception_type, exception_value, traceback):
        self.ssh.close()

    def remote_command(self, command):
        with self as ssh:
            stdin, stdout, stderr = ssh.exec_command(command)
            try:
                stdin = stdin.readlines()
            except:
                stdin = None
            try:
                stdout = stdout.readlines()
            except:
                stdout = None
            try:
                stderr = stderr.readlines()
            except:
                stderr = None
        return (stdin, stdout, stderr)

def subprocess_wrapper(command):
    completed_process = subprocess.run(command, capture_output=True)
    return command, completed_process.stdout, completed_process.stderr

class Queue(object):
    seperator = None
    command_executor = subprocess_wrapper
    queue_command = None

    def get_queue_status(self):
        stdin, stdout, stderr = self.command_executor(self.queue_command)
        queue_status = [l.split(self.seperator) for l in stdout]
        return queue_status

    def to_dataframe(self):
        queue_status = self.get_queue_status()
        headers = queue_status[0]
        if len(queue_status) > 1:
            data = queue_status[1:]
        else:
            data = None
        return pd.DataFrame(data=data, columns=headers)


class SlurmQueue(Queue):
    queue_command = "squeue -o %all"
    seperator = "|"


class RemoteSlurmQueue(RemoteMixin, SlurmQueue):
    command_executor = RemoteMixin.remote_command

