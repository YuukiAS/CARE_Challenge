#!/usr/bin/env python3
"""Metadata-only screening for CineMyoPS pretrained/model candidates.

This script intentionally avoids network downloads and training. It records the
candidate role, compliance risk, local availability, and fail-fast smoke plan so
that a later run can decide which asset is safe to test.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]


CANDIDATES: dict[str, dict[str, object]] = {
    "CineMA": {
        "url": "https://huggingface.co/mathpluscode/CineMA",
        "role": "cine anatomy/foundation backbone",
        "pretrained_weights": "yes",
        "license": "MIT per local note; verify live before use",
        "pretrained_data": "UK Biobank cine; downstream cardiac segmentation data such as ACDC/M&Ms reported in local note",
        "compliance_risk": "low if public pretrained weights only; no external supervised training",
        "expected_care_benefit": "strong cine anatomy/ROI feature for CineMyoPS",
        "integration_difficulty": "low-medium",
        "minimal_smoke_test": "metadata check, then local-weight one-case ED frame inference if weights are already present or download is explicitly approved",
        "fail_fast": "license mismatch, no usable anatomy logits/ROI, or input shape cannot map to CARE cine frame",
        "local_paths": ["third_party/candidates/CineMA", "models/pretrained/CineMA"],
    },
    "CorSeg-CineSAX": {
        "url": "https://github.com/RunhaoXu2003/CorSeg",
        "role": "cine anatomy + topology postprocess",
        "pretrained_weights": "yes",
        "license": "paper CC BY 4.0 per local note; repo license must be verified",
        "pretrained_data": "1555 multi-center cine SAX cases per local note",
        "compliance_risk": "low-medium if public pretrained weights are allowed and license permits challenge use",
        "expected_care_benefit": "reduce anatomy/topology HD failures and supply ROI support",
        "integration_difficulty": "low-medium",
        "minimal_smoke_test": "frozen anatomy mask on one fold0 CARE cine case, no training",
        "fail_fast": "license missing, output cannot map to myocardium/LV ROI, or topology postprocess deletes scar support",
        "local_paths": ["third_party/candidates/CorSeg", "models/pretrained/CorSeg"],
    },
    "ViTa": {
        "url": "https://github.com/Yundi-Zhang/ViTa",
        "role": "3D+T cine pretrained backbone",
        "pretrained_weights": "yes/likely",
        "license": "MIT per local note; verify repo",
        "pretrained_data": "large UKBB cine/time-series CMR per local note",
        "compliance_risk": "low for frozen/init weights; medium if external labels or tabular targets are required",
        "expected_care_benefit": "temporal representation for motion-aware CineMyoPS route",
        "integration_difficulty": "medium",
        "minimal_smoke_test": "metadata/import-only smoke; inspect whether image-only forward path exists",
        "fail_fast": "requires tabular/external training path, unusable input geometry, or excessive runtime",
        "local_paths": ["third_party/candidates/ViTa", "models/pretrained/ViTa"],
    },
    "StrainNet": {
        "url": "https://github.com/EpsteinLabUVA/StrainNet",
        "role": "frozen strain feature side branch",
        "pretrained_weights": "yes/unclear",
        "license": "verify",
        "pretrained_data": "cine contours/strain data; verify",
        "compliance_risk": "medium until contours, weights, and license are clear",
        "expected_care_benefit": "motion abnormality cue for scar/pathology",
        "integration_difficulty": "medium",
        "minimal_smoke_test": "one-case strain-map generation from CARE cine; record geometry and runtime",
        "fail_fast": "requires unavailable contours, wrong geometry, slow runtime, or unreliable output",
        "local_paths": ["third_party/candidates/StrainNet", "models/pretrained/StrainNet"],
    },
    "MTI-MyoScarSeg": {
        "url": "https://arxiv.org/abs/2501.05241",
        "role": "motion-texture cine scar concept",
        "pretrained_weights": "no public code/weights found in local note",
        "license": "paper only",
        "pretrained_data": "paper dataset; do not reuse external supervised data",
        "compliance_risk": "low only if reimplemented with CARE train data",
        "expected_care_benefit": "direct CineMyoPS scar cue from motion + texture",
        "integration_difficulty": "high",
        "minimal_smoke_test": "CARE-only optical-flow feature prototype, no training",
        "fail_fast": "no component/HD signal, too slow, or requires external supervised data",
        "local_paths": ["third_party/candidates/MTI-MyoScarSeg"],
    },
    "VoxelMorph": {
        "url": "https://github.com/voxelmorph/voxelmorph",
        "role": "frame-to-frame registration/DVF feature extractor",
        "pretrained_weights": "generic possible; cardiac checkpoint provenance must be verified",
        "license": "verify source; package/repo licenses can differ",
        "pretrained_data": "generic/non-cardiac unless a specific cardiac checkpoint is documented",
        "compliance_risk": "medium with pretrained checkpoint; low for CARE-only code use",
        "expected_care_benefit": "motion field feature for scar-sensitive route",
        "integration_difficulty": "medium",
        "minimal_smoke_test": "one-case ED-ES registration audit with Jacobian/folding check",
        "fail_fast": "folding/topology failure, bad geometry, or no downstream motion signal",
        "local_paths": ["third_party/CineMyoPS/code/voxelmorph", "third_party/candidates/voxelmorph"],
    },
    "SegMorph": {
        "url": "https://eprints.gla.ac.uk/332276/",
        "role": "joint motion+segmentation concept",
        "pretrained_weights": "no clear public weights",
        "license": "article open access; code unclear",
        "pretrained_data": "cardiac cine in paper; verify",
        "compliance_risk": "low if concept-only; high if external weights/data are needed",
        "expected_care_benefit": "temporal consistency and motion-aware segmentation",
        "integration_difficulty": "high",
        "minimal_smoke_test": "paper/interface review only",
        "fail_fast": "full reimplementation required before any useful smoke",
        "local_paths": ["third_party/candidates/SegMorph"],
    },
    "cineCMR-SAM": {
        "url": "https://github.com/zhennongchen/cineCMR-SAM",
        "role": "temporal SAM anatomy/ROI support",
        "pretrained_weights": "yes/unclear",
        "license": "verify",
        "pretrained_data": "SAM plus cine CMR adaptation data; verify",
        "compliance_risk": "medium until weight license and prompt dependence are clear",
        "expected_care_benefit": "anatomy localization and ROI support, not primary scar model",
        "integration_difficulty": "medium",
        "minimal_smoke_test": "prompted anatomy output on one CARE cine case",
        "fail_fast": "prompting not automatable, license mismatch, or no stable myocardium ROI",
        "local_paths": ["third_party/candidates/cineCMR-SAM", "models/pretrained/cineCMR-SAM"],
    },
    "InverseForm": {
        "url": "https://github.com/Qualcomm-AI-research/InverseForm",
        "role": "boundary/HD-aware loss",
        "pretrained_weights": "no",
        "license": "verify before vendoring",
        "pretrained_data": "none",
        "compliance_risk": "low if code license permits or first-party reimplementation is used",
        "expected_care_benefit": "reduce HD/HD95 for pathology boundary",
        "integration_difficulty": "low-medium",
        "minimal_smoke_test": "loss-only gradient check on CARE-shaped tensors",
        "fail_fast": "unstable gradients or Dice gain with HD regression",
        "local_paths": ["third_party/candidates/InverseForm"],
    },
    "nnU-Net Task114 M&Ms": {
        "url": "https://zenodo.org/records/4288362",
        "role": "cardiac anatomy pretrained initialization/reference",
        "pretrained_weights": "yes; large download",
        "license": "Zenodo license must be verified",
        "pretrained_data": "M&Ms cardiac MRI",
        "compliance_risk": "low-medium; public pretrained allowed but no download in screening pass",
        "expected_care_benefit": "cross-center anatomy warm start",
        "integration_difficulty": "low",
        "minimal_smoke_test": "metadata-only now; authorized download/import later",
        "fail_fast": "license unclear, label mismatch, or download too large without approval",
        "local_paths": ["models/pretrained/Task114_heart_mnms", "data/nnUNet/nnUNet_results/Task114_heart_mnms"],
    },
    "current CineMyoPS paper repo": {
        "url": "third_party/CineMyoPS",
        "role": "baseline/paper reference",
        "pretrained_weights": "Baidu link in README; not used by current CARE Task026 branch",
        "license": "no local LICENSE found",
        "pretrained_data": "paper multi-center cine",
        "compliance_risk": "medium until license/weights provenance are clear",
        "expected_care_benefit": "audit intended paper behavior vs CARE wrapper",
        "integration_difficulty": "already integrated",
        "minimal_smoke_test": "architecture/label audit only",
        "fail_fast": "cannot restore edema/RV/time aggregation parity without rewriting task",
        "local_paths": ["third_party/CineMyoPS"],
    },
}


def resolve_local_paths(paths: list[str]) -> list[dict[str, object]]:
    resolved = []
    for item in paths:
        path = (REPO_ROOT / item).resolve()
        resolved.append({"path": str(path), "exists": path.exists(), "is_dir": path.is_dir()})
    return resolved


def screen_candidate(name: str) -> dict[str, object]:
    if name not in CANDIDATES:
        raise KeyError(f"Unknown candidate {name!r}; known: {sorted(CANDIDATES)}")
    payload = dict(CANDIDATES[name])
    payload["name"] = name
    payload["local_availability"] = resolve_local_paths(list(payload.get("local_paths", [])))
    payload["screening_mode"] = "metadata_only_no_download_no_training"
    payload["recommended_next_action"] = "verify license/provenance before any weight download or inference"
    return payload


def write_markdown(rows: list[dict[str, object]], path: Path) -> None:
    lines = [
        "# Cine Pretrained Candidate Screening",
        "",
        "This report is metadata-only. It does not download weights, run inference, train, submit jobs, or package validation zips.",
        "",
        "| name | role | weights | license | compliance risk | local availability | minimal smoke | fail-fast |",
        "| --- | --- | --- | --- | --- | --- | --- | --- |",
    ]
    for row in rows:
        availability = ", ".join(
            f"{Path(str(item['path'])).name}:{'yes' if item['exists'] else 'no'}"
            for item in row.get("local_availability", [])
        )
        lines.append(
            "| {name} | {role} | {weights} | {license} | {risk} | {availability} | {smoke} | {fail} |".format(
                name=row["name"],
                role=row["role"],
                weights=row["pretrained_weights"],
                license=row["license"],
                risk=row["compliance_risk"],
                availability=availability or "none",
                smoke=row["minimal_smoke_test"],
                fail=row["fail_fast"],
            )
        )
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--candidate", default="all", help="Candidate name or 'all'.")
    parser.add_argument("--output-dir", type=Path, default=REPO_ROOT / "results/diagnostics/cine_pretrained_screening")
    args = parser.parse_args()

    names = sorted(CANDIDATES) if args.candidate == "all" else [args.candidate]
    rows = [screen_candidate(name) for name in names]
    args.output_dir.mkdir(parents=True, exist_ok=True)
    json_path = args.output_dir / "screening.json"
    md_path = args.output_dir / "screening.md"
    json_path.write_text(json.dumps({"candidates": rows}, indent=2), encoding="utf-8")
    write_markdown(rows, md_path)
    print(json.dumps({"candidates": names, "json": str(json_path), "md": str(md_path)}, indent=2))


if __name__ == "__main__":
    main()
