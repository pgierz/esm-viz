"""
This module contains tools for plotting FESOM timeseries and climatology maps
"""

import matplotlib.pyplot as plt
import xarray as xr
import cartopy.crs as ccrs
import holoviews as hv
import hvplot.xarray
import geoviews as gv

import cmocean
import pyfesom as pf
from IPython.core.display import display, HTML

from esm_viz.visualization import get_local_storage_dir_from_config


def load_mesh(config):
    ssh = paramiko.SSHClient()
    ssh.load_system_host_keys()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    ssh.connect(config["host"], username=config["user"])
    with ssh.open_sftp() as sftp:
        scriptdir_contents = sftp.listdir(config["basedir"] + "/scripts")
        runscript = (
            config["basedir"]
            + "/scripts/"
            + [f for f in scriptdir_contents if f.endswith(".run")][0]
        )
        with sftp.file(runscript) as runscript_file:
            mesh_dir = [
                l.strip() for l in runscript_file.readlines() if "MESH_DIR" in l
            ][0].split("=")[-1]
        os.system(
            "rsync -azv "
            + config["user"]
            + "@"
            + config["host"]
            + ":"
            + mesh_dir
            + " "
            + config["storagedir"]
            + "/"
            + config["model"]
            + "/MESHES/"
        )
    return pf.load_mesh(
        config["storagedir"]
        + "/"
        + config["model"]
        + "/MESHES/"
        + mesh_dir.split("/")[-1]
    )
