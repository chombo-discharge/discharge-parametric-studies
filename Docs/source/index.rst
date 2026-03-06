Discharge Parametric Studies
****************************

Documentation for a framework of Python and SLURM scripts for running
multilevel chombo-discharge studies over wide parameter spaces.

.. raw:: html

   <style>
   section#installation,
   section#architecture,
   section#writing-jobscripts,
   section#example-rod-case {
       display:none;
   }
   </style>

.. only:: latex

   .. toctree::
      :caption: Contents

Installation
************

.. toctree::
   :maxdepth: 2
   :caption: Installation
   :hidden:

   Installation/Prerequisites
   Installation/GetSource
   Installation/Venv
   Installation/Install
   Installation/Verify
   Installation/EnvVars

Architecture
************

.. toctree::
   :maxdepth: 2
   :caption: Architecture
   :hidden:

   Architecture/Overview
   Architecture/RepoLayout
   Architecture/DbStudy
   Architecture/RunDefinition
   Architecture/ParamSpace
   Architecture/JsonUri
   Architecture/DummyParams
   Architecture/OutputDir
   Architecture/SlurmConfig
   Architecture/CLI
   Architecture/CallChain
   Architecture/ScriptRoles

Writing Jobscripts
******************

.. toctree::
   :maxdepth: 2
   :caption: Writing Jobscripts
   :hidden:

   Jobscripts/WhereFit
   Jobscripts/GenericArrayJob
   Jobscripts/SetupHelper
   Jobscripts/Simple
   Jobscripts/Database
   Jobscripts/Study
   Jobscripts/HandleCombination

Example — Rod Case
******************

.. toctree::
   :maxdepth: 2
   :caption: Example — Rod Case
   :hidden:

   Example/Prerequisites
   Example/Compile
   Example/SmokeTest
   Example/ParamSpace
   Example/RunConfigurator
   Example/OutputLayout
   Example/Monitor
   Example/Inspect
   Example/Postprocess
