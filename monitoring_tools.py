#!/bin/env python
## fix that

import socket
import getpass
import os
import pandas as pd
import matplotlib.pyplot as plt
import subprocess
import batch_systems 

batch_system_dict = {
                "ollie": batch_systems.slurm
                }

class simulation():
        def __init__(self, expid, path):
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


class component():
        def __init__(self, expid, path,
                        configdir=None, forcingdir=None, inputdir=None, logdir=None, mondir=None, outdatadir=None, restartdir=None):
                self.expid = expid
                self.configdir = configdir or path+"/config/"+self.__class__.__name__
                self.forcingdir = forcingdir or path+"/forcing/"+self.__class__.__name__
                self.inputdir = inputdir or path+"/input/"+self.__class__.__name__
                self.logdir = logdir or path+"/log/"+self.__class__.__name__
                self.mondir = mondir or path+"/mon/"+self.__class__.__name__
                self.outdatadir = outdatadir or path+"/outdata/"+self.__class__.__name__
                self.restartdir = restartdir or path+"/restart/"+self.__class__.__name__

class echam(component):
        def __init__(self, *args):
                self.__name__ = "echam"
                component.__init__(self, *args)

class jsbach(component):
        def __init__(self, *args):
                component.__init__(self, *args)

class fesom(component):
        def __init__(self, *args):
                component.__init__(self, *args)

class pism(component):
        def __init__(self, *args):
                component.__init__(self, *args)

class villma(component):
        def __init__(self, *args):
                component.__init__(self, *args)

class logfile():
        def __init__(self):
                pass

        def get_mean_walltime(self):
                # TODO: find a way to get these times in the methods
                time_diff = time_at_start - time_at_done
                return time_diff

        def get_mean_walltime(self):
                # TODO: find a way to get these times in the methods
                wait_time = time_at_done - time_at_start
                return wait_time
