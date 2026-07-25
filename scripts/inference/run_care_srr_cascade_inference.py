#!/usr/bin/env python
"""Inference entrypoint for CARE-SRR-Cascade checkpoints."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

import torch

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from src.care_myocardium.models.care_srr_cascade_rescue import CARESRRCascadeRescue


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n")


def run_tensor_inference(checkpoint: Path, batch_path: Path, output_path: Path, pathology: str) -> dict[str, Any]:
    payload = torch.load(checkpoint, map_location="cpu", weights_only=False)
    batch = torch.load(batch_path, map_location="cpu", weights_only=True)
    model = CARESRRCascadeRescue(source_feature_channels=int(batch["source_features"].shape[1]))
    state = payload.get("model_state") or payload.get("model_state_dict") or payload.get("model_state")
    if state is None:
        raise ValueError("checkpoint missing model_state")
    model.load_state_dict(state)
    model.eval()
    with torch.inference_mode():
        out = model(**{k: v for k, v in batch.items() if k not in {"labels", "distance_to_gt_union_mm", "distance_to_gt_pathology_surface_mm"}}, active_pathology=pathology)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    torch.save({"final_logits": out["final_logits"].cpu(), "active_pathology": pathology}, output_path)
    return {"decision": "PASS", "output_path": str(output_path), "shape": list(out["final_logits"].shape)}


def contract() -> dict[str, Any]:
    return {
        "entrypoint": "scripts/inference/run_care_srr_cascade_inference.py",
        "mode": "sliding_window_correction_or_prebuilt_tensor_batch",
        "accumulation": "bounded_correction_field_then_add_to_anchor",
        "official_inverse_export_required_in_RC5": True,
        "gt_access_forbidden": True,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--print-contract", action="store_true")
    parser.add_argument("--checkpoint", type=Path)
    parser.add_argument("--batch", type=Path)
    parser.add_argument("--output", type=Path)
    parser.add_argument("--pathology", choices=["scar", "edema"], default="scar")
    args = parser.parse_args()
    if args.print_contract:
        print(json.dumps(contract(), indent=2, sort_keys=True))
        return 0
    if not (args.checkpoint and args.batch and args.output):
        raise SystemExit("--checkpoint, --batch, and --output are required unless --print-contract")
    print(json.dumps(run_tensor_inference(args.checkpoint, args.batch, args.output, args.pathology), indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
