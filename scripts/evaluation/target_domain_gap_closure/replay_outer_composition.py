#!/usr/bin/env python3
"""Replay frozen source composition on fold2/fold3 outer cases."""

from __future__ import annotations

import csv
import json
import os
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import numpy as np
import torch

REPO_ROOT = Path(__file__).resolve().parents[3]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from scripts.evaluation.target_domain_gap_closure.evaluate_inner_lanes import (  # noqa: E402
    CheckpointSpec,
    RESULT_ROOT,
    RUNTIME_ROOT,
    load_case,
    metric_rows,
    now_utc,
    predict_m0r,
    summarize_subset,
    write_csv,
    write_json,
)

INNER_ROOT = RESULT_ROOT / "inner_evaluation"
OUTER_ROOT = RESULT_ROOT / "outer_replay"

_STOCK_PREDICTOR_CACHE: dict[tuple[int, str], Any] = {}


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def outer_cases_for_fold(fold: int) -> list[str]:
    split = json.loads((RESULT_ROOT / "split_receipt_copy.json").read_text(encoding="utf-8"))
    return list(split[f"fold{fold}"]["outer_cases"])


def selected_source(pathology: str) -> dict[str, Any]:
    rows = read_csv(INNER_ROOT / "global_source_selection.csv")
    matches = [row for row in rows if row["pathology"] == pathology]
    if len(matches) != 1:
        raise RuntimeError(f"expected one selected source for {pathology}, found {len(matches)}")
    row = matches[0]
    row["checkpoint_step"] = int(row["checkpoint_step"])
    return row


def m0r_checkpoint(fold: int, step: int) -> CheckpointSpec:
    receipt = json.loads((RESULT_ROOT / "m0r_faithful_control" / f"fold{fold}_training_receipt.json").read_text(encoding="utf-8"))
    for item in receipt["step_checkpoints"]:
        path = Path(item)
        if f"step{step:05d}" in path.name:
            return CheckpointSpec(lane="m0r_faithful_control", fold=fold, step=step, path=path)
    raise FileNotFoundError(f"M0R checkpoint step {step} missing for fold {fold}")


def stock_checkpoint(fold: int) -> CheckpointSpec:
    receipt = json.loads((RESULT_ROOT / "m0r_faithful_control" / f"fold{fold}_training_receipt.json").read_text(encoding="utf-8"))
    path = Path(receipt["pretrained_checkpoint"])
    return CheckpointSpec(lane="stock_nnunet_anatomy", fold=fold, step=-1, path=path)


def get_stock_predictor(spec: CheckpointSpec, device: torch.device) -> Any:
    key = (spec.fold, spec.path.name)
    if key in _STOCK_PREDICTOR_CACHE:
        return _STOCK_PREDICTOR_CACHE[key]

    os.environ["CARE_ROOT"] = str(REPO_ROOT)
    os.environ["nnUNet_raw"] = str(REPO_ROOT / "data/nnUNet/nnUNet_raw")
    os.environ["nnUNet_preprocessed"] = str(REPO_ROOT / "data/nnUNet/nnUNet_preprocessed")
    os.environ["nnUNet_results"] = str(REPO_ROOT / "data/nnUNet/nnUNet_results")
    os.environ.setdefault("MPLCONFIGDIR", str(RUNTIME_ROOT / "outer_replay_mpl_cache"))

    from nnunetv2.inference.predict_from_raw_data import nnUNetPredictor

    predictor = nnUNetPredictor(
        tile_step_size=0.5,
        use_gaussian=True,
        use_mirroring=False,
        perform_everything_on_device=True,
        device=device,
        verbose=False,
        verbose_preprocessing=False,
        allow_tqdm=False,
    )
    predictor.initialize_from_trained_model_folder(str(spec.path.parent.parent), use_folds=(spec.fold,), checkpoint_name=spec.path.name)
    _STOCK_PREDICTOR_CACHE[key] = predictor
    return predictor


def predict_stock(spec: CheckpointSpec, image: np.ndarray, device: torch.device) -> np.ndarray:
    predictor = get_stock_predictor(spec, device)
    with torch.no_grad():
        data = torch.from_numpy(image).to(device=device, dtype=torch.float32)
        logits = predictor.predict_logits_from_preprocessed_data(data).detach().cpu().numpy()
    return np.argmax(logits, axis=0).astype(np.uint8)


def compose_prediction(stock_pred: np.ndarray, scar_pred: np.ndarray, edema_pred: np.ndarray) -> np.ndarray:
    out = np.zeros_like(stock_pred, dtype=np.uint8)
    for label_value in (1, 2, 3):
        out[stock_pred == label_value] = label_value
    out[edema_pred == 4] = 4
    out[scar_pred == 5] = 5
    return out


def main() -> int:
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    scar_source = selected_source("scar")
    edema_source = selected_source("pure_edema")
    case_rows: list[dict[str, Any]] = []
    inference_rows: list[dict[str, Any]] = []

    for fold in (2, 3):
        scar_spec = m0r_checkpoint(fold, int(scar_source["checkpoint_step"]))
        edema_spec = m0r_checkpoint(fold, int(edema_source["checkpoint_step"]))
        stock_spec = stock_checkpoint(fold)
        for case_id in outer_cases_for_fold(fold):
            t0 = time.time()
            image, label = load_case(case_id)
            stock_pred = predict_stock(stock_spec, image, device)
            scar_pred = predict_m0r(scar_spec, image, device)
            edema_pred = predict_m0r(edema_spec, image, device)
            pred = compose_prediction(stock_pred, scar_pred, edema_pred)
            case_rows.extend(metric_rows("outer_replay_composite", fold, -1, case_id, pred, label, population="outer_replay"))
            inference_rows.append(
                {
                    "fold": fold,
                    "case_id": case_id,
                    "status": "COMPLETED",
                    "device": str(device),
                    "stock_anatomy_checkpoint": str(stock_spec.path),
                    "scar_source_lane": scar_source["lane"],
                    "scar_source_step": scar_source["checkpoint_step"],
                    "edema_source_lane": edema_source["lane"],
                    "edema_source_step": edema_source["checkpoint_step"],
                    "outer_cases_accessed": True,
                    "elapsed_seconds": round(time.time() - t0, 3),
                }
            )
            print(json.dumps({"fold": fold, "case": case_id, "status": "COMPLETED"}), flush=True)

    summary_rows: list[dict[str, Any]] = []
    for pathology in ("scar", "pure_edema"):
        subset = [row for row in case_rows if row["pathology"] == pathology]
        summary_rows.append(summarize_subset("outer_replay_composite", "2+3_outer", -1, pathology, subset))

    write_csv(OUTER_ROOT / "casewise_metrics.csv", case_rows)
    write_csv(OUTER_ROOT / "summary_metrics.csv", summary_rows)
    write_csv(OUTER_ROOT / "inference_accounting.csv", inference_rows)
    receipt = {
        "created_at": now_utc(),
        "status": "PASS",
        "population": "fold2_fold3_outer_deterministic_replay",
        "outer_cases_accessed": True,
        "outer_cases_by_fold": {str(fold): outer_cases_for_fold(fold) for fold in (2, 3)},
        "composition": "fold_specific_stock_anatomy_plus_global_scar_source_plus_global_edema_source_with_scar_priority",
        "scar_source": scar_source,
        "edema_source": edema_source,
        "casewise_rows": len(case_rows),
        "summary_rows": len(summary_rows),
    }
    write_json(OUTER_ROOT / "outer_replay_receipt.json", receipt)
    print(json.dumps(receipt, indent=2, sort_keys=True, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
