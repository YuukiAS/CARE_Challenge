#!/usr/bin/env python3
from __future__ import annotations
import csv,json,sys,time
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
RESULT=ROOT/'results/20260724_care_myops_batch10_deadline_rescue'
REF=ROOT/'results/srr_production/evaluation/nnunet_fold0_reproduction.json'

def rows(path):
    with path.open(newline='',encoding='utf-8') as f: return list(csv.DictReader(f))
ref=json.loads(REF.read_text())
summary=rows(RESULT/'baseline_recomputed_summary.csv')
casewise=rows(RESULT/'baseline_recomputed_casewise.csv')
errors=[]
def find(pathology,pop):
    found=[r for r in summary if r.get('variant')=='nnunet_fold0_baseline' and r.get('pathology')==pathology and r.get('population')==pop]
    return found[0] if found else None
for pathology,key in [('scar','scar_dice'),('edema','edema_dice')]:
    r=find(pathology,'full44')
    if not r: errors.append(f'missing full44 {pathology} baseline summary'); continue
    actual=float(r['mean_dice'])
    expected=float(ref['actual'][key])
    tol=float(ref.get('expected',{}).get('tolerance',1e-9))
    if abs(actual-expected)>tol:
        errors.append(f'{pathology} full44 dice mismatch actual={actual} expected={expected} tol={tol}')
if len({r['case_id'] for r in casewise})!=int(ref['case_count']):
    errors.append('case count mismatch against reproduction reference')
required_pops={'full44','positive_gt','all_cases_empty_safe','complete_trimodal','calibration','audit'}
# calibration/audit are added by amended scripts; tolerate missing before repair but report.
existing={r['population'] for r in summary}
missing=required_pops-existing
if missing:
    errors.append('missing required baseline populations after amendment: '+','.join(sorted(missing)))
payload={'schema_version':1,'status':'FAIL' if errors else 'PASS','reference_path':str(REF.relative_to(ROOT)),'recomputed_summary':'results/20260724_care_myops_batch10_deadline_rescue/baseline_recomputed_summary.csv','reference_scope':ref.get('expected_check_scope'),'case_count':len({r['case_id'] for r in casewise}),'reference_case_count':ref['case_count'],'population_warning':'full44/all-case empty-safe scar dice differs from positive-GT scar dice and must not be cross-compared','errors':errors,'checked_unix':int(time.time())}
(RESULT/'baseline_reference_consistency.json').write_text(json.dumps(payload,indent=2,sort_keys=True),encoding='utf-8')
print(json.dumps(payload,indent=2,sort_keys=True))
sys.exit(1 if errors else 0)
