#!/usr/bin/env python3
"""Recover validation export/summary for an SRR fold0 checkpoint."""

from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path
from types import SimpleNamespace

import torch


REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from scripts.training.run_srr_myops_fold0 import (  # noqa: E402
    dictionary_mode_for_variant,
    evaluate_and_export,
    load_hard_negative_targets,
    load_myops_case_metadata,
    load_split,
    make_model,
    proposal_mode_for_variant,
    read_case,
    write_text,
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--checkpoint", required=True, type=Path)
    parser.add_argument("--out-root", required=True, type=Path)
    parser.add_argument("--device", choices=["cuda", "cpu"], default="cuda")
    parser.add_argument("--failure-note", default="")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    checkpoint = args.checkpoint if args.checkpoint.is_absolute() else REPO_ROOT / args.checkpoint
    out_root = args.out_root if args.out_root.is_absolute() else REPO_ROOT / args.out_root
    state = torch.load(checkpoint, map_location="cpu", weights_only=False)
    ckpt_args = dict(state.get("args", {}))
    if not ckpt_args:
        raise ValueError(f"checkpoint has no saved args: {checkpoint}")
    ckpt_args["out_root"] = str(out_root)
    ckpt_args["device"] = args.device
    ns = SimpleNamespace(**ckpt_args)
    device = torch.device("cuda" if args.device == "cuda" and torch.cuda.is_available() else "cpu")
    _, val_ids = load_split(int(ns.fold))
    metadata = load_myops_case_metadata()
    val_cases = [read_case(cid, metadata) for cid in val_ids]
    model = make_model(ns, device)
    model.load_state_dict(state["model_state_dict"])
    variant_dir = out_root / "variants" / ns.variant
    start = time.monotonic()
    evaluate_and_export(model, val_cases, variant_dir, ns.variant, device)
    elapsed = time.monotonic() - start
    hardneg_path = Path(getattr(ns, "hardneg_components_csv", "")) if getattr(ns, "hardneg_components_csv", "") else None
    if hardneg_path is not None and not hardneg_path.is_absolute():
        hardneg_path = REPO_ROOT / hardneg_path
    hardneg_targets = load_hard_negative_targets(hardneg_path, ns.variant)
    checkpoint_final = checkpoint.parent / "checkpoint_final.pt"
    summary = {
        "variant": ns.variant,
        "fold": int(ns.fold),
        "device": str(device),
        "val_cases": len(val_cases),
        "best_step": state.get("step", ""),
        "best_val_patch_loss": state.get("val_patch_loss", ""),
        "stop_reason": "recovered_export_from_checkpoint",
        "elapsed_seconds": elapsed,
        "budget_status": "RECOVERED_EXPORT_ONLY",
        "out_root": str(out_root),
        "checkpoint_best": str(checkpoint),
        "checkpoint_final": str(checkpoint_final) if checkpoint_final.is_file() else "",
        "prediction_dir": str(variant_dir / "predictions/fold_0/checkpoint_best"),
        "export_skipped": False,
        "dictionary_mode": dictionary_mode_for_variant(ns.variant),
        "proposal_mode": proposal_mode_for_variant(ns.variant),
        "lesion_auxiliary_config": {
            "hardneg_components_csv": str(hardneg_path) if hardneg_path else "",
            "hardneg_case_count": len(hardneg_targets),
            "hardneg_component_count": sum(len(v) for v in hardneg_targets.values()),
            "hardneg_sample_prob": float(getattr(ns, "hardneg_sample_prob", 0.0)),
            "proposal_final_mix_weight": float(getattr(ns, "proposal_final_mix_weight", 0.0)),
        },
        "recovery_note": args.failure_note,
    }
    (variant_dir / "summary.json").write_text(json.dumps(summary, indent=2, sort_keys=True), encoding="utf-8")
    write_text(
        variant_dir / "summary.md",
        "\n".join(
            [
                f"# {ns.variant} Fold0 Recovered Export Summary",
                "",
                "- stop_reason: `recovered_export_from_checkpoint`",
                "- budget_status: `RECOVERED_EXPORT_ONLY`",
                f"- checkpoint_best: `{checkpoint}`",
                f"- predictions: `{summary['prediction_dir']}`",
            ]
        )
        + "\n",
    )
    print(json.dumps({"variant": ns.variant, "predictions": summary["prediction_dir"], "elapsed_seconds": elapsed}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
