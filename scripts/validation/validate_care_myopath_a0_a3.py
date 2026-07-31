#!/usr/bin/env python
from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path
from typing import Any


def _find_worktree_root(start: Path) -> Path:
    for parent in [start, *start.parents]:
        if (parent / 'AGENTS.md').is_file():
            return parent
    return start.parents[2]


WORKTREE_ROOT = _find_worktree_root(Path(__file__).resolve())
import sys as _sys
_sys.path.insert(0, str(WORKTREE_ROOT))

from src.care_myocardium.training.care_myopath_pilot.contracts import known_bad_matrix

REQUIRED = [
    'controller_context.json', 'controller_ledger.csv', 'implementation_snapshot.md',
    'a0_identity_report.json', 'a1_summary.json', 'a2_summary.json', 'a3_summary.json',
    'casewise_metrics.csv', 'proposal_metrics.csv', 'component_intervention.csv',
    'help_harm.csv', 'slurm_accounting.csv', 'finalizer_state.json',
    'known_bad_report.json', 'mapper_report_final.md', 'controller_report.md',
    'completion_check.md', 'MANIFEST.md', 'human_override_metric_truth_gate.json',
]
FORBIDDEN_COMPLETION_STATES = {'PENDING', 'RUNNING', 'NEEDS_MONITOR', 'JOB_SUBMITTED', 'AWAITING_SACCT'}
EXPECTED_STEPS = {'A1': 3000, 'A2': 5000, 'A3': 8000}


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding='utf-8'))


def csv_rows(path: Path) -> list[dict[str, str]]:
    with path.open(newline='', encoding='utf-8') as f:
        return list(csv.DictReader(f))


def validate(results_dir: Path) -> dict[str, Any]:
    errors: list[str] = []
    warnings: list[str] = []
    missing = [name for name in REQUIRED if not (results_dir / name).exists()]
    if missing:
        errors.append(f'missing required outputs: {missing}')
    finalizer = load_json(results_dir / 'finalizer_state.json') if (results_dir / 'finalizer_state.json').exists() else {}
    decision = finalizer.get('controller_verification_decision')
    if decision not in {'VERIFIED_COMPLETE', 'NEEDS_REPAIR', 'OPERATIONALLY_BLOCKED'}:
        errors.append('invalid controller_verification_decision')
    if decision == 'VERIFIED_COMPLETE':
        errors.append('VERIFIED_COMPLETE is not allowed because current packet records patch-proxy gate evidence only')
    if decision == 'NEEDS_REPAIR' and finalizer.get('final_status') != 'complete':
        errors.append('NEEDS_REPAIR terminal training packet must use final_status complete')
    if any(str(v) in FORBIDDEN_COMPLETION_STATES for v in finalizer.values()):
        errors.append('finalizer_state contains forbidden pending/running completion state')
    if finalizer.get('roi_refinement_authorized') or finalizer.get('fold_expansion_authorized') or finalizer.get('validation_upload_authorized'):
        errors.append('unauthorized downstream action is enabled')
    override = load_json(results_dir / 'human_override_metric_truth_gate.json') if (results_dir / 'human_override_metric_truth_gate.json').exists() else {}
    if override.get('status') != 'AUTHORIZED_BY_USER':
        errors.append('missing human override metric gate receipt')
    a0 = load_json(results_dir / 'a0_identity_report.json') if (results_dir / 'a0_identity_report.json').exists() else {}
    if a0.get('status') != 'PASS':
        errors.append('A0 identity report must PASS')
    if float(a0.get('fp32_max_abs_error', 1.0)) > 1e-6:
        errors.append('A0 fp32 max_abs_error exceeds 1e-6')
    if int(a0.get('changed_argmax_voxels', 1)) != 0:
        errors.append('A0 changed_argmax_voxels must be 0')
    for variant, steps in EXPECTED_STEPS.items():
        payload = load_json(results_dir / f'{variant.lower()}_summary.json') if (results_dir / f'{variant.lower()}_summary.json').exists() else {}
        if not payload.get('formal_training_started'):
            errors.append(f'{variant} formal_training_started is false')
        if int(payload.get('steps', -1)) != steps or int(payload.get('expected_steps', -2)) != steps:
            errors.append(f'{variant} steps mismatch')
        if payload.get('status') != 'FORMAL_TRAINING_COMPLETE':
            errors.append(f'{variant} did not complete formal training')
        split = payload.get('split_contract', {})
        if int(split.get('inner_select_count', -1)) != 35:
            errors.append(f'{variant} inner_select_count is not 35')
        if split.get('fold1_outer_accessed'):
            errors.append(f'{variant} claims fold1 outer access')
        if payload.get('load_report', {}).get('checkpoint_sha256_status') != 'PASS':
            errors.append(f'{variant} stock checkpoint hash did not PASS')
        if payload.get('last_metrics', {}).get('no_t2_edema_probability_max') not in {0, 0.0}:
            errors.append(f'{variant} no-T2 edema probability is not exact zero')
        ckpt = payload.get('checkpoint_path')
        if not ckpt or not Path(ckpt).is_file():
            errors.append(f'{variant} checkpoint_path missing on disk')
    acct = csv_rows(results_dir / 'slurm_accounting.csv') if (results_dir / 'slurm_accounting.csv').exists() else []
    formal = {r.get('variant'): r for r in acct if r.get('variant') in EXPECTED_STEPS}
    for variant in EXPECTED_STEPS:
        row = formal.get(variant)
        if not row:
            errors.append(f'missing Slurm accounting row for {variant}')
        elif row.get('state') != 'COMPLETED' or row.get('exit_code') != '0:0':
            errors.append(f'{variant} Slurm row not terminal success')
    casewise = csv_rows(results_dir / 'casewise_metrics.csv') if (results_dir / 'casewise_metrics.csv').exists() else []
    counts: dict[tuple[str, str], int] = {}
    for row in casewise:
        counts[(row.get('variant',''), row.get('pathology',''))] = counts.get((row.get('variant',''), row.get('pathology','')), 0) + 1
    for variant in EXPECTED_STEPS:
        if counts.get((variant, 'scar')) != 35:
            errors.append(f'{variant} scar casewise row count must be 35')
        if counts.get((variant, 'pure_edema')) != 7:
            errors.append(f'{variant} pure_edema row count must be T2-present denominator 7')
    if any(row.get('hd95_mm') == 'PATCH_NOT_COMPUTED' for row in casewise):
        warnings.append('casewise metrics are patch proxy; controller decision must remain NEEDS_REPAIR')
        if decision != 'NEEDS_REPAIR':
            errors.append('patch proxy metrics require controller_verification_decision NEEDS_REPAIR')
    interventions = csv_rows(results_dir / 'component_intervention.csv') if (results_dir / 'component_intervention.csv').exists() else []
    if len(interventions) != 140:
        errors.append('A3 component intervention must have 35 cases x 4 interventions = 140 rows')
    if sum(int(float(r.get('changed_labels') or 0)) for r in interventions if r.get('intervention') == 'disable_edema_proposal') != 0:
        warnings.append('edema proposal changes labels in patch proxy; verify direction with full evaluator')
    kb_rows = known_bad_matrix()
    if len(kb_rows) != 20 or not all(row['rejected'] for row in kb_rows):
        errors.append('known-bad matrix did not reject every fixture')
    return {
        'status': 'PASS' if not errors else 'FAIL',
        'controller_verification_decision': decision,
        'errors': errors,
        'warnings': warnings,
        'required_outputs_checked': REQUIRED,
        'formal_steps_expected': EXPECTED_STEPS,
        'known_bad_cases': kb_rows,
        'fail_closed_semantics': 'PASS' if decision == 'NEEDS_REPAIR' and not errors else 'FAIL',
    }


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument('--results-dir', type=Path, default=Path('results/20260731_care_myopath_pr_a0_a3_feasibility'))
    ap.add_argument('--write-report', action='store_true')
    args = ap.parse_args()
    report = validate(args.results_dir)
    if args.write_report:
        (args.results_dir / 'strict_validator_report.json').write_text(json.dumps(report, indent=2, sort_keys=True, ensure_ascii=False) + '\n', encoding='utf-8')
    print(json.dumps(report, indent=2, sort_keys=True, ensure_ascii=False))
    raise SystemExit(0 if report['status'] == 'PASS' else 1)


if __name__ == '__main__':
    main()
