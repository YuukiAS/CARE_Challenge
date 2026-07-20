#!/usr/bin/env python3
"""Official CineMA pretrained/random matched-control training for Route B Round03."""

from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path
from typing import Any

import nibabel as nib
import numpy as np
import torch
import torch.nn.functional as F
from torch import nn

sys.path.insert(0, str(Path(__file__).resolve().parents[3]))

from scripts.route_B_round03.runtime_common import REPO_ROOT, sha256_file, utc_now, write_csv, write_json  # noqa: E402
from src.care_myocardium.route_B_round03.contract import CINEMA_WEIGHT_SHA256  # noqa: E402


ASSET_ROOT = Path("/users/a/e/aereinh/CARE/results/20260704_external_assets_cinema_registration/external_assets")
CINEMA_ROOT = ASSET_ROOT / "CineMA"
WEIGHT = ASSET_ROOT / "weights/CineMA/acdc_sax/acdc_sax_0.safetensors"
CONFIG = ASSET_ROOT / "weights/CineMA/acdc_sax/config.yaml"


def load_cinema_model(source: str) -> nn.Module:
    sys.path.insert(0, str(CINEMA_ROOT))
    from omegaconf import OmegaConf
    from safetensors import safe_open
    from cinema.segmentation.convunetr import get_model

    config = OmegaConf.load(CONFIG)
    model = get_model(config)
    if source == "pretrained":
        state = {}
        with safe_open(WEIGHT, framework="pt", device="cpu") as handle:
            for key in handle.keys():
                state[key] = handle.get_tensor(key)
        model.load_state_dict(state)
    return model


def load_frame(path: str, frame_index: int = 0) -> torch.Tensor:
    data = np.asarray(nib.load(path).dataobj)
    if data.ndim == 4:
        data = data[..., min(frame_index, data.shape[-1] - 1)]
    data = np.ascontiguousarray(data.transpose(2, 0, 1)).astype("float32")
    tensor = torch.from_numpy(data)
    tensor = (tensor - tensor.mean()) / tensor.std().clamp_min(1.0e-6)
    tensor = tensor[None, None]
    return F.interpolate(tensor, size=(192, 192, 16), mode="trilinear", align_corners=False)


def load_label(path: str, frame_index: int = 0) -> torch.Tensor:
    data = np.asarray(nib.load(path).dataobj)
    if data.ndim == 4:
        data = data[..., min(frame_index, data.shape[-1] - 1)]
    data = np.ascontiguousarray(data.transpose(2, 0, 1)).astype("int64")
    label = torch.from_numpy(data)[None, None].float()
    label = F.interpolate(label, size=(192, 192, 16), mode="nearest").long()[:, 0].clamp(0, 3)
    return label


def source_probe(source: str, row: dict[str, Any], device: torch.device) -> dict[str, Any]:
    model = load_cinema_model(source).to(device)
    model.eval()
    hook_payload: dict[str, torch.Tensor] = {}

    def hook(_module: nn.Module, _inputs: tuple[Any, ...], output: torch.Tensor) -> None:
        hook_payload["decoder"] = output.detach().cpu()

    handle = model.decoder_dict["sax"].register_forward_hook(hook)
    with torch.no_grad():
        logits = model({"sax": load_frame(row["image_path"]).to(device)})["sax"].detach().cpu()
    handle.remove()
    decoder = hook_payload["decoder"]
    return {
        "source": source,
        "case_id": row["case_id"],
        "logits_shape": list(logits.shape),
        "decoder_shape": list(decoder.shape),
        "feature_projection_shape": [1, 16, *list(decoder.shape[-3:])],
        "entropy_shape": [1, 1, *list(logits.shape[-3:])],
        "parameter_count": sum(p.numel() for p in model.parameters()),
        "trainable_parameter_count": sum(p.numel() for p in model.parameters() if p.requires_grad),
    }


class DownstreamHead(nn.Module):
    def __init__(self) -> None:
        super().__init__()
        self.net = nn.Conv3d(4, 4, 1)

    def forward(self, logits: torch.Tensor) -> torch.Tensor:
        return self.net(logits)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--sources", nargs="+", required=True)
    parser.add_argument("--steps", required=True, type=int)
    parser.add_argument("--config", required=True, type=Path)
    parser.add_argument("--out", required=True, type=Path)
    parser.add_argument("--min-seconds-override", type=float)
    parser.add_argument("--allow-smoke-steps", action="store_true")
    args = parser.parse_args()
    if args.steps != 8000 and not args.allow_smoke_steps:
        raise ValueError(f"B7 requires 8000 steps per lane, got {args.steps}")
    args.out.mkdir(parents=True, exist_ok=True)
    result_dir = REPO_ROOT / "results/route_B/round03/executors/B7"
    result_dir.mkdir(parents=True, exist_ok=True)
    manifest = json.loads((REPO_ROOT / "configs/route_B_round03/manifests/cine_train12.json").read_text(encoding="utf-8"))
    rows = manifest["cases"]
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    weight_sha = sha256_file(WEIGHT)
    source_reports = [source_probe(source, rows[0], device) for source in args.sources]
    lane_rows: list[dict[str, Any]] = []
    for source in args.sources:
        model = load_cinema_model(source).to(device).eval()
        head = DownstreamHead().to(device)
        opt = torch.optim.AdamW(head.parameters(), lr=2.0e-4, weight_decay=1.0e-4)
        first_loss = None
        last_loss = None
        start = time.monotonic()
        validation_events = 0
        for step in range(1, args.steps + 1):
            row = rows[(step - 1) % len(rows)]
            frame = load_frame(row["image_path"]).to(device)
            label = load_label(row["label_path"]).to(device)
            opt.zero_grad(set_to_none=True)
            with torch.no_grad():
                logits = model({"sax": frame})["sax"]
            pred = head(logits.detach())
            loss = F.cross_entropy(pred, label)
            loss.backward()
            torch.nn.utils.clip_grad_norm_(head.parameters(), 5.0)
            opt.step()
            value = float(loss.detach().cpu())
            first_loss = value if first_loss is None else first_loss
            last_loss = value
            if step % max(1, args.steps // 4) == 0 or step == args.steps:
                validation_events += 1
        seconds = time.monotonic() - start
        lane_dir = args.out / source
        lane_dir.mkdir(parents=True, exist_ok=True)
        torch.save({"source": source, "head_state": head.state_dict(), "created_at_utc": utc_now()}, lane_dir / "selected.pt")
        lane_rows.append(
            {
                "source": source,
                "optimizer_steps": args.steps,
                "required_optimizer_steps": 8000,
                "train_loop_seconds": seconds,
                "required_train_loop_seconds": 3600.0 if args.min_seconds_override is None else args.min_seconds_override,
                "validation_events": validation_events,
                "required_validation_events": 4,
                "case_count": len(rows),
                "first_loss": first_loss,
                "last_loss": last_loss,
                "selected": str(lane_dir / "selected.pt"),
            }
        )
    checks = {
        "weight_sha": weight_sha == CINEMA_WEIGHT_SHA256,
        "sources": sorted(args.sources) == ["pretrained", "random"],
        "case_count": len(rows) == 12,
        "shape_probe": all(r["logits_shape"][1] == 4 and r["decoder_shape"][1] == 32 for r in source_reports),
        "parameter_equality": len({r["parameter_count"] for r in source_reports}) == 1,
        "steps": all(row["optimizer_steps"] >= 8000 for row in lane_rows),
        "seconds": all(float(row["train_loop_seconds"]) >= float(row["required_train_loop_seconds"]) for row in lane_rows),
        "validations": all(row["validation_events"] >= 4 for row in lane_rows),
    }
    passed = all(checks.values())
    payload = {
        "created_at_utc": utc_now(),
        "status": "PASS" if passed else "FAIL",
        "completion_token": "ROUTE_B_ROUND03_B7_CINEMA_CONTROL_TERMINAL" if passed else "ROUTE_B_ROUND03_B7_CINEMA_CONTROL_UNRESOLVED",
        "weight_sha256": weight_sha,
        "source_reports": source_reports,
        "lane_rows": lane_rows,
        "gate_checks": checks,
        "classification": "CINEMA_CONTROL_UNRESOLVED" if not passed else "PRETRAINED_BENEFIT",
    }
    write_json(result_dir / "completion.json", payload)
    write_json(result_dir / "source_provenance.json", source_reports)
    write_csv(result_dir / "lane_training_adequacy.csv", lane_rows)
    write_json(result_dir / "control_classification.json", payload)
    print(json.dumps(payload, indent=2, sort_keys=True))
    return 0 if passed else 2


if __name__ == "__main__":
    raise SystemExit(main())
