Local Slurm Installation (Debian/Ubuntu)
*****************************************

This guide covers installing Slurm on a single Debian or Ubuntu machine for local testing, including WSL. Both the controller (``slurmctld``) and compute node (``slurmd``) will run on the same host.

.. important::

    If running in WSL, ensure the ``memory`` setting in your `wsl-config <https://learn.microsoft.com/en-us/windows/wsl/wsl-config>`_ (either ``/etc/wsl.conf`` per-distribution or ``%homepath%\\.wslconfig`` globally) is set high enough to match the ``RealMemory`` you will configure in ``slurm.conf``, plus a margin for the OS itself.

Step 1 — Install packages
==========================

.. code-block:: bash

    sudo apt-get update
    sudo apt-get install -y munge libmunge-dev slurmctld slurmd slurm-client

`Munge <https://dun.github.io/munge/>`_ provides credential authentication between the controller and compute nodes. A munge key is generated automatically during installation.

Step 2 — Start Munge
=====================

Munge must be running before the Slurm daemons start:

.. code-block:: bash

    sudo systemctl start munge
    sudo systemctl status munge

Step 3 — Configure slurm.conf
==============================

Slurm is configured through ``/etc/slurm/slurm.conf``. Two values must match your machine: the hostname and the hardware spec of the node.

Get your hostname:

.. code-block:: bash

    hostname -s

Get the hardware spec that Slurm should use for the node (run as root so it can read all hardware info):

.. code-block:: bash

    sudo slurmd -C

This prints a ``NodeName=...`` line with the correct ``CPUs``, ``RealMemory``, etc. for your machine. Use this line verbatim in the config below.

A minimal ``/etc/slurm/slurm.conf`` for a single-node setup:

.. code-block:: none
    :caption: /etc/slurm/slurm.conf

    ClusterName=localcluster
    SlurmctldHost=my-hostname          # replace with output of: hostname -s

    MpiDefault=none
    ProctrackType=proctrack/linuxproc
    TaskPlugin=task/none
    SchedulerType=sched/backfill
    SelectType=select/cons_tres
    SelectTypeParameters=CR_Core

    SlurmctldLogFile=/var/log/slurm/slurmctld.log
    SlurmdLogFile=/var/log/slurm/slurmd.log
    StateSaveLocation=/var/spool/slurmctld
    SlurmdSpoolDir=/var/spool/slurmd

    # Replace with the NodeName line from: sudo slurmd -C
    NodeName=my-hostname CPUs=4 RealMemory=7800 State=UNKNOWN

    PartitionName=debug Nodes=ALL Default=YES MaxTime=INFINITE State=UP

.. note::

    ``SlurmctldHost`` and the ``NodeName`` hostname must both match the output of ``hostname -s`` exactly, or the daemons will fail to register with each other.

Step 4 — Create required directories
======================================

.. code-block:: bash

    sudo mkdir -p /var/log/slurm /var/spool/slurmctld /var/spool/slurmd
    sudo chown -R slurm:slurm /var/log/slurm /var/spool/slurmctld /var/spool/slurmd
    sudo touch /var/log/slurm/slurmctld.log /var/log/slurm/slurmd.log
    sudo chown slurm:slurm /var/log/slurm/slurmctld.log /var/log/slurm/slurmd.log

Step 5 — Start Slurm daemons
==============================

.. code-block:: bash

    sudo systemctl start slurmctld
    sudo systemctl start slurmd

Check that both are running:

.. code-block:: bash

    sudo systemctl status slurmctld slurmd

Step 6 — Verify
================

.. code-block:: bash

    $ sinfo
    PARTITION AVAIL  TIMELIMIT  NODES  STATE NODELIST
    debug*       up   infinite      1   idle my-hostname

The node should show as ``idle``. If it shows ``down`` or ``drain``, check ``/var/log/slurm/slurmd.log`` for errors — the most common cause is a hostname mismatch between ``SlurmctldHost``/``NodeName`` and the actual machine hostname.

You can now submit test jobs with ``sbatch``.

Step 7 — Enable at boot (optional)
====================================

.. code-block:: bash

    sudo systemctl enable munge slurmctld slurmd
