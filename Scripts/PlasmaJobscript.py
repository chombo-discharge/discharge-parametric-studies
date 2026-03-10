#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Plasma study jobscript — sets up and submits the per-voltage SLURM array.

This script runs once per parameter combination in the plasma study stage
(invoked as a SLURM array task via ``GenericArrayJob.sh``).  Its job is to
bridge the inception-stepper database with a set of full plasma simulations
at the voltages where the ionisation integral K is meaningful.

Execution flow
--------------
1. **Navigate to run directory** — reads ``structure.json`` to find the run
   prefix, then uses ``setup_jobscript_logging_and_dir`` to change into the
   correct ``run_<i>/`` subdirectory for this SLURM task ID.

2. **Load database metadata** — reads ``../inception_stepper/structure.json``
   (to get the parameter key order) and the corresponding ``index.json`` (to
   map parameter values to run indices).

3. **Resolve K range and polarity** — reads ``plasma_polarity``, ``K_min``,
   and ``K_max`` from ``parameters.json``; falls back to reading
   ``DischargeInceptionStepper.limit_max_K`` from the ``.inputs`` file if
   ``K_max`` is absent.

4. **Build and submit the voltage array** — calls the four helpers in sequence:

   a. :func:`find_database_run` — resolves which ``PDIV_DB/run_<j>/``
      directory contains results for these parameters.
   b. :func:`extract_voltage_table` — reads ``report.txt`` from that database
      run and returns the (voltage, K, position) rows within [K_min, K_max].
   c. :func:`create_voltage_directories` — creates one ``voltage_<i>/``
      directory per table row, writes ``index.json``, copies required files,
      and injects voltage + electron seed position into each run's input files.
   d. :func:`submit_voltage_array` — submits the resulting array to SLURM and
      records the job ID.

Author André Kapelrud
Copyright © 2025 SINTEF Energi AS
"""

import json
import logging
import os
import re
import sys
from pathlib import Path
from subprocess import PIPE, Popen

# local imports
sys.path.append(os.getcwd())  # needed for local imports from slurm scripts
from ExtractElectronPositions import parse_report_file  # noqa: E402
from discharge_inception.config_util import (  # noqa: E402
    DEFAULT_OUTPUT_DIR_PREFIX,
    backup_dir, backup_file,
    build_sbatch_resource_args, copy_files,
    handle_combination, load_slurm_config,
    read_input_float_field, setup_jobscript_logging_and_dir,
)

MAX_BACKUPS = 10
VOLTAGE_DIR_PREFIX = "voltage_"


def find_database_run(parameters: dict, db_structure: dict, db_index: dict) -> Path:
    """Locate the database run directory matching *parameters*.

    Searches *db_index* for the parameter combination defined by
    *db_structure['space_order']* and returns the path to the matched run
    directory inside the database study.

    Parameters
    ----------
    parameters : dict
        The current run's parameter dict, typically loaded from
        ``parameters.json``.  Must contain every key listed in
        ``db_structure['space_order']``.
    db_structure : dict
        The parsed ``structure.json`` of the inception database stage.
        Must contain ``'space_order'`` (ordered list of parameter keys)
        and ``'identifier'`` (the database directory name relative to
        the parent of the current working directory).
    db_index : dict
        The parsed ``index.json`` of the inception database stage.
        Expected keys: ``'index'`` (mapping str(i) → parameter list)
        and optionally ``'prefix'`` (run directory name prefix,
        defaults to ``DEFAULT_OUTPUT_DIR_PREFIX``).

    Returns
    -------
    Path
        Relative path ``../identifier/prefix<i>`` pointing to the
        matching database run directory.

    Raises
    ------
    ValueError
        If ``db_structure`` does not contain ``'space_order'``.
    RuntimeError
        If no entry in *db_index* matches the required parameter
        combination.
    """
    log = logging.getLogger(sys.argv[0])

    if 'space_order' not in db_structure:
        raise ValueError("missing field 'space_order' in database "
                         f"'{db_structure['identifier']}'")
    db_param_order = db_structure['space_order']
    db_path = Path('..') / db_structure['identifier']

    db_search_index = [parameters[p] for p in db_param_order]

    # build a reverse lookup map for O(1) search (JSON-serialised list as key)
    reverse_index = {json.dumps(params): int(db_i)
                     for db_i, params in db_index['index'].items()}
    index = reverse_index.get(json.dumps(db_search_index), -1)
    if index < 0:
        raise RuntimeError(
            f'Unable to find db parameter_set: {db_param_order} = {db_search_index}'
        )
    log.info(
        f"Found database parameters {db_param_order} = {db_search_index} "
        f"at index: {index}"
    )

    db_run_path = db_path
    if 'prefix' in db_index:
        db_run_path /= db_index['prefix'] + str(index)
    else:
        db_run_path /= DEFAULT_OUTPUT_DIR_PREFIX + str(index)
    return db_run_path


def extract_voltage_table(report_path: Path, polarity: int,
                          K_min: float, K_max: float) -> list:
    """Read *report_path* and return a voltage table filtered to [K_min, K_max].

    Parses the data table in the inception stepper ``report.txt`` via
    ``parse_report_file``, then trims each polarity's rows to the voltage
    range where K lies within [K_min, K_max], rounding the upper bound up
    to the nearest available row above K_max.  Both polarity tables are
    merged and sorted by ascending voltage before returning.

    Parameters
    ----------
    report_path : Path
        Path to the ``report.txt`` produced by the inception stepper for
        the matching database run.
    polarity : int
        Which voltage polarities to include.  Use ``1`` for positive only,
        ``-1`` for negative only, or ``0`` for both.
    K_min : float
        Lower bound on the ionisation integral K.  Rows with K below this
        value are excluded (the last row at or below K_min is kept as the
        lower boundary).
    K_max : float
        Upper bound on the ionisation integral K.  Rows with K above this
        value are excluded, except that the first row above K_max is
        included to bracket the range from above.

    Returns
    -------
    list of tuple
        Each entry is ``(voltage, K, position)`` where *voltage* is the
        applied voltage (V), *K* is the ionisation integral value, and
        *position* is the spatial coordinate tuple of the maximum-K point.
        The list is sorted by ascending voltage.
    """
    report_data = parse_report_file(report_path,
                                    ['+/- Voltage',
                                     'Max K(+)',
                                     'Max K(-)',
                                     'Pos. max K(+)',
                                     'Pos. max K(-)'])
    report_data = report_data[1]  # discard column names

    def pick_data(data):
        imin, iMax = (0, 0)
        for i, (_, K, _) in enumerate(data):
            if K <= K_min:
                imin = i
            if K <= K_max:
                iMax = i
        if data[iMax][1] != K_max and iMax + 1 < len(data):
            iMax += 1  # round to nearest K higher than K_max
        return data[imin:iMax + 1]

    table = []
    if polarity >= 0:
        table.extend(pick_data([(v, Kp, pos_p)
                                for v, Kp, _, pos_p, _ in report_data]))
    if polarity <= 0:
        table.extend(pick_data([(v, Km, pos_n)
                                for v, _, Km, _, pos_n in report_data]))

    return sorted(table, key=lambda t: t[0])


def create_voltage_directories(table: list, structure: dict,
                               input_file: str, parameters: dict) -> None:
    """Create per-voltage run directories, copy files, and inject parameters.

    Writes ``index.json`` for the voltage array, creates ``voltage_<i>/``
    directories, symlinks the executable, copies required files, and injects
    the voltage and particle-position parameters into each run's input files.

    For each entry in *table* this function:

    1. Backs up any pre-existing ``voltage_<i>/`` directory (up to
       ``MAX_BACKUPS`` generations) to avoid silently overwriting prior runs.
    2. Creates the directory skeleton: ``voltage_<i>/`` and
       ``voltage_<i>/logs/``.
    3. Symlinks ``voltage_<i>/main`` → ``../main`` (the shared executable).
    4. Copies all ``required_files`` from *structure* into the new directory.
    5. Builds a parameter combination from the voltage value and the
       electron seed position (Y-coordinate only, with X and Z set to zero),
       then calls ``handle_combination`` to write those values into the
       target ``.inputs`` and ``chemistry.json`` files.

    The electron sphere distribution is centred at the seed position with
    a radius of half the electrode tip radius (``0.5 * geometry_radius``).

    Parameters
    ----------
    table : list of tuple
        Voltage table as returned by :func:`extract_voltage_table`.
        Each entry is ``(voltage, K, position)``; the Y-component of
        *position* is used as the electron seed coordinate.
    structure : dict
        Parsed ``structure.json`` for the current plasma study stage.
        Must contain ``'required_files'`` (list of file names to copy
        into each voltage directory).
    input_file : str
        Name of the ``.inputs`` file inside the voltage directory that
        receives the ``plasma.voltage`` field.
    parameters : dict
        The current run's parameter dict (from ``parameters.json``).
        Must contain ``'geometry_radius'`` (tip radius in metres), which
        determines the electron seed sphere radius.

    Raises
    ------
    RuntimeError
        If ``'geometry_radius'`` is absent from *parameters*.
    """
    log = logging.getLogger(sys.argv[0])

    if 'geometry_radius' not in parameters:
        raise RuntimeError("'geometry_radius' is missing from 'parameters.json'")

    enum_table = list(enumerate(table))

    index_path = Path('index.json')
    # guard for reposting of the job
    backup_file(index_path, max_backups=MAX_BACKUPS)

    # write voltage index
    with open(index_path, 'w') as voltage_index_file:
        json.dump(dict(
            key=["voltage", "K", "particle_position"],
            prefix=VOLTAGE_DIR_PREFIX,
            index={i: item for i, item in enum_table}
        ), voltage_index_file, indent=4)

    if not os.path.islink('jobscript_symlink'):
        # recreate the generic job-script symlink, so that the actual .sh jobscript works:
        os.symlink('GenericArrayJobJobscript.py', 'jobscript_symlink')

    # grab original file names from structure
    required_files = [Path(f).name for f in structure['required_files']]

    for i, row in enum_table:
        voltage_dir = Path(f'{VOLTAGE_DIR_PREFIX}{i:d}')

        # don't delete old invocations
        backup_dir(voltage_dir, max_backups=MAX_BACKUPS)
        os.makedirs(voltage_dir, exist_ok=False)
        os.makedirs(voltage_dir / 'logs')

        # further symlink program executable
        link_path = voltage_dir / 'main'
        if not link_path.is_symlink():
            os.symlink(Path('../main'), link_path)

        copy_files(log, required_files, voltage_dir)

        # reuse the combination writing code from the configurator / ConfigUtil, by
        # building a fake combination and parameter space:
        particle_pos = [0.0, row[2][1], 0.0]  # strip X and Z coords
        comb_dict = dict(
            voltage=row[0],
            sphere_dist_props=[
                particle_pos,                          # center position
                0.5 * parameters['geometry_radius']    # half the tip's radius
            ],
            single_particle_position=particle_pos      # center position
        )
        distribution_type = 'sphere distribution'
        pspace = {
            "voltage": {
                "target": voltage_dir / input_file,
                "uri": "plasma.voltage",
            },
            "sphere_dist_props": {
                "target": voltage_dir / 'chemistry.json',
                'uri': [
                    'plasma species',
                    '+["id"="e"]',  # find electrons in list
                    'initial particles',
                    f'+["{distribution_type}"]',
                    distribution_type,  # TODO: fix duplicity here
                    ['center', 'radius']  # NB! two parameters
                ]
            },
            "single_particle_position": {
                "target": voltage_dir / 'chemistry.json',
                'uri': [
                    'plasma species',
                    '+["id"="e"]',  # find electrons in list
                    'initial particles',
                    f'+["single particle"]',
                    "single particle",  # TODO: fix duplicity here
                    'position'  # NB! two parameters
                ]
            }
        }
        handle_combination(pspace, comb_dict)


def submit_voltage_array(num_voltages: int, identifier: str, slurm: dict) -> int:
    """Submit a SLURM voltage array job and return the job ID.

    Calls ``sbatch`` with ``--array=0-<num_voltages-1>`` and resource
    arguments derived from the ``plasma`` stage of *slurm*.  Parses the
    "Submitted batch job <id>" line from sbatch's stdout to capture the
    job ID, then writes it to ``logs/array_job_id`` (backing up any
    previous file first).

    Parameters
    ----------
    num_voltages : int
        Total number of voltage directories created by
        :func:`create_voltage_directories`.  Determines the SLURM array
        size: tasks are indexed ``0`` through ``num_voltages - 1``.
    identifier : str
        Human-readable name for the study (from ``structure['identifier']``).
        Used to label the SLURM job as ``<identifier>_voltage``.
    slurm : dict
        SLURM resource configuration as returned by ``load_slurm_config``.
        The ``'plasma'`` sub-dict is passed to ``build_sbatch_resource_args``
        to produce flags such as ``--nodes``, ``--ntasks``, etc.

    Returns
    -------
    int
        The SLURM job ID of the submitted array job, or ``-1`` if the job
        ID could not be parsed from sbatch's output (e.g. dry-run or
        submission failure).
    """
    log = logging.getLogger(sys.argv[0])

    sbatch_args = (
        [f'--array=0-{num_voltages - 1}',
         f'--job-name="{identifier}_voltage"']
        + build_sbatch_resource_args(slurm, stage='plasma')
    )

    cmdstr = 'sbatch ' + ' '.join(sbatch_args) + ' GenericArrayJob.sh'
    log.debug(f'cmd string: \'{cmdstr}\'')
    p = Popen(cmdstr, shell=True, stdout=PIPE, encoding='utf-8')

    job_id = -1
    while True:  # wait until sbatch is complete
        # try to capture the job id
        line = p.stdout.readline()
        if line:
            m = re.match('^Submitted batch job (?P<job_id>[0-9]+)', line)
            if m:
                job_id_str = m.groupdict()['job_id']
                job_id = int(job_id_str)

                array_job_id_path = Path('logs') / 'array_job_id'
                backup_file(array_job_id_path, max_backups=MAX_BACKUPS)

                with open(array_job_id_path, 'w') as job_id_file:
                    job_id_file.write(job_id_str)
                log.info(f"Submitted array job (for '{identifier}_voltage' "
                         f"combination set). [slurm job id = {job_id}]")

        if p.poll() is not None:
            break

    return job_id


def main():
    """Entry point: run the four-step plasma setup pipeline."""

    # --- 1. Read study structure and navigate to this run's directory --------
    with open('structure.json') as f:
        structure = json.load(f)
    prefix = structure.get('output_dir_prefix', DEFAULT_OUTPUT_DIR_PREFIX)
    log, task_id, run_dir, input_file = setup_jobscript_logging_and_dir(prefix=prefix)

    # --- 2. Load inception database metadata and this run's parameters -------
    with open('../inception_stepper/structure.json') as f:
        db_structure = json.load(f)

    # derive all subsequent database paths from the identifier stored in structure.json
    # so that renaming the database study doesn't silently break this script.
    db_path = Path('..') / db_structure['identifier']

    with open(db_path / 'index.json') as f:
        db_index = json.load(f)

    with open('parameters.json') as f:
        parameters = json.load(f)

    # --- 3. Resolve K range and polarity from parameters / .inputs -----------
    polarity = 0  # 1, 0, or -1
    if 'plasma_polarity' not in parameters:
        log.warning(
            "'plasma_polarity' was not found in parameters.json, "
            "running for both polarities"
        )
    else:
        if parameters['plasma_polarity'] == 'positive':
            polarity = 1
        elif parameters['plasma_polarity'] == 'negative':
            polarity = -1
        log.info(f'Running with polarity {polarity} (0:both, 1:positive, -1:negative)')

    K_min = 0
    if 'K_min' not in parameters:
        log.warning("'K_min' not found in parameters, using K_min=0")
    else:
        K_min = parameters['K_min']

    if 'K_max' not in parameters:
        log.warning("'K_max' not found in parameters, trying to read from .inputs file")
        K_max = read_input_float_field(input_file, 'DischargeInceptionStepper.limit_max_K')
        if K_max is None:
            raise RuntimeError(
                f"'{input_file}' does not contain "
                "'DischargeInceptionStepper.limit_max_K' field"
            )
        log.info(f"Using K_max={K_max}")
    else:
        K_max = parameters['K_max']

    # --- 4. Run the four-step plasma setup pipeline --------------------------
    db_run_path = find_database_run(parameters, db_structure, db_index)
    table = extract_voltage_table(db_run_path / 'report.txt', polarity, K_min, K_max)
    create_voltage_directories(table, structure, input_file, parameters)

    slurm = load_slurm_config()
    submit_voltage_array(len(table), structure['identifier'], slurm)


if __name__ == '__main__':
    main()
