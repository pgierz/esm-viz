.. include:: ../README.rst

``ESM Viz`` is a command line tool to schedule automatic monitoring of earth system model simulation. 

The easiest way to get started is:

.. code-block:: console

    $ esm_viz
    
Without any arguments, this will ask you a series of questions about your experiment, and set up a default monitoring page for you. The defaults include:

+ Queue status of the supercomputer
+ Average walltime, queuing time, efficiency, and optimal and actual throughout
+ simulation progress, with an estimated completion time
+ A timeline of the last 10 runs, showing when they were run and when they were in the queue. 

Furthermore, depending on the model setup you specified, you get timeseries and climatology maps of:

+ Atmosphere:
    - Near Surface Temperature
    - Total Precipitation 
    - Total Evaporation
    - Net P-E
    - Sea-level Pressure
+ Ocean
    - Sea surface temperature 
    - Sea surface salinity
    - Surface velocity
    - AMOC strength index
    
Currently, the following components are supported:
+ ECHAM6 (``AWICM 1/2``)

Still to come:
+ FESOM
+ PISM
+ ECHAM6 (``MPI-ESM``)
+ MPIOM (``MPI-ESM``)
+ ECHAM5 (``COSMOS``)
+ MPIOM (``COSMOS``)

By default, the monitoring page will update every 2 hours. 