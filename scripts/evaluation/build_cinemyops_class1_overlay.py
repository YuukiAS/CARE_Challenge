#!/usr/bin/env python3
"""Build a CineMyoPS class_1-primary overlay prediction set.

The output keeps anatomy labels from an anatomy-prior prediction directory
and overlays scar label 3 from a pathology prediction directory where the
anatomy prediction marks myocardium. This is an export-only diagnostic
candidate, not a training step.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np
import SimpleITK as sitk


def read_label(path: Path) -> tuple[sitk.Image, np.ndarray]:
    image = sitk.ReadImage(str(path))
    return image, sitk.GetArrayFromImage(image).astype(np.uint8, copy=False)


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--anatomy-dir", type=Path, required=True)
    ap.add_argument("--pathology-dir", type=Path, required=True)
    ap.add_argument("--output-dir", type=Path, required=True)
    ap.add_argument(
        "--scar-source-label",
        type=int,
        default=3,
        help="Label id to take from pathology-dir as scar.",
    )
    ap.add_argument(
        "--scar-target-label",
        type=int,
        default=3,
        help="Label id to write in the overlay output.",
    )
    ap.add_argument(
        "--gate-label",
        type=int,
        default=1,
        help="Only overlay scar where the anatomy prediction has this label.",
    )
    args = ap.parse_args()

    args.output_dir.mkdir(parents=True, exist_ok=True)
    manifest: dict[str, object] = {
        "anatomy_dir": str(args.anatomy_dir),
        "pathology_dir": str(args.pathology_dir),
        "output_dir": str(args.output_dir),
        "scar_source_label": args.scar_source_label,
        "scar_target_label": args.scar_target_label,
        "gate_label": args.gate_label,
        "cases": {},
    }

    anatomy_paths = sorted(args.anatomy_dir.glob("*.nii.gz"))
    if not anatomy_paths:
        raise FileNotFoundError(f"No .nii.gz predictions found in {args.anatomy_dir}")

    for anatomy_path in anatomy_paths:
        pathology_path = args.pathology_dir / anatomy_path.name
        if not pathology_path.is_file():
            raise FileNotFoundError(f"Missing pathology prediction for {anatomy_path.name}: {pathology_path}")

        anatomy_img, anatomy_arr = read_label(anatomy_path)
        pathology_img, pathology_arr = read_label(pathology_path)
        if anatomy_arr.shape != pathology_arr.shape:
            raise ValueError(
                f"Shape mismatch for {anatomy_path.name}: anatomy={anatomy_arr.shape} pathology={pathology_arr.shape}"
            )
        if anatomy_img.GetSize() != pathology_img.GetSize():
            raise ValueError(f"Geometry size mismatch for {anatomy_path.name}")

        overlay = anatomy_arr.copy()
        scar_mask = (pathology_arr == args.scar_source_label) & (anatomy_arr == args.gate_label)
        overlay[scar_mask] = args.scar_target_label

        output_img = sitk.GetImageFromArray(overlay)
        output_img.CopyInformation(anatomy_img)
        output_path = args.output_dir / anatomy_path.name
        sitk.WriteImage(output_img, str(output_path))

        unique, counts = np.unique(overlay, return_counts=True)
        manifest["cases"][anatomy_path.name.replace(".nii.gz", "")] = {
            "overlay_scar_voxels": int(scar_mask.sum()),
            "labels": {str(int(k)): int(v) for k, v in zip(unique, counts)},
        }

    manifest_path = args.output_dir / "manifest.json"
    manifest_path.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(f"Wrote overlay predictions: {args.output_dir}")
    print(f"Wrote manifest: {manifest_path}")


if __name__ == "__main__":
    main()
