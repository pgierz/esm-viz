#!/usr/bin/env python
# coding: utf-8

# In[1]:


import panel as pn
import ipywidgets as widgets

# In[2]:


import matplotlib.pyplot as plt
import numpy as np


# In[3]:


# Make something that is pandas-esc:
import pandas as pd


# In[4]:


import sys

sys.path.insert(0, "../")


# In[5]:


from esm_viz.visualization.logfile import Logfile


# In[6]:


from esm_viz.visualization.general import General


# In[7]:


import esm_viz


# In[8]:


config = esm_viz.esm_viz.read_simulation_config("../examples/example.yaml")


# In[9]:


log = Logfile.from_file("/tmp/LGM_011_awicm_compute.log")


# In[10]:


general = General(
    "a270077",
    "mistral.dkrz.de",
    "/work/ba0989/a270077/AWICM_PISM/LGM_011",
    False,
    "/tmp",
    use_password=True,
)


# In[11]:


pn.Row(general.progress_bar(config, log))


# In[12]:


queue_info = ("Queue Information", general.queue_info())
run_stats = ("Run Statistics", pn.Row(log.run_stats(), log.run_gauge()))
# disk_usage = ("Disk Usage", general.plot_usage(config))
progress_bar = ("Progress Bar", general.progress_bar(config, log))
pbar = widgets.IntProgress(
    value=7,
    min=0,
    max=10,
    step=1,
    description="Loading:",
    bar_style="",  # 'success', 'info', 'warning', 'danger' or ''
    orientation="horizontal",
)
test = ("My Widget", pbar)

General_Tabs = [queue_info, run_stats, progress_bar, test]


# In[13]:


heading = pn.pane.Markdown("# Monitoring Example")
f, ax = plt.subplots(1, 1)
ax.plot(np.random.random(10))
plt.close(f)
my_mon = pn.Column(heading, pn.Tabs(("General", pn.Tabs(*General_Tabs))))


# In[20]:


my_mon.save("test.html")
