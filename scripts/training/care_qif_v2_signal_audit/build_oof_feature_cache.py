#!/usr/bin/env python3
"""Build patient-clean OOF nnU-Net feature cache for CARE-QIF v2."""

from __future__ import annotations

import argparse
import csv
import sys
from pathlib import Path
from typing import Any

import numpy as np
import torch

REPO_ROOT_FOR_IMPORT = Path(__file__).resolve().parents[3]
if str(REPO_ROOT_FOR_IMPORT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT_FOR_IMPORT))

from scripts.evaluation.evaluate_care_prism import crop_to_shape, pad_to_multiple, spatial_multiple  # noqa: E402
from scripts.forensics.care_qif_v2_signal_audit.common import (  # noqa: E402
    FEATURE_ROOT,
    PLANS_JSON,
    RESULT_ROOT,
    checkpoint_path_for_fold,
    feature_cache_path,
    load_image,
    load_seg,
    rel,
    sha256_file,
    spacing_zyx,
    utc_now,
    write_csv,
    write_json,
    read_json,
)
from src.care_myocardium.models.care_prism import CAREPRISMConfig, build_source_nnunet  # noqa: E402
from src.care_myocardium.models.myowall_if.stock_adapter import checkpoint_state_dict  # noqa: E402


class CleanOOFFeatureExtractor:
    """Patient-clean nnU-Net OOF feature extractor used by this audit only."""

    def __init__(self, fold: int, device: torch.device) -> None:
        self.fold = int(fold)
        self.device = device
        self.network = load_stock_network(self.fold, self.device)

    def extract(self, case_id: str) -> dict[str, np.ndarray]:
        return run_case(self.network, case_id, self.device)


def read_oof_manifest(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def load_stock_network(fold: int, device: torch.device) -> torch.nn.Module:
    config = CAREPRISMConfig.from_nnunet_plans(PLANS_JSON, configuration="3d_fullres")
    network = build_source_nnunet(config).to(device)
    payload = torch.load(checkpoint_path_for_fold(fold), map_location="cpu", weights_only=False)
    missing, unexpected = network.load_state_dict(checkpoint_state_dict(payload), strict=False)
    if missing or unexpected:
        print(f"fold={fold} missing_keys={len(missing)} unexpected_keys={len(unexpected)}")
    for p in network.parameters():
        p.requires_grad_(False)
    network.eval()
    return network


def run_case(network: torch.nn.Module, case_id: str, device: torch.device) -> dict[str, np.ndarray]:
    config = CAREPRISMConfig.from_nnunet_plans(PLANS_JSON, configuration="3d_fullres")
    image = torch.from_numpy(load_image(case_id)).unsqueeze(0).to(device=device, dtype=torch.float32)
    padded, spatial = pad_to_multiple(image, spatial_multiple(config))
    decoder_feats: list[torch.Tensor] = []
    handles = []
    if not hasattr(network, "decoder") or not hasattr(network.decoder, "stages"):
        raise RuntimeError("source nnU-Net decoder stages are unavailable")
    for stage in network.decoder.stages:
        def _capture(_module: Any, _inputs: Any, output: Any, bucket: list[torch.Tensor] = decoder_feats) -> None:
            if torch.is_tensor(output):
                bucket.append(output.detach())
            elif isinstance(output, (list, tuple)) and output and torch.is_tensor(output[0]):
                bucket.append(output[0].detach())

        handles.append(stage.register_forward_hook(_capture))
    try:
        with torch.no_grad():
            logits = network(padded)
    finally:
        for handle in handles:
            handle.remove()
    if isinstance(logits, (list, tuple)):
        logits = logits[0]
    logits = crop_to_shape(logits, spatial)
    probs = torch.softmax(logits, dim=1)
    if len(decoder_feats) < 2:
        raise RuntimeError(f"{case_id} produced {len(decoder_feats)} decoder features")
    f0 = crop_to_shape(decoder_feats[-1], spatial)
    f1 = decoder_feats[-2]
    return {
        "f0": f0[0].detach().cpu().to(torch.float16).numpy(),
        "f1": f1[0].detach().cpu().to(torch.float16).numpy(),
        "p_myo": (probs[:, 1:2] + probs[:, 4:5] + probs[:, 5:6])[0, 0].detach().cpu().to(torch.float16).numpy(),
        "p_lv": probs[:, 2:3][0, 0].detach().cpu().to(torch.float16).numpy(),
        "stock_scar_prob": probs[:, 5:6][0, 0].detach().cpu().to(torch.float16).numpy(),
        "stock_pred": probs.argmax(dim=1)[0].detach().cpu().to(torch.uint8).numpy(),
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--manifest", type=Path, default=RESULT_ROOT / "oof_backbone_manifest.csv")
    parser.add_argument("--feature-root", type=Path, default=FEATURE_ROOT)
    parser.add_argument("--device", default="cuda")
    parser.add_argument("--max-cases", type=int)
    args = parser.parse_args()

    device = torch.device(args.device)
    if device.type == "cuda" and not torch.cuda.is_available():
        raise SystemExit("CUDA requested but not available")
    rows = read_oof_manifest(args.manifest)
    if args.max_cases is not None:
        rows = rows[: args.max_cases]
    args.feature_root.mkdir(parents=True, exist_ok=True)
    receipt_path = RESULT_ROOT / "feature_cache_receipt.json"
    manifest_path = RESULT_ROOT / "feature_cache_manifest.csv"
    if args.max_cases is None and receipt_path.exists() and manifest_path.exists():
        try:
            receipt = read_json(receipt_path)
            manifest_rows = read_oof_manifest(manifest_path)
            if (
                receipt.get("status") == "PASS"
                and receipt.get("case_count") == 80
                and len(manifest_rows) == 80
                and all((args.feature_root / f"{row['case_id']}.npz").exists() for row in manifest_rows)
            ):
                print("feature_cache_reuse=PASS case_count=80")
                return 0
        except Exception as exc:
            print(f"feature_cache_reuse=SKIP reason={exc}")

    manifest: list[dict[str, Any]] = []
    for fold in sorted({int(row["oof_fold"]) for row in rows}):
        extractor = CleanOOFFeatureExtractor(fold, device)
        fold_rows = [row for row in rows if int(row["oof_fold"]) == fold]
        ckpt = checkpoint_path_for_fold(fold)
        for row in fold_rows:
            case_id = row["case_id"]
            out_path = args.feature_root / f"{case_id}.npz"
            arrays = extractor.extract(case_id)
            seg = load_seg(case_id)
            if tuple(arrays["p_myo"].shape) != tuple(seg.shape):
                raise RuntimeError(f"{case_id} soft context shape {arrays['p_myo'].shape} != seg {seg.shape}")
            np.savez_compressed(
                out_path,
                **arrays,
                spacing_zyx=np.asarray(spacing_zyx(case_id), dtype=np.float32),
                case_id=np.asarray(case_id),
                center=np.asarray(row["center"]),
                oof_fold=np.asarray(fold, dtype=np.int16),
            )
            manifest.append(
                {
                    "case_id": case_id,
                    "center": row["center"],
                    "oof_fold": fold,
                    "feature_cache_path": str(out_path),
                    "feature_cache_sha256": sha256_file(out_path),
                    "checkpoint_path": rel(ckpt),
                    "checkpoint_sha256": row["checkpoint_sha256"],
                    "case_membership_status": row["case_membership_status"],
                    "f0_shape": "x".join(str(v) for v in arrays["f0"].shape),
                    "f1_shape": "x".join(str(v) for v in arrays["f1"].shape),
                    "soft_context_shape": "x".join(str(v) for v in arrays["p_myo"].shape),
                    "status": "PASS",
                }
            )
        del extractor
        if device.type == "cuda":
            torch.cuda.empty_cache()

    write_csv(RESULT_ROOT / "feature_cache_manifest.csv", manifest)
    write_json(
        RESULT_ROOT / "feature_cache_receipt.json",
        {
            "created_at": utc_now(),
            "feature_root": str(args.feature_root),
            "case_count": len(manifest),
            "expected_case_count": 80 if args.max_cases is None else args.max_cases,
            "all_patient_clean": all(row["case_membership_status"] == "PASS" for row in manifest),
            "status": "PASS" if manifest and all(row["status"] == "PASS" for row in manifest) else "FAIL",
        },
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
