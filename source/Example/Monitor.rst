.. _example_monitor:

Monitoring jobs
===============

.. code-block:: bash

   squeue -u $USER

   # Check the submitted job IDs
   cat ~/my_rod_study/pdiv_database/array_job_id       # database job ID
   cat ~/my_rod_study/plasma_simulations/array_job_id  # study job ID (depends on above)

The study job will remain in ``Pending`` state (dependency not yet satisfied)
until the database job finishes successfully.
