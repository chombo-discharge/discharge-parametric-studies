Basic Usage
===========
The ``configurator.py`` script can be used to set up directory structures and submit slurm jobs for wide parametric sweeps over chombo-discharge based studies.

.. code-block::
   :caption: Invocation options
    $ python configurator.py --help

    usage: configurator.py [-h] [--verbose] [--logfile LOGFILE] [--output-dir OUTPUT_DIR]
                           [--dim DIM]
                           run_definition

    Batch script for running user-defined, parametrised chombo-discharge studies.

    positional arguments:
      run_definition        parameter space input file. Json read directly, or if .py file look
                            for 'top_object' dictionary

    options:
      -h, --help            show this help message and exit
      --verbose             increase verbosity
      --logfile LOGFILE     log file. (Postfix) Rotated automatically each invocation.
      --output-dir OUTPUT_DIR
                            output directory for study result files
      --dim DIM             Dimensionality of simulations. Must match chombo-discharge
                            compilation.

The most important part is the ``run_definition``, which is either structured as a json file or python file. If it is a python file it is dynamically imported and the object ``top_object`` (a dictionary) is loaded. A python dictionary containing basic types (sub-dictionaries, lists, strings, numbers, booleans) almost has the same syntax structured JSON data, and it is easy to use the json module to dump such a dictionary to a json file if needed. There are benefits for keeping your `run_definition` as a .py file though, e.g. the possibility to use variables when setting up the project structure or specifying numerical parameter ranges.
