"""Deterministic CARE-ASE split authority helpers."""

from __future__ import annotations

import csv
import hashlib
import json
import math
import pickle
import random
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

import blosc2
import numpy as np

from src.care_myocardium.data.case_metadata import MyoPSCaseMetadata, load_myops_case_metadata


PREPROCESSED_REL = Path("data/nnUNet/nnUNet_preprocessed/Dataset501_CAREMyoPS/nnUNetPlans_3d_fullres")
SPLITS_REL = Path("data/nnUNet/nnUNet_preprocessed/Dataset501_CAREMyoPS/splits_final.json")
SENTINEL_CASES = (
    "Case3008",
    "Case3009",
    "Case3012",
    "Case3027",
    "Case2034",
    "Case2025",
    "Case2019",
    "Case2012",
    "Case1045",
    "Case1029",
    "Case8021",
    "Case2009",
)


@dataclass(frozen=True)
class CAREASECaseRole:
    fold: int
    case_id: str
    role: str
    center: str
    modality_group: str
    availability: str
    t2_present: bool
    scar_voxels: int
    scar_volume_mm3: float
    scar_volume_bin: str
    stratum: str
    sentinel: bool


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def _seg_and_spacing(repo_root: Path, case_id: str) -> tuple[np.ndarray, tuple[float, float, float]]:
    preprocessed = repo_root / PREPROCESSED_REL
    seg = np.asarray(blosc2.open(str(preprocessed / f"{case_id}_seg.b2nd"), mode="r")[:])[0]
    with (preprocessed / f"{case_id}.pkl").open("rb") as f:
        props = pickle.load(f)
    spacing = tuple(float(v) for v in props.get("spacing", (1.0, 1.0, 1.0)))
    return seg, spacing


def _scar_bin(volume_mm3: float) -> str:
    if volume_mm3 <= 0.0:
        return "scar_zero"
    if volume_mm3 < 1000.0:
        return "scar_small_lt1000mm3"
    if volume_mm3 < 5000.0:
        return "scar_medium_1000_5000mm3"
    return "scar_large_ge5000mm3"


def _case_features(repo_root: Path, case_id: str, metadata: MyoPSCaseMetadata) -> dict[str, Any]:
    seg, spacing = _seg_and_spacing(repo_root, case_id)
    scar_voxels = int((seg == 5).sum())
    scar_volume = float(scar_voxels * math.prod(spacing))
    availability = "".join(str(int(v)) for v in metadata.availability)
    scar_bin = _scar_bin(scar_volume)
    stratum = "|".join([metadata.center, availability, f"t2={int(metadata.t2_present)}", scar_bin])
    return {
        "availability": availability,
        "scar_voxels": scar_voxels,
        "scar_volume_mm3": scar_volume,
        "scar_volume_bin": scar_bin,
        "stratum": stratum,
    }


def _choose_inner_cases(case_ids: list[str], features: dict[str, dict[str, Any]], seed: int) -> set[str]:
    grouped: dict[str, list[str]] = {}
    for case_id in case_ids:
        grouped.setdefault(str(features[case_id]["stratum"]), []).append(case_id)
    target = int(round(0.20 * len(case_ids)))
    quotas: dict[str, int] = {}
    remainders: list[tuple[float, str]] = []
    for stratum, rows in grouped.items():
        raw = 0.20 * len(rows)
        base = int(math.floor(raw))
        quotas[stratum] = min(base, len(rows))
        remainders.append((raw - base, stratum))
    remaining = max(0, target - sum(quotas.values()))
    for _rem, stratum in sorted(remainders, key=lambda item: (-item[0], item[1]))[:remaining]:
        if quotas[stratum] < len(grouped[stratum]):
            quotas[stratum] += 1

    selected: set[str] = set()
    for stratum, rows in sorted(grouped.items()):
        rng = random.Random(f"{seed}|{stratum}")
        shuffled = sorted(rows)
        rng.shuffle(shuffled)
        selected.update(shuffled[: quotas[stratum]])
    return selected


def build_care_ase_case_roles(repo_root: Path, fold: int) -> list[CAREASECaseRole]:
    repo_root = repo_root.resolve()
    splits = json.loads((repo_root / SPLITS_REL).read_text(encoding="utf-8"))
    outer = {str(v) for v in splits[int(fold)]["val"]}
    development = [str(v) for v in splits[int(fold)]["train"]]
    metadata = load_myops_case_metadata(repo_root)
    features = {case_id: _case_features(repo_root, case_id, metadata[case_id]) for case_id in development + sorted(outer)}
    inner = _choose_inner_cases(development, features, seed=20260801 + int(fold))
    rows: list[CAREASECaseRole] = []
    for case_id in sorted(set(development) | outer):
        meta = metadata[case_id]
        role = "outer" if case_id in outer else "inner" if case_id in inner else "actual-train"
        feat = features[case_id]
        rows.append(
            CAREASECaseRole(
                fold=int(fold),
                case_id=case_id,
                role=role,
                center=meta.center,
                modality_group=meta.modality_group,
                availability=str(feat["availability"]),
                t2_present=bool(meta.t2_present),
                scar_voxels=int(feat["scar_voxels"]),
                scar_volume_mm3=float(feat["scar_volume_mm3"]),
                scar_volume_bin=str(feat["scar_volume_bin"]),
                stratum=str(feat["stratum"]),
                sentinel=case_id in SENTINEL_CASES,
            )
        )
    return rows


def actual_train_cases(repo_root: Path, fold: int, *, complete_only: bool = True) -> list[tuple[str, tuple[float, float, float]]]:
    metadata = load_myops_case_metadata(repo_root)
    rows = build_care_ase_case_roles(repo_root, fold)
    out: list[tuple[str, tuple[float, float, float]]] = []
    for row in rows:
        if row.role != "actual-train":
            continue
        meta = metadata[row.case_id]
        if complete_only and not (meta.lge_present and meta.t2_present and meta.c0_present):
            continue
        out.append((row.case_id, meta.availability))
    if not out:
        raise RuntimeError(f"no CARE-ASE actual-train cases for fold {fold} complete_only={complete_only}")
    return out


def write_case_roles_csv(path: Path, rows: list[CAREASECaseRole]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=list(asdict(rows[0])) if rows else ["fold", "case_id"])
        writer.writeheader()
        for row in rows:
            writer.writerow(asdict(row))
