.. _jobscripts_handle_combination:

Parameter injection with ``handle_combination()``
==================================================

``handle_combination(pspace, comb_dict)`` is the same function the configurator
uses to write parameter values into ``*.inputs`` and ``*.json`` files.  Calling
it from a jobscript lets you inject runtime-computed values (e.g. voltages from
a database result) using the same URI syntax as the run definition.

*  **``*.inputs`` target** — ``uri`` is a dot-separated ParmParse key:

   .. code-block:: python

      handle_combination(
          {"voltage": {"target": input_file, "uri": "plasma.voltage"}},
          {"voltage": 42000.0}
      )

*  **``*.json`` target** — ``uri`` is a list traversing the JSON hierarchy;
   see :ref:`arch_param_space` and :ref:`arch_json_uri` for syntax details.

The *fake pspace / comb_dict* pattern from ``PlasmaJobscript.py`` lets you
write multiple fields in one call:

.. code-block:: python

   comb_dict = dict(
       voltage=row[0],
       sphere_dist_props=[center_pos, tip_radius],
   )
   pspace = {
       "voltage": {
           "target": voltage_dir / input_file,
           "uri": "plasma.voltage",
       },
       "sphere_dist_props": {
           "target": voltage_dir / 'chemistry.json',
           'uri': [
               'plasma species',
               '+["id"="e"]',
               'initial particles',
               '+["sphere distribution"]',
               'sphere distribution',
               ['center', 'radius']   # two simultaneous writes
           ]
       },
   }
   handle_combination(pspace, comb_dict)
