.. _example_output_layout:

Output directory layout
========================

Just after submission (before any SLURM job has run), the layout looks like:

.. code-block:: text

   $ ls -R --file-type ~/my_rod_study
   .:
   PDIV_DB/  study0/

   ./PDIV_DB:
   array_job_id  DischargeInceptionJobscript.py  GenericArrayJob.sh
   index.json    master.inputs                   ParseReport.py
   main2d.Linux.64.mpic++.gfortran.OPTHIGH.MPI.ex
   run_0/  structure.json  chemistry.json  electron_transport_data.dat  detachment_rate.dat
   jobscript_symlink@

   ./PDIV_DB/run_0:
   chk/  master.inputs  parameters.json  plt/  pout.*  main@
   chemistry.json  electron_transport_data.dat  detachment_rate.dat

   ./study0:
   array_job_id  chemistry.json  GenericArrayJob.sh  inception_stepper@
   index.json    master.inputs   PlasmaJobscript.py
   main2d.Linux.64.mpic++.gfortran.OPTHIGH.MPI.ex
   run_0/  structure.json  jobscript_symlink@

   ./study0/run_0:
   chemistry.json  detachment_rate.dat  electron_transport_data.dat
   master.inputs   parameters.json      main@

Key points:

* ``jobscript_symlink@`` in ``PDIV_DB/`` points to
  ``DischargeInceptionJobscript.py``; in ``study0/`` it points to
  ``PlasmaJobscript.py``.  ``GenericArrayJob.sh`` calls
  ``python ./jobscript_symlink`` without knowing which script it is.

* ``study0/inception_stepper@`` is a symlink to ``../PDIV_DB``, giving the
  plasma study jobscript direct access to inception results.

* ``run_N/main@`` in both stages points to the executable in the parent stage
  directory.  Both stages use the same binary.

* ``master.inputs`` in ``PDIV_DB/run_N/`` has ``app.mode = inception``; in
  ``study0/run_N/`` it has ``app.mode = plasma``.  The configurator writes
  this automatically.

See :ref:`arch_output_dir` for a full description of every metadata file.
