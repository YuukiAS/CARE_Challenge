#!/usr/bin/env python3
from __future__ import annotations
import csv,json,sys,time
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
RESULT=ROOT/'results/20260724_care_myops_batch10_deadline_rescue'
prov=json.loads((RESULT/'selection_provenance.json').read_text())
with (RESULT/'rescue_split_manifest.csv').open(newline='',encoding='utf-8') as f:
    split=list(csv.DictReader(f))
cal={r['case_id'] for r in split if r['rescue_split']=='calibration'}
audit={r['case_id'] for r in split if r['rescue_split']=='audit'}
errors=[]
for i,event in enumerate(prov.get('selection_events',[]),1):
    used=set(event.get('selection_read_case_ids') or [])
    audit_used=set(event.get('audit_case_ids_used_for_selection') or [])
    if audit_used:
        errors.append(f'event {i} {event.get("event")} explicitly used audit cases: {sorted(audit_used)}')
    if used & audit:
        errors.append(f'event {i} {event.get("event")} selection_read_case_ids overlap audit: {sorted(used & audit)}')
    if used and not used <= cal:
        errors.append(f'event {i} {event.get("event")} selection_read_case_ids not subset of calibration')
payload={'schema_version':1,'status':'FAIL' if errors else 'PASS','selection_event_count':len(prov.get('selection_events',[])),'calibration_case_count':len(cal),'audit_case_count':len(audit),'errors':errors,'checked_unix':int(time.time())}
(RESULT/'selection_provenance_audit.json').write_text(json.dumps(payload,indent=2,sort_keys=True),encoding='utf-8')
print(json.dumps(payload,indent=2,sort_keys=True))
sys.exit(1 if errors else 0)
