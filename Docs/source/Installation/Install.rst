.. _install_package:

Install the package
===================

Install in *editable* mode so that local edits take effect immediately without
reinstalling:

.. code-block:: bash

   pip install -e .                 # core only
   pip install -e ".[plot]"         # with matplotlib + scipy
