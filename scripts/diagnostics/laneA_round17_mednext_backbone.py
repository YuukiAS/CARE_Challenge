#!/usr/bin/env python3
"""Lane A Round17 MedNeXt / stronger-backbone low-risk diagnostics.

This script executes only the front gates of the Round17 controller:

* reproducibility/path/label/fold0 baseline gate;
* MedNeXt metadata and compliance audit from the existing Round16 clone;
* import, instantiate, forward, and backward shape smoke on synthetic tensors.

It does not train, submit Slurm, download weights, create validation zips,
upload, or write into nnU-Net baseline result/cache directories.
"""

from __future__ import annotations

import csv
import json
import os
import subprocess
import sys
import time
from contextlib import contextmanager
from pathlib import Path
from typing import Iterator


REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

OUT_ROOT = REPO_ROOT / "results/diagnostics/care_myocardium/laneA_myops/round17_mednext_backbone"
PLAN_PATH = REPO_ROOT / "docs/plans/laneA_round17_next_mednext_stronger_backbone_integration_execution.md"
REGISTRY_PATH = REPO_ROOT / "docs/plans/care_myocardium_plan_registry_rules.md"
DATASET_JSON = REPO_ROOT / "data/nnUNet/nnUNet_raw/Dataset501_CAREMyoPS/dataset.json"
PREPROC_DATASET_JSON = REPO_ROOT / "data/nnUNet/nnUNet_preprocessed/Dataset501_CAREMyoPS/dataset.json"
SPLITS_JSON = REPO_ROOT / "data/nnUNet/nnUNet_preprocessed/Dataset501_CAREMyoPS/splits_final.json"
PREPROC_ROOT = REPO_ROOT / "data/nnUNet/nnUNet_preprocessed/Dataset501_CAREMyoPS"
PREPROC_FULLRES = PREPROC_ROOT / "nnUNetPlans_3d_fullres"
RAW_ROOT = REPO_ROOT / "data/nnUNet/nnUNet_raw/Dataset501_CAREMyoPS"
BASELINE_ROOT = (
    REPO_ROOT
    / "data/nnUNet/nnUNet_results/Dataset501_CAREMyoPS/"
    / "nnUNetTrainer_500epochs__nnUNetPlans__3d_fullres"
)
BASELINE_FOLD0 = BASELINE_ROOT / "fold_0"
BASELINE_VAL = BASELINE_FOLD0 / "validation"
ROUND16_ROOT = REPO_ROOT / "results/diagnostics/care_myocardium/laneA_myops/round16_external_mechanism_integration"
MEDNEXT_REPO = ROUND16_ROOT / "external_repos/MedNeXt"
FOCUS_CASES = ["Case2031", "Case3011", "Case3012", "Case3040", "Case3044"]


def write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def write_csv(path: Path, rows: list[dict[str, object]], fieldnames: list[str] | None = None) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    names = fieldnames or (list(rows[0].keys()) if rows else [])
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=names, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def read_json(path: Path) -> object | None:
    if not path.is_file():
        return None
    return json.loads(path.read_text(encoding="utf-8"))


def git_value(repo: Path, args: list[str]) -> str:
    if not (repo / ".git").is_dir():
        return "missing_git_dir"
    try:
        return subprocess.check_output(["git", "-C", str(repo), *args], text=True, stderr=subprocess.STDOUT).strip()
    except Exception as exc:  # noqa: BLE001
        return f"ERROR:{type(exc).__name__}:{exc}"


def first_existing(root: Path, names: list[str]) -> Path | None:
    for name in names:
        path = root / name
        if path.exists():
            return path
    return None


@contextmanager
def sys_path_prepend(path: Path) -> Iterator[None]:
    text = str(path)
    sys.path.insert(0, text)
    try:
        yield
    finally:
        try:
            sys.path.remove(text)
        except ValueError:
            pass


def dataset_labels() -> dict[str, int]:
    data = read_json(DATASET_JSON)
    if not isinstance(data, dict):
        return {}
    labels = data.get("labels", {})
    return {str(k): int(v) for k, v in labels.items()} if isinstance(labels, dict) else {}


def channel_names() -> dict[str, str]:
    data = read_json(DATASET_JSON)
    if not isinstance(data, dict):
        return {}
    channels = data.get("channel_names", {})
    return {str(k): str(v) for k, v in channels.items()} if isinstance(channels, dict) else {}


def fold0_split() -> tuple[list[str], list[str]]:
    data = read_json(SPLITS_JSON)
    if not isinstance(data, list) or not data:
        return [], []
    split = data[0]
    if not isinstance(split, dict):
        return [], []
    return list(split.get("train", [])), list(split.get("val", []))


def stage1_reproducibility() -> None:
    labels = dataset_labels()
    channels = channel_names()
    train_cases, val_cases = fold0_split()
    val_nii = sorted(BASELINE_VAL.glob("Case*.nii.gz"))
    val_npz = sorted(BASELINE_VAL.glob("Case*.npz"))
    val_pkl = sorted(BASELINE_VAL.glob("Case*.pkl"))
    summary_json = BASELINE_VAL / "summary.json"
    hard_case_rows = []
    for case in FOCUS_CASES:
        hard_case_rows.append(
            {
                "case": case,
                "in_fold0_val": case in val_cases,
                "baseline_pred": str((BASELINE_VAL / f"{case}.nii.gz").relative_to(REPO_ROOT))
                if (BASELINE_VAL / f"{case}.nii.gz").is_file()
                else "",
                "baseline_npz": str((BASELINE_VAL / f"{case}.npz").relative_to(REPO_ROOT))
                if (BASELINE_VAL / f"{case}.npz").is_file()
                else "",
                "raw_lge": str((RAW_ROOT / "imagesTr" / f"{case}_0000.nii.gz").relative_to(REPO_ROOT))
                if (RAW_ROOT / "imagesTr" / f"{case}_0000.nii.gz").is_file()
                else "",
                "raw_t2": str((RAW_ROOT / "imagesTr" / f"{case}_0001.nii.gz").relative_to(REPO_ROOT))
                if (RAW_ROOT / "imagesTr" / f"{case}_0001.nii.gz").is_file()
                else "",
                "raw_c0": str((RAW_ROOT / "imagesTr" / f"{case}_0002.nii.gz").relative_to(REPO_ROOT))
                if (RAW_ROOT / "imagesTr" / f"{case}_0002.nii.gz").is_file()
                else "",
                "label": str((RAW_ROOT / "labelsTr" / f"{case}.nii.gz").relative_to(REPO_ROOT))
                if (RAW_ROOT / "labelsTr" / f"{case}.nii.gz").is_file()
                else "",
            }
        )

    gate_rows = [
        {
            "check": "round17_plan_exists",
            "status": "pass" if PLAN_PATH.is_file() else "fail",
            "evidence": str(PLAN_PATH.relative_to(REPO_ROOT)),
        },
        {
            "check": "plan_registry_exists",
            "status": "pass" if REGISTRY_PATH.is_file() else "fail",
            "evidence": str(REGISTRY_PATH.relative_to(REPO_ROOT)),
        },
        {
            "check": "canonical_output_root",
            "status": "pass" if "phase0_phase1" not in str(OUT_ROOT) else "fail",
            "evidence": str(OUT_ROOT.relative_to(REPO_ROOT)),
        },
        {
            "check": "dataset_json_exists",
            "status": "pass" if DATASET_JSON.is_file() and PREPROC_DATASET_JSON.is_file() else "fail",
            "evidence": f"{DATASET_JSON.relative_to(REPO_ROOT)}; {PREPROC_DATASET_JSON.relative_to(REPO_ROOT)}",
        },
        {
            "check": "label_semantics_class4_class5",
            "status": "pass" if labels.get("edema") == 4 and labels.get("scar") == 5 else "fail",
            "evidence": json.dumps(labels, ensure_ascii=False, sort_keys=True),
        },
        {
            "check": "channel_semantics_lge_t2_c0",
            "status": "pass" if channels == {"0": "LGE", "1": "T2", "2": "C0"} else "warn",
            "evidence": json.dumps(channels, ensure_ascii=False, sort_keys=True),
        },
        {
            "check": "fold0_split_counts",
            "status": "pass" if len(train_cases) == 176 and len(val_cases) == 44 else "fail",
            "evidence": f"train={len(train_cases)} val={len(val_cases)}",
        },
        {
            "check": "baseline_fold0_predictions",
            "status": "pass" if len(val_nii) == 44 and len(val_npz) == 44 else "fail",
            "evidence": f"nii={len(val_nii)} npz={len(val_npz)} pkl={len(val_pkl)}",
        },
        {
            "check": "baseline_summary_json",
            "status": "pass" if summary_json.is_file() else "warn",
            "evidence": str(summary_json.relative_to(REPO_ROOT)),
        },
        {
            "check": "hard_cases_in_fold0_val",
            "status": "pass" if all(case in val_cases for case in FOCUS_CASES) else "fail",
            "evidence": ",".join(case for case in FOCUS_CASES if case in val_cases),
        },
    ]
    write_csv(OUT_ROOT / "round17_reproducibility_gate.csv", gate_rows)
    write_csv(OUT_ROOT / "round17_hard_case_path_manifest.csv", hard_case_rows)
    write_csv(
        OUT_ROOT / "round17_baseline_path_manifest.csv",
        [
            {
                "name": "Dataset501 raw dataset_json",
                "path": str(DATASET_JSON.relative_to(REPO_ROOT)),
                "exists": DATASET_JSON.is_file(),
            },
            {
                "name": "Dataset501 preprocessed dataset_json",
                "path": str(PREPROC_DATASET_JSON.relative_to(REPO_ROOT)),
                "exists": PREPROC_DATASET_JSON.is_file(),
            },
            {
                "name": "Dataset501 splits_final",
                "path": str(SPLITS_JSON.relative_to(REPO_ROOT)),
                "exists": SPLITS_JSON.is_file(),
            },
            {
                "name": "Dataset501 preprocessed root",
                "path": str(PREPROC_ROOT.relative_to(REPO_ROOT)),
                "exists": PREPROC_ROOT.is_dir(),
            },
            {
                "name": "nnU-Net501 fold0 baseline root",
                "path": str(BASELINE_FOLD0.relative_to(REPO_ROOT)),
                "exists": BASELINE_FOLD0.is_dir(),
            },
            {
                "name": "nnU-Net501 fold0 validation",
                "path": str(BASELINE_VAL.relative_to(REPO_ROOT)),
                "exists": BASELINE_VAL.is_dir(),
            },
        ],
    )


def candidate_matrix() -> None:
    rows = [
        {
            "candidate_id": "R17_A_mednext_s_kernel3_standard_dicece_fold0_vs",
            "model_size": "S",
            "kernel_size": 3,
            "channels": 3,
            "classes": 6,
            "deep_supervision": False,
            "role": "first priority CARE-only architecture baseline",
            "job_type": "fold0 very-short after Stage1-4 gates",
            "primary_gate": "myops_edema class_4 T2-present GT-positive / CenterC",
            "scar_gate": "myops_scar class_5 co-primary non-regression/improvement",
        },
        {
            "candidate_id": "R17_B_mednext_b_kernel3_standard_dicece_fold0_vs",
            "model_size": "B",
            "kernel_size": 3,
            "channels": 3,
            "classes": 6,
            "deep_supervision": False,
            "role": "second priority if memory permits",
            "job_type": "fold0 very-short after A shape gate",
            "primary_gate": "myops_edema class_4 T2-present GT-positive / CenterC",
            "scar_gate": "myops_scar class_5 co-primary non-regression/improvement",
        },
        {
            "candidate_id": "R17_C_mednext_s_kernel5_upkern_or_largekernel_fold0_vs",
            "model_size": "S",
            "kernel_size": 5,
            "channels": 3,
            "classes": 6,
            "deep_supervision": False,
            "role": "watch: larger kernel only after A/B viable",
            "job_type": "shape smoke first",
            "primary_gate": "edema cannot trade Dice for HD95/component regression",
            "scar_gate": "scar co-primary cannot regress",
        },
        {
            "candidate_id": "R17_D_mednext_s_modality_channels_fold0_vs",
            "model_size": "S",
            "kernel_size": 3,
            "channels": 6,
            "classes": 6,
            "deep_supervision": False,
            "role": "watch: optional modality-presence channels",
            "job_type": "shape smoke first",
            "primary_gate": "edema signal plus no-T2 stability",
            "scar_gate": "scar co-primary cannot regress",
        },
        {
            "candidate_id": "R17_E_mednext_s_small_boundary_aux_fold0_vs",
            "model_size": "S",
            "kernel_size": 3,
            "channels": 3,
            "classes": 6,
            "deep_supervision": False,
            "role": "auxiliary only after standard MedNeXt signal",
            "job_type": "post-A/B watch",
            "primary_gate": "HD95/component improves without edema over-pruning",
            "scar_gate": "scar co-primary cannot regress",
        },
    ]
    write_csv(OUT_ROOT / "round17_mednext_candidate_matrix.csv", rows)


def mednext_metadata() -> None:
    lic = first_existing(MEDNEXT_REPO, ["LICENSE", "LICENSE.md", "LICENSE.txt", "COPYING"])
    license_text = lic.read_text(encoding="utf-8", errors="ignore") if lic and lic.is_file() else ""
    license_status = "apache_2_0_detected" if "Apache License" in license_text and "Version 2.0" in license_text else "missing_or_needs_review"
    setup = first_existing(MEDNEXT_REPO, ["setup.py", "pyproject.toml", "requirements.txt", "environment.yml"])
    remote = git_value(MEDNEXT_REPO, ["config", "--get", "remote.origin.url"])
    commit = git_value(MEDNEXT_REPO, ["rev-parse", "HEAD"])
    status = git_value(MEDNEXT_REPO, ["status", "--short"])

    compliance_rows = [
        {
            "candidate": "MedNeXt v1 code-only architecture",
            "url": remote,
            "commit": commit,
            "license": license_status,
            "pretrained_weights_available": "not_used",
            "pretrained_data_source": "not_applicable_code_only",
            "external_training_data_required": "no",
            "compliance_risk": "low_for_code_only; weight_route_blocked_pending_provenance",
            "stage17_stance": "pass_metadata_if_import_smoke_passes",
        },
        {
            "candidate": "MedNeXt pretrained / M&Ms / Task114 route",
            "url": "unclear_or_not_selected",
            "commit": "not_applicable",
            "license": "pending",
            "pretrained_weights_available": "unclear_not_downloaded",
            "pretrained_data_source": "unclear",
            "external_training_data_required": "unclear",
            "compliance_risk": "medium_until_weight_provenance_documented",
            "stage17_stance": "watch_do_not_use_without_pass_weight_gate",
        },
    ]
    write_csv(OUT_ROOT / "round17_mednext_compliance_matrix.csv", compliance_rows)
    write_csv(
        OUT_ROOT / "round17_pretrained_weight_provenance_audit.csv",
        [
            {
                "asset": "MedNeXt v1 source code",
                "used_in_round17": "yes_code_only",
                "weights_downloaded": "no",
                "pretrained_data_source": "not_applicable",
                "status": "allowed_for_metadata_shape_smoke",
            },
            {
                "asset": "MedNeXt / M&Ms / Task114 pretrained weights",
                "used_in_round17": "no",
                "weights_downloaded": "no",
                "pretrained_data_source": "pending_manual_provenance",
                "status": "blocked_pending_pass_weight_gate",
            },
        ],
    )
    write_text(
        OUT_ROOT / "round17_mednext_repo_metadata_audit.md",
        "\n".join(
            [
                "# Round17 MedNeXt Repo Metadata Audit",
                "",
                f"- Repo path: `{MEDNEXT_REPO.relative_to(REPO_ROOT)}`",
                f"- Exists: `{MEDNEXT_REPO.is_dir()}`",
                f"- Remote: `{remote}`",
                f"- Commit: `{commit}`",
                f"- Git status: `{status or 'clean_or_no_output'}`",
                f"- License path: `{lic.relative_to(REPO_ROOT) if lic else 'missing'}`",
                f"- License status: `{license_status}`",
                f"- Dependency/setup file: `{setup.relative_to(REPO_ROOT) if setup else 'missing'}`",
                "",
                "Round17 uses the existing Round16 clone for metadata/import smoke only. No pretrained weights, external datasets, Slurm jobs, or validation packages are used here.",
                "",
                "Compliance stance: code-only architecture route is low risk after import/shape smoke; pretrained routes remain blocked until weight provenance and CARE challenge compliance are documented.",
            ]
        )
        + "\n",
    )


def mednext_smoke() -> None:
    rows: list[dict[str, object]] = []
    mem_rows: list[dict[str, object]] = []
    notes: list[str] = ["# Round17 MedNeXt Network Shape Smoke", ""]
    if not MEDNEXT_REPO.is_dir():
        rows.append({"candidate": "MedNeXt", "status": "fail_missing_repo", "detail": str(MEDNEXT_REPO)})
        write_csv(OUT_ROOT / "round17_import_onecase_smoke_summary.csv", rows)
        write_text(OUT_ROOT / "round17_network_shape_smoke.md", "\n".join(notes + ["MedNeXt repo missing."]) + "\n")
        return

    try:
        import torch

        from src.care_myocardium.mednext import MedNeXtConfig, create_care_mednext

        torch.set_num_threads(min(2, max(1, os.cpu_count() or 1)))
        os.environ.setdefault("CARE_MEDNEXT_REPO", str(MEDNEXT_REPO))
    except Exception as exc:  # noqa: BLE001
        rows.append({"candidate": "MedNeXt import", "status": "fail", "detail": f"{type(exc).__name__}:{exc}"})
        write_csv(OUT_ROOT / "round17_import_onecase_smoke_summary.csv", rows)
        write_text(OUT_ROOT / "round17_network_shape_smoke.md", "\n".join(notes + [f"Import failed: `{type(exc).__name__}: {exc}`"]) + "\n")
        return

    smoke_specs = [
        ("R17_A_mednext_s_kernel3_standard_dicece_fold0_vs", "S", 3, 3, True),
        ("R17_B_mednext_b_kernel3_standard_dicece_fold0_vs", "B", 3, 3, False),
        ("R17_D_mednext_s_modality_channels_fold0_vs", "S", 3, 6, False),
    ]
    # Synthetic shape is deliberately tiny but divisible through MedNeXt down/up path.
    shape = (1, 0, 32, 64, 64)
    for candidate, model_size, kernel_size, channels, run_backward in smoke_specs:
        started = time.time()
        status = "pass"
        detail = ""
        out_shape = ""
        loss_value = ""
        grad_norm = ""
        params = 0
        try:
            import torch

            model = create_care_mednext(
                MedNeXtConfig(
                    model_id=model_size,
                    num_input_channels=channels,
                    num_classes=6,
                    kernel_size=kernel_size,
                    deep_supervision=False,
                )
            )
            model.train()
            params = sum(p.numel() for p in model.parameters())
            x_shape = (shape[0], channels, shape[2], shape[3], shape[4])
            x = torch.randn(x_shape, dtype=torch.float32)
            out = model(x)
            logits = out[0] if isinstance(out, (tuple, list)) else out
            out_shape = "x".join(str(v) for v in logits.shape)
            ok_shape = tuple(logits.shape) == (1, 6, shape[2], shape[3], shape[4])
            if not ok_shape:
                status = "fail"
                detail = f"unexpected output shape {tuple(logits.shape)}"
            if run_backward and status == "pass":
                y = torch.randint(0, 6, (1, shape[2], shape[3], shape[4]), dtype=torch.long)
                loss = torch.nn.functional.cross_entropy(logits, y)
                loss.backward()
                total = 0.0
                for p in model.parameters():
                    if p.grad is not None:
                        total += float(p.grad.detach().pow(2).sum().item())
                grad_norm = f"{total ** 0.5:.6g}"
                loss_value = f"{float(loss.detach().item()):.6g}"
                if not torch.isfinite(loss):
                    status = "fail"
                    detail = "non_finite_loss"
            elif status == "pass":
                loss_value = "not_run_for_speed"
                grad_norm = "not_run_for_speed"
        except Exception as exc:  # noqa: BLE001
            status = "fail"
            detail = f"{type(exc).__name__}:{exc}"[:500]
        elapsed = time.time() - started
        rows.append(
            {
                "candidate": candidate,
                "model_size": model_size,
                "kernel_size": kernel_size,
                "input_channels": channels,
                "output_classes": 6,
                "synthetic_input_shape": f"1x{channels}x{shape[2]}x{shape[3]}x{shape[4]}",
                "output_shape": out_shape,
                "params": params,
                "backward": run_backward,
                "loss_value": loss_value,
                "grad_norm": grad_norm,
                "status": status,
                "detail": detail,
                "elapsed_sec": f"{elapsed:.3f}",
            }
        )
        mem_rows.append(
            {
                "candidate": candidate,
                "model_size": model_size,
                "input_channels": channels,
                "params": params,
                "param_memory_mb_fp32": f"{params * 4 / 1024 / 1024:.2f}",
                "synthetic_input_shape": f"1x{channels}x{shape[2]}x{shape[3]}x{shape[4]}",
                "smoke_elapsed_sec": f"{elapsed:.3f}",
                "memory_note": "CPU smoke only; GPU memory must be measured in Stage4/5 before fold0 jobs.",
            }
        )

    write_csv(OUT_ROOT / "round17_import_onecase_smoke_summary.csv", rows)
    write_csv(OUT_ROOT / "round17_memory_footprint_estimate.csv", mem_rows)
    notes.extend(
        [
            "Synthetic smoke used no CARE image labels and performed no training.",
            "",
            "| candidate | status | output_shape | params | backward | loss | grad_norm |",
            "| --- | --- | --- | --- | --- | --- | --- |",
        ]
    )
    for row in rows:
        notes.append(
            f"| {row['candidate']} | {row['status']} | {row['output_shape']} | {row['params']} | {row['backward']} | {row['loss_value']} | {row['grad_norm']} |"
        )
    write_text(OUT_ROOT / "round17_network_shape_smoke.md", "\n".join(notes) + "\n")


def _pad_or_crop_spatial(array, target_shape: tuple[int, int, int], *, pad_value: float | int):
    import numpy as np

    out = array
    slices = []
    for dim, target in zip(out.shape[-3:], target_shape):
        if dim > target:
            start = (dim - target) // 2
            slices.append(slice(start, start + target))
        else:
            slices.append(slice(0, dim))
    out = out[(..., *slices)]
    pads = []
    for dim, target in zip(out.shape[-3:], target_shape):
        before = max((target - dim) // 2, 0)
        after = max(target - dim - before, 0)
        pads.append((before, after))
    return np.pad(out, [(0, 0), *pads], mode="constant", constant_values=pad_value)


def _load_b2nd_case(case_id: str):
    import blosc2

    data_path = PREPROC_FULLRES / f"{case_id}.b2nd"
    seg_path = PREPROC_FULLRES / f"{case_id}_seg.b2nd"
    if not data_path.is_file() or not seg_path.is_file():
        raise FileNotFoundError(f"missing preprocessed b2nd for {case_id}: {data_path}, {seg_path}")
    data = blosc2.open(urlpath=str(data_path), mode="r")[...]
    seg = blosc2.open(urlpath=str(seg_path), mode="r")[...]
    return data, seg


def dataset_adapter_smoke() -> None:
    rows: list[dict[str, object]] = []
    audit_rows: list[dict[str, object]] = []
    config_root = OUT_ROOT / "round17_train_config_templates"
    config_root.mkdir(parents=True, exist_ok=True)
    train_cases, val_cases = fold0_split()
    train_case = train_cases[0] if train_cases else ""
    val_case = "Case3011" if "Case3011" in val_cases else (val_cases[0] if val_cases else "")
    # Keep Stage4 CPU-only smoke intentionally small. This validates channel,
    # label, padding, and MedNeXt forward/backward wiring without approximating
    # a real training patch or exhausting login-node memory.
    patch_shape = (32, 64, 64)

    labels = dataset_labels()
    channels = channel_names()
    audit_rows.append(
        {
            "item": "dataset_channel_names",
            "status": "pass" if channels == {"0": "LGE", "1": "T2", "2": "C0"} else "warn",
            "value": json.dumps(channels, ensure_ascii=False, sort_keys=True),
        }
    )
    audit_rows.append(
        {
            "item": "dataset_label_semantics",
            "status": "pass" if labels.get("edema") == 4 and labels.get("scar") == 5 else "fail",
            "value": json.dumps(labels, ensure_ascii=False, sort_keys=True),
        }
    )

    def smoke_case(case_id: str, split_name: str, run_backward: bool) -> None:
        started = time.time()
        status = "pass"
        detail = ""
        data_shape = ""
        seg_shape = ""
        patch_data_shape = ""
        patch_seg_shape = ""
        label_unique = ""
        output_shape = ""
        loss_value = ""
        try:
            import numpy as np
            import torch

            from src.care_myocardium.mednext import MedNeXtConfig, create_care_mednext

            data, seg = _load_b2nd_case(case_id)
            data_shape = "x".join(str(v) for v in data.shape)
            seg_shape = "x".join(str(v) for v in seg.shape)
            label_vals = np.unique(seg)
            label_unique = " ".join(str(int(v)) for v in label_vals.tolist())
            # nnU-Net preprocessed segmentations may include -1 ignore labels
            # outside the valid cropped/resampled support. Compact CARE labels
            # themselves must remain 0..5.
            if any(int(v) < -1 or int(v) > 5 for v in label_vals.tolist()):
                status = "fail"
                detail = f"unexpected labels {label_unique}"
            data_patch = _pad_or_crop_spatial(data.astype("float32", copy=False), patch_shape, pad_value=0.0)
            seg_patch = _pad_or_crop_spatial(seg.astype("int64", copy=False), patch_shape, pad_value=0)
            patch_data_shape = "x".join(str(v) for v in data_patch.shape)
            patch_seg_shape = "x".join(str(v) for v in seg_patch.shape)
            x = torch.from_numpy(data_patch[None])
            y = torch.from_numpy(np.where(seg_patch[0][None] < 0, 0, seg_patch[0][None]))
            model = create_care_mednext(
                MedNeXtConfig(
                    model_id="S",
                    num_input_channels=3,
                    num_classes=6,
                    kernel_size=3,
                    deep_supervision=False,
                )
            )
            model.train(run_backward)
            out = model(x)
            logits = out[0] if isinstance(out, (tuple, list)) else out
            output_shape = "x".join(str(v) for v in logits.shape)
            if tuple(logits.shape) != (1, 6, *patch_shape):
                status = "fail"
                detail = f"unexpected output shape {tuple(logits.shape)}"
            if run_backward and status == "pass":
                loss = torch.nn.functional.cross_entropy(logits, y)
                if not torch.isfinite(loss):
                    status = "fail"
                    detail = "non_finite_loss"
                else:
                    loss.backward()
                    loss_value = f"{float(loss.detach().item()):.6g}"
        except Exception as exc:  # noqa: BLE001
            status = "fail"
            detail = f"{type(exc).__name__}:{exc}"[:500]
        rows.append(
            {
                "split": split_name,
                "case": case_id,
                "data_path": str((PREPROC_FULLRES / f"{case_id}.b2nd").relative_to(REPO_ROOT)) if case_id else "",
                "seg_path": str((PREPROC_FULLRES / f"{case_id}_seg.b2nd").relative_to(REPO_ROOT)) if case_id else "",
                "raw_data_shape": data_shape,
                "raw_seg_shape": seg_shape,
                "patch_data_shape": patch_data_shape,
                "patch_seg_shape": patch_seg_shape,
                "label_unique": label_unique,
                "output_shape": output_shape,
                "backward": run_backward,
                "loss_value": loss_value,
                "status": status,
                "detail": detail,
                "elapsed_sec": f"{time.time() - started:.3f}",
            }
        )

    if train_case:
        smoke_case(train_case, "fold0_train", True)
    else:
        rows.append({"split": "fold0_train", "case": "", "status": "fail", "detail": "missing_train_cases"})
    if val_case:
        smoke_case(val_case, "fold0_val", False)
    else:
        rows.append({"split": "fold0_val", "case": "", "status": "fail", "detail": "missing_val_cases"})

    audit_rows.append(
        {
            "item": "preprocessed_patch_semantics",
            "status": "pass" if all(row.get("status") == "pass" for row in rows) else "fail",
            "value": f"patch_shape={patch_shape}; source={PREPROC_FULLRES.relative_to(REPO_ROOT)}",
        }
    )
    write_csv(OUT_ROOT / "round17_dataset_adapter_smoke_summary.csv", rows)
    write_csv(OUT_ROOT / "round17_channel_label_semantics_audit.csv", audit_rows)
    for candidate, model_size, kernel_size, channels in [
        ("R17_A_mednext_s_kernel3_standard_dicece_fold0_vs", "S", 3, 3),
        ("R17_B_mednext_b_kernel3_standard_dicece_fold0_vs", "B", 3, 3),
    ]:
        write_text(
            config_root / f"{candidate}.yaml",
            "\n".join(
                [
                    f"candidate_id: {candidate}",
                    "round: 17",
                    "lane: laneA_myops",
                    "output_root: results/diagnostics/care_myocardium/laneA_myops/round17_mednext_backbone",
                    "dataset: Dataset501_CAREMyoPS",
                    "fold: 0",
                    "trainer_scope: future_round17_mednext_first_party",
                    "model:",
                    "  architecture: MedNeXtV1",
                    f"  model_size: {model_size}",
                    f"  kernel_size: {kernel_size}",
                    f"  input_channels: {channels}",
                    "  output_classes: 6",
                    "  deep_supervision: false",
                    "labels:",
                    "  background: 0",
                    "  myocardium: 1",
                    "  LV_blood: 2",
                    "  RV_blood: 3",
                    "  edema: 4",
                    "  scar: 5",
                    "objective:",
                    "  primary_gate: myops_edema class_4 T2-present GT-positive / CenterC",
                    "  co_primary_metric: myops_scar class_5 non-regression/improvement",
                    "  loss: conservative_dice_ce_or_repo_equivalent",
                    "constraints:",
                    "  pretrained_weights: not_used",
                    "  external_training_data: forbidden",
                    "  validation_zip: forbidden",
                    "  fold1_4: forbidden_without_user_authorization",
                    "",
                ]
            ),
        )
    decision = "pass" if all(row.get("status") == "pass" for row in rows) else "fail"
    write_text(
        OUT_ROOT / "round17_stage4_gate_decision.md",
        "\n".join(
            [
                "# Round17 Stage4 Dataset Adapter Smoke Decision",
                "",
                f"- Decision: `{decision}`",
                f"- Train smoke case: `{train_case}`",
                f"- Validation smoke case: `{val_case}`",
                f"- Patch shape: `{patch_shape}`",
                "- Baseline cache was not modified.",
                "- No training or Slurm submission was run.",
                "",
                "Next if pass: prepare isolated first-party MedNeXt runner/job templates for fold0 very-short candidates. Do not submit without explicit Stage5 approval.",
            ]
        )
        + "\n",
    )


def stage5_submission_plan() -> None:
    rows = [
        {
            "candidate_id": "R17_A_mednext_s_kernel3_standard_dicece_fold0_vs",
            "priority": "high",
            "job_type": "fold0_very_short",
            "partition": "htzhulab",
            "status": "ready_not_submitted",
            "requires": "Stage1-4 pass; runner/job py_compile and bash -n pass",
            "output_dir": str((OUT_ROOT / "R17_A_mednext_s_kernel3_standard_dicece_fold0_vs").relative_to(REPO_ROOT)),
            "notes": "first CARE-only MedNeXt-S kernel3 standard Dice/CE candidate",
        },
        {
            "candidate_id": "R17_B_mednext_b_kernel3_standard_dicece_fold0_vs",
            "priority": "high_if_memory_permits",
            "job_type": "fold0_very_short",
            "partition": "htzhulab",
            "status": "planned_not_submitted",
            "requires": "A runner stable; model_id=B memory estimate accepted",
            "output_dir": str((OUT_ROOT / "R17_B_mednext_b_kernel3_standard_dicece_fold0_vs").relative_to(REPO_ROOT)),
            "notes": "base capacity check; do not run if S already unstable",
        },
        {
            "candidate_id": "R17_D_mednext_s_modality_channels_fold0_vs",
            "priority": "watch",
            "job_type": "fold0_very_short",
            "partition": "htzhulab",
            "status": "planned_not_submitted",
            "requires": "6-channel handling implemented explicitly in trainer/job env",
            "output_dir": str((OUT_ROOT / "R17_D_mednext_s_modality_channels_fold0_vs").relative_to(REPO_ROOT)),
            "notes": "modality presence route only after 3-channel baseline is viable",
        },
    ]
    write_csv(OUT_ROOT / "round17_batch_job_status.csv", rows)
    write_text(
        OUT_ROOT / "round17_batch_job_submission_plan.md",
        "\n".join(
            [
                "# Round17 Batch Job Submission Plan",
                "",
                "Stage1-4 gates are designed to run without training. Stage5 is the first point where bounded Slurm jobs may be submitted.",
                "",
                "Current status: `not_submitted`. Isolated runner/job support exists for the first MedNeXt-S candidate and passed py_compile / bash -n / initialize-only smoke. Do not submit unless the user authorizes Stage5 Slurm execution.",
                "",
                "Prepared entrypoints:",
                "",
                "- `scripts/training/run_laneA_round17_mednext_train.py`",
                "- `jobs/nnUNet/laneA_round17_mednext_fold0_very_short.sh`",
                "",
                "Default partition: `htzhulab` with `--qos=gpu_access`. Do not switch partition unless queue state makes the expected wait materially long relative to the very-short budget.",
                "",
                "| candidate | priority | initial status |",
                "| --- | --- | --- |",
                *[f"| {row['candidate_id']} | {row['priority']} | {row['status']} |" for row in rows],
                "",
                "Submission guardrails:",
                "",
                "- No fold1-4 or 5-fold.",
                "- No validation zip or upload.",
                "- No pretrained weights.",
                "- No external image/label data.",
                "- Each candidate must write to an isolated output directory under the Round17 root.",
                "- Compare edema class_4 and scar class_5 separately; edema is the hardest primary gate and scar is co-primary non-regression/improvement.",
            ]
        )
        + "\n",
    )


def execution_readme() -> None:
    write_text(
        OUT_ROOT / "round17_goal_execution_readme.md",
        "\n".join(
            [
                "# Round17 MedNeXt / Stronger Backbone Execution Readme",
                "",
                "This directory contains the low-risk Stage1-4 execution artifacts and Stage5 submission-prep artifacts for Lane A Round17.",
                "",
                "Executed stages:",
                "",
                "- Stage1 reproducibility/path/label/fold0 baseline gate.",
                "- Stage2 MedNeXt metadata/compliance audit from the existing Round16 clone.",
                "- Stage3 MedNeXt import/instantiate/forward/backward synthetic shape smoke.",
                "- Bounded Stage4 CARE one-batch adapter smoke with no optimizer step and no cache writes.",
                "- Stage5 batch job planning/status; no Slurm job submitted.",
                "",
                "Not executed:",
                "",
                "- No training.",
                "- No Slurm submission.",
                "- No pretrained weight download.",
                "- No external data usage.",
                "- No validation zip/upload.",
                "- No fold1-4/5-fold expansion.",
                "",
                "Round17 target interpretation: MedNeXt / stronger backbone aims to improve MyoPS scar and edema jointly. Edema remains the hardest primary gate; scar is a co-primary non-regression/improvement metric.",
            ]
        )
        + "\n",
    )


def main() -> int:
    OUT_ROOT.mkdir(parents=True, exist_ok=True)
    execution_readme()
    stage1_reproducibility()
    candidate_matrix()
    mednext_metadata()
    mednext_smoke()
    dataset_adapter_smoke()
    stage5_submission_plan()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
