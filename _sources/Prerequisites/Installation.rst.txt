Installation
============

``discharge-ps`` is distributed as an installable Python package.
Installing it into a virtual environment makes the ``discharge-ps`` entry-point command available and allows SLURM compute nodes to resolve package imports without any ``sys.path`` manipulation.

Create and activate a virtual environment
------------------------------------------

From the repository root:

.. code-block:: bash

   python -m venv .venv
   source .venv/bin/activate

Install the package
-------------------

Install in *editable* mode so that local edits take effect immediately without reinstalling:

.. code-block:: bash

   pip install -e .

To also install the optional plotting dependencies (``matplotlib``, ``scipy``):

.. code-block:: bash

   pip install -e ".[plot]"

Verify
------

.. code-block:: bash

   which discharge-ps          # should point into .venv/bin/
   discharge-ps --help

Configure SLURM compute nodes
------------------------------

Compute nodes need the same virtual environment activated before running a job script.
``GenericArrayJob.sh`` reads the ``DISCHARGE_PS_VENV`` environment variable and activates the virtual environment automatically before calling the job script.

Add the following to your ``.bashrc``, SLURM prologue, or cluster environment module:

.. code-block:: bash

   export DISCHARGE_PS_VENV=/path/to/repo/.venv

.. note::

   The path must be reachable from all compute nodes — typically a shared filesystem
   such as ``$HOME`` or a project scratch space.
