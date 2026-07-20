#!/usr/bin/env python3
"""Build Route B Round03 source, manifest, sampler, and fixture receipts."""

from __future__ import annotations

import argparse
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
import subprocess
from typing import Any

import nibabel as nib
import numpy as np


REPO_ROOT = Path(__file__).resolve().parents[2]
MAIN_USERS_ROOT = Path("/users/a/e/aereinh/CARE")
DATA_ROOT = MAIN_USERS_ROOT / "data" / "CARE_Challenge"
PRIMARY_MANIFEST = REPO_ROOT / "results" / "20260704_srr_v25_training_ablation_matrix" / "full_fold0_eval" / "manifest.json"
MODALITY_ORDER = ("LGE", "T2", "C0")
SCAR_RAW = 2221
EDEMA_RAW = 1220


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def sha256_file(path: Path) -> str:
    return sha256_bytes(path.read_bytes())


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    encoded = json.dumps(payload, indent=2, sort_keys=True) + "\n"
    path.write_text(encoded, encoding="utf-8")


def git_blob(path: str) -> str:
    cp = subprocess.run(
        ["git", "rev-parse", f"HEAD:{path}"],
        cwd=REPO_ROOT,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )
    return cp.stdout.strip() if cp.returncode == 0 else ""


def load_primary_ids() -> list[str]:
    payload = json.loads(PRIMARY_MANIFEST.read_text(encoding="utf-8"))
    ids = payload.get("eval_case_ids", [])
    if not isinstance(ids, list) or len(ids) != 44:
        raise RuntimeError(f"expected 44 eval_case_ids in {PRIMARY_MANIFEST}")
    return [str(item) for item in ids]


def find_case(root: Path, case_id: str) -> Path:
    matches = sorted(root.glob(f"*/{case_id}"))
    if len(matches) != 1:
        raise RuntimeError(f"expected one case directory for {case_id}, found {len(matches)}")
    return matches[0]


def label_values(path: Path) -> list[int]:
    data = np.asarray(nib.load(str(path)).dataobj)
    return [int(v) for v in np.unique(data) if int(v) != 0]


def myops_row(case_id: str) -> dict[str, Any]:
    case_dir = find_case(DATA_ROOT / "MyoPS_train", case_id)
    files = {mod: case_dir / f"{case_id}_{mod}.nii.gz" for mod in MODALITY_ORDER}
    label = case_dir / f"{case_id}_gd.nii.gz"
    values = label_values(label)
    return {
        "case_id": case_id,
        "center": case_dir.parent.name,
        "case_dir": str(case_dir),
        "image_paths": {mod: str(path) if path.exists() else None for mod, path in files.items()},
        "label_path": str(label),
        "availability_order": list(MODALITY_ORDER),
        "availability": [bool(files[mod].exists()) for mod in MODALITY_ORDER],
        "scar_positive": SCAR_RAW in values,
        "t2_present": files["T2"].exists(),
        "edema_positive": EDEMA_RAW in values,
        "t2_edema_positive": bool(files["T2"].exists() and EDEMA_RAW in values),
        "raw_label_values": values,
        "label_sha256": sha256_file(label),
    }


def build_myops_manifests(config_dir: Path) -> dict[str, Any]:
    rows = [myops_row(cid) for cid in load_primary_ids()]
    edema_rows = [row for row in rows if row["t2_edema_positive"]]
    scar_rows = [row for row in rows if row["scar_positive"]]
    remaining = [row for row in rows if not row["t2_edema_positive"] and not row["scar_positive"]]
    sampler = {
        "precedence": ["E", "S", "R"],
        "draw_cycle": ["E", "E", "S", "R"],
        "philox_seed": 26071821,
        "strata": {
            "E": [row["case_id"] for row in edema_rows],
            "S": [row["case_id"] for row in scar_rows if not row["t2_edema_positive"]],
            "R": [row["case_id"] for row in remaining],
        },
    }
    primary_path = config_dir / "manifests" / "myops_fold0_primary_44.json"
    edema_path = config_dir / "manifests" / "myops_t2_edema_positive.json"
    strata_path = config_dir / "manifests" / "myops_sampler_strata.json"
    write_json(primary_path, {"case_count": len(rows), "cases": rows})
    write_json(edema_path, {"case_count": len(edema_rows), "cases": edema_rows})
    write_json(strata_path, sampler)
    return {
        "primary_path": str(primary_path),
        "edema_path": str(edema_path),
        "sampler_path": str(strata_path),
        "primary_sha256": sha256_file(primary_path),
        "edema_sha256": sha256_file(edema_path),
        "sampler_sha256": sha256_file(strata_path),
        "primary_case_count": len(rows),
        "t2_edema_positive_count": len(edema_rows),
        "scar_positive_count": len(scar_rows),
        "center_counts": {center: sum(1 for row in rows if row["center"] == center) for center in sorted({row["center"] for row in rows})},
    }


def build_cine_manifest(config_dir: Path) -> dict[str, Any]:
    root = DATA_ROOT / "CineMyoPS_train"
    rows: list[dict[str, Any]] = []
    for center in ("center_alpha", "center_beta"):
        cases = sorted((root / center).glob("Case*_Cine.nii.gz"))[:6]
        for image in cases:
            case_id = image.name.removesuffix("_Cine.nii.gz")
            label = image.with_name(f"{case_id}_gd.nii.gz")
            img = nib.load(str(image))
            shape = tuple(int(v) for v in img.shape)
            frame_count = shape[-1] if len(shape) == 4 else 1
            rows.append(
                {
                    "case_id": case_id,
                    "center": center,
                    "image_path": str(image),
                    "label_path": str(label),
                    "image_shape": list(shape),
                    "frame_count": int(frame_count),
                    "affine_header_sha256": sha256_bytes(img.affine.tobytes() + str(img.header).encode("utf-8")),
                    "image_sha256": sha256_file(image),
                    "label_sha256": sha256_file(label),
                }
            )
    cine_path = config_dir / "manifests" / "cine_train12.json"
    write_json(cine_path, {"case_count": len(rows), "cases": rows})
    return {
        "cine_path": str(cine_path),
        "cine_sha256": sha256_file(cine_path),
        "cine_case_count": len(rows),
        "cine_center_counts": {center: sum(1 for row in rows if row["center"] == center) for center in sorted({row["center"] for row in rows})},
        "min_frame_count": min((row["frame_count"] for row in rows), default=0),
    }


def build_source_probe(contract: Path) -> dict[str, Any]:
    source_paths = [
        "src/care_myocardium/anchors/myops_decode.py",
        "src/care_myocardium/models/srr_propref.py",
        "src/care_myocardium/models/pathology_heads.py",
        "src/care_myocardium/models/proposal_prototypes.py",
        "src/care_myocardium/models/srr_dictionary_memory.py",
        "src/care_myocardium/losses/srr_losses.py",
        "src/care_myocardium/refiner/soft_roi.py",
        "src/care_myocardium/cine/cinema_adapter.py",
        "src/care_myocardium/cine/registration_model.py",
        "src/care_myocardium/cine/temporal_model.py",
        "src/care_myocardium/cine/temporal_dictionary.py",
    ]
    return {
        "created_at_utc": utc_now(),
        "contract_path": str(contract),
        "contract_sha256": sha256_file(contract),
        "git_head": subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=REPO_ROOT, text=True).strip(),
        "canonical_modality_order": list(MODALITY_ORDER),
        "legacy_order_rejected": ["LGE", "C0", "T2"],
        "source_blobs": {path: git_blob(path) for path in source_paths},
        "known_bad_historical_paths": [
            "src/care_myocardium/route_B/**",
            "deterministic_axis_bootstrap_pending_train_or_oof_fit",
            "online_ema_formal_memory",
            "small_internal_CineMAAdapter",
            "direct_velocity_displacement",
            "abstract_temporal_z",
        ],
    }


def build_fixture_index(result_dir: Path) -> dict[str, Any]:
    fixtures = [
        ("wrong_modality_order", "ROUTE_B_ROUND03_WRONG_MODALITY_ORDER"),
        ("bootstrap_formal_memory", "ROUTE_B_ROUND03_BOOTSTRAP_FORMAL_MEMORY"),
        ("ema_formal_memory", "ROUTE_B_ROUND03_EMA_FORMAL_MEMORY"),
        ("fake_cinema", "ROUTE_B_ROUND03_FAKE_CINEMA"),
        ("direct_velocity_displacement", "ROUTE_B_ROUND03_DIRECT_VELOCITY_DISPLACEMENT"),
        ("proxy_jacobian", "ROUTE_B_ROUND03_PROXY_JACOBIAN"),
        ("abstract_temporal_z", "ROUTE_B_ROUND03_TEMPORAL_Z_ONLY"),
        ("monitor_packet_completion", "ROUTE_B_ROUND03_MONITOR_PACKET_IS_NOT_COMPLETION"),
        ("bare_python_wrapper", "ROUTE_B_ROUND03_BARE_PYTHON_WRAPPER"),
        ("zero_myops_effect_plus_cine_gain", "ROUTE_B_ROUND03_ZERO_MYOPS_EFFECT_PLUS_CINE_GAIN"),
    ]
    return {
        "fixture_count": len(fixtures),
        "fixtures": [
            {
                "name": name,
                "mutation": name,
                "expected_exit": 1,
                "expected_failure_key": key,
                "command": f"/users/a/e/aereinh/CARE/envs/env_CARE/bin/python scripts/validation/route_B_round03/known_bad_fixture.py --fixture {name}",
            }
            for name, key in fixtures
        ],
        "index_path": str(result_dir / "validator_fixture_index.json"),
    }


def build_partition_matrix() -> dict[str, Any]:
    return {
        "partitions": {
            "htzhulab": {"default": True, "qos": "gpu_access", "gres": "gpu:1"},
            "a100-gpu": {"fallback_or_race": True, "qos": "gpu_access", "gres": "gpu:nvidia_a100-pcie-40gb:1"},
            "volta-gpu": {"v100_user_approved": True, "qos": "gpu_access", "gres": "gpu:tesla_v100-sxm2-16gb:1"},
        },
        "race_rules": {
            "scientific_hashes_identical": True,
            "isolated_output_log_checkpoint_cache_roots": True,
            "atomic_winner_lock_required": True,
            "pending_loser_cancellation_required": True,
            "loser_training_credit": "zero",
            "retry_lineage_required": True,
            "all_attempt_finalizer_coverage_required": True,
            "v100_semantic_downscaling_forbidden": True,
        },
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--contract", required=True, type=Path)
    parser.add_argument("--out", required=True, type=Path)
    args = parser.parse_args()

    result_dir = args.out
    config_dir = REPO_ROOT / "configs" / "route_B_round03"
    result_dir.mkdir(parents=True, exist_ok=True)
    source_probe = build_source_probe(args.contract)
    myops = build_myops_manifests(config_dir)
    cine = build_cine_manifest(config_dir)
    fixture_index = build_fixture_index(result_dir)
    partition_matrix = build_partition_matrix()

    write_json(result_dir / "source_probe.json", source_probe)
    write_json(result_dir / "sampler_contract.json", json.loads((config_dir / "manifests" / "myops_sampler_strata.json").read_text(encoding="utf-8")))
    write_json(result_dir / "validator_fixture_index.json", fixture_index)
    write_json(result_dir / "partition_static_matrix.json", partition_matrix)

    freeze = {
        "created_at_utc": utc_now(),
        "data_root": str(DATA_ROOT),
        "route_worktree_data_dir_present": (REPO_ROOT / "data").exists(),
        **myops,
        **cine,
    }
    write_json(result_dir / "manifest_freeze_receipt.json", freeze)
    write_json(REPO_ROOT / "results" / "route_B" / "round03" / "manifest_freeze_receipt.json", freeze)

    passed = (
        myops["primary_case_count"] == 44
        and myops["t2_edema_positive_count"] >= 8
        and myops["center_counts"].get("CenterB", 0) > 0
        and myops["center_counts"].get("CenterC", 0) > 0
        and cine["cine_case_count"] == 12
        and set(cine["cine_center_counts"].values()) == {6}
    )
    token = "ROUTE_B_ROUND03_B0_READY_FOR_CONTROLLER_MERGE" if passed else "ROUTE_B_ROUND03_B0_MANIFEST_INADEQUATE"
    write_json(
        result_dir / "completion.json",
        {
            "completion_token": token,
            "status": "PASS" if passed else "FAIL",
            "required_completion_token": "ROUTE_B_ROUND03_B0_READY_FOR_CONTROLLER_MERGE",
            "manifest_freeze_receipt": str(result_dir / "manifest_freeze_receipt.json"),
            "sha256_values": {
                "myops_fold0_primary_44": myops["primary_sha256"],
                "myops_t2_edema_positive": myops["edema_sha256"],
                "myops_sampler_strata": myops["sampler_sha256"],
                "cine_train12": cine["cine_sha256"],
            },
        },
    )
    print(token)
    return 0 if passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
