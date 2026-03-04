Overall Design
==============

This piece of software parses a run definition dictionary/JSON structure that is comprised of *databases* and *studies*.

.. code-block:: python
    :caption: config_concept.py

    db_study = {
        ...
    }

    main_study = {
        ...
    }

    top_object = dict(
            databases=[db_study],
            studies=[main_study]
            )

The difference between a *database* and a *study* is mainly a semantic one; a study can depend on database, and the configurator will create and submit a slurm job hierarchy as well as create an output file hierarchy that reflects this.

A database is meant to be used as a first simulation step running specific (perhaps light-weight) jobs (chombo-discharge simulations, or other software) to generate intermediate data that the main studies depend on.

Each database or study step relies on running a (chombo-discharge) executable repeatedly, and often in parallel, over a defined parameter set. Ex.: if a parameter *pressure* should be varied over 5 different values, and another parameter *radius* should be varied over 3 different values, the parameter space would require 15 distinct runs. Now, the preliminary database study might only depend on the *pressure*, while the whole main study depends on both parameters. This would result in 5 jobs (submitted as parallel array job to slurm) for the database study, **followed** by 15 jobs (parallel, and depending on the success of the first database's array job) for the main study.
