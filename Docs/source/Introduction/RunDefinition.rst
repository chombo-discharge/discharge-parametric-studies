Run Definition
==============

A database/study will have these configurable fields:

* ``identifier``, unique
* ``output_directory``, relative to the cmdline output directory, i.e.  ``--output-dir``
* ``output_dir_prefix`` (default: ``"run_"``)
* ``program``, executable to run. Will be copied to output directory hierarchy.
* ``job-script``, job script to do the heavy lifting (call mpirun / start simulation code)
* ``job_script_dependencies``, (python) scripts and files that the job-script needs
* ``required_files``, typical input files for the simulation, post-analysis scripts, etc.
* ``parameter_space``, a dictionary of parameters (c.f. :ref:`param_space`)

The difference between ``job_script_dependencies`` and ``required_files`` is that the ``required_files`` will be copied into the bottom-level directory where the program is run from, i.e. into every specific *run* directory for every invocation over the parameter space.

- ``required_files`` is typically used for ``*.inputs`` chombo-discharge files, physical/chemical input files like ``*.json`` files, or other plain data files. Sometimes extra python modules or bash-scripts might be needed at the run-level, so use this field to copy those dependencies in.
- ``job_script_dependencies``, as the name implies, should point to whatever code is needed to configure and submit the actual slurm jobs.

The ``Configurator.py`` script will set up directory structures and copy files into place, then launch slurm array jobs over all the configured parameter space referenced in each database. Then the same is repeated for the second-level studies. These second-level slurm array jobs are made dependent on the database jobs, essentially securing that they are run in sequence.

.. important::

   It is up to the `job_script` to submit the actual slurm jobs. Facilities are in place to translate a given slurm array job id/index into the correct parameter values.

.. code-block:: python
    :caption: directory structure example

    import numpy as np

    inception_stepper = {
        'identifier': 'inception_stepper',
        'output_directory': 'is_db',
        'program': 'main{DIMENSIONALITY}d.Linux.64.mpic++.gfortran.OPTHIGH.MPI.ex',
        'job_script': 'DischargeInceptionJobscript.py',
        'job_script_dependencies': [
            'GenericArrayJob.sh',
            'ParseReport.py',
            ...
            ],
        'required_files': [
            'master.inputs',
            'transport_data.txt'
            ],
        'parameter_space': {
            ...
            }
        }

    plasma_study = {
        'identifier': 'photoion',
        'output_directory': 'study0',
        'program': 'main{DIMENSIONALITY}d.Linux.64.mpic++.gfortran.OPTHIGH.MPI.ex',
        'job_script': 'PlasmaJobscript.py',
        'job_script_dependencies': [
            'GenericArrayJob.sh',
            ...
            ],
        'required_files': [
            'master.inputs',
            'chemistry.json',
            'detachment_rate.dat',
            'electron_transport_data.dat'
            'Analyze.py',
            ],
        'parameter_space': {
            ...
            }
        }

    top_object = dict(
            databases=[inception_stepper],
            studies=[plasma_study]
            )

The example above has a more realistic structure. How the parameter spaces are defined can be found in a later section.

Note the use of a templated filename for the ``program`` field, where the part ``"{DIMENSIONALITY}"`` is substituted with the dimension specified on the command line using the ``--dim`` flag.

Just after issuing this command, when the first slurm job for the database named *'inception_stepper'* has just started in the subdirectory ``run_0``, the resulting file hierarchy from this could look like:

.. code-block:: bash


    $ ls -R --file-type output-dir
    .:
    is_db/  study0/

    ./is_db:
    array_job_id                      jobscript_symlink@                                 run_0/
    DischargeInceptionJobscript.py  master.inputs                                      structure.json
    GenericArrayJob.sh              ParseReport.py                                    transport_data.txt
    index.json                        main3d.Linux.64.mpic++.gfortran.OPTHIGH.MPI.ex

    ./is_db/run_0:
    chk/    geo/           mpi/             plt/    pout.1  pout.3  main@  restart/
    crash/  master.inputs  parameters.json  pout.0  pout.2  pout.4  regrid/   transport_data.txt

    ./study0:
    Analyze.py                   GenericArrayJob.sh  ParseReport.py
    array_job_id                 inception_stepper@    PlasmaJobscript.py
    chemistry.json               index.json            main3d.Linux.64.mpic++.gfortran.OPTHIGH.MPI.ex
    ConfigUtil.py               jobscript_symlink@    run_0/
    detachment_rate.dat          JsonRequirement.py   structure.json
    electron_transport_data.dat  master.inputs

    ./study0/run_0:
    Analyze.py      detachment_rate.dat          GenericArrayJob.sh  parameters.json
    chemistry.json  electron_transport_data.dat  master.inputs         main@

Do notice:

* The rather self-explainatory named ``jobscript_symlink`` symlink pointing to the jobscripts:

    .. code-block:: bash

        output-dir/is_db$ readlink jobscript_symlink
        DischargeInceptionJobscript.py

        output-dir/study0$ readlink jobscript_symlink
        PlasmaJobscript.py

* The ``study0/inception_stepper`` symlink pointing across the file hierarchy:

    .. code-block:: bash

        output-dir/study0$ readlink inception_stepper
        ../is_db

* The ``main`` symlinks in the *"run_*"* sub-directories. These point to the actual executable in their respective parent directories.

    .. code-block:: bash

        output-dir/is_db/run_0$ readlink main
        ../main3d.Linux.64.mpic++.gfortran.OPTHIGH.MPI.ex

* A job-script typically receives an array job index from slurm (through the environment variable ``$SLURM_ARRAY_TASK_ID``), and must use this to find the relevant parameters, dependent databases, get structural metadata and enter its own run-subdirectory and execute code there.
* For each database/study there are certain metadata files that are generated to make it possible to programatically traverse the created file-hierarchy from within the jobscripts or from within post-simulation analysis scripts. These files becomes especially imortant when the second-level studies have to traverse the databases' result hierarchies to retrieve and parse database results before launching their own slurm jobs.

    .. note::

        Sometimes, one need to manipulate simulation input files directly from the job-scripts, e.g. to change some parameter depending on a *database* result. Python utility functions are provided to manipulate configuration files on-the-fly in this intermediate step. C.f. examples in the :ref:`ex_database` for usage.

    Generated files:

    * ``array_job_id`` containing a single integer; the slurm array job id for the this database/study
    * ``index.json``, containing a mapping between specific array job indices and all parameter sets for this database/study
    * ``structure.json`` a parsed dump of the overall structure of the database/study. This matches a parsed export of the corresponding section in the original `run_definition`. Included both for data consistency and for usage by the jobscripts to get extra metadata for setting up batch jobs.
    * ``run_*/parameters.json`` containing the actual parameter space point for that run.


The `Configurator.py` script contains helper code to in-place manipulate both `.*inputs` files (normally used to specify chombo-discharge parameters), as well as generic structured `.json` files (e.g. used by chombo-discharge or physical/chemical data input.

.. _param_space:

Defining Parameter Spaces
-------------------------

A parameter space is a dictionary where the uniquely named keys (also dictionaries) are the parameters.

.. code-block:: python

   "parameter_space" = {
            "parameter_name_0":{
                ...
            },
            "another_descriptive_parameter_name":{
                ...
            },
            "some_other_parameter_name":{
                ...
            }
        }

Each parameter can contain several fields:

* ``database``: unique identifier referencing a database study. This specifies that this parameter is used in a database, and hence that this study depends on the referenced database
* ``target``: the file target (either ``*.json`` or ``*.inputs`` files))
* ``uri``: (abbr. of *Uniform Resource Identifier*); the address to the resource you want to change within the target file.
* ``values``: ``list()``/``[]`` of values. Scalars should be written as ``[scalar-value]``. Depending on the uri, this can be a 2nd order list (list of lists) if the uri references several uri endpoints. In that case the parameter will change two or more uri targets at the same time.

Continuing the example from the previous section:

.. code-block:: python
    :caption: directory structure example cont...

    import numpy as np

    inception_stepper = {
        'identifier': 'inception_stepper',
        'output_directory': 'is_db',
        ..
        'parameter_space': {
            "pressure": {
                "target": "master.inputs",
                "uri": "DischargeInception.pressure"
                },
            "geometry_radius": {
                "target": "master.inputs",
                "uri": "Rod.radius",
                },
            }
        }

    plasma_study = {
        'identifier': 'photoion',
        'output_directory': 'study0',
        ...
        'parameter_space': {
            "geometry_radius": {
                "database": "inception_stepper",  # database dependency
                "target": "master.inputs",
                "uri": "Rod.radius",
                "values": [1e-3, 2e-3, 3e-3]
                },
            "pressure": {
                "database": "inception_stepper",  # database dependency
                "target": "chemistry.json",
                "uri": ["gas", "law", "ideal_gas", "pressure"],
                "values": np.arange(1e5, 11e5, 1e5).tolist()
                },
            "photoionization": {
                "target": "chemistry.json",
                "uri": [
                    "photoionization",
                    [
                        '+["reaction"=<chem_react>"Y + (O2) -> e + O2+"]',  # non-optional match
                        '*["reaction"=<chem_react>"Y + (O2) -> (null)"]'  # optional match (create-if-not-exists)
                        ],
                    "efficiency"
                    ],
                "values": [[1.0, 0.0]]  #[[float(v), float(1.0-v)] for v in np.arange(0.0, 1.0, 1.0)]
                },
            }
        }

    top_object = dict(
            databases=[inception_stepper],
            studies=[plasma_study]
            )

The actual parameter values are typically specified for the top study definition, not the databases. The database only specifies where changes are to be made for a given value.

In this example there are several distinctly named parameters changing different aspects of the simulations:

* ``geometry_radius``:

    Marked as dependent on the database; meaning that this study will run after the database study.

    .. important::

        Both the database and the study has the same ``target`` file name and ``uri`` field, namely the ``master.inputs`` chombo-discharge input file and its ``Rod.radius`` field. Note that these are now different files residing within the output directory file hierarchy.

    This parameter contributes a factor 3 to the overall parameter space size.

* ``pressure``:

    List of values (Evaluates to ``[100000.0, 200000.0, ..., 900000.0, 1000000.0]``).

    The database will write this parameter to the ``master.inputs`` file by changing the ``DischargeInception.pressure`` (uri-field) input parameter, while the study has a different target, utilizing the json-writing capabilities to change the ``pressure`` field in the json hierarchy according to the list in the uri-field.

    This parameter contributes a factor 10 to the overall parameter space size.

* ``photoionization``:

    This is the most complex parameter. It only affects the ``chemistry.json`` target in the study.

    As can be seen in the uri specification the second level is a list of length 2. This means that this parameter changes two fields in ``chemistry.json`` at the same time. Similarly, the ``values`` field is a double list, where the first element of each contained list will be written to the uri of the first target field and the second element of each contained list will be written to the uri of the second target field.

    This, the value ``[[1.0, 0.0]]`` is to be regarded as a scalar quantity in the parameter space, and this parameter contributes a factor 1 to the overall parameter space size (not really affecting it).

    The resulting change for the runs in `study0/run_*/chemistry.json` will be:

    .. code-block::
        :caption: resulting chemistry.json

        {
            ...
            "photoionization": [
                {
                    "reaction": "Y + (O2) -> e + O2+",
                    "efficiency": 1.0
                },
                {
                    "reaction": "Y + (O2) -> (null)",
                    "efficiency": 0.0
                }
            ],
            ...
        }

    For the special syntax encountered see :ref:`navigating_json`.

.. _navigating_json:

Navigating JSON object hierarchies
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

The special syntax ``+["field-name"="search-value"]`` and ``*["field-name"="search-value"]`` is used to search a json list for an child object ``{...}`` containing a specific member ``"field-name"`` with a specific value "search-value".

* ``+[]`` requires the object with the member ``field-name`` to exist.
* ``*[]`` will create the object with the member ``field-name`` if it doesn't exist.

.. note::
   If searching for an object in a list where the search key itself is an JSON object, ``search-value`` can be omitted: ``+["fields-name"]``. Remember to repeat the ``fields-name`` in your uri as the next list element to select that child object if needed.

.. code-block::

    {
        "parent":{
            "list-1":[
                {
                    "field-name-0":"value_0"
                },
                {
                    "field-name-1":{
                        "target-field":"change-me!"
                    }
                },
                {
                    "field-name-2":"value_2"
                },
            ]
        }
    }

which can be found with

.. code-block:: python

    "uri" = [
        "parent",
        "list-1",
        '+["field-name-1"]',  # this finds the "unnamed" container object
        "field-name-1", # selects the object
        "target-field"  # this is the actual target within the above object
        ]

.. note::
    The special notation ``<chem_react>`` is a hint to the parser that the value searched for in this specific example should be a valid chombo-discharge chemical reaction, c.f. `"Specifying reactions" in the Plasma Model <https://chombo-discharge.github.io/chombo-discharge/Applications/CdrPlasmaModel.html?highlight=reaction#specifying-reactions>`_. The comparison of the chemical reactions between ``search-value`` and json file is thus a parsed/semantic comparison.

Navigating a json object hierarchy can sometimes involve having to search through several lists down the tree:

.. code-block::

    {
        "parent":{
            "list-level-1":[
                {
                    "field-name-0":"value_0"
                },
                {
                    "field-name-1":"value_1_0",
                    "target-field":"dont-you-change-me!"
                },
                {
                    "field-name-1":"value_1_1",
                    "target-field":"change-me!"
                },
                {
                    "field-name-2":"value_2"
                },
            ]
        }
    }

In the above contrived example, we want to change the third contained object in the list; i.e. the object that has ``"field-name-1":"value_1_1"``. The required parameter space uri would be:

.. code-block:: python

    "uri" = [
        "parent",
        "list-level-1",
        '+["field-name-1"="value_1_1"]',  # this finds the object
        "target-field"  # this is the actual target within the above object
        ]

A deeper hierarchy with two list levels to traverse:

.. code-block::

    {
        "parent":{
            "list-level-1":[
                {
                    "field-name-0":"value_0"
                },
                {
                    "field-name-1":"value_1_0",
                    "target-field":"dont-you-change-me!"
                },
                {
                    "field-name-1":"value_1_1",
                    "target-field":[
                        {
                            "search-field"="some-value",
                            "target2-field":"don-try-to-change-me!"
                        },
                        {
                            "search-field"="search-value",
                            "target2-field":"change-me!"
                        }
                    ]
                },
                {
                    "field-name-2":"value_2"
                },
            ]
        }
    }

.. code-block::

    "uri" = [
        "parent",
        "list-level-1",
        '+["field-name-1"="value_1_1"]',  # find the right object
        "target-field",  # alter this one
        '+["search-field"="search-value"]',  # find the right object
        "target2-field"  # target aquired!
        ]

The corresponding value specification for this parameter in the run_definition should be a single list: ``"values"=[new-value-0, new-value-1, ..., new-value-N]`` contributing a factor *N* to the parameter space size.

Dummy parameters
^^^^^^^^^^^^^^^^
It is possible to pass ``dummy`` parameters as a mechanism to set options for the jobscripts. A dummy parameter doesn't have to specify a target file, only a name and ``values``-field, and optionally the ``database`` field. If the values is a single element the parameter won't grow the parameter space size, and thus not contributing to an increase in the number of slurm jobs. A dummy parameter will end up in the generated ``index.json``, ``structure.json`` and ``parameters.json`` files.

Say, if study's jobscript needs a configurable parameter we can use a dummy parameter to pass it:

.. code-block:: python

    db_study = {
        ...
        "parameter_space": {
            ...  # no "K_min" parameter here
        }
    }

    main_study = {
        ...
        "parameter_space": {
            "K_min": {
                "values": [6.0]
                },
        }
    }

    top_object = dict(
            databases=[db_study],
            studies=[main_study]
            )
