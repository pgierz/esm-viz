"""
This module contains a couple of things that might be needed in the "general"
section of an experiment montioring:

    1. queue information
    1. disk usage
    1. throughput
    1. progress bar

Functions that display the queue status for a particular machine as a pandas dataframe.
"""
import datetime

import paramiko
import pandas as pd

from matplotlib.patches import Circle, Wedge, Rectangle
import os, sys
import matplotlib
from matplotlib import cm
from matplotlib import pyplot as plt
import numpy as np
from IPython.display import display_html
from IPython.core.display import display, HTML


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
        display(HTML("This experiment uses %s space" % bytes2human(exp_usage))

        
def get_log_output(config, esm_style=True):
    exp_path = config['basedir']
    model_name = config['model'].lower()
    ssh = paramiko.SSHClient()
    ssh.load_system_host_keys()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    ssh.connect(config['host'], username=config['user'])
    expid = exp_path.split("/")[-1]
    if esm_style:
        log_file = exp_path+"/scripts/"+expid+"_"+model_name+"_compute.log"
    else:
        log_file = exp_path+"/scripts/"+expid+".log"
    stdin, stdout, stderr = ssh.exec_command('cat '+ log_file)
    return stdout.readlines()


def generate_dataframe_from_esm_logfile(log):
    df = pd.DataFrame([l.split(" : ") for l in log], columns=["Date", "Message"])
    df2 = df['Message'].str.split(expand=True)
    # We drop the first row since it says "Start of Experiment"
    log_df = pd.concat([df[1:]['Date'], df2[1:]], axis=1)
    log_df.columns = ["Date", "Run Number", "Exp Date", "Job ID", "Seperator", "State"]
    log_df.drop("Seperator", axis=1, inplace=True)
    log_df.set_index("Date", inplace=True)
    log_df.index = pd.to_datetime(log_df.index)
    return log_df


def generate_dataframe_from_mpimet_logfile(log):
    log_df = pd.read_table(log,
                                  sep=r" :  | -" ,
                                  skiprows=1,
                                  infer_datetime_format=True,
                                  names=["Date", "Message", "State"],
                                  engine='python', index_col=0)
    middle_column = log_df["Message"].apply(lambda x: pd.Series(str(x).split()))
    log_df.drop("Message", axis=1, inplace=True)
    middle_column.columns = ["Run Number", "Exp Date", "Job ID"]
    log_df = pd.concat([log_df, middle_column], axis=1)
    log_df.set_index(pd.to_datetime(log_df.index), inplace=True)
    return log_df


def compute_throughput(log_df):
    starts = log_df[log_df.State.str.contains("start")]
    ends = log_df[log_df.State.str.contains("done")]
    # Drop the duplicated starts:
    starts.drop_duplicates(subset="Run Number", keep="last", inplace=True)
    merged = pd.concat([starts, ends])
    groupby = merged.groupby("Run Number")
    run_diffs = {"Run Number": [], "Wall Time": [], "Queue Time": []}
    for name, group in groupby:
        if int(name) > 1:
            previous_group = groupby.get_group(str(int(name)-1))
            run_diffs["Queue Time"].append(group.index[0] - previous_group.index[-1])
        else:
            run_diffs["Queue Time"].append(datetime.timedelta(0))
        run_diffs["Run Number"].append(int(name))
        run_diffs["Wall Time"].append(group.index[-1] - group.index[0])
    diffs = pd.DataFrame(run_diffs).sort_values("Run Number").set_index("Run Number")
    DAY = datetime.timedelta(1)
    throughput = DAY / diffs.mean()
    return diffs.mean(), throughput, diffs


# Average walltime and effective number of simulated years per day:
# FIXME: What about coupling????
def compute_walltime_and_throughput(config, esm_style=True):
    # NOTE: ``exp`` is actually ``basedir``
    exp = config['basedir']
    model = config['model'].lower() 
    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    client.connect(config['host'], username=config['user'])
    stdin, stdout, stderr = client.exec_command("cd "+exp+"/scripts; grep -i \"initial_date\" *.run")
    start_year = stdout.readlines()[0].split()[0].split("=")[-1].split("-")[0]
    # This won't work for coupled experiments:
    stdin, stdout, stderr = client.exec_command("cd "+exp+"/scripts; cat *.date")
    if esm_style:
        current_year = stdout.readlines()[0].split("=")[-1].split("-")[0]
    else:
        current_year = stdout.readlines()[0].split()[0][:4]
    stdin, stdout, stderr = client.exec_command("cd "+exp+"/scripts; grep -i \"final_date\" *.run")
    final_year = stdout.readlines()[0].split()[0].split("=")[-1].split("-")[0]
    start_year = int(start_year)
    print(current_year)
    current_year = int(current_year) - start_year
    final_year = int(final_year) - start_year

    walltime, throughput, diffs = compute_effective_throughput(
        generate_dataframe_from_mpiesm_logfile(get_log_output(exps_full[0])))
    df = pd.DataFrame.from_dict({"Walltime": walltime,
                       "Throughput": throughput}, orient="index")
    return df


def simulation_timeline(log_df):
    # Drop the last entry if it's start:
    if "start" in log_df.iloc[-1]["State"]:
        end_of_log = log_df.iloc[:-1].tail(30)
    else:
        end_of_log = log_df.tail(30)
    end_groups = end_of_log.groupby("Run Number")
    f, ax = plt.subplots(1, 1, dpi=150, figsize=(15, 1.5))
    for name, group in end_groups:
        bdate = group.index[0]
        edate = group.index[1]
        edate, bdate = [mdates.date2num(item) for item in (edate, bdate)]
        # The color is the same as the progressbar below, use the colormeter to figure it out.
        ax.barh(0, edate - bdate, left=bdate, height=0.2, color=(217./255., 83./255., 79./255.),
                edgecolor="black")
    ax.set_ylim(-0.5, 0.5)
    for direction in ["top", "left", "right"]:
        ax.spines[direction].set_visible(False)
    ax.yaxis.set_visible(False)
    ax.xaxis_date()
    ax.xaxis.set_major_formatter(mdates.DateFormatter("%H:%M %d.%m.%y"))
    
def degree_range(n): 
    start = np.linspace(0,180,n+1, endpoint=True)[0:-1]
    end = np.linspace(0,180,n+1, endpoint=True)[1::]
    mid_points = start + ((end-start)/2.)
    return np.c_[start, end], mid_points

def rot_text(ang): 
    rotation = np.degrees(np.radians(ang) * np.pi / np.pi - np.radians(90))
    return rotation

def gauge(labels=['LOW','MEDIUM','HIGH','VERY HIGH','EXTREME'], \
          colors='jet_r', arrow=1, title='', fname=False): 
    
    """
    some sanity checks first
    
    """
    
    N = len(labels)
    
    if arrow > N: 
        raise Exception("\n\nThe category ({}) is greated than \
        the length\nof the labels ({})".format(arrow, N))
 
    
    """
    if colors is a string, we assume it's a matplotlib colormap
    and we discretize in N discrete colors 
    """
    
    if isinstance(colors, str):
        cmap = cm.get_cmap(colors, N)
        cmap = cmap(np.arange(N))
        colors = cmap[::-1,:].tolist()
    if isinstance(colors, list): 
        if len(colors) == N:
            colors = colors[::-1]
        else: 
            raise Exception("\n\nnumber of colors {} not equal \
            to number of categories{}\n".format(len(colors), N))

    """
    begins the plotting
    """
    
    fig, ax = plt.subplots()

    ang_range, mid_points = degree_range(N)

    labels = labels[::-1]
    
    """
    plots the sectors and the arcs
    """
    patches = []
    for ang, c in zip(ang_range, colors): 
        # sectors
        patches.append(Wedge((0.,0.), .4, *ang, facecolor='w', lw=2))
        # arcs
        patches.append(Wedge((0.,0.), .4, *ang, width=0.10, facecolor=c, lw=2, alpha=0.5))
    
    [ax.add_patch(p) for p in patches]

    
    """
    set the labels (e.g. 'LOW','MEDIUM',...)
    """

    for mid, lab in zip(mid_points, labels): 

        ax.text(0.35 * np.cos(np.radians(mid)), 0.35 * np.sin(np.radians(mid)), lab, \
            horizontalalignment='center', verticalalignment='center', fontsize=8, rotation = rot_text(mid))

    """
    set the bottom banner and the title
    """
    r = Rectangle((-0.4,-0.1),0.8,0.1, facecolor='w', lw=2)
    ax.add_patch(r)
    
    ax.text(0, -0.05, title, horizontalalignment='center', \
         verticalalignment='center', fontsize=22, fontweight='bold')

    """
    plots the arrow now
    """
    
    pos = mid_points[abs(arrow - N)]
    
    ax.arrow(0, 0, 0.225 * np.cos(np.radians(pos)), 0.225 * np.sin(np.radians(pos)), \
                 width=0.04, head_width=0.09, head_length=0.1, fc='k', ec='k')
    
    ax.add_patch(Circle((0, 0), radius=0.02, facecolor='k'))
    ax.add_patch(Circle((0, 0), radius=0.01, facecolor='w', zorder=11))

    """
    removes frame and ticks, and makes axis equal and tight
    """
    
    ax.set_frame_on(False)
    ax.axes.set_xticks([])
    ax.axes.set_yticks([])
    ax.axis('equal')
    plt.tight_layout()
    if fname:
        fig.savefig(fname, dpi=200)
    return ax

        
def find_nearest(array, value):
    array = np.asarray(array)
    idx = (np.abs(array - value)).argmin()
    return idx
        
    
def run_efficiency(config):
    log = get_log_output(config)
    log_df = generate_dataframe_from_esm_logfile(log)
    diffs = compute_throughput(log_df)[2]
    efficiency = diffs["Wall Time"].mean() / (diffs["Queue Time"].mean() + diffs["Wall Time"].mean())
    levels = np.arange(0, 105, 5)
    arrow_level = find_nearest(levels, 100*efficiency) + 1
    levels = ["%.0f" % number for number in levels]
    levels = [l+"%" for l in levels]
    ax = gauge(labels=levels, \
      colors='RdYlGn_r', arrow=arrow_level, title='Run Efficiency')
    prefix = \
"""
 <!DOCTYPE html>
<html>
<head>
<style>
* {
    box-sizing: border-box;
}

.column {
    float: left;
    width: 33.33%;
    padding: 5px;
}

/* Clearfix (clear floats) */
.row::after {
    content: "";
    clear: both;
    display: table;
}
</style>
</head>
<body>

<div class="row">
  <div class="column">
"""
    suffix = \
"""
  </div>
  <div class="column">
    <img src="pic_file.png" alt="Graph" style="width:100%">
  </div>
</div>
</body>
</html>
"""
    df = pd.DataFrame.from_dict({
        "Mean Walltime": diffs["Wall Time"].mean(),
        "Mean Queuing Time": diffs["Queue Time"].mean(),
        "Run Efficiency": efficiency*100
        }, orient='index', columns=["Run Statistics"])
    title = config['basedir'].split("/")[-1]+"_efficiency"
    fig = ax.get_figure()
    fig.savefig(os.environ.get("HOME")+"/public_html/"+title+".png", dpi=200)
    plt.close(fig)
    html = prefix.replace('title', title)+df.to_html()+suffix.replace('pic_file.png', title+".png")
    display_html(html, raw=True)
