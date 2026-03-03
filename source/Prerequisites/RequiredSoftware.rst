Required Software
*****************

Slurm
=====

`Slurm <https://slurm.schedmd.com>`_ (Simple Linux Utility for Resource Management) is an open-source workload manager and job scheduler for Linux clusters. It handles queuing, resource allocation, and execution of batch jobs across one or more compute nodes.

This project uses Slurm to:

* Submit array jobs (``sbatch --array``) — each array index maps to one point in the parameter space
* Enforce job dependencies — database jobs must complete successfully before dependent study jobs are allowed to start
* Supply ``$SLURM_ARRAY_TASK_ID`` to jobscripts so they can locate their own parameter set and run directory

Slurm has three main components:

* ``slurmctld`` — the central controller daemon; manages the job queue and scheduling decisions
* ``slurmd`` — the compute node daemon; executes jobs as directed by the controller
* Client tools (``sbatch``, ``squeue``, ``sinfo``, ``scancel``) — used to submit and monitor jobs

**For local testing**, both ``slurmctld`` and ``slurmd`` can run on the same machine — a workstation or WSL instance is sufficient for small test runs. See :doc:`Example` for a step-by-step setup guide.

**On a cluster**, Slurm is typically pre-installed and managed by system administrators. You need only the client tools and access to an account and partition.

Python
======

*configurator.py* and its helper modules require Python >= 3.13.0. Only standard library modules are used by the configurator itself.

Certain example analysis scripts in the repository additionally require:

* ``numpy``
