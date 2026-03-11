"""
Robert Marskar
Copyright © 2026 SINTEF Energi AS

Slurm job status reporting for discharge-inception studies.
"""

import json
import re
import subprocess
import sys
from dataclasses import dataclass, field
from pathlib import Path

ARRAY_TASK_PAT = re.compile(r'^\d+_(\d+)$')

_STATE_MAP = {
    'PENDING':       'PENDING',
    'RUNNING':       'RUNNING',
    'COMPLETED':     'COMPLETED',
    'FAILED':        'FAILED',
    'CANCELLED':     'CANCELLED',
    'TIMEOUT':       'FAILED',
    'NODE_FAIL':     'FAILED',
    'OUT_OF_MEMORY': 'FAILED',
    'PREEMPTED':     'PENDING',
}


def classify_state(state: str) -> str:
    return _STATE_MAP.get(state.rstrip('+'), 'UNKNOWN')


def read_job_id(logs_dir: Path) -> 'int | None':
    p = logs_dir / 'array_job_id'
    if not p.is_file():
        return None
    try:
        return int(p.read_text().strip())
    except (ValueError, OSError):
        return None


def query_sacct(job_id: int) -> 'dict[int, tuple[str, str]]':
    """Query sacct for array task states. Returns {task_idx: (state, exitcode)}."""
    try:
        result = subprocess.run(
            ['sacct', '-j', str(job_id),
             '--format=JobIDRaw,State,ExitCode',
             '-P', '--noheader'],
            capture_output=True, text=True, timeout=15
        )
    except (FileNotFoundError, subprocess.TimeoutExpired):
        return {}

    tasks = {}
    for line in result.stdout.splitlines():
        parts = line.split('|')
        if len(parts) < 3:
            continue
        job_id_raw = parts[0]
        state = parts[1].strip()
        exitcode = parts[2].strip()
        m = ARRAY_TASK_PAT.match(job_id_raw)
        if m:
            tasks[int(m.group(1))] = (state, exitcode)
    return tasks


def query_squeue(job_id: int) -> 'dict[int, str]':
    """Query squeue for pending/running array tasks. Returns {task_idx: state}."""
    try:
        result = subprocess.run(
            ['squeue', '-j', str(job_id), '-h', '-o', '%i %T'],
            capture_output=True, text=True, timeout=10
        )
    except (FileNotFoundError, subprocess.TimeoutExpired):
        return {}

    tasks = {}
    for line in result.stdout.splitlines():
        parts = line.split()
        if len(parts) < 2:
            continue
        m = ARRAY_TASK_PAT.match(parts[0])
        if m:
            tasks[int(m.group(1))] = parts[1]
    return tasks


def get_task_states(job_id: int) -> 'dict[int, tuple[str, str]]':
    """Merge sacct and squeue into {task_idx: (state, exitcode_str)}."""
    sacct_data = query_sacct(job_id)
    sq_data = query_squeue(job_id)

    if not sacct_data:
        # Job may not be in sacct history yet (just submitted)
        return {idx: (state, '') for idx, state in sq_data.items()}

    # sacct takes priority; squeue fills tasks not yet visible in sacct
    merged = dict(sacct_data)
    for idx, state in sq_data.items():
        if idx not in merged:
            merged[idx] = (state, '')
    return merged


def get_run_count(study_dir: Path) -> 'tuple[int, str, dict]':
    """Read index.json. Returns (n_runs, prefix, index_dict)."""
    index_path = study_dir / 'index.json'
    if not index_path.is_file():
        return 0, 'run_', {}
    try:
        with open(index_path) as f:
            index = json.load(f)
        prefix = index.get('prefix', 'run_')
        runs = index.get('index', {})
        return len(runs), prefix, runs
    except (OSError, json.JSONDecodeError):
        return 0, 'run_', {}


def is_plasma_study(study_dir: Path, prefix: str, index: dict) -> bool:
    """True if the first run directory contains logs/array_job_id."""
    if not index:
        return False
    first_idx = sorted(int(k) for k in index)[0]
    run_dir = study_dir / f'{prefix}{first_idx}'
    return (run_dir / 'logs' / 'array_job_id').is_file()


def get_voltage_summary(run_dir: Path) -> str:
    """Return a compact string describing the inner voltage array status."""
    job_id = read_job_id(run_dir / 'logs')
    if job_id is None:
        return 'not submitted'

    task_states = get_task_states(job_id)
    if not task_states:
        return f'no history (job {job_id})'

    total = len(task_states)
    counts: dict[str, int] = {}
    for state, _ in task_states.values():
        c = classify_state(state)
        counts[c] = counts.get(c, 0) + 1

    n_done = counts.get('COMPLETED', 0)
    n_fail = counts.get('FAILED', 0)
    n_run  = counts.get('RUNNING', 0)
    n_pend = counts.get('PENDING', 0)

    if n_fail:
        return f'FAILED ({n_fail}/{total})'
    if n_run:
        return f'running ({n_done}/{total} done)'
    if n_pend and n_done == 0:
        return f'pending (0/{total})'
    if n_pend:
        return f'pending ({n_done}/{total} done)'
    return f'{n_done}/{total} done'


@dataclass
class StudyStatus:
    study_dir: Path
    job_id: 'int | None'
    run_count: int
    prefix: str
    task_states: 'dict[int, tuple[str, str]]'
    is_plasma: bool
    voltage_summaries: 'dict[int, str]' = field(default_factory=dict)


def collect_study_status(study_dir: Path, skip_voltage: bool = False) -> StudyStatus:
    n_runs, prefix, index = get_run_count(study_dir)
    job_id = read_job_id(study_dir / 'logs')
    task_states = get_task_states(job_id) if job_id is not None else {}
    plasma = is_plasma_study(study_dir, prefix, index)

    voltage_summaries: dict[int, str] = {}
    if plasma and not skip_voltage and index:
        for k in index:
            idx = int(k)
            run_dir = study_dir / f'{prefix}{idx}'
            voltage_summaries[idx] = get_voltage_summary(run_dir)

    return StudyStatus(
        study_dir=study_dir,
        job_id=job_id,
        run_count=n_runs,
        prefix=prefix,
        task_states=task_states,
        is_plasma=plasma,
        voltage_summaries=voltage_summaries,
    )


def print_study_status(status: StudyStatus) -> None:
    # Header
    job_info = f'job {status.job_id}' if status.job_id is not None else 'no job submitted'
    n = status.run_count
    print(f"{status.study_dir}  ({n} run{'s' if n != 1 else ''}, {job_info})")

    if n == 0:
        print('  (empty)')
        print()
        return

    # Build rows: (label, state_str, extra_str, exit_str)
    # extra_str = voltage summary (plasma) or '' (non-plasma)
    # exit_str  = exit code for non-plasma FAILED/non-zero
    rows = []
    sorted_indices = sorted(range(n))
    any_nonzero_exit = False

    for idx in sorted_indices:
        label = f'{status.prefix}{idx}'
        state_raw, exitcode = status.task_states.get(idx, ('unknown', ''))
        classified = classify_state(state_raw) if state_raw != 'unknown' else 'UNKNOWN'
        state_str = classified.lower()

        if status.is_plasma:
            extra = status.voltage_summaries.get(idx, '')
            rows.append((label, state_str, extra, ''))
        else:
            show_exit = exitcode and exitcode != '0:0' and classified in ('FAILED', 'UNKNOWN')
            if show_exit:
                any_nonzero_exit = True
            rows.append((label, state_str, '', exitcode if show_exit else ''))

    # Column headers
    if status.is_plasma:
        headers = ['run', 'state', 'voltages']
    elif any_nonzero_exit:
        headers = ['run', 'state', 'exit']
    else:
        headers = ['run', 'state']

    # Column widths
    col_w = [len(h) for h in headers]
    for label, state_str, extra, exit_str in rows:
        col_w[0] = max(col_w[0], len(label))
        col_w[1] = max(col_w[1], len(state_str))
        if len(headers) > 2:
            third = extra if status.is_plasma else exit_str
            col_w[2] = max(col_w[2], len(third))

    sep = '  '
    header_line = sep.join(f'{h:<{col_w[j]}}' for j, h in enumerate(headers))
    rule        = sep.join('-' * w for w in col_w)
    print('  ' + header_line)
    print('  ' + rule)

    for label, state_str, extra, exit_str in rows:
        cells = [label, state_str]
        if status.is_plasma:
            cells.append(extra)
        elif any_nonzero_exit:
            cells.append(exit_str)
        line = sep.join(f'{c:<{col_w[j]}}' for j, c in enumerate(cells))
        print('  ' + line.rstrip())

    # Summary line
    counts: dict[str, int] = {}
    for _, state_str, _, _ in rows:
        counts[state_str] = counts.get(state_str, 0) + 1
    order = ['completed', 'running', 'pending', 'failed', 'cancelled', 'unknown']
    parts = [f'{counts[s]} {s}' for s in order if s in counts]
    if parts:
        print('  Summary: ' + ', '.join(parts))
    print()


def cmd_status(args) -> None:
    dirs = []
    for p in args.study_dirs:
        p = Path(p)
        if (p / 'index.json').is_file():
            dirs.append(p)
        elif p.is_dir():
            children = sorted(
                s for s in p.iterdir()
                if s.is_dir() and (s / 'index.json').is_file()
            )
            if children:
                dirs.extend(children)
            else:
                print(f"warning: no study directories found in '{p}'", file=sys.stderr)
        else:
            print(f"error: '{p}' is not a directory", file=sys.stderr)

    for d in dirs:
        status = collect_study_status(d, skip_voltage=args.no_voltage)
        print_study_status(status)
