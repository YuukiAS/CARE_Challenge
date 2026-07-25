#!/usr/bin/env python3
from __future__ import annotations
import json, sys
from pathlib import Path
import yaml
ROOT=Path(__file__).resolve().parents[2]
ENTRY=ROOT/'configs/srr_production/entrypoints.yaml'
OUT=ROOT/'results/20260724_care_myops_batch10_deadline_rescue/strict_entrypoint_audit.json'
data=yaml.safe_load(ENTRY.read_text())
formal=data.get('formal_entrypoints') or []
errors=[]
if len(formal)!=1 or formal[0].get('id')!='care_myops_batch10_deadline_rescue':
    errors.append('formal_entrypoints must contain only care_myops_batch10_deadline_rescue')
if formal and not formal[0].get('formal_authority'):
    errors.append('Batch10 formal_authority must be true')
for row in data.get('candidate_entrypoints') or []:
    if row.get('id')=='care_myops_batch9_exposed_issues_repair' and row.get('formal_authority'):
        errors.append('Batch9 repair must not remain formal_authority')
if data.get('publication_boundary',{}).get('batch11_authorized'):
    errors.append('Batch11 must remain unauthorized')
if data.get('publication_boundary',{}).get('nnunet_model_or_fallback_authorized'):
    errors.append('nnU-Net model/fallback must remain forbidden')
payload={'schema_version':1,'status':'FAIL' if errors else 'PASS','entrypoint_path':str(ENTRY.relative_to(ROOT)),'formal_entrypoints':formal,'errors':errors,'parallel_executor': formal[0].get('parallel_executor') if formal else None,'independent_slurm_jobs_can_run_in_parallel': formal[0].get('independent_slurm_jobs_can_run_in_parallel') if formal else None}
OUT.parent.mkdir(parents=True,exist_ok=True)
OUT.write_text(json.dumps(payload,indent=2,sort_keys=True),encoding='utf-8')
print(json.dumps(payload,indent=2,sort_keys=True))
sys.exit(1 if errors else 0)
