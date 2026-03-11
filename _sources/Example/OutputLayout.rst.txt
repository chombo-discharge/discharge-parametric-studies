.. _example_output_layout:

Output directory layout
========================

Just after submission (before any SLURM job has run), the layout looks like:

.. code-block:: text

   $ ls -R --file-type ~/my_rod_study
   .:
   pdiv_database/  plasma_simulations/

   ./pdiv_database:
   array_job_id  DischargeInceptionJobscript.py  ExtractElectronPositions.py
   GenericArrayJob.sh  index.json  master.inputs  chemistry.json
   electron_transport_data.dat  ion_transport_data.dat  detachment_rate.dat
   main2d.Linux.64.mpic++.gfortran.OPTHIGH.MPI.ex
   run_0/  run_1/  run_2/  structure.json
   jobscript_symlink@

   ./pdiv_database/run_0:
   master.inputs  parameters.json  chemistry.json
   electron_transport_data.dat  ion_transport_data.dat  detachment_rate.dat
   chk/  plt/  pout.*  main@

   ./plasma_simulations:
   array_job_id  chemistry.json  GenericArrayJob.sh  GenericArrayJobJobscript.py
   ExtractElectronPositions.py  inception_stepper@  index.json  master.inputs
   PlasmaJobscript.py
   main2d.Linux.64.mpic++.gfortran.OPTHIGH.MPI.ex
   run_0/  run_1/  run_2/  structure.json  jobscript_symlink@

   ./plasma_simulations/run_0:
   chemistry.json  detachment_rate.dat  electron_transport_data.dat
   ion_transport_data.dat  master.inputs  parameters.json  main@

Key points:

* ``jobscript_symlink@`` in ``pdiv_database/`` points to
  ``DischargeInceptionJobscript.py``; in ``plasma_simulations/`` it points to
  ``PlasmaJobscript.py``.  ``GenericArrayJob.sh`` calls
  ``python ./jobscript_symlink`` without knowing which script it is.

* ``plasma_simulations/inception_stepper@`` is a symlink to
  ``../pdiv_database``, giving the plasma study jobscript direct access to
  inception results.  The symlink name matches the database ``identifier``
  (``'inception_stepper'``).

* ``run_N/main@`` in both stages points to the executable in the parent stage
  directory.  Both stages use the same binary.

* ``master.inputs`` in ``pdiv_database/run_N/`` has ``app.mode = inception``; in
  ``plasma_simulations/run_N/`` it has ``app.mode = plasma``.  The configurator
  writes this automatically via ``input_overrides``.

See :ref:`arch_output_dir` for a full description of every metadata file.
