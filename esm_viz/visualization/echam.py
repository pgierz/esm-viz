"""
This module contains tools for plotting ECHAM timeseries and climatology maps
"""

import matplotlib.pyplot as plt
import xarray as xr
import cartopy.crs as ccrs
from IPython.core.display import display, HTML

from esm_viz.visualization import get_local_storage_dir_from_config


def plot_global_timeseries(config):
    display(HTML("<h2> Global Timeseries of ECHAM </h2>"))
    file_dir =  get_local_storage_dir_from_config(config)+"/analysis/echam/"
    expid = config['basedir'].split("/")[-1]
    for variable in config['echam']['Global Timeseries']:
        ds = xr.open_dataset(file_dir+expid+"_echam_"+variable+"_global_timeseries.nc")
        plot_kwargs = {"color": "black", "lw": 0.66}
        runmean_color = 'red'
        runmean_lw = 2
        if 'plot arguments' in config['echam']['Global Timeseries'][variable]: 
            plot_kwargs.update(config['echam']['Global Timeseries'][variable]['plot arguments'])
            runmean_color = config['echam']['Global Timeseries'][variable]['plot arguments'].get('runmean color', runmean_color)
            runmean_lw = config['echam']['Global Timeseries'][variable]['plot arguments'].get('runmean lw', runmean_lw)
        f, ax = plt.subplots(dpi=150)
        ax.grid(linestyle=":", linewidth=0.33, color="gray")
        ax.plot(ds[variable].squeeze(), **plot_kwargs)
        ax.set_xlabel("Simulation Time (Years)")
        if hasattr(ds[variable], 'long_name') and hasattr(ds[variable], 'units'):
            ax.set_ylabel(ds[variable].long_name+" ("+ds[variable].units+")")
        if len(ds[variable]) >= 30:
            ax.plot(ds[variable].rolling(time=30, center=True).mean().squeeze(),
                    color=runmean_color, 
                    lw=runmean_lw)