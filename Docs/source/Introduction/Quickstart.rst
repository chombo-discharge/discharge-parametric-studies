Quickstart — Rod Case
=====================

This guide walks through the complete workflow for the ``Exec/Rod`` parametric study — from compilation through post-processing.
The Rod case demonstrates the two-level database → study pipeline: a discharge-inception database is computed first, and its results feed a full plasma simulation study.

Prerequisites
-------------

Before starting, ensure the following are available:

* ``DISCHARGE_HOME`` must be set and point to a compiled `chombo-discharge <https://chombo-discharge.github.io/>`_ installation.
* A SLURM scheduler must be available. See :doc:`../Prerequisites/Example` for a local install example.

Compile
-------

.. code-block:: bash

    cd Exec/Rod
    make -j4

This builds two executables:

* ``DischargeInception/main{N}d.Linux.64.mpic++.gfortran.OPTHIGH.MPI.ex`` — used for the database (inception voltage) step.
* ``ItoKMC/main{N}d.Linux.64.mpic++.gfortran.OPTHIGH.MPI.ex`` — used for the plasma simulation study step.

The ``{N}`` in the filename is replaced at runtime by the dimensionality specified with ``--dim``.

Configure the parameter space
------------------------------

Open ``Exec/Rod/Studies/pressure_study/Runs.py`` to inspect or adjust the parameter space.
The top-level structure is:

.. code-block:: python

    top_object = dict(
            databases=[inception_stepper],
            studies=[plasma_study_1]
            )

**Database** (``inception_stepper``) — computes inception voltages over a grid of pressures and rod radii:

.. code-block:: python

    'parameter_space': {
        "pressure": {
            "target": "master.inputs",
            "uri": "DischargeInception.pressure"
            },
        "geometry_radius": {
            "target": "master.inputs",
            "uri": "Rod.radius",
            },
        'K_max': {
            "target": "master.inputs",
            "uri": "DischargeInceptionStepper.limit_max_K"
            }
        }

**Study** (``plasma_study_1``) — runs plasma simulations using the database results:

.. code-block:: python

    'parameter_space': {
        "geometry_radius": {
            "database": "inception_stepper",
            "target": "master.inputs",
            "uri": "Rod.radius",
            "values": [1e-3]
            },
        "pressure": {
            "database": "inception_stepper",
            "target": "chemistry.json",
            "uri": ["gas", "law", "ideal_gas", "pressure"],
            "values": [1e5]
            },
        "K_min": { "values": [6] },
        "K_max": {
            "database": "inception_stepper",
            "values": [12.0]
            },
        "photoionization": {
            "target": "chemistry.json",
            "uri": [...],
            "values": [[1.0, 0.0]]
            },
        }

Parameters marked with ``"database": "inception_stepper"`` declare a dependency: the study jobs will not start until all database jobs have finished.
See :doc:`RunDefinition` for full parameter space syntax.

Run the Configurator
---------------------

.. code-block:: bash

    cd Exec/Rod/Studies/pressure_study
    python ../../../Configurator.py Runs.py \
        --output-dir ~/my_rod_study \
        --dim 2 \
        --verbose

The Configurator:

1. Creates the output directory tree.
2. Copies executables, input files, and job scripts into place.
3. Submits a SLURM array job for the database (``is_db/``).
4. Submits a second SLURM array job for the study (``study0/``), chained to depend on the database job completing first.

The resulting directory layout looks like:

.. code-block:: bash

    $ ls -R --file-type ~/my_rod_study
    .:
    is_db/  study0/

    ./is_db:
    array_job_id  DischargeInceptionJobscript.py  GenericArrayJob.sh
    index.json    master.inputs                   ParseReport.py
    main2d.Linux.64.mpic++.gfortran.OPTHIGH.MPI.ex
    run_0/  structure.json  transport_data.txt

    ./is_db/run_0:
    chk/  master.inputs  parameters.json  plt/  pout.*  main@  transport_data.txt

    ./study0:
    array_job_id  chemistry.json  GenericArrayJob.sh  inception_stepper@
    index.json    master.inputs   PlasmaJobscript.py
    main2d.Linux.64.mpic++.gfortran.OPTHIGH.MPI.ex
    run_0/  structure.json

    ./study0/run_0:
    chemistry.json  detachment_rate.dat  electron_transport_data.dat
    master.inputs   parameters.json      main@

.. note::

    ``study0/inception_stepper`` is a symlink pointing to ``../is_db``, giving study job scripts direct access to the database results.

Monitor jobs
-------------

.. code-block:: bash

    squeue -u $USER

    # Check the submitted job IDs
    cat ~/my_rod_study/is_db/array_job_id     # database job ID
    cat ~/my_rod_study/study0/array_job_id    # study job ID (depends on above)

Inspect results
----------------

After both jobs complete:

.. code-block:: bash

    # Database results — inception voltage reports
    ls ~/my_rod_study/is_db/run_*/report.txt

    # Study results — plasma simulation output
    ls ~/my_rod_study/study0/run_*/pout.*
    ls ~/my_rod_study/study0/run_*/plt/

Post-process
-------------

Scripts in ``PostProcess/`` summarise and plot the study results:

.. code-block:: bash

    cd ~/my_rod_study/study0
    bash /path/to/PostProcess/Summarize.sh

Or run the analysis scripts directly:

.. code-block:: bash

    python /path/to/PostProcess/Gather.py
    python /path/to/PostProcess/PlotDeltaERel.py
