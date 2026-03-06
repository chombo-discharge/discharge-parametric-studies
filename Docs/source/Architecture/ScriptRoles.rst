.. _arch_script_roles:

Script roles
============

.. list-table::
   :header-rows: 1
   :widths: 30 25 25 20

   * - Script
     - Role
     - Reads
     - Called by
   * - ``Util/GenericArrayJob.sh``
     - SLURM wrapper; loads modules, activates venv
     - ``DISCHARGE_PS_SLURM_CONFIG`` → ``slurm.toml``
     - ``sbatch --array=...``
   * - ``GenericArrayJobJobscript.py``
     - Runs plasma solver for one voltage
     - ``index.json``, ``*.inputs``, ``slurm.toml``
     - Second ``sbatch`` in ``PlasmaJobscript.py``
   * - ``DischargeInceptionJobscript.py``
     - Runs inception solver, validates voltage range
     - ``index.json``, ``*.inputs``, ``report.txt``
     - First ``sbatch`` on database study
   * - ``PlasmaJobscript.py``
     - Orchestrates voltage sweep: reads inception results, creates subdirs, submits child array
     - ``structure.json``, ``parameters.json``, ``../inception_stepper/``, ``report.txt``
     - First ``sbatch`` on plasma study
   * - ``discharge_ps/configurator.py``
     - Expands parameter space, creates dirs, submits initial arrays
     - ``Runs.py`` / ``top_object``
     - ``discharge-ps run`` CLI
   * - ``discharge_ps/config_util.py``
     - URI injection, file helpers, SLURM task ID, jobscript setup
     - Called by all jobscripts
     - All jobscripts
