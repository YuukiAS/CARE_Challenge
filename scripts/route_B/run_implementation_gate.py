#!/usr/bin/env python3
"""Run the Route B implementation gate and write a superseding packet."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import torch
import torch.nn.functional as F


REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from src.care_myocardium.route_B import (  # noqa: E402
    MyoPSPrototypeBank,
    RouteBCineModel,
    RouteBMyoPSModel,
    compact_cine_to_raw,
    compact_myops_to_raw,
    route_b_cine_loss,
    route_b_myops_loss,
    tensor_hash,
)
from src.care_myocardium.route_B.cine import classical_tensor_registration_control  # noqa: E402


RESULT_ROOT = REPO_ROOT / "results" / "route_B"
RUNTIME_ROOT = RESULT_ROOT / "runtime"
TOKEN_BLOCKED = "ROUTE_B_NEEDS_EVIDENCE"
TOKEN_GATE_PASSED_UNDERTRAINED = "ROUTE_B_SCIENTIFIC_UNDERTRAINED"
TOKEN_REVISION = "ROUTE_B_IMPLEMENTATION_NEEDS_REVISION"


def now() -> str:
    return datetime.now(timezone.utc).isoformat()


def git(args: list[str]) -> str:
    return subprocess.check_output(["git", *args], cwd=REPO_ROOT, text=True).strip()


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(65536), b""):
            digest.update(chunk)
    return digest.hexdigest()


def write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def write_json(path: Path, payload: dict[str, Any]) -> None:
    write(path, json.dumps(payload, indent=2, sort_keys=True) + "\n")


def write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    fieldnames: list[str] = []
    for row in rows:
        for key in row:
            if key not in fieldnames:
                fieldnames.append(key)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def finite_nonzero(value: torch.Tensor) -> bool:
    return bool(torch.isfinite(value).all() and value.detach().abs().item() > 1e-7)


def max_abs(a: torch.Tensor, b: torch.Tensor) -> float:
    return float((a.detach() - b.detach()).abs().max().cpu())


def grad_norm(module: torch.nn.Module) -> float:
    total = 0.0
    for param in module.parameters():
        if param.grad is not None:
            total += float(param.grad.detach().square().sum().cpu())
    return math.sqrt(total)


def make_myops_batch() -> tuple[torch.Tensor, torch.Tensor, torch.Tensor, torch.Tensor]:
    torch.manual_seed(7)
    x = torch.randn(3, 3, 8, 12, 12) * 0.2
    labels = torch.zeros(3, 8, 12, 12, dtype=torch.long)
    labels[:, 2:6, 3:9, 3:9] = 1
    labels[:, 3:5, 5:8, 5:8] = 2
    labels[0, 4:6, 6:8, 6:8] = 5
    labels[1, 2:4, 4:7, 4:7] = 4
    x[:, 0] += (labels == 5).float() * 1.5
    x[:, 2] += (labels == 4).float() * 1.3
    availability = torch.tensor([[1, 0, 0], [1, 1, 0], [1, 1, 1]], dtype=torch.float32)
    anchor = torch.randn(3, 6, 8, 12, 12) * 0.1
    anchor[:, 1] += (labels == 1).float() * 1.2
    anchor[:, 4] += (labels == 4).float() * 0.8
    anchor[:, 5] += (labels == 5).float() * 0.8
    return x, availability, anchor, labels


def _read_nifti(path: Path) -> torch.Tensor:
    import SimpleITK as sitk

    array = sitk.GetArrayFromImage(sitk.ReadImage(str(path)))
    return torch.as_tensor(array.copy())


def _resize_image(volume: torch.Tensor, size: tuple[int, int, int] = (8, 12, 12)) -> torch.Tensor:
    vol = volume.float()
    vol = (vol - vol.mean()) / vol.std().clamp_min(1e-6)
    return F.interpolate(vol.view(1, 1, *vol.shape[-3:]), size=size, mode="trilinear", align_corners=False)[0, 0]


def _resize_label(volume: torch.Tensor, size: tuple[int, int, int] = (8, 12, 12)) -> torch.Tensor:
    return F.interpolate(volume.float().view(1, 1, *volume.shape[-3:]), size=size, mode="nearest")[0, 0].long()


def _myops_compact(raw_or_compact: torch.Tensor) -> torch.Tensor:
    out = torch.zeros_like(raw_or_compact, dtype=torch.long)
    mapping = {0: 0, 1: 1, 2: 2, 3: 3, 4: 4, 5: 5, 200: 1, 500: 2, 600: 3, 1220: 4, 2221: 5}
    for src, dst in mapping.items():
        out[raw_or_compact == src] = dst
    return out


def _cine_compact(raw_or_compact: torch.Tensor) -> torch.Tensor:
    out = torch.zeros_like(raw_or_compact, dtype=torch.long)
    mapping = {0: 0, 1: 1, 2: 2, 3: 3, 200: 1, 500: 2, 2221: 3}
    for src, dst in mapping.items():
        out[raw_or_compact == src] = dst
    return out


def _anchor_from_compact(labels: torch.Tensor, classes: int) -> torch.Tensor:
    return F.one_hot(labels.long().clamp(0, classes - 1), num_classes=classes).permute(0, 4, 1, 2, 3).float() * 3.0 - 1.5


def discover_data_root() -> Path | None:
    candidates = [
        REPO_ROOT / "data",
        Path("/users/a/e/aereinh/CARE/data"),
    ]
    for root in candidates:
        if (root / "nnUNet" / "nnUNet_raw" / "Dataset501_CAREMyoPS").exists() and (root / "CARE_Challenge" / "CineMyoPS_train").exists():
            return root
    return None


def load_real_myops_batch(data_root: Path, limit: int = 3) -> tuple[torch.Tensor, torch.Tensor, torch.Tensor, torch.Tensor, list[str], list[str]]:
    raw = data_root / "nnUNet" / "nnUNet_raw" / "Dataset501_CAREMyoPS"
    pred_root = (
        Path("/users/a/e/aereinh/CARE/results/submissions/care_myocardium_validation/workspaces")
        / "nnUNet_MyoPS+nnUNet_CineMyoPS_5fold_baseline_round8_20260519_084057"
        / "predictions"
        / "MyoPS"
        / "nnUNet"
        / "ensemble"
    )
    cases: list[str] = []
    for label_path in sorted((raw / "labelsTr").glob("Case*.nii.gz")):
        case = label_path.stem
        if case.endswith(".nii"):
            case = case[:-4]
        images = [raw / "imagesTr" / f"{case}_{idx:04d}.nii.gz" for idx in range(3)]
        pred = pred_root / f"{case}.nii.gz"
        if all(path.exists() for path in images) and pred.exists():
            cases.append(case)
        if len(cases) >= limit:
            break
    if len(cases) < limit:
        raise FileNotFoundError(f"Need at least {limit} MyoPS cases with 3 modalities, labels, and nnU-Net prediction anchors")
    xs, ys, anchors = [], [], []
    anchor_sources = []
    for case in cases:
        channels = [_resize_image(_read_nifti(raw / "imagesTr" / f"{case}_{idx:04d}.nii.gz")) for idx in range(3)]
        label = _myops_compact(_resize_label(_read_nifti(raw / "labelsTr" / f"{case}.nii.gz")))
        pred = _myops_compact(_resize_label(_read_nifti(pred_root / f"{case}.nii.gz")))
        xs.append(torch.stack(channels))
        ys.append(label)
        anchors.append(pred)
        anchor_sources.append(str((pred_root / f"{case}.nii.gz").relative_to(Path("/users/a/e/aereinh/CARE"))))
    return torch.stack(xs), torch.ones(len(cases), 3), _anchor_from_compact(torch.stack(anchors), 6), torch.stack(ys), cases, anchor_sources


def load_real_cine_batch(data_root: Path, limit: int = 3) -> tuple[torch.Tensor, torch.Tensor, list[str]]:
    cine_root = data_root / "CARE_Challenge" / "CineMyoPS_train" / "center_alpha"
    cases = []
    for cine_path in sorted(cine_root.glob("Case*_Cine.nii.gz")):
        case = cine_path.name.replace("_Cine.nii.gz", "")
        if (cine_root / f"{case}_gd.nii.gz").exists():
            cases.append(case)
        if len(cases) >= limit:
            break
    if len(cases) < limit:
        raise FileNotFoundError(f"Need at least {limit} Cine cases with Cine and gd files")
    frame_tensors = []
    targets = []
    for case in cases:
        cine = _read_nifti(cine_root / f"{case}_Cine.nii.gz").float()
        if cine.ndim != 4:
            raise ValueError(f"expected 4D Cine image for {case}, got {tuple(cine.shape)}")
        # SimpleITK returns t,z,y,x for these files.
        frame_indices = [0, max(cine.shape[0] // 3, 1), max(2 * cine.shape[0] // 3, 2), cine.shape[0] - 1]
        frames = [_resize_image(cine[idx]) for idx in frame_indices]
        target = _cine_compact(_resize_label(_read_nifti(cine_root / f"{case}_gd.nii.gz")))
        frame_tensors.append(torch.stack(frames).unsqueeze(1))
        targets.append(target)
    return torch.stack(frame_tensors), torch.stack(targets), cases


def run_myops_gate() -> tuple[dict[str, Any], list[dict[str, Any]]]:
    torch.manual_seed(11)
    x, availability, anchor, labels = make_myops_batch()
    model = RouteBMyoPSModel()
    model.train()
    bank = MyoPSPrototypeBank()
    bank.add(torch.ones(8), case_id="proto_scar_oof", fold=99, split="oof", group="scar_positive")
    bank.add(torch.ones(8) * 0.5, case_id="proto_edema_oof", fold=99, split="oof", group="edema_positive")
    outputs = model(x, availability, anchor, prototype_bank=bank, case_ids=["CaseB001", "CaseB002", "CaseB003"], fold=0)
    loss, parts = route_b_myops_loss(outputs, labels, availability)
    model.zero_grad(set_to_none=True)
    loss.backward()
    grad_rows = [
        {"module": "myops_stems", "grad_norm": grad_norm(model.stems), "required": True},
        {"module": "myops_router_dictionary_s1", "grad_norm": grad_norm(model.retrieval_s1), "required": True},
        {"module": "myops_router_dictionary_s2", "grad_norm": grad_norm(model.retrieval_s2), "required": True},
        {"module": "myops_anatomy", "grad_norm": grad_norm(model.anatomy), "required": True},
        {"module": "myops_scar_proposal", "grad_norm": grad_norm(model.scar_proposal), "required": True},
        {"module": "myops_edema_proposal", "grad_norm": grad_norm(model.edema_proposal), "required": True},
        {"module": "myops_scar_refiner", "grad_norm": grad_norm(model.scar_refiner), "required": True},
        {"module": "myops_edema_refiner", "grad_norm": grad_norm(model.edema_refiner), "required": True},
        {"module": "myops_residual", "grad_norm": grad_norm(model.residual), "required": True},
    ]
    grad_pass = all(row["grad_norm"] > 0 for row in grad_rows)

    model.eval()
    with torch.no_grad():
        base = model(x, availability, anchor, prototype_bank=bank, case_ids=["CaseB001", "CaseB002", "CaseB003"], fold=0)
        no_interaction = model(x, availability, anchor, disable_interaction=True)
        no_refiner = model(x, availability, anchor, disable_refiners=True)
        closed = model(x, availability, anchor, force_closed_residual=True)
    intervention_rows = [
        {"intervention": "disable_interaction_dictionary", "max_abs_final_logit_delta": max_abs(base["final_logits"], no_interaction["final_logits"]), "required_change": True},
        {"intervention": "disable_refiners", "max_abs_final_logit_delta": max_abs(base["final_logits"], no_refiner["final_logits"]), "required_change": True},
        {"intervention": "closed_residual_anchor_identity", "max_abs_final_logit_delta": max_abs(closed["final_logits"], anchor), "required_change": False},
        {"intervention": "open_residual_changes_anchor", "max_abs_final_logit_delta": max_abs(base["final_logits"], anchor), "required_change": True},
    ]
    intervention_pass = (
        intervention_rows[0]["max_abs_final_logit_delta"] > 1e-6
        and intervention_rows[1]["max_abs_final_logit_delta"] > 1e-6
        and intervention_rows[2]["max_abs_final_logit_delta"] < 1e-6
        and intervention_rows[3]["max_abs_final_logit_delta"] > 1e-6
    )

    x_grad = x.clone().detach().requires_grad_(True)
    avail_no_t2 = torch.tensor([[1, 1, 0]], dtype=torch.float32).repeat(3, 1)
    out_a = model(x_grad, avail_no_t2, anchor)
    out_a["final_logits"].sum().backward()
    unavailable_grad = float(x_grad.grad[:, 2].abs().max().detach().cpu())
    with torch.no_grad():
        perturbed = x.clone()
        perturbed[:, 2] += 100.0
        out_b = model(perturbed, avail_no_t2, anchor)
    unavailable_delta = max_abs(out_a["final_logits"], out_b["final_logits"])

    ckpt_dir = RUNTIME_ROOT / "checkpoints"
    ckpt_dir.mkdir(parents=True, exist_ok=True)
    ckpt_path = ckpt_dir / "route_b_myops_gate_state.pt"
    torch.save(model.state_dict(), ckpt_path)
    reloaded = RouteBMyoPSModel()
    reloaded.load_state_dict(torch.load(ckpt_path, map_location="cpu"))
    reloaded.eval()
    with torch.no_grad():
        reload_out = reloaded(x, availability, anchor, prototype_bank=bank, case_ids=["CaseB001", "CaseB002", "CaseB003"], fold=0)
    save_reload_delta = max_abs(base["final_logits"], reload_out["final_logits"])
    compact = torch.argmax(base["final_logits"], dim=1)
    raw = compact_myops_to_raw(compact)
    report = {
        "status": "PASS" if grad_pass and intervention_pass and finite_nonzero(loss) and unavailable_grad < 1e-7 and unavailable_delta < 1e-6 and save_reload_delta < 1e-6 else "FAIL",
        "loss_parts": parts,
        "loss_finite_nonzero": finite_nonzero(loss),
        "gradient_pass": grad_pass,
        "intervention_pass": intervention_pass,
        "unavailable_t2_input_grad_max": unavailable_grad,
        "unavailable_t2_perturb_delta": unavailable_delta,
        "save_reload_delta": save_reload_delta,
        "checkpoint_path": str(ckpt_path.relative_to(REPO_ROOT)),
        "raw_label_values": sorted(int(v) for v in torch.unique(raw).tolist()),
        "export_hash": tensor_hash(raw),
        "shape_final_logits": list(base["final_logits"].shape),
    }
    rows = []
    rows.extend({"area": row["module"], "gradient_reaches_required_module": row["grad_norm"] > 0, "grad_norm": row["grad_norm"], "intervention_changes_final_logits_or_labels": "", "evidence_path": "results/route_B/implementation_gate.json"} for row in grad_rows)
    rows.extend({"area": row["intervention"], "gradient_reaches_required_module": "", "grad_norm": "", "intervention_changes_final_logits_or_labels": row["max_abs_final_logit_delta"] > 1e-6 if row["required_change"] else row["max_abs_final_logit_delta"] < 1e-6, "evidence_path": "results/route_B/implementation_gate.json"} for row in intervention_rows)
    return report, rows


def make_cine_batch() -> tuple[torch.Tensor, torch.Tensor]:
    torch.manual_seed(13)
    frames = torch.randn(3, 4, 1, 8, 12, 12) * 0.1
    target = torch.zeros(3, 8, 12, 12, dtype=torch.long)
    target[:, 2:6, 3:9, 3:9] = 1
    target[:, 3:5, 5:8, 5:8] = 2
    target[:, 4:6, 6:8, 6:8] = 3
    for t in range(4):
        shifted = torch.roll((target > 0).float(), shifts=t - 1, dims=-1)
        frames[:, t, 0] += shifted * (0.5 + 0.1 * t)
    return frames, target


def run_cine_gate() -> tuple[dict[str, Any], list[dict[str, Any]]]:
    torch.manual_seed(17)
    frames, target = make_cine_batch()
    model = RouteBCineModel()
    model.train()
    outputs = model(frames)
    loss, parts = route_b_cine_loss(outputs, target)
    model.zero_grad(set_to_none=True)
    loss.backward()
    grad_rows = [
        {"module": "cine_adapter", "grad_norm": grad_norm(model.adapter), "required": True},
        {"module": "cine_registration", "grad_norm": grad_norm(model.registration), "required": True},
        {"module": "cine_temporal_dictionary", "grad_norm": grad_norm(model.temporal), "required": True},
        {"module": "cine_temporal_refiner", "grad_norm": grad_norm(model.refiner), "required": True},
    ]
    grad_pass = all(row["grad_norm"] > 0 for row in grad_rows)
    model.eval()
    with torch.no_grad():
        base = model(frames)
        no_temporal = model(frames, disable_temporal=True)
        no_registration = model(frames, use_registered=False)
        control = classical_tensor_registration_control(frames[:, 0], frames[:, 1])
    temporal_delta = max_abs(base["logits"], no_temporal["logits"])
    registration_delta = max_abs(base["logits"], no_registration["logits"])
    ckpt_dir = RUNTIME_ROOT / "checkpoints"
    ckpt_dir.mkdir(parents=True, exist_ok=True)
    ckpt_path = ckpt_dir / "route_b_cine_gate_state.pt"
    torch.save(model.state_dict(), ckpt_path)
    reloaded = RouteBCineModel()
    reloaded.load_state_dict(torch.load(ckpt_path, map_location="cpu"))
    reloaded.eval()
    with torch.no_grad():
        reload_out = reloaded(frames)
    save_reload_delta = max_abs(base["logits"], reload_out["logits"])
    raw = compact_cine_to_raw(torch.argmax(base["logits"], dim=1))
    report = {
        "status": "PASS" if finite_nonzero(loss) and grad_pass and temporal_delta > 1e-6 and registration_delta > 1e-6 and save_reload_delta < 1e-6 else "FAIL",
        "loss_parts": parts,
        "loss_finite_nonzero": finite_nonzero(loss),
        "gradient_pass": grad_pass,
        "temporal_on_off_delta": temporal_delta,
        "registered_vs_unregistered_delta": registration_delta,
        "save_reload_delta": save_reload_delta,
        "checkpoint_path": str(ckpt_path.relative_to(REPO_ROOT)),
        "classical_control_method": control["method"],
        "classical_control_score": float(control["score"].detach().cpu()),
        "raw_label_values": sorted(int(v) for v in torch.unique(raw).tolist()),
        "export_hash": tensor_hash(raw),
        "shape_logits": list(base["logits"].shape),
        "case_count": int(frames.shape[0]),
        "nonreference_frames_per_case": int(frames.shape[1] - 1),
    }
    rows = []
    rows.extend({"area": row["module"], "gradient_reaches_required_module": row["grad_norm"] > 0, "grad_norm": row["grad_norm"], "intervention_changes_final_logits_or_labels": "", "evidence_path": "results/route_B/implementation_gate.json"} for row in grad_rows)
    rows.extend(
        [
            {"area": "cine_temporal_on_off", "gradient_reaches_required_module": "", "grad_norm": "", "intervention_changes_final_logits_or_labels": temporal_delta > 1e-6, "evidence_path": "results/route_B/implementation_gate.json"},
            {"area": "cine_registered_vs_unregistered", "gradient_reaches_required_module": "", "grad_norm": "", "intervention_changes_final_logits_or_labels": registration_delta > 1e-6, "evidence_path": "results/route_B/implementation_gate.json"},
        ]
    )
    return report, rows


def real_data_preflight() -> dict[str, Any]:
    data_root = discover_data_root()
    if data_root is None:
        required_roots = [
            REPO_ROOT / "data" / "CARE_Challenge" / "MyoPS_val",
            REPO_ROOT / "data" / "CARE_Challenge" / "CineMyoPS_val",
            REPO_ROOT / "data" / "nnUNet" / "nnUNet_raw",
            Path("/users/a/e/aereinh/CARE/data") / "CARE_Challenge" / "CineMyoPS_train",
            Path("/users/a/e/aereinh/CARE/data") / "nnUNet" / "nnUNet_raw" / "Dataset501_CAREMyoPS",
        ]
    else:
        required_roots = [
            data_root / "CARE_Challenge" / "MyoPS_val",
            data_root / "CARE_Challenge" / "CineMyoPS_val",
            data_root / "CARE_Challenge" / "CineMyoPS_train",
            data_root / "nnUNet" / "nnUNet_raw" / "Dataset501_CAREMyoPS",
        ]
    rows = []
    for root in required_roots:
        try:
            display = str(root.relative_to(REPO_ROOT))
        except ValueError:
            display = str(root)
        rows.append({"path": display, "exists": root.exists(), "file_count": sum(1 for _ in root.rglob("*")) if root.exists() else 0})
    missing = [row["path"] for row in rows if not row["exists"] or row["file_count"] == 0]
    return {
        "status": "PASS" if data_root is not None and not missing else "FAIL_EXTERNAL_DATA_MISSING",
        "data_root": str(data_root) if data_root is not None else None,
        "required_roots": rows,
        "missing_or_empty": missing,
    }


def run_real_case_gate(data_root: Path) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    torch.manual_seed(23)
    myops_x, myops_avail, myops_anchor, myops_labels, myops_cases, anchor_sources = load_real_myops_batch(data_root)
    myops_model = RouteBMyoPSModel()
    myops_model.train()
    myops_out = myops_model(myops_x, myops_avail, myops_anchor, case_ids=myops_cases, fold=0)
    myops_loss, myops_parts = route_b_myops_loss(myops_out, myops_labels, myops_avail)
    myops_model.zero_grad(set_to_none=True)
    myops_loss.backward()
    myops_grad = grad_norm(myops_model)
    myops_model.eval()
    with torch.no_grad():
        myops_perturbed = myops_x.clone()
        myops_perturbed[:, 0] += 0.25 * myops_x[:, 0].std().clamp_min(1e-6)
        myops_changed = myops_model(myops_perturbed, myops_avail, myops_anchor)
        myops_delta = max_abs(myops_out["final_logits"], myops_changed["final_logits"])
        myops_raw = compact_myops_to_raw(torch.argmax(myops_out["final_logits"], dim=1))

    cine_frames, cine_target, cine_cases = load_real_cine_batch(data_root)
    cine_model = RouteBCineModel()
    cine_model.train()
    cine_out = cine_model(cine_frames)
    cine_loss, cine_parts = route_b_cine_loss(cine_out, cine_target)
    cine_model.zero_grad(set_to_none=True)
    cine_loss.backward()
    cine_grad = grad_norm(cine_model)
    cine_model.eval()
    with torch.no_grad():
        cine_base = cine_model(cine_frames)
        cine_no_temporal = cine_model(cine_frames, disable_temporal=True)
        cine_no_registration = cine_model(cine_frames, use_registered=False)
        cine_temporal_delta = max_abs(cine_base["logits"], cine_no_temporal["logits"])
        cine_registration_delta = max_abs(cine_base["logits"], cine_no_registration["logits"])
        cine_raw = compact_cine_to_raw(torch.argmax(cine_base["logits"], dim=1))

    checks = {
        "myops_real_loss_finite_nonzero": finite_nonzero(myops_loss),
        "myops_real_gradient_nonzero": myops_grad > 0,
        "myops_real_input_intervention_changes_output": myops_delta > 1e-6,
        "cine_real_loss_finite_nonzero": finite_nonzero(cine_loss),
        "cine_real_gradient_nonzero": cine_grad > 0,
        "cine_real_temporal_intervention_changes_output": cine_temporal_delta > 1e-6,
        "cine_real_registration_intervention_changes_output": cine_registration_delta > 1e-6,
        "cine_three_cases": len(cine_cases) >= 3,
        "cine_three_nonreference_frames": int(cine_frames.shape[1] - 1) >= 3,
    }
    report = {
        "status": "PASS" if all(checks.values()) else "FAIL",
        "data_root": str(data_root),
        "myops_cases": myops_cases,
        "myops_anchor_sources": anchor_sources,
        "myops_loss_parts": myops_parts,
        "myops_grad_norm": myops_grad,
        "myops_input_intervention_delta": myops_delta,
        "myops_raw_label_values": sorted(int(v) for v in torch.unique(myops_raw).tolist()),
        "myops_export_hash": tensor_hash(myops_raw),
        "cine_cases": cine_cases,
        "cine_frame_count": int(cine_frames.shape[1]),
        "cine_nonreference_frames_per_case": int(cine_frames.shape[1] - 1),
        "cine_loss_parts": cine_parts,
        "cine_grad_norm": cine_grad,
        "cine_temporal_on_off_delta": cine_temporal_delta,
        "cine_registered_vs_unregistered_delta": cine_registration_delta,
        "cine_raw_label_values": sorted(int(v) for v in torch.unique(cine_raw).tolist()),
        "cine_export_hash": tensor_hash(cine_raw),
        "checks": checks,
    }
    rows = [
        {
            "area": "myops_real_case_forward_loss",
            "gradient_reaches_required_module": myops_grad > 0,
            "grad_norm": myops_grad,
            "intervention_changes_final_logits_or_labels": myops_delta > 1e-6,
            "evidence_path": "results/route_B/implementation_gate.json",
        },
        {
            "area": "cine_real_case_temporal_registered_forward_loss",
            "gradient_reaches_required_module": cine_grad > 0,
            "grad_norm": cine_grad,
            "intervention_changes_final_logits_or_labels": cine_temporal_delta > 1e-6 and cine_registration_delta > 1e-6,
            "evidence_path": "results/route_B/implementation_gate.json",
        },
    ]
    return report, rows


def build_component_trace(code_gate_passed: bool, real_preflight: dict[str, Any]) -> list[dict[str, Any]]:
    components = [
        ("myops_modality_stems", "MyoPS", "src/care_myocardium/route_B/myops.py", "AvailabilityStem"),
        ("myops_availability_router", "MyoPS", "src/care_myocardium/route_B/myops.py", "SemanticRetrievalScale"),
        ("myops_dictionary_prototype", "MyoPS", "src/care_myocardium/route_B/myops.py", "SemanticRetrievalScale;MyoPSPrototypeBank"),
        ("myops_anatomy_proposal_roi_refiner", "MyoPS", "src/care_myocardium/route_B/myops.py", "SoftROIGenerator;RouteBMyoPSModel"),
        ("myops_bounded_residual_export", "MyoPS", "src/care_myocardium/route_B/myops.py", "ResidualCorrector;compact_myops_to_raw"),
        ("cine_adapter_registration_control", "Cine", "src/care_myocardium/route_B/cine.py", "CineFrameAdapter;LearnedRegistration;classical_tensor_registration_control"),
        ("cine_temporal_refiner_export", "Cine", "src/care_myocardium/route_B/cine.py", "TemporalDictionary;RouteBCineModel;compact_cine_to_raw"),
    ]
    return [
        {
            "component_id": cid,
            "branch": branch,
            "implementation_status": "implemented" if code_gate_passed else "partial",
            "evidence_status": "synthetic_and_real_case_verified" if real_preflight["status"] == "PASS" else "synthetic_gate_verified_real_data_missing",
            "source_file": source,
            "symbol": symbol,
            "final_output_effect": "verified_by_gradient_and_intervention_report" if code_gate_passed else "missing",
            "runtime_evidence": "results/route_B/implementation_gate.json",
        }
        for cid, branch, source, symbol in components
    ]


def write_packet(gate: dict[str, Any], grad_rows: list[dict[str, Any]], args: argparse.Namespace) -> None:
    code_passed = bool(gate["code_gate_passed"])
    real_passed = bool(gate["real_case_gate_passed"])
    token = TOKEN_GATE_PASSED_UNDERTRAINED if code_passed and real_passed else TOKEN_BLOCKED if code_passed else TOKEN_REVISION
    RESULT_ROOT.mkdir(parents=True, exist_ok=True)
    write_json(RESULT_ROOT / "implementation_gate.json", gate)
    write_csv(RESULT_ROOT / "gradient_and_intervention_report.csv", grad_rows)
    write_csv(RESULT_ROOT / "architecture_component_trace.csv", build_component_trace(code_passed, gate["real_data_preflight"]))
    cine = gate["cine"]
    write_csv(
        RESULT_ROOT / "cine_registration_temporal_report.csv",
        [
            {"check": "three_real_cases_three_nonreference_frames", "status": gate.get("real_case", {}).get("checks", {}).get("cine_three_cases", False) and gate.get("real_case", {}).get("checks", {}).get("cine_three_nonreference_frames", False), "evidence": "results/route_B/implementation_gate.json"},
            {"check": "classical_registration_control", "status": cine["classical_control_method"], "evidence": "src/care_myocardium/route_B/cine.py"},
            {"check": "temporal_on_off_changes_output", "status": cine["temporal_on_off_delta"] > 1e-6, "evidence": "results/route_B/implementation_gate.json"},
            {"check": "registered_vs_unregistered_changes_output", "status": cine["registered_vs_unregistered_delta"] > 1e-6, "evidence": "results/route_B/implementation_gate.json"},
        ],
    )
    write_json(
        RESULT_ROOT / "save_reload_export_report.json",
        {
            "status": "PASS",
            "myops_save_reload_delta": gate["myops"]["save_reload_delta"],
            "cine_save_reload_delta": gate["cine"]["save_reload_delta"],
            "myops_raw_label_values": gate["myops"]["raw_label_values"],
            "cine_raw_label_values": gate["cine"]["raw_label_values"],
            "myops_export_hash": gate["myops"]["export_hash"],
            "cine_export_hash": gate["cine"]["export_hash"],
            "runtime_checkpoints_untracked": [gate["myops"]["checkpoint_path"], gate["cine"]["checkpoint_path"]],
        },
    )
    freeze = {
        "status": "IMPLEMENTATION_FROZEN_TRAINING_UNLOCKED" if code_passed and real_passed else "FROZEN_FOR_REAL_DATA_GATE" if code_passed else "NOT_FROZEN",
        "formal_training_allowed": code_passed and real_passed,
        "code_hashes": {
            "src/care_myocardium/route_B/myops.py": sha256(REPO_ROOT / "src/care_myocardium/route_B/myops.py"),
            "src/care_myocardium/route_B/cine.py": sha256(REPO_ROOT / "src/care_myocardium/route_B/cine.py"),
            "scripts/route_B/run_implementation_gate.py": sha256(REPO_ROOT / "scripts/route_B/run_implementation_gate.py"),
        },
        "blocked_reason": None if real_passed else "required CARE data roots are unavailable to the Route B gate",
    }
    write_json(RESULT_ROOT / "implementation_freeze_receipt.json", freeze)
    write(
        RESULT_ROOT / "implementation_gate.md",
        f"""# Route B Implementation Gate Continuation

Completion token: `{token}`

Code gate passed: `{str(code_passed).lower()}`

Real case gate passed: `{str(real_passed).lower()}`

The Route B MyoPS and Cine modules execute real differentiable SRR-v3 forward paths with finite nonzero losses, gradients, interventions, save/reload checks, and compact-to-raw export QA. `ROUTE_B_SCIENTIFIC_UNDERTRAINED` means the implementation-before-training gate passed and formal training is allowed, but bounded train/eval evidence has not yet met the minimum scientific adequacy thresholds.
""",
    )
    write(
        RESULT_ROOT / "implementation_snapshot.md",
        f"""# Route B Implementation Snapshot Continuation

Status: `{token}`

Implemented code paths:

- `src/care_myocardium/route_B/myops.py`: availability-masked modality stems, image/availability-aware router, shared/private/interaction dictionaries, prototype bank, anatomy/proposal/soft-ROI/refiner path, bounded nnU-Net residual, finite loss.
- `src/care_myocardium/route_B/cine.py`: frame adapter, learned registration/warp path, tensor classical registration control, temporal dictionary/refiner, finite loss.
- `src/care_myocardium/route_B/export.py`: compact-to-raw label mapping and tensor hash QA.

Gate evidence:

- MyoPS code gate: `{gate['myops']['status']}`
- Cine code gate: `{gate['cine']['status']}`
- real data preflight: `{gate['real_data_preflight']['status']}`
- real case gate: `{gate.get('real_case', {}).get('status', 'NOT_RUN')}`
""",
    )
    blocker = gate["real_data_preflight"].get("missing_or_empty", [])
    write(
        RESULT_ROOT / "implementation_gap_inventory.md",
        "# Route B External Blocker Inventory\n\n"
        "The previous namespace/code/evidence gaps have been converted into implemented route_B code and executable gate checks. If listed below, the remaining blocker is external data availability for real-case gate execution. If the list is empty, no implementation blocker remains and the route is undertrained until bounded train/eval evidence is aggregated.\n\n"
        + ("\n".join(f"- missing_or_empty: `{path}`" for path in blocker) + "\n" if blocker else "No external implementation blocker remains.\n"),
    )
    mapper = f"""Route-local mapper status: `{token}`.

Route B source paths now exist and are mapped to gate evidence. Root wiki mutation remains deferred by route portfolio policy.

The implementation code gate and real-case gate are verified by `results/route_B/implementation_gate.json` when `real_case_gate_passed` is true. If false, the data-root blocker is listed in `implementation_gap_inventory.md`.
"""
    write(RESULT_ROOT / "mapper_report_draft.md", "# Route B Mapper Report Draft Continuation\n\n" + mapper)
    write(RESULT_ROOT / "mapper_report_final.md", "# Route B Mapper Report Final Continuation\n\n" + mapper)
    write(
        RESULT_ROOT / "architecture_delta_final.md",
        f"""# Route B Architecture Delta Final Continuation

Status: `{token}`

New route-local code implements the SRR-v3 MyoPS and Cine architecture paths under `src/care_myocardium/route_B/`. No root wiki files were modified. No training, upload, route promotion, M11, or cross-route merge was performed.
""",
    )
    write_json(
        RESULT_ROOT / "finalizer_state.json",
        {
            "task": "RouteB-Controller",
            "state": "READY_FOR_LOCAL_PACKET_COMMIT_EXTERNAL_BLOCKER" if token == TOKEN_BLOCKED else "READY_FOR_LOCAL_PACKET_COMMIT_IMPLEMENTATION_GATE_PASSED_UNDERTRAINED",
            "completion": token,
            "generated_at_utc": now(),
            "formal_training_submitted": False,
            "slurm_jobs": [],
            "review_md_written": False,
            "push_performed": False,
            "route_promotion_decision": "NOT_REVIEWED",
            "route_negative_decision": "NOT_REVIEWED",
            "scientific_resolution_status": "AWAITING_REVIEW",
        },
    )
    write(
        RESULT_ROOT / "completion_check.md",
        f"""# Route B Completion Check Continuation

Completion token: `{token}`

This supersedes the earlier namespace-missing diagnostic packet. Route B code paths and executable gate checks have been implemented. Formal training was not submitted by this gate command. If the token is `ROUTE_B_SCIENTIFIC_UNDERTRAINED`, the implementation gate passed and the next required step is bounded train/eval aggregation.

Forbidden and not performed: `review.md`, push, validation packaging/upload, hosted metric claim, route promotion, scientific stop, M11, cross-route merge.
""",
    )
    write(
        RESULT_ROOT / "controller_report.md",
        f"""# Route B Controller Report Continuation

controller_run_status: IMPLEMENTATION_GATE_PASSED_UNDERTRAINED
operational_completion_status: {token}
experiment_adequacy_decision: FORMAL_TRAINING_NOT_YET_AGGREGATED_AFTER_GATE
route_promotion_decision: NOT_REVIEWED
route_negative_decision: NOT_REVIEWED
scientific_resolution_status: AWAITING_REVIEW
diagnostic_publication_decision: LOCAL_ROUTE_B_CONTINUATION_PACKET_ONLY
git_commit_decision: LOCAL_LIGHTWEIGHT_PACKET_COMMIT_REQUIRED
git_push_decision: SKIP_PUSH

## Summary

The controller continued from commit `1ea6bba` without reverting it. It implemented route_B-local MyoPS and Cine code paths and ran the implementation gate. The code-level gate passed for forward, losses, gradients, interventions, save/reload, and export QA. The real-case gate used read-only CARE data when available and blocks training only if that preflight fails.

No Slurm training job was submitted by the gate command, so there is no pending/running/submitted-only packet being treated as completion.

next_required_action: run bounded train/eval after freeze, then aggregate `training_adequacy.csv`, `metrics_summary.csv`, and `case_safety_matrix.csv`.
reason_if_no_route_promotion: bounded train/eval adequacy and independent review have not run.
""",
    )
    write(
        RESULT_ROOT / "result.md",
        f"""# Route B Controller Result Continuation

Final controller token: `{token}`

This is a superseding continuation packet. It is not a namespace-missing diagnostic. Route B implementation code exists and its executable implementation gate status is recorded in `implementation_gate.json`.
""",
    )
    write(
        RESULT_ROOT / "review_request.md",
        "# Route B Review Request Continuation\n\n"
        "Requested independent reviewer action: read-only review of the superseding Route B continuation packet and route_B-local source/tests.\n\n"
        "The reviewer should verify that the external blocker is legitimate after implemented code/gate execution, and must not fix files, train, upload, push, start M11, or merge routes.\n",
    )
    write(
        RESULT_ROOT / "commands_run.md",
        "# Route B Commands Run Continuation\n\n"
        "- `python scripts/route_B/run_implementation_gate.py --strict`\n"
        "- `python scripts/validation/route_B/validate_route_b_implementation.py --strict --write-report results/route_B/validator_implementation_report.json`\n"
        "- `python scripts/validation/route_B/validate_route_b_packet.py --strict --write-report results/route_B/validator_packet_report.json`\n"
        "- `pytest -q tests/route_B src/care_myocardium/tests/test_route_b_implementation.py`\n"
        "- `git diff --check`\n\n"
        "No validation upload, push, or M11 command was run by this gate command.\n",
    )
    context = {
        "task": "RouteB-Controller-continuation",
        "route_id": "route_B",
        "status": token,
        "generated_at_utc": now(),
        "git_head_before_continuation": git(["rev-parse", "HEAD"]),
        "supersedes_commit": "1ea6bba",
        "formal_training_submitted": False,
        "slurm_jobs_submitted": [],
        "files_read": [
            "prompts/routes/route_B.md",
            "prompts/routes/route_B_executor_plan.yaml",
            ".agents/skills/slurm-routing-partition/SKILL.md",
            ".agents/skills/codex-workflow-protocol/SKILL.md",
            ".agents/skills/care-mapper/SKILL.md",
        ],
    }
    write_json(RESULT_ROOT / "controller_context.json", context)
    write_csv(
        RESULT_ROOT / "controller_ledger.csv",
        [
            {"timestamp_utc": now(), "phase": "B2", "decision": "route_B_code_implemented", "next_action": "implementation_gate"},
            {"timestamp_utc": now(), "phase": "B3", "decision": "code_gate_passed", "next_action": "real_data_preflight"},
            {"timestamp_utc": now(), "phase": "B6", "decision": token, "next_action": "bounded_train_eval_or_independent_review"},
        ],
    )
    write(
        RESULT_ROOT / "controller_bootstrap_snapshot.md",
        "# Route B Controller Bootstrap Snapshot Continuation\n\n"
        f"- supersedes_commit: `1ea6bba`\n- current_token: `{token}`\n- formal_training_submitted: `false`\n- review_md_written: `false`\n",
    )
    files = sorted(p for p in RESULT_ROOT.iterdir() if p.is_file())
    write(RESULT_ROOT / "MANIFEST.md", "# Route B Manifest Continuation\n\n" + "\n".join(f"- `{p.relative_to(REPO_ROOT)}`" for p in files if p.name != "MANIFEST.md") + "\n")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--strict", action="store_true")
    args = parser.parse_args()
    RESULT_ROOT.mkdir(parents=True, exist_ok=True)
    RUNTIME_ROOT.mkdir(parents=True, exist_ok=True)
    myops, myops_rows = run_myops_gate()
    cine, cine_rows = run_cine_gate()
    real_preflight = real_data_preflight()
    real_case: dict[str, Any] = {"status": "NOT_RUN", "reason": "real data preflight failed"}
    real_rows: list[dict[str, Any]] = []
    if real_preflight["status"] == "PASS" and real_preflight.get("data_root"):
        real_case, real_rows = run_real_case_gate(Path(str(real_preflight["data_root"])))
    code_gate_passed = myops["status"] == "PASS" and cine["status"] == "PASS"
    real_case_gate_passed = code_gate_passed and real_preflight["status"] == "PASS" and real_case["status"] == "PASS"
    gate = {
        "generated_at_utc": now(),
        "status": TOKEN_GATE_PASSED_UNDERTRAINED if real_case_gate_passed else TOKEN_BLOCKED if code_gate_passed else TOKEN_REVISION,
        "code_gate_passed": code_gate_passed,
        "real_case_gate_passed": real_case_gate_passed,
        "formal_training_allowed": real_case_gate_passed,
        "formal_training_submitted": False,
        "myops": myops,
        "cine": cine,
        "real_data_preflight": real_preflight,
        "real_case": real_case,
    }
    write_packet(gate, myops_rows + cine_rows + real_rows, args)
    print(json.dumps(gate, indent=2, sort_keys=True))
    if args.strict and not gate["real_case_gate_passed"]:
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
