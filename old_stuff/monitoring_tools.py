#!/bin/env python
## fix that


# TODO: PEP conform import order
import socket
import getpass
import os
import pandas as pd
import matplotlib.pyplot as plt
import subprocess
import batch_systems
import xarray as xr
import datetime

from tqdm import tnrange, tqdm_notebook

batch_system_dict = {"ollie": batch_systems.slurm}


class simulation:
    def __init__(self, expid, path):
        """
                Creates a generic simulation, which can be used as a quick access point for:
                + netcd xarray objects
                + slurm batch monitoring

                Dr. Paul Gierz
                pgierz@awi.de
                AWI Bremerhaven
                """
        # FIXME: Theres probably a better way to write this one
        self.batch_system = [
            value
            for key, value in batch_system_dict.items()
            if key in socket.gethostname()
        ][0]()
        self.expid = expid
        self.exp_home = path
        self.setup = None
        self.progress = None

    def __repr__(self):
        return "A {setup} simulation".format(setup=self.setup)

    def _repr_markdown_(self):
        part1 = """ Here is some information concerning your simulation, `{expid}`. It is made of up: 
## {setup}

### Atmosphere:
{}

### Land Surface:
{}

### Ocean:
{}

### Ice:
{}

### Solid Earth:
{}
""".format(
            expid=self.expid,
            setup=self.setup.upper(),
            *[
                component._repr_markdown_()
                if hasattr(component, "_repr_markdown_")
                else component
                for component in self.components
            ]
        )
        part3 = self.batch_system._repr_html_()
        return part1 + part3


class awicm_pism(simulation):
    def __init__(self, expid, path):
        super().__init__(expid, path)
        self.setup = "awicm_pism"
        self.atmosphere = echam(expid, path + "/awicm/")
        self.land_surface = jsbach(expid, path + "/awicm/")
        self.ocean = fesom(expid, path + "/awicm/")
        self.ice = pism(expid, path + "/pism_standalone/")
        self.solid_earth = None
        self.components = [
            self.atmosphere,
            self.land_surface,
            self.ocean,
            self.ice,
            self.solid_earth,
        ]
        self.used_components = [
            component for component in self.components if component is not None
        ]
        self.awicm_log = logfile(path, expid, "awicm")

    def awicm_progress(self):
        current_dates = self.awicm_log.get_progress()
        pbar = tqdm_notebook(
            total=(current_dates["Final date"] - current_dates["Initial date"]).days
        )
        pbar.update(
            (current_dates["Current date"] - current_dates["Initial date"]).days
        )
        pbar.close()


class awicm(simulation):
    def __init__(self, expid, path):
        super().__init__(expid, path)
        self.setup = "awicm"
        self.atmosphere = echam(expid, path)
        self.land_surface = jsbach(expid, path)
        self.ocean = fesom(expid, path)
        self.ice = None
        self.solid_earth = None
        self.components = [
            self.atmosphere,
            self.land_surface,
            self.ocean,
            self.ice,
            self.solid_earth,
        ]
        self.used_components = [
            component for component in self.components if component is not None
        ]


class component:
    def __init__(
        self,
        expid,
        path,
        configdir=None,
        forcingdir=None,
        inputdir=None,
        logdir=None,
        mondir=None,
        outdatadir=None,
        restartdir=None,
    ):
        # Set up names etc.
        self.expid = expid
        self.__name__ = self.__class__.__name__ or "component"
        self.configdir = configdir or path + "/config/" + self.__name__
        self.forcingdir = forcingdir or path + "/forcing/" + self.__name__
        self.inputdir = inputdir or path + "/input/" + self.__name__
        self.logdir = logdir or path + "/log/" + self.__name__
        self.mondir = mondir or path + "/mon/" + self.__name__
        self.outdatadir = outdatadir or path + "/outdata/" + self.__name__
        self.restartdir = restartdir or path + "/restart/" + self.__name__

        self._data_loaded = False

    def _list_dir(self, _type):
        # TODO: This needs to throw away symlinks, we really only want **files**
        all_files = os.listdir(getattr(self, _type + "dir"))
        for remove_substring in [self.expid]:
            all_files = [
                thisfile.replace(remove_substring, "") for thisfile in all_files
            ]
        return all_files

    def _generalize_file_types(self, _type):
        # The assumption here is that file types are split something taking the form:
        #
        # ${EXP_ID}_${SOME_SUB_STREAM_WITH_POTENTIAL_UNDERSCORES}_${DATE}.${SUFFIX}
        # for file in _list_dir(_type):
        output_common_strings = []
        list_of_files = self._list_dir(_type)
        self._set_of_processed_files = set()
        for filename in list_of_files:
            suffix = filename.split(".")[-1]
            # NOTE Only netCDF files are valid for xarray
            # This actually isn't true, we can also load grb with
            # a different library, but we chose to restrict only to
            # netCDF for now.
            if suffix == "nc":
                fileparts = filename.split(".")[0].split("_")
                fileparts = [
                    filepart for filepart in fileparts if not filepart.isdigit()
                ]
                self._set_of_processed_files.add(
                    self.expid + "_".join(fileparts) + "*." + suffix
                )
        # Turn the set into a dict now that all the files have been processed
        self._set_of_processed_files = {
            value.replace(self.expid, "").replace("*.nc", ""): value
            for value in self._set_of_processed_files
        }
        self._clean_up_names()

    def _clean_up_names(self):
        pass

    def load_datasets(self):
        self._generalize_file_types("outdata")
        for set_name, fileset in self._set_of_processed_files.items():
            print("Trying to load: ", self.outdatadir + "/" + fileset)
            setattr(
                self,
                set_name,
                xr.open_mfdataset(
                    self.outdatadir + "/" + fileset,
                    autoclose=True,
                    preprocess=drop_time_vars,
                ),
            )
        self._data_loaded = True

    def __str__(self):
        a = "An" if self.__name__[0] in "aeiou" else "A"
        return "{a} {model} run".format(a=a, model=self.__name__.upper())

    def _repr_markdown_(self):
        a = "An" if self.__name__[0] in "aeiou" else "A"
        return """{a} `{model}` run

Data loaded: `{data_loaded}`        

""".format(
            a=a, model=self.__name__.upper(), data_loaded=self._data_loaded
        )


def non_time_coords(ds):
    return [v for v in ds.data_vars if "time" not in ds[v].dims]


def drop_time_vars(ds):
    return ds.drop(non_time_coords(ds))


class echam(component):
    def __init__(self, *args):
        self.__name__ = "echam"
        super().__init__(*args)

    def _clean_up_names(self):
        # NOTE: Remove the first character for the key, since we don't want underscores in the key names
        self._set_of_processed_files = {
            k[1:]: v for k, v in self._set_of_processed_files.items()
        }

    def load_datasets(self):
        print("Please be patient, loading ECHAM6 data may take time")
        print("To load ATM, BOT, LOG streams takes up to 6 minutes")
        super().load_datasets()


class jsbach(component):
    def __init__(self, *args):
        self.__name__ = "jsbach"
        super().__init__(*args)


class fesom(component):
    def __init__(self, *args):
        self.__name__ = "fesom"
        super().__init__(*args)

    def _clean_up_names(self):
        # NOTE: Since FESOM doesn't add the EXP_ID to its file names, we remove it here:
        self._set_of_processed_files = {
            k.replace(self.expid, "").replace("_fesom", ""): v.replace(self.expid, "")
            for k, v in self._set_of_processed_files.items()
        }


class pism(component):
    def __init__(self, *args):
        super().__init__(*args)


class villma(component):
    def __init__(self, *args):
        super().__init__(*args)


class logfile:
    def __init__(self, path, expid, setup):
        self.path = path
        self.expid = expid
        log = self.path + "/scripts/" + self.expid + "_" + setup + ".log"
        log_dataframe = pd.read_table(
            log,
            sep=r" :  | -",
            skiprows=1,
            infer_datetime_format=True,
            names=["Date", "Message", "State"],
            engine="python",
            index_col=0,
        )
        middle_column = log_dataframe["Message"].apply(
            lambda x: pd.Series(str(x).split())
        )
        log_dataframe.drop("Message", axis=1, inplace=True)
        middle_column.columns = ["Run Number", "Exp Date", "Job ID"]
        log_dataframe = pd.concat([log_dataframe, middle_column], axis=1)
        log_dataframe.set_index(pd.to_datetime(log_dataframe.index), inplace=True)
        self.dataframe = log_dataframe[~log_dataframe.State.str.contains("post")]

    def get_mean_walltime(self):
        starts = self.dataframe[self.dataframe.State == " start"]
        ends = self.dataframe[self.dataframe.State == " done"]
        # Drop the duplicates if we start more than one time (e.g. by hand)
        starts.drop_duplicates(subset="Run Number", keep="last", inplace=True)
        ends.drop_duplicates(subset="Run Number", keep="last", inplace=True)

        shorter_list = min(len(starts), len(ends))

        starts = starts[:shorter_list]
        ends = ends[:shorter_list]
        self._starts = starts
        self._ends = ends
        starts = starts.index.tolist()
        ends = ends.index.tolist()
        diffs = [ends[i] - starts[i] for i in range(len(ends))]
        average_timedelta = sum(diffs, datetime.timedelta(0)) / len(diffs)
        return average_timedelta

    def get_progress(self):
        last_job_id = self.dataframe["Job ID"][-1]
        self.dates = {
            "Initial date": None,
            "Current date": None,
            "End date": None,
            "Final date": None,
        }
        script = self.path + "/scripts/" + self.expid + "_" + last_job_id + ".log"
        for line in open(script):
            for k in self.dates.keys():
                if k in line:
                    self.dates[k] = line.split(":")[-1].strip()
        self.dates["Initial date"] = datetime.datetime.strptime(
            self.dates["Initial date"], "%Y-%m-%d"
        )
        self.dates["Current date"] = datetime.datetime.strptime(
            self.dates["Current date"], "%Y%m%d"
        )
        self.dates["End date"] = datetime.datetime.strptime(
            self.dates["End date"], "%Y%m%d"
        )
        self.dates["Final date"] = datetime.datetime.strptime(
            self.dates["Final date"], "%Y-%m-%d"
        )
        return self.dates

    def get_queuing_walltime(self):
        # TODO: find a way to get these times in the methods
        wait_time = time_at_done - time_at_start
        return wait_time
