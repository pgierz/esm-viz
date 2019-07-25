# TL;DR

If you don't like reading, here's what to do:
1. Make sure you don't have ssh password requirements anywhere
1. Write a script that minimizes your data on your compute server
1. Write a script that copies it to your analysis server
1. Write a visualization script that can export to HTML
1. Write a cronjob that executes all of the above, and moves the HTML to a folder `${HOME}/public_html`

Since you don't like reading; I'll assume you know what all of that means. If not, please read on...

- - - -

For automatic visualization of an experiment called "something", you can do this:

```shell
$ git clone https://github.com/pgierz/esm-viz
$ cd esm-viz
$ pip install --user .
$ esm_viz --version
$ esm_viz --expid=something
```

You also need a file called `something.yaml`, which should be in your `${HOME}/.config/monitoring`

Currently supported models:
+ ECHAM6
+ Custom notebooks written by the user

Still to come:
+ FESOM

Please feel free to help out!!
- - - -

While the concepts below still apply, the section above provides an improved example which works for the current implementation.

# General concepts

In the following, we refer to 3 different computers. To get a clear terminology, here is what each will be:
+ **compute server** is the machine (probably a supercomputer) where you are running simulations
+ **analysis server** is the machine where you have a way to visualize a minimized dataset in a way you think is useful
+ **web server** is a machine where you have a, well, *web server* set up. In the examples provided below, **analysis server** and **web server** are the same.

# Example

In this example, the following machines are going to be used:
+ **compute server** is `ollie1.awi.de` (or `ollie0.awi.de`, they are the same for our purposes)
+ **analysis server** and **web server** are `paleosrv1.awi.de` (in principle, you could have a different web server)

Let's say you have a simulation running on `ollie`. You want to get a periodic view of how it's doing. You might want to get a feeling for the mean climate state, how long you're sitting in the queue, *if* you are still in the queue or something has gone horribly awry, and other interesting information. How many people are using the machine?

Enter: **esm-viz** It's the tool you were looking for. Until it's 100% finished, you can follow the steps below to set up your own things:

# Tools for Simulation Monitoring

Getting a self-updating view of your simulation can be very important. It helps to:
+ Make sure everything is still running
+ Catches any errors more regularly than you would be hand
+ Gives a 'real-time' indication of throughput and queuing time, rather than hand-wavy estimates.
+ Shows the climate state equilibration in real-time

To do this, you need several tools:
1. The ability to log in to the computer where the simulation is happening without typing your password
1. Some way of maximally preprocessing the data you want to look at --> smaller files
1. Copy the data to a monitoring server for analysis
1. Make a visualization
1. Optionally, get some information about the queue to nicely display
1. Put all this together in some format that can be quickly displayed and accessed

And, of course, all of the above steps **should happen automatically**, in the background, without you needing to type out anything by hand.

- - - -

# Solving some of the overhead:

So, let's go through and try to solve some of the problems we had to make this whole thing a bit quicker and more reproducible

## Typing your password for everything

You can have the `ssh` protocol save your password and automatically send it to the other computer via so-called `ssh-keys`. Let's set that up:

```shell
ssh-keygen -t rsa
ssh `whoami`@ollie1.awi.de mkdir -p .ssh
cat ${HOME}/.ssh/id_rsa.pub | \
    ssh `whoami`@ollie1.awi.de 'cat >> .ssh/authorized_keys'
```

Some more info can be found [here](http://www.linuxproblem.org/art_9.html). Alternatively, you can use the provided [script](https://github.com/pgierz/simulation_monitoring/blob/master/generate_automatic_ssh_key.sh) to set up keys. The script will ask you questions and figure out the rest for you.

## Automate the Pre-Processing for the Analysis

Here, the answer is obvious: write a script. An example could look like this:

```bash
#!/bin/bash -e
# Set up where the directories are. If you store this script in a folder:
# ${EXP_BASE_DIR}/analysis/script everything will work automatically, also for
# different experiments. ESM-runscript style directory trees are assumed.

CURRENT_DIR=$(cd $(dirname ${BASH_SOURCE[0]}) && pwd)
EXP_BASE_DIR=$(cd $(dirname ${BASH_SOURCE[0]})/../../ && pwd)
EXP_ID=$(basename ${EXP_BASE_DIR})

OUTDATA_DIR_FESOM=${EXP_BASE_DIR}/outdata/fesom
ANALYSIS_DIR_FESOM=${EXP_BASE_DIR}/analysis/fesom

# Make sure an analysis directory exists
if [ ! -d $ANALYSIS_DIR_FESOM ]; then
        mkdir -p ${ANALYSIS_DIR_FESOM}
fi

# Remove old files if you want to recreate them (probably a good idea to keep
# monitoring up to date)
RECREATE_ANALYSIS_FILE_DURING_RUN=1
if [ ${RECREATE_ANALYSIS_FILE_DURING_RUN} == 1 ]; then
        if [ -f ${ANALYSIS_DIR_FESOM}/${EXP_ID}_tos_fesom_catted_yearmean_fldmean.nc ]; then
                rm -v ${ANALYSIS_DIR_FESOM}/${EXP_ID}_tos_fesom_catted_yearmean_fldmean.nc
        fi
fi

# Get all tos files from the outdata
cdo -f nc cat \
        ${OUTDATA_DIR_FESOM}/tos_fesom_*.nc \
        ${ANALYSIS_DIR_FESOM}/tos_fesom_catted.nc
rmlist="${ANALYSIS_DIR_FESOM}/tos_fesom_catted.nc $rmlist"

# Make a yearmean and a fldmean
cdo -f nc -fldmean -yearmean \
        ${ANALYSIS_DIR_FESOM}/tos_fesom_catted.nc \
        ${ANALYSIS_DIR_FESOM}/${EXP_ID}_tos_fesom_catted_yearmean_fldmean.nc

# Cleanup any files you might not need anymore
rm -v $rmlist
```

## Automate the Copying

It would of course be nice if we also automated the execution of this script, along with the copying this computer for visualization:

```shell
#!/bin/bash -e
remote_analysis_fesom_dir=/work/ollie/pgierz/AWICM/LGM-CTRL/analysis/fesom
remote_analysis_script_dir=/work/ollie/pgierz/AWICM/LGM-CTRL/analysis/scripts
remote_script=ANALYSIS_fesom_sst_fldmean_yearmean.sh
remote_output_file=LGM-CTRL_tos_fesom_catted_yearmean_fldmean.nc

ssh pgierz@ollie1 "cd $remote_analysis_script_dir; ./${remote_script}"
scp pgierz@ollie1:${remote_analysis_fesom_dir}/${remote_output_file} /tmp/
```

## Automate the Visualization

Here, we can use a jupyter notebook. First, we can prepare one "by hand" to make sure it has everything we want to look at. After that, there are ways to execute them directly from the command line and convert the result into an HTML page.

```shell
$ jupyter nbconvert --execute LGM_SST.ipynb
```

We can just place this at the end of the script that executes and copies the data.

## Putting this somewhere it can be easily viewed:

Almost done! We want to place this where it can easily be viewed. `paleosrv1` has a web server. You need to do the following in your home directory:

```
cd ${HOME}
mkdir public_html
chmod 755 public_html  # Very important! You can't have "secrets" here
                       # or the webserver won't display anything
```

If you copy your file here, it can now easily be viewed [in your browser](http://paleosrv1.awi.de/~pgierz/LGM_SST.html). This also belongs as part of the script above.

## Automating Everything

So far, we have gone through and made everything to preprocess data, copy it here for visualization, made a plot, and exported it to a format that can easily be viewed in a browser. We still needed to fire off the script by hand, so the very last step is to automatically do this as well. To do that, we can make a so-called `cronjob`.

You can see which jobs the computer will automatically run for you by typing `crontab -e`

```
# Edit this file to introduce tasks to be run by cron.
#
# Each task to run has to be defined through a single line
# indicating with different fields when the task will be run
# and what command to run for the task
#
# To define the time you can provide concrete values for
# minute (m), hour (h), day of month (dom), month (mon),
# and day of week (dow) or use '*' in these fields (for 'any').#
# Notice that tasks will be started based on the cron's system
# daemon's notion of time and timezones.
#
# Output of the crontab jobs (including errors) is sent through
# email to the user the crontab file belongs to (unless redirected).
#
# For example, you can run a backup of all your user accounts
# at 5 a.m every week with:
# 0 5 * * 1 tar -zcf /var/backups/home.tgz /home/
#
# For more information see the manual pages of crontab(5) and cron(8)
#
# m h  dom mon dow   command
```

To set up a command that runs every 3 hours, you can add:
```
0 */3 * * * cd /home/csys/pgierz/cronjobs/sxace/Holocene_Transient; /scratch/work/pgierz/anaconda3/bin/jupyter nbconvert --to html --execute Holocene_Transient.ipynb; mv Holocene_Transient.html /home/csys/pgierz/public_html
```

**Note** that you should probably use *absolute paths*, since otherwise the job might run into complications! I'm also not sure if line-breaks are allowed.

## How to set up a crontab:
Here's something useful: https://crontab.guru
