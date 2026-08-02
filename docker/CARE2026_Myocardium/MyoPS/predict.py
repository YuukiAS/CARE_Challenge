#!/usr/bin/env python3
from __future__ import annotations

import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

import numpy as np
import SimpleITK as sitk

APP = Path(__file__).resolve().parent
INPUT_DIR = Path(os.environ.get("CARE_INPUT_DIR", "/input"))
OUTPUT_DIR = Path(os.environ.get("CARE_OUTPUT_DIR", "/output/myops"))
NNUNET_RESULTS = Path(os.environ.get("nnUNet_results", APP / "models/nnunet/nnUNet_results"))
NNUNET_RAW = Path(os.environ.get("nnUNet_raw", APP / "models/nnunet/nnUNet_raw"))
NNUNET_PREPROCESSED = Path(os.environ.get("nnUNet_preprocessed", APP / "models/nnunet/nnUNet_preprocessed"))

CHANNELS = (("LGE", 0), ("T2", 1), ("C0", 2))
OFFICIAL_LABELS = {
    0: 0,
    1: 200,
    2: 500,
    3: 600,
    4: 1220,
    5: 2221,
}


def discover_cases(input_dir: Path) -> list[tuple[str, dict[str, Path]]]:
    search_root = input_dir if input_dir.exists() else Path("/input")
    lge_files = sorted(search_root.glob("**/*_LGE.nii.gz"))
    cases: list[tuple[str, dict[str, Path]]] = []
    errors: list[str] = []

    for lge_path in lge_files:
        case_id = lge_path.name.removesuffix("_LGE.nii.gz")
        case_dir = lge_path.parent
        modalities = {"LGE": lge_path}
        missing = []
        for modality, _ in CHANNELS:
            candidate = case_dir / f"{case_id}_{modality}.nii.gz"
            if candidate.exists():
                modalities[modality] = candidate
            else:
                missing.append(modality)
        if missing:
            errors.append(f"{case_id}: missing modalities {','.join(missing)} in {case_dir}")
        else:
            cases.append((case_id, modalities))

    if not lge_files:
        raise RuntimeError(f"No MyoPS LGE inputs found under {search_root}")
    if errors:
        raise RuntimeError("Incomplete MyoPS input cases:\n" + "\n".join(errors))
    return sorted(cases, key=lambda item: item[0])


def prepare_nnunet_input(cases: list[tuple[str, dict[str, Path]]], out_dir: Path) -> None:
    out_dir.mkdir(parents=True, exist_ok=True)
    for case_id, modalities in cases:
        for modality, channel in CHANNELS:
            shutil.copy2(modalities[modality], out_dir / f"{case_id}_{channel:04d}.nii.gz")


def run_nnunet(in_dir: Path, out_dir: Path) -> None:
    device = os.environ.get("CARE_DEVICE", "cpu")
    cmd = [
        "nnUNetv2_predict",
        "-d",
        "501",
        "-tr",
        "nnUNetTrainer_500epochs",
        "-c",
        "3d_fullres",
        "-f",
        "0",
        "1",
        "2",
        "3",
        "4",
        "-chk",
        "checkpoint_best.pth",
        "-i",
        str(in_dir),
        "-o",
        str(out_dir),
        "-npp",
        "1",
        "-nps",
        "1",
        "-device",
        device,
        "--disable_progress_bar",
    ]
    env = os.environ.copy()
    env["nnUNet_results"] = str(NNUNET_RESULTS)
    env["nnUNet_raw"] = str(NNUNET_RAW)
    env["nnUNet_preprocessed"] = str(NNUNET_PREPROCESSED)
    subprocess.run(cmd, check=True, env=env)


def map_to_official_labels(raw_path: Path, final_path: Path) -> None:
    image = sitk.ReadImage(str(raw_path))
    raw = sitk.GetArrayFromImage(image)
    raw_values = set(np.unique(raw).astype(int).tolist())
    unexpected = sorted(raw_values.difference(OFFICIAL_LABELS))
    if unexpected:
        raise RuntimeError(f"{raw_path.name}: unexpected nnU-Net labels {unexpected}")

    final = np.zeros(raw.shape, dtype=np.int16)
    for raw_label, official_label in OFFICIAL_LABELS.items():
        if official_label:
            final[raw == raw_label] = official_label

    out_image = sitk.GetImageFromArray(final)
    out_image.CopyInformation(image)
    final_path.parent.mkdir(parents=True, exist_ok=True)
    tmp_path = final_path.with_name(f".{final_path.name.removesuffix('.nii.gz')}.tmp.nii.gz")
    sitk.WriteImage(out_image, str(tmp_path))
    os.replace(tmp_path, final_path)


def main() -> int:
    try:
        cases = discover_cases(INPUT_DIR)
        print(f"Found {len(cases)} complete MyoPS cases under {INPUT_DIR}")
        OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
        with tempfile.TemporaryDirectory(prefix="care_myops_nnunet_") as tmpdir:
            tmp = Path(tmpdir)
            nnunet_in = tmp / "input"
            nnunet_out = tmp / "output"
            prepare_nnunet_input(cases, nnunet_in)
            run_nnunet(nnunet_in, nnunet_out)
            for case_id, _ in cases:
                raw_path = nnunet_out / f"{case_id}.nii.gz"
                if not raw_path.exists():
                    raise RuntimeError(f"{case_id}: nnU-Net did not produce {raw_path}")
                map_to_official_labels(raw_path, OUTPUT_DIR / f"{case_id}_pred.nii.gz")
                print(f"{case_id}: wrote {OUTPUT_DIR / f'{case_id}_pred.nii.gz'}")
    except Exception as exc:
        print(f"CARE MyoPS inference failed: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
