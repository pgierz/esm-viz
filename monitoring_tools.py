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


batch_system_dict = {
                "ollie": batch_systems.slurm
                }

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
                self.batch_system = [value for key, value in batch_system_dict.items() if key in socket.gethostname()][0]()
                self.expid = expid
                self.exp_home = path
                self.setup = None


class awicm_pism(simulation):
        def __init__(self, expid, path):
                super().__init__(expid, path)
                self.setup = "awicm_pism"
                self.atmosphere = echam(expid, path+"/awicm/")
                self.land_surface = jsbach(expid, path+"/awicm/")
                self.ocean = fesom(expid, path+"/awicm/")
                self.ice = pism(expid, path+"/pism_standalone/")
                self.solid_earth = None
                components = [self.atmosphere, self.land_surface, self.ocean, self.ice, self.solid_earth]
                self.components = [component for component in components if component is not None]

class awicm(simulation):
        def __init__(self, expid, path):
                super().__init__(expid, path)
                self.setup = "awicm"
                self.atmosphere = echam(expid, path)
                self.land_surface = jsbach(expid, path)
                self.ocean = fesom(expid, path)
                self.ice = None
                self.solid_earth = None
                components = [self.atmosphere, self.land_surface, self.ocean, self.ice, self.solid_earth]
                self.components = [component for component in components if component is not None]


class component:
        def __init__(self, expid, path,
                        configdir=None, forcingdir=None, inputdir=None, logdir=None, mondir=None, outdatadir=None, restartdir=None):
                # Set up names etc.
                self.expid = expid
                self.__name__ = self.__class__.__name__ or "component"
                self.configdir = configdir or path+"/config/"+self.__name__
                self.forcingdir = forcingdir or path+"/forcing/"+self.__name__
                self.inputdir = inputdir or path+"/input/"+self.__name__
                self.logdir = logdir or path+"/log/"+self.__name__
                self.mondir = mondir or path+"/mon/"+self.__name__
                self.outdatadir = outdatadir or path+"/outdata/"+self.__name__
                self.restartdir = restartdir or path+"/restart/"+self.__name__

        def _list_dir(self, _type):
                # TODO: This needs to throw away symlinks, we really only want **files**
                all_files = os.listdir(getattr(self, _type+"dir"))
                for remove_substring in [self.expid]:
                        all_files = [thisfile.replace(remove_substring, "") for thisfile in all_files]
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
                                fileparts = [filepart for filepart in fileparts if not filepart.isdigit()]
                                self._set_of_processed_files.add(self.expid+"_".join(fileparts)+"*."+suffix)
                # Turn the set into a dict now that all the files have been processed
                self._set_of_processed_files = {value.replace(self.expid, "").replace("*.nc", ""): value for value in self._set_of_processed_files}
                self._clean_up_names()

        def _clean_up_names(self):
                pass

        def load_datasets(self):
                self._generalize_file_types("outdata")
                for set_name, fileset in self._set_of_processed_files.items():
                        print("Trying to load: ", self.outdatadir+"/"+fileset)
                        setattr(self, set_name, xr.open_mfdataset(self.outdatadir+"/"+fileset, autoclose=True, preprocess=drop_time_vars)) 
                self._data_loaded = True

        def __str__(self):
                return "A {model} run".format(model=self.__name__.upper())


def non_time_coords(ds):
        return [v for v in ds.data_vars if 'time' not in ds[v].dims]

def drop_time_vars(ds):
        return ds.drop(non_time_coords(ds))

class echam(component):
        def __init__(self, *args):
                self.__name__ = "echam"
                super().__init__(*args)

        def _clean_up_names(self):
                # NOTE: Remove the first character for the key, since we don't want underscores in the key names
                self._set_of_processed_files = {k[1:]: v for k, v in self._set_of_processed_files.items()}

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
                self._set_of_processed_files = {k.replace(self.expid, "").replace("_fesom", ""): v.replace(self.expid, "")
                                                for k, v
                                                in self._set_of_processed_files.items()}

class pism(component):
        def __init__(self, *args):
                super().__init__(*args)

class villma(component):
        def __init__(self, *args):
                super().__init__(*args)

class logfile():
        def __init__(self):
                pass

        def get_mean_walltime(self):
                # TODO: find a way to get these times in the methods
                time_diff = time_at_start - time_at_done
                return time_diff

        def get_queuing_walltime(self):
                # TODO: find a way to get these times in the methods
                wait_time = time_at_done - time_at_start
                return wait_time
