"""
This module contains a couple of things that might be needed in the "general"
section of an experiment montioring:

    1. queue information
    1. disk usage
    1. throughput
    1. progress bar

Functions that display the queue status for a particular machine as a pandas dataframe.
"""

import paramiko
import pandas as pd


SLURM_QUEUE_COMMAND = r"squeue -u `whoami` -o '%.18i %.9P %.50j %.8u %.8T %.10M  %.6D %R %Z'"


PBS_QUEUE_COMMAND = r"qstat -l"


BATCH_SYSTEMS = {
    'mistral.dkrz.de': SLURM_QUEUE_COMMAND,
    'ollie0.awi.de': SLURM_QUEUE_COMMAND,
    'ollie1.awi.de': SLURM_QUEUE_COMMAND,
    'juwels.fz-juelich.de': SLURM_QUEUE_COMMAND,
    'stan0.awi.de': PBS_QUEUE_COMMAND,
    'stan1.awi.de': PBS_QUEUE_COMMAND,
    }


QUOTA_COMMANDS = {
    'mistral.dkrz.de': None,
    'ollie0.awi.de': 'sudo quota.sh',
    'ollie1.awi.de': 'sudo quota.sh',
    'juwels.fz-juelich.de': None,
    'stan0.awi.de': None,
    'stan1.awi.de': None,
        }


def queue_info(config):
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
    queue_check_cmd = BATCH_SYSTEMS[config['host']]
    ssh = paramiko.SSHClient()
    ssh.load_system_host_keys()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    ssh.connect(config['host'], username=config['user'])
    _, stdout, _ = ssh.exec_command(queue_check_cmd)
    queue_status = stdout.readlines()
    # Either we have just the header, or nothing at all, so nothing is running,
    # probably.
    if len(queue_status) <= 1:
        print('No jobs running on', config['host'])
        return None
    queue_status = [l.split() for l in queue_status]
    queue_df = pd.DataFrame(queue_status[1:])
    queue_df.columns = queue_status[0]
    return queue_df


def quota_parser_ollie(quota_output):
    """ A specialized quota parser for ollie. Has hopefully sensible error handling"""
    try:
        used = [l.split(":")[-1].strip().split(" ") for l in quota_output]
        quota_used_TB = float(used[1][0])
        quota_available_TB = float(used[1][4])
        return quota_used_TB * 10**12, quota_available_TB * 10**12
    except:
        # Something probably changed with Malte's quota program. You get
        # nothing back, twice; the "normal" behaviour also gives you back
        # a 2-element tuple.
        return (None, None)


QUOTA_PARSERS = {
    'mistral.dkrz.de': None,
    'ollie0.awi.de': quota_parser_ollie,
    'ollie1.awi.de': quota_parser_ollie,
    'juwels.fz-juelich.de': None,
    'stan0.awi.de': None,
    'stan1.awi.de': None,
        }


def disk_usage(config):
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
    ssh = paramiko.SSHClient()
    ssh.load_system_host_keys()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    ssh.connect(config['host'], username=config['user'])
    _, stdout, _ = ssh.exec_command('cd '+config['basedir']+';'+disk_check_command)
    currently_used_space = float(stdout.readlines()[0].strip().replace('\t', ''))
    if QUOTA_COMMANDS[config['host']]:
        _, stdout, stderr = ssh.exec_command(QUOTA_COMMANDS[config['host']])
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
        return (currently_used_space,) + QUOTA_PARSERS[config['host']](quota_output)
    return (currently_used_space, None, None)


def bytes2human(n):
    symbols = ('K', 'M', 'G', 'T', 'P', 'E', 'Z', 'Y')
    prefix = {}
    for i, s in enumerate(symbols):
        prefix[s] = 1 << (i+1)*10
    for s in reversed(symbols):
        if n >= prefix[s]:
            value = float(n) / prefix[s]
            return '%.3f%s' % (value, s)
    return "%sB" % n


def plot_usage(exp_usage, total_usage, total_quota):
    if total_usage and total_quota:
        total_free = total_quota - total_usage
        total_not_this_exp = total_usage - exp_usage
        f, ax = plt.subplots(1, 1, dpi=150, figsize=(2.5,2.5))
        ax.pie([exp_usage, total_not_this_exp, total_free],
               colors=["lightblue", "lightgray", "white"],
               labels=["This Exp", "Other Storage", "Free"],
               autopct='%1.1f%%', shadow=True, startangle=90,
               explode=(0.1, 0, 0), textprops={"fontsize": 5})
    else:
        print("This experiment uses %s" % bytes2human(exp_usage))

        
def get_log_output(exp_path):
    ssh = paramiko.SSHClient()
    ssh.load_system_host_keys()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    ssh.connect(config['host'], username=config['user'])
    expid = exp_path.split("/")[-1]
    stdin, stdout, stderr = ssh.exec_command('cat '+exp_path+"/scripts/"+expid+".log")
    return stdout


def generate_dataframe_from_mpimet_logfile(log):
    log_dataframe = pd.read_table(log,
                                  sep=r" :  | -" ,
                                  skiprows=1,
                                  infer_datetime_format=True,
                                  names=["Date", "Message", "State"],
                                  engine='python', index_col=0)
    middle_column = log_dataframe["Message"].apply(lambda x: pd.Series(str(x).split()))
    log_dataframe.drop("Message", axis=1, inplace=True)
    middle_column.columns = ["Run Number", "Exp Date", "Job ID"]
    log_dataframe = pd.concat([log_dataframe, middle_column], axis=1)
    log_dataframe.set_index(pd.to_datetime(log_dataframe.index), inplace=True)
    return log_dataframe