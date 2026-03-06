.. _install_prereqs:

Prerequisites
=============

Python
------

``discharge-ps`` requires **Python ≥ 3.10**.

``numpy`` is a declared dependency and is installed automatically by ``pip``.
Certain post-processing scripts additionally require ``matplotlib`` and ``scipy``,
available via the ``[plot]`` extra:

.. code-block:: bash

   pip install -e ".[plot]"

chombo-discharge
----------------

A compiled `chombo-discharge <https://chombo-discharge.github.io/>`_ installation
is required.  The environment variable ``DISCHARGE_HOME`` must be set and point to
the root of that installation before compiling any ``Exec/`` case.

SLURM
-----

SLURM client tools (``sbatch``, ``squeue``, ``sinfo``, ``scancel``) must be
available on the machine from which you submit jobs.  On HPC clusters these are
typically pre-installed by system administrators — you need only an account and
partition access.

For local testing, both the SLURM controller (``slurmctld``) and the worker
daemon (``slurmd``) can run on the same workstation or WSL instance.  See the
`SLURM documentation <https://slurm.schedmd.com/documentation.html>`_ for
installation instructions.
