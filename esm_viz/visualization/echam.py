"""
This module contains tools for plotting ECHAM timeseries and climatology maps
"""

import matplotlib.pyplot as plt
import xarray as xr
import cartopy.crs as ccrs
import holoviews as hv
import hvplot.xarray  # noqa
import geoviews as gv
import panel as pn
import cmocean


from esm_viz.visualization import get_local_storage_dir_from_config

from ..deployment import Simulation_Monitor


class EchamPanel(Simulation_Monitor):
    def render_pane(self, config):
        all_timeseries = plot_global_timeseries(config)
        all_variable_names = list(config["echam"]["Global Timeseries"])
        names_and_ts = zip(all_variable_names, all_timeseries)

        all_climatologies = plot_global_climatology(config)
        all_variable_names = list(config["echam"]["Global Climatology"])
        names_and_clims = zip(all_variable_names, all_climatologies)
        return pn.Tabs(
            ("Timeseries", pn.Tabs(*names_and_ts)),
            ("Climatologies", pn.Tabs(*names_and_clims)),
        )


def plot_global_timeseries(config):
    file_dir = get_local_storage_dir_from_config(config) + "/analysis/echam/"
    expid = config["basedir"].split("/")[-1]
    return_list = []
    for variable in config["echam"]["Global Timeseries"]:
        ds = xr.open_dataset(
            file_dir + expid + "_echam_" + variable + "_global_timeseries.nc"
        )
        # Fix the time axes:
        ds["time"] = range(len(ds["time"]))
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
            if "plot arguments" in config["echam"]["Global Timeseries"][variable]:
                plot_kwargs.update(
                    config["echam"]["Global Timeseries"][variable]["plot arguments"]
                )
                runmean_color = config["echam"]["Global Timeseries"][variable][
                    "plot arguments"
                ].get("runmean color", runmean_color)
                runmean_lw = config["echam"]["Global Timeseries"][variable][
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


def plot_global_climatology(config):
    file_dir = get_local_storage_dir_from_config(config) + "/analysis/echam/"
    expid = config["basedir"].split("/")[-1]
    return_list = []
    for variable in config["echam"]["Global Climatology"]:
        ds = xr.open_dataset(
            file_dir + expid + "_echam_" + variable + "_global_climatology.nc"
        )

        # Initialize no cmap, just in case the user didn't give us one:
        user_cmap = "jet"
        if "plot arguments" in config["echam"]["Global Climatology"][variable]:
            if (
                "cmap"
                in config["echam"]["Global Climatology"][variable]["plot arguments"]
            ):
                user_cmap = config["echam"]["Global Climatology"][variable][
                    "plot arguments"
                ]["cmap"]
                if user_cmap.startswith("cmocean."):
                    user_cmap = getattr(cmocean.cm, user_cmap.replace("cmocean.", ""))
                else:
                    user_cmap = getattr(plt.cm, user_cmap)
                # Delete the cmap to avoid double arguments in plot_kwargs if using matplotlib
                del config["echam"]["Global Climatology"][variable]["plot arguments"][
                    "cmap"
                ]

        if "use_hvplot" in config:
            o = (
                ds[variable]
                .squeeze()
                .hvplot.quadmesh(
                    "lon",
                    "lat",
                    projection=ccrs.Robinson(),
                    project=True,
                    global_extent=True,
                    width=600,
                    height=300,
                    cmap=user_cmap,
                    rasterize=True,
                    dynamic=False,
                )
                * gv.feature.coastline
            )
            redim_dict = {
                variable: {
                    "name": getattr(ds[variable], "long_name", None),
                    "unit": getattr(ds[variable], "units", None),
                }
            }
            o = o.redim(**redim_dict)
            return_list.append(o * gv.feature.coastline)
        else:
            plot_kwargs = {"transform": ccrs.PlateCarree()}

            if "plot arguments" in config["echam"]["Global Climatology"][variable]:
                plot_kwargs.update(
                    config["echam"]["Global Climatology"][variable]["plot arguments"]
                )
            f, ax = plt.subplots(dpi=150, subplot_kw={"projection": ccrs.Robinson()})
            ax.gridlines()
            ax.coastlines()

            ax.contourf(ds[variable].squeeze(), cmap=user_cmap, **plot_kwargs)

            if hasattr(ds[variable], "long_name") and hasattr(ds[variable], "units"):
                ds[variable].long_name + " (" + ds[variable].units + ")"
            return_list.append((f, ax))
    if "use_hvplot" in config:
        return hv.Layout(return_list).cols(1)
    else:
        return return_list
