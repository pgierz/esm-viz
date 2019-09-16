"""
This module contains tools for plotting PISM timeseries and climatology maps
"""

import matplotlib.pyplot as plt
import xarray as xr
import cartopy.crs as ccrs
import holoviews as hv
import hvplot.xarray  # noqa
import geoviews as gv

import cmocean

from IPython.core.display import display, HTML

from esm_viz.visualization import get_local_storage_dir_from_config


def plot_timeseries(config):
    display(HTML("<h2> Global Timeseries of PISM </h2>"))
    file_dir = get_local_storage_dir_from_config(config) + "/analysis/pism/"
    expid = config["basedir"].split("/")[-1]
    return_list = []
    for variable in config["pism"]["Timeseries"]:
        ds = xr.open_dataset(
            file_dir + expid + "_pism_" + variable + "_timeseries.nc",
            decode_times=False,
        )
        pism_command_parts = ds.command.split()
        # Fix the time axes:
        pism_ts_times = pism_command_parts[pism_command_parts.index("-ts_times") + 1]
        if ":" in pism_ts_times:
            pism_nyears = int(pism_ts_times.split(":")[1])
        elif pism_ts_times == "yearly":
            pism_nyears = 1
        elif pism_ts_times == "monthly":
            pism_nyears = 1 / 12.0
        else:
            raise TypeError("Sorry, don't know what to do for PISM times")
        ds["time"] = range(0, len(ds["time"]), pism_nyears)
        if "use_hvplot" in config:
            o = ds[variable].squeeze().hvplot.line(title=variable)
            # Due to syntax differences, hvplot (actually Bokeh) has slightly different keywords than matplotlib.
            # Turn on the grid:
            o.options(
                color="black",
                line_width=0.66,
                gridstyle={
                    "grid_line_dash": "dotted",
                    "grid_line_color": "gray",
                    "grid_line_width": 0.33,
                },
                show_grid=True,
                clone=False,
            )
            redim_dict = {
                variable: {
                    "name": getattr(ds[variable], "long_name", None),
                    "unit": getattr(ds[variable], "units", None),
                },
                "time": {"name": "Simulation Time", "unit": "Years"},
            }
            o = o.redim(**redim_dict)
            if len(ds[variable]) >= 30:
                o_runmean = (
                    ds[variable]
                    .rolling(time=30, center=True)
                    .mean()
                    .squeeze()
                    .hvplot.line(color="red")
                )
                units_attr = getattr(ds[variable], "units", None)
                o_runmean = o_runmean.redim(
                    value={
                        "name": ds[variable].long_name + ": 30 year running mean",
                        "unit": units_attr,
                    }
                )
                return_list.append(o * o_runmean)
            else:
                return_list.append(o)
        else:
            plot_kwargs = {"color": "black", "lw": 0.66}
            runmean_color = "red"
            runmean_lw = 2
            if "plot arguments" in config["pism"]["Timeseries"][variable]:
                plot_kwargs.update(
                    config["pism"]["Timeseries"][variable]["plot arguments"]
                )
                runmean_color = config["pism"]["Timeseries"][variable][
                    "plot arguments"
                ].get("runmean color", runmean_color)
                runmean_lw = config["pism"]["Timeseries"][variable][
                    "plot arguments"
                ].get("runmean lw", runmean_lw)
            f, ax = plt.subplots(dpi=150)
            ax.grid(linestyle=":", linewidth=0.33, color="gray")
            ax.plot(ds[variable].squeeze(), **plot_kwargs)
            ax.set_xlabel("Simulation Time (Years)")
            if hasattr(ds[variable], "long_name") and hasattr(ds[variable], "units"):
                ax.set_ylabel(ds[variable].long_name + " (" + ds[variable].units + ")")
            if len(ds[variable]) >= 30:
                ax.plot(
                    ds[variable].rolling(time=30, center=True).mean().squeeze(),
                    color=runmean_color,
                    lw=runmean_lw,
                )
            return_list.append((f, ax))
    if "use_hvplot" in config:
        return hv.Layout(return_list).cols(1)
    else:
        return return_list
