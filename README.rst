=======
esm-viz
=======


.. image:: https://img.shields.io/pypi/v/esm_viz.svg
        :target: https://pypi.python.org/pypi/esm_viz

.. image:: https://img.shields.io/travis/pgierz/esm_viz.svg
        :target: https://travis-ci.org/pgierz/esm_viz

.. image:: https://readthedocs.org/projects/esm-viz/badge/?version=latest
        :target: https://esm-viz.readthedocs.io/en/latest/?badge=latest
        :alt: Documentation Status


``ESM Viz`` is a command line tool to schedule automatic monitoring of Earth System Model simulations.

* Free software: GNU General Public License v3
* Documentation: https://esm-viz.readthedocs.io.


First Steps
-----------

The easiest way to get started is:

.. code-block:: console

    $ esm_viz --help

This will display a series of options you can use. In order to set up automatic monitoring for an experiment, you can use ``esm_viz template``


Installation
------------

For AWI Users
^^^^^^^^^^^^^

On ``paleosrv1.awi.de``; the software is already installed. 


For Other Users
^^^^^^^^^^^^^^^

There are several external packages that need to be installed in order for everything to work correctly. The easiest way to get everything in one go is:

.. code-block:: console

    $ pip install esm_viz
    
You can then type 

.. code-block:: console

    $ esm_viz configure

This will ask open up a configuration file for you to edit.

Usage Demonstration
-------------------

Interactively setting up a new monitoring job:

.. code-block:: console
    
    $ esm_viz
    
Setting up a monitoring job from a YAML file:

.. code-block:: console

    $ esm_viz </PATH/TO/EXPERIMENT.yaml>

Setting up a monitoring job from a YAML file already stored in ``${HOME}/.config/monitoring``

.. code-block:: console
    
    $ esm_viz EXPERIMENT
    
.. note::
    The ``.yaml`` extension is appended automatically!
    
Performing only certain parts of a job:

.. code-block:: console
    
    $ # Only schedule a job to run every 2 hours:
    $ esm_viz schedule EXPERIMENT
    $ # Schedule a job to run every 6 hours:
    $ esm_viz schedule --frequency 6 EXPERIMENT
    $ # Deploying monitoring scripts and running them on the supercomputer
    $ # Note that the scripts actually run depend on the configuration file
    $ esm_viz deploy EXPERIMENT
    $ # Combining results into a webpage
    $ esm_viz combine EXPERIMENT


In the next section, the command line interface and python modules are explained in more detail. Then, we show an explanation about how to customize what is shown in the plots.   
- - - -


Features
--------

* TODO

Credits
-------

This package was created with Cookiecutter_ and the `audreyr/cookiecutter-pypackage`_ project template.

.. _Cookiecutter: https://github.com/audreyr/cookiecutter
.. _`audreyr/cookiecutter-pypackage`: https://github.com/audreyr/cookiecutter-pypackage
