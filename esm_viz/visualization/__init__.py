"""
General utils that are probably going to be needed by most components.
"""
import os


def get_local_storage_dir_from_config(config):
    """
    Retrieves the local strorage directory from the config

    Parameters
    ----------
    config : dict
        Your monitoring configuration based on the yaml file

    Returns
    -------
    storage_path : str
        The path on the web serving computer where you are storing the experiments. This is basically just the same tree as on the compute server, but with a replaced beginning of the path.
    """
    basedir = config["basedir"]
    storage_prefix = config["storagedir"]
    user = config["user"]
    return os.path.normpath(
        "/".join(
            storage_prefix.split("/")
            + basedir.split("/")[1 + basedir.split("/").index(user) :]
        )
    )
