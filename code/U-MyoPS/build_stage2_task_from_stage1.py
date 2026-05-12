#!/usr/bin/env python3
"""Build a fold-specific U-MyoPS Stage2 nnU-Net v1 raw task from CARE data and Stage1 outputs."""
from __future__ import annotations

import argparse
import json
import os
import shutil
import sys
from dataclasses import dataclass
from pathlib import Path

import numpy as np
import SimpleITK as sitk


def repo_root() -> Path:
    return Path(__file__).resolve().parents[2]


def resolve_stage2_task_name(base_task: str, fold: int, per_fold: bool) -> str:
    return f"{base_task}_fold{fold}" if per_fold else base_task


def find_subject_dir(staged_root: Path, case_id: str) -> Path:
    matches = sorted(p for p in staged_root.glob(f"*_{case_id}") if p.is_dir())
    if len(matches) != 1:
        raise FileNotFoundError(f"Expected exactly one staged subject dir for {case_id}, found {matches}")
    return matches[0]


def candidate_stage1_run_dirs(outputs_root: Path, fold: int) -> list[Path]:
    return sorted(
        p
        for p in outputs_root.iterdir()
        if p.is_dir()
        and p.name != "nnunet"
        and p.name.endswith(f"_fold{fold}")
        and (p / "gen_res").is_dir()
    )


def score_stage1_run_dir(path: Path, net: str, data_source: str, weight: str) -> tuple[int, float]:
    exact = f"asn_myo_tps_{net}_{data_source}_{weight}"
    score = 0
    if path.name.startswith(exact):
        score += 100
    if net in path.name:
        score += 10
    if data_source in path.name:
        score += 10
    if weight in path.name:
        score += 10
    latest = path.stat().st_mtime
    return score, latest


def find_stage1_run_dir(
    outputs_root: Path,
    fold: int,
    net: str,
    data_source: str,
    weight: str,
    explicit: Path | None,
) -> Path:
    if explicit is not None:
        run_dir = explicit.resolve()
        if not (run_dir / "gen_res").is_dir():
            raise FileNotFoundError(f"Stage1 run dir missing gen_res/: {run_dir}")
        return run_dir

    candidates = candidate_stage1_run_dirs(outputs_root, fold)
    if not candidates:
        raise FileNotFoundError(f"No Stage1 output dirs found under {outputs_root} for fold {fold}")
    return max(candidates, key=lambda p: score_stage1_run_dir(p, net, data_source, weight))


def absolute_symlink(src: Path, dst: Path) -> None:
    dst.parent.mkdir(parents=True, exist_ok=True)
    if dst.exists() or dst.is_symlink():
        dst.unlink()
    os.symlink(src.resolve(), dst)


def compact_pathology_label(gt_img: sitk.Image) -> sitk.Image:
    """
    Map CARE MyoPS pathology labels into nnU-Net Task901 internal ids {0,1,2}.

    CARE unified eval / CARE2026 leaderboard (MyoPS pathology):
      - myops_edema  <-> CARE class 4  <-> nnU-Net foreground label 1 (named \"edema\" in dataset.json)
      - myops_scar   <-> CARE class 5  <-> nnU-Net foreground label 2 (named \"scar\" in dataset.json)

    Dataset501 labelsTr are usually already compact (4,5). Some exports may still use raw challenge ids
    1220 (edema) / 2221 (scar); map those as well so Stage2 training labels stay aligned with CARE.
    """
    gt = sitk.GetArrayFromImage(gt_img).astype(np.int32, copy=False)
    out = np.zeros(gt.shape, dtype=np.uint8)
    out[(gt == 4) | (gt == 1220)] = 1
    out[(gt == 5) | (gt == 2221)] = 2
    img = sitk.GetImageFromArray(out)
    img.CopyInformation(gt_img)
    return img


def unique_file(pattern: str, root: Path) -> Path | None:
    matches = sorted(root.glob(pattern))
    if len(matches) == 1:
        return matches[0]
    if not matches:
        return None
    raise RuntimeError(f"Ambiguous pattern {pattern} under {root}: {matches}")


@dataclass
class CaseAssets:
    case_id: str
    subject_dir: Path
    prior: Path
    c0: Path
    t2: Path
    lge: Path
    gt: Path


def discover_case_assets(
    case_id: str,
    staged_root: Path,
    stage1_gen_dir: Path,
    gt_root: Path,
    prior_tag: str,
) -> CaseAssets:
    subject_dir = find_subject_dir(staged_root, case_id)
    gt = gt_root / f"{case_id}.nii.gz"
    if not gt.is_file():
        raise FileNotFoundError(f"Missing CARE GT label for {case_id}: {gt}")

    prior = unique_file(f"*_{prior_tag}_{case_id}.nii.gz", stage1_gen_dir / subject_dir.name)
    if prior is None:
        raise FileNotFoundError(
            f"Missing Stage1 prior for {case_id} under {(stage1_gen_dir / subject_dir.name)} "
            f"(expected tag {prior_tag})"
        )

    c0 = unique_file(f"*img_c0_assn_img_{case_id}.nii.gz", stage1_gen_dir / subject_dir.name)
    t2 = unique_file(f"*img_t2_assn_img_{case_id}.nii.gz", stage1_gen_dir / subject_dir.name)
    lge = unique_file(f"*img_de_assn_img_{case_id}.nii.gz", stage1_gen_dir / subject_dir.name)

    if c0 is None:
        c0 = unique_file(f"*img_c0_{case_id}.nii.gz", subject_dir)
    if t2 is None:
        t2 = unique_file(f"*img_t2_{case_id}.nii.gz", subject_dir)
    if lge is None:
        lge = unique_file(f"*img_de_{case_id}.nii.gz", subject_dir)

    if c0 is None or t2 is None or lge is None:
        raise FileNotFoundError(
            f"Missing Stage1-aligned image(s) for {case_id}: c0={c0}, t2={t2}, lge={lge}"
        )

    return CaseAssets(case_id=case_id, subject_dir=subject_dir, prior=prior, c0=c0, t2=t2, lge=lge, gt=gt)


def write_dataset_json(task_dir: Path, task_name: str, cases: list[str]) -> None:
    dataset = {
        "name": task_name,
        "description": "CARE U-MyoPS Stage2 fold-specific task built from Stage1 priors and aligned images",
        "tensorImageSize": "4D",
        "reference": "CARE benchmark / U-MyoPS",
        "licence": "CARE internal benchmark dataset",
        "release": "1.0",
        "modality": {
            "0": "prior",
            "1": "C0_assn",
            "2": "T2_assn",
            "3": "LGE_assn",
        },
        "labels": {
            "0": "background",
            "1": "edema",
            "2": "scar",
        },
        "numTraining": len(cases),
        "numTest": 0,
        "training": [
            {"image": f"./imagesTr/{cid}.nii.gz", "label": f"./labelsTr/{cid}.nii.gz"}
            for cid in cases
        ],
        "test": [],
    }
    (task_dir / "dataset.json").write_text(json.dumps(dataset, indent=2), encoding="utf-8")


def main() -> None:
    ap = argparse.ArgumentParser(description="Build U-MyoPS Stage2 raw nnU-Net task from Stage1 outputs")
    ap.add_argument("--fold", type=int, required=True)
    ap.add_argument("--base-task-name", type=str, default="Task901_CARE_UmyopsPathology")
    ap.add_argument("--per-fold-task", action="store_true", default=False)
    ap.add_argument("--staged-root", type=Path, default=repo_root() / "data" / "benchmarks" / "U-MyoPS" / "gen_ZS_unaligned" / "data")
    ap.add_argument("--stage1-outputs-root", type=Path, default=repo_root() / "third_party" / "U-MyoPS_myops" / "outputs")
    ap.add_argument("--stage1-run-dir", type=Path, default=None)
    ap.add_argument("--task-root-base", type=Path, default=repo_root() / "third_party" / "U-MyoPS_myops" / "outputs" / "nnunet" / "raw" / "nnUNet_raw_data")
    ap.add_argument("--gt-root", type=Path, default=repo_root() / "data" / "nnUNet" / "nnUNet_raw" / "Dataset501_CAREMyoPS" / "labelsTr")
    ap.add_argument("--cases-root", type=Path, default=repo_root() / "data" / "nnUNet" / "nnUNet_raw" / "Dataset501_CAREMyoPS" / "labelsTr")
    ap.add_argument("--prior-tag", type=str, default="img_de_branch_lab")
    ap.add_argument("--stage1-net", type=str, default="tps")
    ap.add_argument("--stage1-data-source", type=str, default="ZS_unaligned")
    ap.add_argument("--stage1-weight", type=str, default="1.0")
    ap.add_argument("--max-cases", type=int, default=0)
    ap.add_argument("--force-clean", action="store_true")
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    task_name = resolve_stage2_task_name(args.base_task_name, args.fold, args.per_fold_task)
    task_dir = args.task_root_base / task_name
    stage1_run_dir = find_stage1_run_dir(
        args.stage1_outputs_root,
        args.fold,
        args.stage1_net,
        args.stage1_data_source,
        args.stage1_weight,
        args.stage1_run_dir,
    )
    stage1_gen_dir = stage1_run_dir / "gen_res"

    cases = sorted(p.name.replace(".nii.gz", "") for p in args.cases_root.glob("*.nii.gz"))
    if args.max_cases > 0:
        cases = cases[: args.max_cases]
    if not cases:
        raise FileNotFoundError(f"No cases found under {args.cases_root}")

    assets: list[CaseAssets] = []
    for case_id in cases:
        assets.append(
            discover_case_assets(
                case_id=case_id,
                staged_root=args.staged_root,
                stage1_gen_dir=stage1_gen_dir,
                gt_root=args.gt_root,
                prior_tag=args.prior_tag,
            )
        )

    print(f"Stage1 run dir: {stage1_run_dir}")
    print(f"Task dir: {task_dir}")
    print(f"Cases: {len(assets)}")
    if args.dry_run:
        for item in assets[: min(5, len(assets))]:
            print(
                f"[dry-run] {item.case_id}: prior={item.prior.name} c0={item.c0.name} "
                f"t2={item.t2.name} lge={item.lge.name}"
            )
        return

    if task_dir.exists() and args.force_clean:
        shutil.rmtree(task_dir)
    (task_dir / "imagesTr").mkdir(parents=True, exist_ok=True)
    (task_dir / "labelsTr").mkdir(parents=True, exist_ok=True)
    (task_dir / "imagesTs").mkdir(parents=True, exist_ok=True)

    for item in assets:
        absolute_symlink(item.prior, task_dir / "imagesTr" / f"{item.case_id}_0000.nii.gz")
        absolute_symlink(item.c0, task_dir / "imagesTr" / f"{item.case_id}_0001.nii.gz")
        absolute_symlink(item.t2, task_dir / "imagesTr" / f"{item.case_id}_0002.nii.gz")
        absolute_symlink(item.lge, task_dir / "imagesTr" / f"{item.case_id}_0003.nii.gz")

        gt_img = sitk.ReadImage(str(item.gt))
        sitk.WriteImage(compact_pathology_label(gt_img), str(task_dir / "labelsTr" / f"{item.case_id}.nii.gz"))

    write_dataset_json(task_dir, task_name, [item.case_id for item in assets])
    print(f"Wrote raw task {task_name} to {task_dir}")


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:  # pragma: no cover - CLI wrapper
        print(f"error: {exc}", file=sys.stderr)
        sys.exit(1)
