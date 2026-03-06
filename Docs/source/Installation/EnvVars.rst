.. _install_env_vars:

Environment variables
=====================

Two environment variables configure runtime behaviour on compute nodes.  Both
paths must be reachable from all compute nodes (typically a shared filesystem
such as ``$HOME`` or a project scratch space).

``DISCHARGE_PS_VENV``
   Absolute path to the ``.venv`` directory.  ``GenericArrayJob.sh`` reads this
   variable and activates the virtual environment on compute nodes before calling
   the jobscript.

``DISCHARGE_PS_SLURM_CONFIG``
   Absolute path to ``slurm.toml``.  Job scripts read this file to obtain MPI
   launcher settings, module lists, and per-stage resource requests.  See
   :ref:`arch_slurm_config` for the file format.

Add both exports to your ``.bashrc``, SLURM prologue, or cluster environment
module:

.. code-block:: bash

   export DISCHARGE_PS_VENV=/path/to/repo/.venv
   export DISCHARGE_PS_SLURM_CONFIG=/path/to/repo/slurm.toml

.. note::

   As an alternative to ``DISCHARGE_PS_SLURM_CONFIG``, standard SLURM
   environment variables (``SBATCH_ACCOUNT``, ``SBATCH_TIMELIMIT``, etc.) are
   respected by ``sbatch`` and can be used to supply resource requests without a
   ``slurm.toml`` file.
