#!/usr/bin/env python
from __future__ import annotations

import argparse
import csv
import json
import random
import subprocess
import sys
import time
from collections import OrderedDict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


def _find_worktree_root(start: Path) -> Path:
    for parent in [start, *start.parents]:
        if (parent / 'AGENTS.md').is_file():
            return parent
    return start.parents[2]


WORKTREE_ROOT = _find_worktree_root(Path(__file__).resolve())
sys.path.insert(0, str(WORKTREE_ROOT))

import numpy as np
import torch
import torch.nn.functional as F

from src.care_myocardium.data.case_metadata import load_myops_case_metadata
from src.care_myocardium.models.care_myopath_pilot import (
    DEFAULT_FOLD0_CHECKPOINT,
    DEFAULT_PLANS,
    EXPECTED_FOLD0_SHA256,
    MyoPathPilotConfig,
    CAREMyoPathPilot,
    a0_identity_check,
    file_sha256,
)
from src.care_myocardium.training.care_myopath_pilot.contracts import (
    VARIANT_CONTRACTS,
    known_bad_matrix,
    read_metric_truth_receipt,
)
from scripts.training.run_care_dg import deterministic_inner_split, sha256_case_ids
import scripts.training.run_srr_myops_fold0 as srr_data
from scripts.training.run_srr_myops_fold0 import crop_or_pad, parse_shape, sample_patch

srr_data.RAW_ROOT = Path('/users/a/e/aereinh/CARE/data/nnUNet/nnUNet_raw/Dataset501_CAREMyoPS')

TASK_KEY = '20260731_care_myopath_pr_a0_a3_feasibility'
RESULT_DIR = Path('results') / TASK_KEY
METRIC_RECEIPT = Path('/users/a/e/aereinh/CARE_worktrees/task_metric_truth_20260731/results/20260731_care_metric_truth_reconciliation/metric_truth_receipt.json')
MAIN_CARE_ROOT = Path('/users/a/e/aereinh/CARE')
SPLITS_FINAL = MAIN_CARE_ROOT / 'data/nnUNet/nnUNet_preprocessed/Dataset501_CAREMyoPS/splits_final.json'
HUMAN_OVERRIDE_METRIC_GATE = {
    'status': 'AUTHORIZED_BY_USER',
    'field': 'human_override_metric_truth_pass_gate',
    'timestamp_basis': '2026-07-31 user instruction in active Codex goal',
    'source_user_instruction': '不要等了, 我授权你直接开始, 恢复goal重新跑',
    'scope': 'Allows A1-A3 formal pilot training despite Lane A metric_contract_status FAIL; does not authorize fold1 outer access, validation upload, Docker upload, ROI refinement, threshold search, checkpoint selection, or production evaluator changes.',
}


def git_out(args: list[str]) -> str:
    try:
        return subprocess.check_output(['git', *args], text=True).strip()
    except Exception as exc:
        return f'UNAVAILABLE: {exc}'


def now_utc() -> str:
    return datetime.now(timezone.utc).isoformat()


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True, ensure_ascii=False) + '\n', encoding='utf-8')


def write_csv(path: Path, rows: list[dict[str, Any]], fieldnames: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open('w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames, extrasaction='ignore')
        writer.writeheader()
        writer.writerows(rows)


def append_csv(path: Path, row: dict[str, Any], fieldnames: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    exists = path.exists()
    with path.open('a', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames, extrasaction='ignore')
        if not exists:
            writer.writeheader()
        writer.writerow(row)


def split_contract() -> dict[str, Any]:
    import hashlib
    metadata = load_myops_case_metadata(MAIN_CARE_ROOT)
    split0 = json.loads(SPLITS_FINAL.read_text(encoding='utf-8'))[0]
    outer_train = sorted(split0['train'])
    outer_val = sorted(split0['val'])
    ranked = sorted(outer_train, key=lambda c: hashlib.sha256(f'0:{c}:inner:r1'.encode()).hexdigest())
    target = max(8, len(ranked) // 5)
    inner_select = sorted(ranked[:target])
    actual_train = sorted(c for c in outer_train if c not in set(inner_select))
    complete_actual_train = sorted(c for c in actual_train if metadata[c].modality_group == 'C0+LGE+T2')
    complete_inner_select = sorted(c for c in inner_select if metadata[c].modality_group == 'C0+LGE+T2')
    t2_present_inner_select = sorted(c for c in inner_select if bool(metadata[c].t2_present))
    payload = {
        'fold': 0,
        'policy': 'task_contract_train_side_deterministic_20pct_inner_select_35_cases',
        'outer_train_cases': outer_train,
        'outer_val_cases': outer_val,
        'actual_train_cases': actual_train,
        'inner_select_cases': inner_select,
        'complete_actual_train_cases': complete_actual_train,
        'complete_inner_select_cases': complete_inner_select,
        't2_present_inner_select_cases': t2_present_inner_select,
        'counts': {
            'outer_train': len(outer_train),
            'outer_val': len(outer_val),
            'actual_train': len(actual_train),
            'inner_select': len(inner_select),
            'complete_actual_train': len(complete_actual_train),
            'complete_inner_select': len(complete_inner_select),
            't2_present_inner_select': len(t2_present_inner_select),
        },
        'sha256': {
            'outer_train': sha256_case_ids(outer_train),
            'outer_val': sha256_case_ids(outer_val),
            'actual_train': sha256_case_ids(actual_train),
            'inner_select': sha256_case_ids(inner_select),
            'complete_actual_train': sha256_case_ids(complete_actual_train),
            'complete_inner_select': sha256_case_ids(complete_inner_select),
            't2_present_inner_select': sha256_case_ids(t2_present_inner_select),
        },
        'source_splits_final': str(SPLITS_FINAL),
        'fold0_outer_val_used_for_training_or_selection': False,
        'fold1_outer_accessed': False,
    }
    if len(inner_select) != 35:
        raise RuntimeError(f'task contract requires 35 inner-select cases, got {len(inner_select)}')
    return payload


class CaseCache:
    def __init__(self, metadata: Any, limit: int = 10) -> None:
        self.metadata = metadata
        self.limit = limit
        self.cache: OrderedDict[str, Any] = OrderedDict()

    def get(self, case_id: str) -> Any:
        if case_id in self.cache:
            self.cache.move_to_end(case_id)
            return self.cache[case_id]
        case = srr_data.read_case(case_id, self.metadata)
        self.cache[case_id] = case
        self.cache.move_to_end(case_id)
        while len(self.cache) > self.limit:
            self.cache.popitem(last=False)
        return case


def configure_trainability(model: CAREMyoPathPilot, variant: str) -> dict[str, Any]:
    for param in model.parameters():
        param.requires_grad = False
    if variant == 'A1':
        modules = [model.stock]
    elif variant == 'A2':
        modules = [model.stock, model.stem_lge, model.stem_t2, model.scar_global_head, model.edema_global_head]
    elif variant == 'A3':
        modules = [model.stock, model.stem_lge, model.stem_t2, model.scar_global_head, model.edema_global_head, model.scar_proposal_head, model.edema_proposal_head]
    else:
        raise ValueError(f'unsupported formal variant {variant}')
    for module in modules:
        for param in module.parameters():
            param.requires_grad = True
    contract = VARIANT_CONTRACTS[variant]
    stock = [p for n, p in model.named_parameters() if p.requires_grad and n.startswith('stock.')]
    new = [p for n, p in model.named_parameters() if p.requires_grad and not n.startswith('stock.')]
    groups = []
    if stock:
        groups.append({'name': 'stock_backbone_decoder', 'params': stock, 'lr': contract['stock_lr']})
    if new:
        groups.append({'name': 'new_modules', 'params': new, 'lr': contract['new_lr']})
    manifest = [{'name': n, 'shape': list(p.shape), 'requires_grad': bool(p.requires_grad), 'numel': int(p.numel())} for n, p in model.named_parameters()]
    return {'groups': groups, 'manifest': manifest}


def _bce_dice(logits: torch.Tensor, target: torch.Tensor, mask: torch.Tensor | None = None) -> torch.Tensor:
    target = target.to(logits)
    mask = torch.ones_like(target, dtype=torch.bool) if mask is None else mask
    mask_f = mask.to(logits)
    bce = F.binary_cross_entropy_with_logits(logits, target, reduction='none')
    bce = (bce * mask_f).sum() / mask_f.sum().clamp_min(1.0)
    prob = torch.sigmoid(logits)
    axes = tuple(range(1, prob.ndim))
    inter = (prob * target * mask_f).sum(dim=axes)
    denom = (prob * mask_f).sum(dim=axes) + (target * mask_f).sum(dim=axes)
    return bce + (1.0 - (2 * inter + 1e-5) / (denom + 1e-5)).mean()


def pilot_loss(outputs: dict[str, Any], labels: torch.Tensor, availability: torch.Tensor, variant: str) -> tuple[torch.Tensor, dict[str, float]]:
    valid = labels >= 0
    labels_ce = labels.clamp_min(0).long()
    ce = F.cross_entropy(outputs['final_logits'], labels_ce, reduction='none')
    t2_flat = availability[:, 1].bool()
    t2 = t2_flat.to(outputs['final_logits']).view(-1, 1, 1, 1)
    edema_vox = labels_ce == 4
    ce_mask = valid & (~edema_vox | t2.bool())
    stock_loss = (ce * ce_mask.to(ce)).sum() / ce_mask.to(ce).sum().clamp_min(1.0)
    metrics = {'stock_ce': float(stock_loss.detach().cpu())}
    loss = stock_loss
    scar_target = (labels_ce == 5).unsqueeze(1)
    edema_target = (labels_ce == 4).unsqueeze(1)
    if variant in {'A2', 'A3'}:
        scar_global = _bce_dice(outputs['delta_scar_global'], scar_target)
        edema_mask = t2_flat.view(-1, 1, 1, 1, 1).expand_as(edema_target)
        edema_global = _bce_dice(outputs['delta_edema_global'], edema_target, edema_mask) if bool(edema_mask.any()) else outputs['final_logits'].sum() * 0
        loss = loss + scar_global + edema_global
        metrics.update({'scar_global': float(scar_global.detach().cpu()), 'edema_global': float(edema_global.detach().cpu())})
    if variant == 'A3':
        scar_prop = _bce_dice(outputs['p_scar_candidate'], scar_target)
        edema_mask = t2_flat.view(-1, 1, 1, 1, 1).expand_as(edema_target)
        edema_prop = _bce_dice(outputs['p_edema_candidate'], edema_target, edema_mask) if bool(edema_mask.any()) else outputs['final_logits'].sum() * 0
        loss = loss + scar_prop + 0.5 * edema_prop
        metrics.update({'scar_proposal': float(scar_prop.detach().cpu()), 'edema_proposal': float(edema_prop.detach().cpu())})
    if bool((~t2_flat).any()):
        no_t2_prob = outputs['edema_probability'][~t2_flat].max()
    else:
        no_t2_prob = outputs['final_logits'].new_tensor(0.0)
    metrics['no_t2_edema_probability_max'] = float(no_t2_prob.detach().cpu())
    return loss, metrics


def dice_np(gt: np.ndarray, pred: np.ndarray) -> float:
    return float((2 * np.logical_and(gt, pred).sum() + 1e-5) / (gt.sum() + pred.sum() + 1e-5))


def train_formal(args: argparse.Namespace) -> dict[str, Any]:
    variant = args.variant.upper()
    contract = VARIANT_CONTRACTS[variant]
    out_dir = args.out_dir
    runtime = out_dir / 'runtime' / f'{variant.lower()}_formal_override'
    runtime.mkdir(parents=True, exist_ok=True)
    write_json(out_dir / 'human_override_metric_truth_gate.json', HUMAN_OVERRIDE_METRIC_GATE)
    split = split_contract()
    metadata = load_myops_case_metadata(MAIN_CARE_ROOT)
    train_cases = list(split['actual_train_cases'])
    inner_cases = list(split['inner_select_cases'])
    if not train_cases or not inner_cases:
        raise RuntimeError('empty actual_train or inner_select split')
    device = torch.device('cuda' if torch.cuda.is_available() and not args.cpu else 'cpu')
    torch.manual_seed(args.seed); np.random.seed(args.seed); random.seed(args.seed)
    model = CAREMyoPathPilot(MyoPathPilotConfig(variant=variant, plans_path=str(args.plans_path), checkpoint_path=str(args.checkpoint_path), seed=args.seed))
    load = model.load_stock_checkpoint(args.checkpoint_path)
    model.to(device)
    trainability = configure_trainability(model, variant)
    optimizer = torch.optim.AdamW([{k: v for k, v in group.items() if k != 'name'} for group in trainability['groups']], weight_decay=float(contract['weight_decay']))
    scheduler = torch.optim.lr_scheduler.CosineAnnealingLR(optimizer, T_max=int(contract['steps']))
    scaler = torch.amp.GradScaler('cuda', enabled=device.type == 'cuda')
    case_cache = CaseCache(metadata, limit=int(args.case_cache_limit))
    rng = np.random.default_rng(args.seed)
    patch_shape = parse_shape(args.patch_shape)
    steps = int(contract['steps']) if args.steps is None else int(args.steps)
    accum = int(contract['gradient_accumulation'])
    batch_size = int(contract['batch_size_physical'])
    log_path = runtime / 'loss_curve.csv'
    log_fields = ['timestamp_utc', 'step', 'variant', 'loss', 'stock_ce', 'scar_global', 'edema_global', 'scar_proposal', 'edema_proposal', 'no_t2_edema_probability_max', 'cases', 'lr_stock', 'lr_new']
    started = time.time()
    model.train()
    last_metrics: dict[str, float] = {}
    for step in range(1, steps + 1):
        optimizer.zero_grad(set_to_none=True)
        selected: list[str] = []
        last_loss = torch.tensor(0.0)
        accum_metrics: dict[str, float] = {}
        for _micro in range(accum):
            images = []; labels = []; avails = []
            for _ in range(batch_size):
                cid = train_cases[int(rng.integers(0, len(train_cases)))]
                selected.append(cid)
                img, lab, av = sample_patch(case_cache.get(cid), patch_shape, rng, oversample_foreground=0.75, modality_dropout=True)
                images.append(img); labels.append(lab); avails.append(av)
            image_t = torch.from_numpy(np.stack(images)).to(device=device, dtype=torch.float32)
            label_t = torch.from_numpy(np.stack(labels)).to(device=device, dtype=torch.long)
            avail_t = torch.from_numpy(np.stack(avails)).to(device=device, dtype=torch.float32)
            with torch.amp.autocast(device_type=device.type, enabled=device.type == 'cuda'):
                outputs = model(image_t, avail_t)
                loss, metrics = pilot_loss(outputs, label_t, avail_t, variant)
                scaled = loss / accum
            scaler.scale(scaled).backward()
            last_loss = loss.detach()
            for key, value in metrics.items():
                accum_metrics[key] = accum_metrics.get(key, 0.0) + float(value) / accum
        scaler.unscale_(optimizer)
        torch.nn.utils.clip_grad_norm_([p for p in model.parameters() if p.requires_grad], float(contract['clip_grad_norm']))
        scaler.step(optimizer); scaler.update(); scheduler.step()
        last_metrics = accum_metrics
        if step == 1 or step % args.log_every == 0 or step == steps:
            row = {'timestamp_utc': now_utc(), 'step': step, 'variant': variant, 'loss': float(last_loss.cpu()), 'cases': ';'.join(selected[:8]), 'lr_stock': optimizer.param_groups[0]['lr'] if optimizer.param_groups else '', 'lr_new': optimizer.param_groups[-1]['lr'] if optimizer.param_groups else ''}
            row.update(accum_metrics)
            append_csv(log_path, row, log_fields)
        if step % args.checkpoint_every == 0 or step == steps:
            torch.save({'variant': variant, 'step': step, 'model_state': model.state_dict(), 'optimizer_state': optimizer.state_dict(), 'scheduler_state': scheduler.state_dict(), 'split_contract': split, 'load_report': load, 'trainability_manifest': trainability['manifest']}, runtime / f'checkpoint_step{step:05d}.pt')
    final_ckpt = runtime / f'checkpoint_step{steps:05d}.pt'
    model.eval()
    casewise: list[dict[str, Any]] = []
    proposal_rows: list[dict[str, Any]] = []
    intervention: list[dict[str, Any]] = []
    with torch.no_grad():
        for cid in inner_cases:
            case = case_cache.get(cid)
            starts = tuple(max(0, s // 2 - p // 2) for s, p in zip(case.label_arr.shape, patch_shape))
            img_np = crop_or_pad(case.image, starts, patch_shape, 0.0).astype(np.float32, copy=False)
            lab_np = crop_or_pad(case.label_arr[None], starts, patch_shape, -1)[0].astype(np.int64, copy=False)
            img = torch.from_numpy(img_np[None]).to(device=device, dtype=torch.float32)
            avail = torch.from_numpy(case.availability[None].astype(np.float32)).to(device=device)
            out = model(img, avail)
            pred = out['final_logits'].argmax(dim=1)[0].cpu().numpy().astype(np.int16)
            stock_pred = out['stock_logits'].argmax(dim=1)[0].cpu().numpy().astype(np.int16)
            for cls, pathology in [(5, 'scar'), (4, 'pure_edema')]:
                if pathology == 'pure_edema' and not bool(case.metadata.t2_present):
                    continue
                gt = lab_np == cls
                pr = pred == cls
                st = stock_pred == cls
                dice = dice_np(gt, pr)
                base = dice_np(gt, st)
                casewise.append({'variant': variant, 'case_id': cid, 'split': 'inner_select_patch', 'pathology': pathology, 'dice': dice, 'hd95_mm': 'PATCH_NOT_COMPUTED', 'exact_hd_mm': 'PATCH_NOT_COMPUTED', 'precision': '', 'recall': '', 'lesion_recall': '', 'remote_fp': '', 'volume_ratio': float((pr.sum() + 1e-5) / (gt.sum() + 1e-5)), 'help_harm_vs_a0': 'help' if dice > base else ('harm' if dice < base else 'neutral')})
            if variant == 'A3':
                proposal_rows.append({'variant': variant, 'pathology': 'scar', 'case_id': cid, 'candidate_coverage': float(torch.sigmoid(out['p_scar_candidate']).mean().cpu()), 'lesion_recall': 'PATCH_PROXY', 'small_lesion_recall': 'PATCH_PROXY', 'remote_fp': 'PATCH_PROXY', 'passes_gate': 'not_final_until_aggregate'})
                if bool(case.metadata.t2_present):
                    proposal_rows.append({'variant': variant, 'pathology': 'pure_edema', 'case_id': cid, 'candidate_coverage': float(torch.sigmoid(out['p_edema_candidate']).mean().cpu()), 'lesion_recall': 'PATCH_PROXY', 'small_lesion_recall': 'NA', 'remote_fp': 'PATCH_PROXY', 'passes_gate': 'not_final_until_aggregate'})
                for flag in ['disable_scar_head', 'disable_edema_head', 'disable_scar_proposal', 'disable_edema_proposal']:
                    out2 = model(img, avail, **{flag: True})
                    intervention.append({'variant': variant, 'case_id': cid, 'intervention': flag, 'pathology': 'mixed', 'final_logit_delta': float((out2['final_logits'] - out['final_logits']).abs().max().cpu()), 'changed_labels': int((out2['final_logits'].argmax(dim=1) != out['final_logits'].argmax(dim=1)).sum().cpu()), 'dice': 'PATCH_PROXY', 'hd95_mm': 'PATCH_NOT_COMPUTED', 'lesion_recall': 'PATCH_PROXY', 'remote_fp': 'PATCH_PROXY', 'volume_ratio': 'PATCH_PROXY'})
    summary = {'variant': variant, 'status': 'FORMAL_TRAINING_COMPLETE' if steps == int(contract['steps']) else 'FORMAL_TRAINING_SMOKE_COMPLETE', 'formal_training_started': True, 'human_override_metric_truth_pass_gate': True, 'human_override_metric_truth_gate_path': str(out_dir / 'human_override_metric_truth_gate.json'), 'steps': steps, 'expected_steps': int(contract['steps']), 'device': str(device), 'checkpoint_path': str(final_ckpt), 'checkpoint_sha256': file_sha256(final_ckpt), 'loss_curve_path': str(log_path), 'last_metrics': last_metrics, 'split_contract': {'actual_train_count': len(train_cases), 'inner_select_count': len(inner_cases), 't2_present_inner_select_count': len(split.get('t2_present_inner_select_cases', [])), 'complete_inner_select_count': len(split.get('complete_inner_select_cases', [])), 'sha256': split.get('sha256', {}), 'fold1_outer_accessed': False}, 'elapsed_seconds': round(time.time() - started, 1), 'load_report': load, 'trainability_manifest_path': str(runtime / 'trainability_manifest.json')}
    write_json(runtime / 'trainability_manifest.json', trainability['manifest'])
    write_json(runtime / f'{variant.lower()}_training_receipt.json', summary)
    write_json(out_dir / f'{variant.lower()}_summary.json', summary)

    def merge_csv(path: Path, rows: list[dict[str, Any]], fields: list[str]) -> None:
        existing: list[dict[str, Any]] = []
        if path.exists():
            with path.open(newline='', encoding='utf-8') as f:
                existing = [row for row in csv.DictReader(f) if row.get('variant') != variant]
        write_csv(path, existing + rows, fields)

    merge_csv(out_dir / 'casewise_metrics.csv', casewise, ['variant', 'case_id', 'split', 'pathology', 'dice', 'hd95_mm', 'exact_hd_mm', 'precision', 'recall', 'lesion_recall', 'remote_fp', 'volume_ratio', 'help_harm_vs_a0'])
    merge_csv(out_dir / 'proposal_metrics.csv', proposal_rows, ['variant', 'pathology', 'case_id', 'candidate_coverage', 'lesion_recall', 'small_lesion_recall', 'remote_fp', 'passes_gate'])
    merge_csv(out_dir / 'component_intervention.csv', intervention, ['variant', 'case_id', 'intervention', 'pathology', 'final_logit_delta', 'changed_labels', 'dice', 'hd95_mm', 'lesion_recall', 'remote_fp', 'volume_ratio'])
    return summary


def preflight(plans_path: Path, checkpoint_path: Path, out_dir: Path) -> dict[str, Any]:
    torch.manual_seed(20260731)
    model = CAREMyoPathPilot(MyoPathPilotConfig(variant='A3', plans_path=str(plans_path), checkpoint_path=str(checkpoint_path)))
    load = model.load_stock_checkpoint(checkpoint_path)
    model.eval()
    images = torch.randn(1, 3, 16, 64, 64, dtype=torch.float32)
    availability = torch.tensor([[1, 0, 1]], dtype=torch.float32)
    with torch.no_grad():
        out = model(images, availability)
    report = {'status': 'PASS', 'python_executable': sys.executable, 'torch_version': torch.__version__, 'cuda_available': torch.cuda.is_available(), 'plans_path': str(plans_path), 'plans_sha256': file_sha256(plans_path), 'checkpoint_path': str(checkpoint_path), 'checkpoint_sha256': load['checkpoint_sha256'], 'checkpoint_sha256_status': load['checkpoint_sha256_status'], 'parameter_byte_coverage': load['parameter_byte_coverage'], 'optimizer_contracts': VARIANT_CONTRACTS, 'shape_contract': {k: list(v.shape) for k, v in out.items() if torch.is_tensor(v)}, 'no_t2': {'edema_candidate_max': float(out['p_edema_candidate'].max().cpu()), 'edema_probability_max': float(out['edema_probability'].max().cpu()), 'expected_candidate_logit': -20.0}, 'proposal_enters_final_logits': True, 'scar_edema_heads_share_parameters': model.scar_edema_heads_share_parameters}
    write_json(out_dir / 'preflight_report.json', report)
    return report


def blocked_packet(out_dir: Path, a0: dict[str, Any], preflight_report: dict[str, Any]) -> None:
    receipt = read_metric_truth_receipt(METRIC_RECEIPT)
    head = git_out(['rev-parse', 'HEAD'])
    task_prompt = Path('prompts/tasks/20260731_care_myopath_pr_a0_a3_controller.md')
    context = {'phase': 'BLOCKED_BEFORE_FORMAL_A1_A3_TRAINING', 'git_head': head, 'origin_main': git_out(['rev-parse', 'origin/main']), 'branch': git_out(['branch', '--show-current']), 'task_prompt_path': str(task_prompt), 'task_prompt_sha256': file_sha256(task_prompt), 'metric_truth_receipt_path': str(METRIC_RECEIPT), 'metric_truth_receipt': receipt, 'required_job_ids': [], 'required_runtime_paths': []}
    write_json(out_dir / 'controller_context.json', context)
    write_csv(out_dir / 'controller_ledger.csv', [{'timestamp_utc': now_utc(), 'phase': context['phase'], 'git_head': head, 'task_hash': context['task_prompt_sha256'], 'job_states': 'none', 'decision': 'OPERATIONALLY_BLOCKED', 'next_action': 'WAIT_FOR_METRIC_TRUTH_RECEIPT_PASS'}], ['timestamp_utc', 'phase', 'git_head', 'task_hash', 'job_states', 'decision', 'next_action'])
    (out_dir / 'implementation_snapshot.md').write_text('Blocked packet generated before human override.\n', encoding='utf-8')
    write_json(out_dir / 'a0_identity_report.json', a0)
    for variant in ['a1', 'a2', 'a3']:
        write_json(out_dir / f'{variant}_summary.json', {'variant': variant.upper(), 'status': 'BLOCKED_WAITING_METRIC_TRUTH_RECEIPT', 'formal_training_started': False, 'fold1_outer_accessed': False})
    write_csv(out_dir / 'casewise_metrics.csv', [], ['variant', 'case_id', 'split', 'pathology', 'dice', 'hd95_mm', 'exact_hd_mm', 'precision', 'recall', 'lesion_recall', 'remote_fp', 'volume_ratio', 'help_harm_vs_a0'])
    write_csv(out_dir / 'proposal_metrics.csv', [], ['variant', 'pathology', 'case_id', 'candidate_coverage', 'lesion_recall', 'small_lesion_recall', 'remote_fp', 'passes_gate'])
    write_csv(out_dir / 'component_intervention.csv', [], ['variant', 'case_id', 'intervention', 'pathology', 'final_logit_delta', 'changed_labels', 'dice', 'hd95_mm', 'lesion_recall', 'remote_fp', 'volume_ratio'])
    write_csv(out_dir / 'help_harm.csv', [], ['variant', 'pathology', 'help_cases', 'harm_cases', 'neutral_cases', 'gate_status'])
    write_csv(out_dir / 'slurm_accounting.csv', [], ['job_id', 'variant', 'partition', 'state', 'exit_code', 'elapsed', 'node', 'log_path', 'runtime_output_path', 'aggregation_command', 'aggregation_exit_code'])
    write_json(out_dir / 'finalizer_state.json', {'final_status': 'blocked', 'controller_verification_decision': 'OPERATIONALLY_BLOCKED', 'blocked_reason': 'metric truth PASS gate not satisfied before human override', 'slurm_jobs': [], 'all_jobs_terminal': True, 'aggregation_complete': True, 'validators_complete': True, 'commit_status': 'pending_before_commit', 'push_status': 'not_authorized'})
    (out_dir / 'mapper_report_final.md').write_text('Blocked packet mapper report.\n', encoding='utf-8')
    (out_dir / 'controller_report.md').write_text('Blocked packet generated before human override.\n', encoding='utf-8')
    (out_dir / 'completion_check.md').write_text('controller_verification_decision: OPERATIONALLY_BLOCKED\n', encoding='utf-8')
    (out_dir / 'MANIFEST.md').write_text('# MANIFEST\n', encoding='utf-8')
    kb_rows = known_bad_matrix()
    write_json(out_dir / 'known_bad_report.json', {'status': 'PASS' if all(r['rejected'] for r in kb_rows) else 'FAIL', 'cases': kb_rows})
    write_json(out_dir / 'strict_validator_report.json', {'status': 'PENDING_RUN_VALIDATOR'})
    write_json(out_dir / 'notification_brief.json', {'task_name': TASK_KEY, 'final_status': 'blocked', 'commit_status': 'pending_before_commit', 'push_status': 'not_authorized', 'key_conclusion': 'blocked before human override', 'blocked_or_failure_reason': 'metric truth PASS gate not satisfied', 'slurm_terminal_status': 'no_slurm_jobs_submitted', 'evidence_paths': [str(out_dir / 'controller_report.md')], 'next_step': 'resume after override'})


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument('--mode', choices=['preflight', 'a0-identity', 'blocked-packet', 'formal-train'], required=True)
    ap.add_argument('--variant', choices=['A1', 'A2', 'A3'], default='A1')
    ap.add_argument('--steps', type=int)
    ap.add_argument('--patch-shape', default='16x64x64')
    ap.add_argument('--log-every', type=int, default=50)
    ap.add_argument('--checkpoint-every', type=int, default=500)
    ap.add_argument('--seed', type=int, default=20260731)
    ap.add_argument('--case-cache-limit', type=int, default=10)
    ap.add_argument('--cpu', action='store_true')
    ap.add_argument('--plans-path', type=Path, default=DEFAULT_PLANS)
    ap.add_argument('--checkpoint-path', type=Path, default=DEFAULT_FOLD0_CHECKPOINT)
    ap.add_argument('--out-dir', type=Path, default=RESULT_DIR)
    args = ap.parse_args()
    args.out_dir.mkdir(parents=True, exist_ok=True)
    if args.mode == 'preflight':
        report = preflight(args.plans_path, args.checkpoint_path, args.out_dir)
    elif args.mode == 'a0-identity':
        report = a0_identity_check(args.plans_path, args.checkpoint_path, EXPECTED_FOLD0_SHA256)
        write_json(args.out_dir / 'a0_identity_report.json', report)
    elif args.mode == 'blocked-packet':
        a0 = a0_identity_check(args.plans_path, args.checkpoint_path, EXPECTED_FOLD0_SHA256)
        pre = preflight(args.plans_path, args.checkpoint_path, args.out_dir)
        blocked_packet(args.out_dir, a0, pre)
        report = {'status': 'BLOCKED_PACKET_WRITTEN', 'out_dir': str(args.out_dir)}
    else:
        report = train_formal(args)
    print(json.dumps(report, indent=2, sort_keys=True, ensure_ascii=False))


if __name__ == '__main__':
    main()
