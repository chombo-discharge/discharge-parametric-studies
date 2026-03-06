.. _example_param_space:

Inspecting the parameter space definition
==========================================

Open ``Exec/Rod/Studies/PressureStudy/Runs.py`` to inspect or adjust the
parameter space.  The top-level structure is:

.. code-block:: python

   top_object = dict(
       databases=[inception_stepper],
       studies=[plasma_study_1]
   )

Both entries point to the flat ``Exec/Rod/`` directory:

.. code-block:: python

   rod_dir = '../../'

**Database** (``inception_stepper``) — computes inception voltages over a grid
of pressures and rod radii.  ``app.mode=inception`` is injected on the command
line by ``DischargeInceptionJobscript.py`` at runtime, so it is not part of the
parameter space here.  Pressure is written into ``chemistry.json`` so both
stages always use the same gas conditions:

.. code-block:: python

   'parameter_space': {
       "pressure": {
           "target": "chemistry.json",
           "uri": ["gas", "law", "ideal_gas", "pressure"]
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

**Study** (``plasma_study_1``) — runs plasma simulations using the database
results.  ``app.mode`` is set to ``plasma`` via its own parameter entry so the
same binary runs the full ItoKMC simulation.  Parameters marked with
``"database": "inception_stepper"`` declare a SLURM dependency: study jobs will
not start until all database jobs have completed.  The applied voltage comes
from the inception results and is set per voltage sub-run:

.. code-block:: python

   'parameter_space': {
       "app_mode": {
           "target": "master.inputs",
           "uri": "app.mode",
           "values": ["plasma"]
       },
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
       "K_min": {"values": [6]},
       "K_max": {
           "database": "inception_stepper",
           "values": [12.0]
       },
       ...
   }

See :ref:`arch_param_space` and :ref:`arch_db_study` for a full explanation of
parameter space syntax and database dependencies.
