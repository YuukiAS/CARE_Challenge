#!/usr/bin/env python3
"""Batch10 amended calibration-only screening for periodic direct/teacher checkpoints."""
from __future__ import annotations
import argparse,csv,hashlib,json,os,re,subprocess,sys,time
from collections import defaultdict
from pathlib import Path
from typing import Any
import numpy as np

REPO_ROOT=Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0,str(REPO_ROOT))
from src.care_myocardium.data.care_mm_batch9 import sha256_file  # noqa: E402

TASK_KEY='20260724_care_myops_batch10_deadline_rescue'
RESULT_ROOT=REPO_ROOT/'results'/TASK_KEY
BATCH9_RUNTIME=REPO_ROOT/'results/20260723_care_myops_batch9_exposed_issues_repair/runtime'
INFERENCE=REPO_ROOT/'scripts/inference/run_care_mm_batch10_fair_inference.py'
SCREEN_ROOT=RESULT_ROOT/'runtime/checkpoint_screening'


def read_csv(path:Path)->list[dict[str,str]]:
    if not path.is_file(): return []
    with path.open(newline='',encoding='utf-8') as f: return list(csv.DictReader(f))

def write_csv(path:Path, rows:list[dict[str,Any]])->None:
    path.parent.mkdir(parents=True,exist_ok=True)
    fields=sorted({k for r in rows for k in r}) if rows else ['empty']
    with path.open('w',newline='',encoding='utf-8') as f:
        w=csv.DictWriter(f,fieldnames=fields,lineterminator='\n'); w.writeheader(); w.writerows(rows)

def write_json(path:Path,payload:Any)->None:
    path.parent.mkdir(parents=True,exist_ok=True)
    path.write_text(json.dumps(payload,indent=2,sort_keys=True),encoding='utf-8')

def calibration_cases()->list[str]:
    rows=read_csv(RESULT_ROOT/'rescue_split_manifest.csv')
    cases=sorted(r['case_id'] for r in rows if r.get('rescue_split')=='calibration')
    if len(cases)!=22:
        raise RuntimeError(f'expected 22 calibration cases, found {len(cases)}')
    return cases

def audit_cases()->list[str]:
    return sorted(r['case_id'] for r in read_csv(RESULT_ROOT/'rescue_split_manifest.csv') if r.get('rescue_split')=='audit')

def discover()->list[dict[str,Any]]:
    rows=[]
    patterns=[
        ('student_direct_reliable','student_direct_reliable__official_aug_restart2'),
        ('student_direct_reliable_legacy','student_direct_reliable'),
        ('teacher_full_view','teacher_full_view'),
    ]
    for seed_dir in sorted(BATCH9_RUNTIME.glob('seed202607*')):
        seed=seed_dir.name.replace('seed','')
        for screen_variant, dirname in patterns:
            d=seed_dir/dirname
            if not d.is_dir():
                rows.append({'seed':seed,'screen_variant':screen_variant,'runtime_dir':str(d.relative_to(REPO_ROOT)),'checkpoint_path':'','epoch':'','checkpoint_exists':0,'checkpoint_sha256':'','screen_status':'MISSING_RUNTIME_DIR','selection_status':'NOT_SCREENED'})
                continue
            for ckpt in sorted(d.glob('checkpoint_epoch*.pt'), key=lambda p:int(re.search(r'epoch(\d+)',p.name).group(1))):
                epoch=int(re.search(r'epoch(\d+)',ckpt.name).group(1))
                st=ckpt.stat()
                rows.append({'seed':seed,'screen_variant':screen_variant,'runtime_dir':str(d.relative_to(REPO_ROOT)),'checkpoint_path':str(ckpt.relative_to(REPO_ROOT)),'epoch':epoch,'checkpoint_exists':1,'checkpoint_sha256':'','checkpoint_hash_status':'PENDING_SCREEN_HASH','checkpoint_size_bytes':st.st_size,'checkpoint_mtime_ns':st.st_mtime_ns,'screen_status':'DISCOVERED','selection_status':'PENDING_SCREEN'})
    return rows

def preserve_existing_screen_hashes(rows:list[dict[str,Any]])->list[dict[str,Any]]:
    """Aggregate must be safely rerunnable after screening.

    Screening output prefixes include the checkpoint hash.  A fresh discover()
    pass does not hash every checkpoint, so reuse the previously recorded
    manifest hashes before checking whether per-checkpoint outputs are complete.
    """
    prior=read_csv(RESULT_ROOT/'checkpoint_screening_manifest.csv')
    by_path={r.get('checkpoint_path'):r for r in prior if r.get('checkpoint_path') and r.get('checkpoint_sha256')}
    out=[]
    for row in rows:
        current=dict(row)
        prev=by_path.get(str(current.get('checkpoint_path') or ''))
        if prev:
            for key in ('checkpoint_sha256','checkpoint_hash_status'):
                if prev.get(key):
                    current[key]=prev[key]
        out.append(current)
    return out

def checkpoint_digest(row:dict[str,Any])->str:
    digest=str(row.get('checkpoint_sha256') or '')
    if digest:
        return digest[:8]
    raw=f"{row.get('checkpoint_path')}|{row.get('checkpoint_size_bytes')}|{row.get('checkpoint_mtime_ns')}"
    return hashlib.sha256(raw.encode('utf-8')).hexdigest()[:8]

def prefix(row:dict[str,Any])->str:
    return f"screen_{row['screen_variant']}_seed{row['seed']}_epoch{int(row['epoch']):03d}_{checkpoint_digest(row)}"

def completed(row:dict[str,Any])->bool:
    path=RESULT_ROOT/f"{prefix(row)}_casewise_metrics.csv"
    rows=read_csv(path)
    return len(rows)==44 and len({r.get('case_id') for r in rows})==22

def run_one(row:dict[str,Any], device:str, force:bool)->dict[str,Any]:
    if not row.get('checkpoint_path'):
        return {**row,'screen_status':'MISSING','selection_status':'NOT_SCREENED'}
    if not row.get('checkpoint_sha256'):
        row=dict(row)
        row['checkpoint_sha256']=sha256_file(REPO_ROOT/row['checkpoint_path'])
        row['checkpoint_hash_status']='HASHED_FOR_SCREENING'
    pref=prefix(row)
    if completed(row) and not force:
        return {**row,'screen_status':'SCREENED','selection_status':'SCREENED_CACHE'}
    pred_dir=SCREEN_ROOT/row['screen_variant']/f"seed{row['seed']}"/f"epoch{int(row['epoch']):03d}_{str(row['checkpoint_sha256'])[:8]}"
    cmd=[sys.executable,str(INFERENCE),'--variant',row['screen_variant'],'--seed',str(row['seed']),'--checkpoint',row['checkpoint_path'],'--prediction-dir',str(pred_dir.relative_to(REPO_ROOT)),'--output-dir',str(RESULT_ROOT.relative_to(REPO_ROOT)),'--prefix',pref,'--cases',','.join(calibration_cases()),'--device',device]
    started=int(time.time())
    proc=subprocess.run(cmd,cwd=REPO_ROOT,text=True)
    attempts=read_csv(RESULT_ROOT/'checkpoint_screening_attempts.csv')
    attempts.append({'timestamp_unix':started,'finished_unix':int(time.time()),'slurm_job_id':os.environ.get('SLURM_JOB_ID','local'),'screen_variant':row['screen_variant'],'seed':row['seed'],'epoch':row['epoch'],'checkpoint_path':row['checkpoint_path'],'checkpoint_sha256':row['checkpoint_sha256'],'prefix':pref,'case_count':len(calibration_cases()),'device':device,'returncode':proc.returncode,'command':' '.join(cmd)})
    write_csv(RESULT_ROOT/'checkpoint_screening_attempts.csv',attempts)
    if proc.returncode!=0:
        return {**row,'screen_status':'SCREEN_FAILED','selection_status':'NOT_PROMOTED','screen_error':f'rc={proc.returncode}'}
    return {**row,'screen_status':'SCREENED','selection_status':'SCREENED'}

def to_float(x:Any)->float|None:
    if x in (None,'','nan','None'): return None
    try: v=float(x)
    except Exception: return None
    return None if np.isnan(v) or np.isinf(v) else v

def mean(vals:list[Any])->float|None:
    xs=[v for v in (to_float(x) for x in vals) if v is not None]
    return float(np.mean(xs)) if xs else None

def score_row(row:dict[str,Any])->dict[str,Any]:
    pref=prefix(row)
    metrics=read_csv(RESULT_ROOT/f'{pref}_casewise_metrics.csv')
    out={**row,'prefix':pref}
    for pathology in ['scar','edema']:
        pos=[r for r in metrics if r.get('pathology')==pathology and r.get('gt_positive')=='1']
        out[f'{pathology}_calibration_positive_gt_cases']=len(pos)
        out[f'{pathology}_calibration_positive_gt_dice']=mean([r.get('dice') for r in pos])
        out[f'{pathology}_calibration_positive_gt_hd95']=mean([r.get('hd95') for r in pos])
        out[f'{pathology}_empty_prediction_count']=sum(int(float(r.get('empty_prediction') or 0)) for r in pos)
        out[f'{pathology}_remote_fp_volume_mm3']=mean([r.get('remote_fp_volume_mm3') for r in pos])
    dices=[out.get('scar_calibration_positive_gt_dice'),out.get('edema_calibration_positive_gt_dice')]
    out['min_pathology_calibration_dice']=min(v for v in dices if v is not None) if any(v is not None for v in dices) else None
    out['mean_pathology_calibration_dice']=mean(dices)
    out['calibration_case_count']=len({r.get('case_id') for r in metrics})
    out['audit_case_count_used_for_selection']=0
    return out

def select(scored:list[dict[str,Any]])->list[dict[str,Any]]:
    by=defaultdict(list)
    for r in scored:
        if r.get('screen_status')=='SCREENED':
            by[(r['seed'],r['screen_variant'])].append(r)
    out=[]
    for key, rows in by.items():
        rows.sort(key=lambda r:(to_float(r.get('min_pathology_calibration_dice')) if to_float(r.get('min_pathology_calibration_dice')) is not None else -1.0, to_float(r.get('mean_pathology_calibration_dice')) if to_float(r.get('mean_pathology_calibration_dice')) is not None else -1.0, -int(r.get('epoch') or 0)), reverse=True)
        promoted={id(r) for r in rows[:2]}
        for rank,r in enumerate(rows,1):
            rr=dict(r); rr['screen_rank_within_seed_variant']=rank; rr['selection_status']='PROMOTED_TOP2_CALIBRATION_ONLY' if id(r) in promoted else 'REJECTED_BELOW_TOP2_CALIBRATION_ONLY'; out.append(rr)
    missing=[r for r in scored if r.get('screen_status')!='SCREENED']
    for r in missing:
        rr=dict(r); rr.setdefault('selection_status','NOT_PROMOTED'); rr['screen_rank_within_seed_variant']=''; out.append(rr)
    return sorted(out,key=lambda r:(str(r.get('seed')),str(r.get('screen_variant')),int(r.get('epoch') or -1)))

def update_provenance(selected_rows:list[dict[str,Any]])->None:
    path=RESULT_ROOT/'selection_provenance.json'
    data=json.loads(path.read_text()) if path.is_file() else {'schema_version':1,'selection_events':[]}
    promoted=[r for r in selected_rows if r.get('selection_status')=='PROMOTED_TOP2_CALIBRATION_ONLY']
    data.setdefault('selection_events',[]).append({'event':'checkpoint_screening_top2_per_seed_variant','timestamp_unix':int(time.time()),'selection_rule':'calibration_only_no_tta_batch10_sliding_window_official_inverse_export_top2_by_min_then_mean_pathology_dice','selection_read_case_ids':calibration_cases(),'audit_case_ids':audit_cases(),'audit_case_ids_used_for_selection':[],'promoted_checkpoints':[{'seed':r['seed'],'screen_variant':r['screen_variant'],'epoch':r['epoch'],'checkpoint_path':r['checkpoint_path'],'checkpoint_sha256':r['checkpoint_sha256'],'rank':r['screen_rank_within_seed_variant']} for r in promoted]})
    data['status']='CHECKPOINT_SCREENING_RECORDED'
    path.write_text(json.dumps(data,indent=2,sort_keys=True),encoding='utf-8')

def main()->int:
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--phase',choices=['discover','screen','aggregate','all'],default='aggregate')
    ap.add_argument('--device',default='cuda')
    ap.add_argument('--force',action='store_true')
    args=ap.parse_args()
    RESULT_ROOT.mkdir(parents=True,exist_ok=True)
    discovered=preserve_existing_screen_hashes(discover())
    if args.phase=='discover':
        write_csv(RESULT_ROOT/'checkpoint_screening_manifest.csv',discovered)
        print(json.dumps({'status':'DISCOVERED','rows':len(discovered),'calibration_cases':len(calibration_cases()),'audit_cases_used_for_selection':0},indent=2))
        return 0
    screened=[]
    if args.phase in {'screen','all'}:
        for row in discovered:
            screened.append(run_one(row,args.device,args.force))
    else:
        screened=discovered
    scored=[]
    for row in screened:
        if row.get('checkpoint_path') and completed(row):
            r=score_row(row); r['screen_status']='SCREENED'; scored.append(r)
        else:
            scored.append(row)
    selected=select(scored)
    write_csv(RESULT_ROOT/'checkpoint_screening_manifest.csv',selected)
    update_provenance(selected)
    receipt={'schema_version':1,'status':'PASS' if any(r.get('selection_status')=='PROMOTED_TOP2_CALIBRATION_ONLY' for r in selected) else 'FAIL','discovered_rows':len(discovered),'screened_rows':sum(1 for r in selected if r.get('screen_status')=='SCREENED'),'promoted_rows':sum(1 for r in selected if r.get('selection_status')=='PROMOTED_TOP2_CALIBRATION_ONLY'),'calibration_case_ids':calibration_cases(),'audit_case_ids_used_for_selection':[],'batch10_sliding_window_official_inverse_export':True,'mirror_tta':False}
    write_json(RESULT_ROOT/'checkpoint_screening_receipt.json',receipt)
    print(json.dumps(receipt,indent=2,sort_keys=True))
    return 0 if receipt['status']=='PASS' else 2
if __name__=='__main__':
    raise SystemExit(main())
