"""
This module contains tools for plotting ECHAM timeseries and climatology maps
"""

import matplotlib.pyplot as plt
import xarray as xr
import cartopy.crs as ccrs
import holoviews as hv
import hvplot.xarray
import geoviews as gv

import cmocean

from IPython.core.display import display, HTML

from esm_viz.visualization import get_local_storage_dir_from_config


def plot_global_timeseries(config):
    display(HTML("<h2> Global Timeseries of ECHAM </h2>"))
    file_dir =  get_local_storage_dir_from_config(config)+"/analysis/echam/"
    expid = config['basedir'].split("/")[-1]
    return_list = []
    for variable in config['echam']['Global Timeseries']:
        ds = xr.open_dataset(file_dir+expid+"_echam_"+variable+"_global_timeseries.nc")
        # Fix the time axes:
        ds['time'] = range(len(ds['time']))
        if 'use_hvplot' in config:
            o = ds[variable].squeeze().hvplot.line(title=variable)
            # Due to syntax differences, hvplot (actually Bokeh) has slightly different keywords than matplotlib.
            # Turn on the grid:
            o.options(color='black', 
                      line_width=0.66, 
                      gridstyle={
                          "grid_line_dash": 'dotted', 
                          "grid_line_color": "gray", 
                          "grid_line_width": 0.33},
                      show_grid=True,
                     clone=False)
            redim_dict = {variable: {'name': getattr(ds[variable], 'long_name', None), 'unit': getattr(ds[variable], 'units', None)},
                         'time': {'name': 'Simulation Time', 'unit': 'Years'}}
            o = o.redim(**redim_dict)
            if len(ds[variable]) >= 30:
                o_runmean = ds[variable].rolling(time=30, center=True).mean().squeeze().hvplot.line(color='red')
                o_runmean = o_runmean.redim(value = {'name': ds[variable].long_name + ": 30 year running mean",
                                                     'unit': ds[variable].units})
                return_list.append(o * o_runmean)
            else:
                return_list.append(o)
        else:
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
            return_list.append((f, ax))
    if 'use_hvplot' in config:
        return hv.Layout(return_list).cols(1)
    else:
        return return_list


def plot_global_climatology(config):
    display(HTML("<h2> Global Climatologies of ECHAM </h2>"))
    file_dir =  get_local_storage_dir_from_config(config)+"/analysis/echam/"
    expid = config['basedir'].split("/")[-1]
    return_list = []
    for variable in config['echam']['Global Climatology']:
        ds = xr.open_dataset(file_dir+expid+"_echam_"+variable+"_global_climatology.nc")
        
        # Initialize no cmap, just in case the user didn't give us one:
        user_cmap='jet'
        if 'plot arguments' in config['echam']['Global Climatology'][variable]:
            if 'cmap' in config['echam']['Global Climatology'][variable]['plot arguments']:
                user_cmap = config['echam']['Global Climatology'][variable]['plot arguments']['cmap']
                if user_cmap.startswith("cmocean."):
                    user_cmap = getattr(cmocean.cm, user_cmap.replace("cmocean.", ""))
                else:
                    user_cmap = getattr(plt.cm, user_cmap)
                # Delete the cmap to avoid double arguments in plot_kwargs if using matplotlib
                del config['echam']['Global Climatology'][variable]['plot arguments']['cmap']
    
        if 'use_hvplot' in config:
            o = ds[variable].squeeze().hvplot.quadmesh(
                    'lon',
                    'lat',
                    projection=ccrs.PlateCarree(), project=True, global_extent=True,
                    width=600, height=540, cmap=user_cmap, rasterize=True, dynamic=False)  * gv.feature.coastline
            redim_dict = {variable: {'name': getattr(ds[variable], 'long_name', None), 'unit': getattr(ds[variable], 'units', None)}}
            o = o.redim(**redim_dict)
            return_list.append(o * gv.feature.coastline)
        else:
            plot_kwargs = {"transform": ccrs.PlateCarree()}

            if 'plot arguments' in config['echam']['Global Climatology'][variable]: 
                plot_kwargs.update(config['echam']['Global Climatology'][variable]['plot arguments'])
            f, ax = plt.subplots(dpi=150, subplot_kw={'projection': ccrs.Robinson()})
            ax.gridlines()
            ax.coastlines()

            cf = ax.contourf(ds[variable].squeeze(), cmap=user_cmap, **plot_kwargs)

            if hasattr(ds[variable], 'long_name') and hasattr(ds[variable], 'units'):
                cbar_label = ds[variable].long_name+" ("+ds[variable].units+")"
            else:
                cbar_label = variable
            return_list.append((f, ax))
    if 'use_hvplot' in config:
        return hv.Layout(return_list).cols(1)
    else:
        return return_list
