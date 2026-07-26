#!/usr/bin/env python3
"""Train a low-capacity CARE-SafeScar-v1 scar component gate.

The gate is deliberately small: regularized logistic regression over the
pre-registered component feature table. It refuses to run unless the component
dataset was built from a 220-case no-leakage OOF audit.
"""

from __future__ import annotations

import argparse
import csv
import json
import math
from pathlib import Path
from typing import Any

import numpy as np

REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_RESULT_ROOT = REPO_ROOT / "results/20260726_care_fullinfo_nnunet_and_care_scf/care_scf_v1"
FEATURE_COLUMNS = [
    "nnunet_probability_mean",
    "nnunet_uncertainty_mean",
    "mosaic_probability_mean",
    "anatomy_overlap",
    "log_size",
    "surface_to_volume",
    "fill_fraction",
    "elongation",
    "positive_prototype_similarity",
    "negative_prototype_similarity",
]
C_GRID = [0.05, 0.1, 0.2, 0.5, 1.0, 2.0]
THRESHOLD_GRID = [0.30, 0.35, 0.40, 0.45, 0.50, 0.55, 0.60, 0.65, 0.70]


def read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def write_csv(path: Path, rows: list[dict[str, Any]], fieldnames: list[str] | None = None) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if fieldnames is None:
        fieldnames = sorted({k for row in rows for k in row}) if rows else ["empty"]
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames, extrasaction="ignore", lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")


def require_component_dataset(result_root: Path) -> dict[str, Any]:
    oof = read_json(result_root / "mosaic_oof_no_leakage_audit.json")
    comp = read_json(result_root / "component_dataset/component_dataset_receipt.json")
    if oof.get("status") != "PASS" or int(oof.get("covered_unique_cases", -1)) != 220:
        raise RuntimeError(f"OOF audit not 220-case PASS: {oof}")
    if comp.get("status") != "PASS":
        raise RuntimeError(f"component dataset not PASS: {comp}")
    return {"oof": oof, "component": comp}


def finite_float(value: Any) -> float:
    try:
        v = float(value)
    except (TypeError, ValueError):
        return 0.0
    return v if math.isfinite(v) else 0.0


def load_matrix(rows: list[dict[str, str]]) -> tuple[np.ndarray, np.ndarray, np.ndarray, list[str]]:
    x = np.asarray([[finite_float(r[c]) for c in FEATURE_COLUMNS] for r in rows], dtype=np.float64)
    y = np.asarray([int(r["component_label_positive"]) for r in rows], dtype=np.int64)
    groups = np.asarray([r["case_id"] for r in rows])
    ids = [r["component_id"] for r in rows]
    return x, y, groups, ids


def standardize_train_apply(x_train: np.ndarray, x_eval: np.ndarray) -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
    mu = x_train.mean(axis=0)
    sigma = x_train.std(axis=0)
    sigma[sigma < 1e-6] = 1.0
    return (x_train - mu) / sigma, (x_eval - mu) / sigma, mu, sigma


def grouped_folds(groups: np.ndarray, n_splits: int = 5) -> list[tuple[np.ndarray, np.ndarray]]:
    unique = np.asarray(sorted(set(groups.tolist())))
    buckets = [[] for _ in range(n_splits)]
    for i, case in enumerate(unique):
        buckets[i % n_splits].append(case)
    splits = []
    for bucket in buckets:
        val_cases = set(bucket)
        val = np.asarray([g in val_cases for g in groups])
        train = ~val
        if train.any() and val.any():
            splits.append((np.where(train)[0], np.where(val)[0]))
    return splits


def metrics_for(y_true: np.ndarray, y_pred: np.ndarray) -> dict[str, Any]:
    tp = int(((y_true == 1) & (y_pred == 1)).sum())
    tn = int(((y_true == 0) & (y_pred == 0)).sum())
    fp = int(((y_true == 0) & (y_pred == 1)).sum())
    fn = int(((y_true == 1) & (y_pred == 0)).sum())
    precision = tp / max(1, tp + fp)
    recall = tp / max(1, tp + fn)
    f1 = 2 * precision * recall / max(1e-12, precision + recall)
    return {"tp": tp, "tn": tn, "fp": fp, "fn": fn, "precision": precision, "recall": recall, "f1": f1, "harmful_retained_fp": fp, "helpful_retained_tp": tp}


def train_logistic(x: np.ndarray, y: np.ndarray, c_value: float):
    from sklearn.linear_model import LogisticRegression

    model = LogisticRegression(C=float(c_value), penalty="l2", solver="liblinear", class_weight="balanced", max_iter=1000, random_state=20260726)
    model.fit(x, y)
    return model


def crossfit_grid(x: np.ndarray, y: np.ndarray, groups: np.ndarray) -> tuple[dict[str, Any], list[dict[str, Any]], np.ndarray]:
    splits = grouped_folds(groups, 5)
    grid_rows: list[dict[str, Any]] = []
    best: dict[str, Any] | None = None
    best_probs = np.zeros(len(y), dtype=np.float64)
    for c_value in C_GRID:
        oof_prob = np.zeros(len(y), dtype=np.float64)
        for train_idx, val_idx in splits:
            xtr, xva, _mu, _sig = standardize_train_apply(x[train_idx], x[val_idx])
            model = train_logistic(xtr, y[train_idx], c_value)
            oof_prob[val_idx] = model.predict_proba(xva)[:, 1]
        for threshold in THRESHOLD_GRID:
            pred = (oof_prob >= threshold).astype(np.int64)
            metrics = metrics_for(y, pred)
            # Harm-averse but not closed: prefer fewer FP, then recall/F1.
            score = metrics["tp"] - 2.0 * metrics["fp"] - 0.25 * metrics["fn"]
            row = {"C": c_value, "threshold": threshold, "score": score, **metrics}
            grid_rows.append(row)
            if best is None or (score, metrics["f1"], metrics["recall"]) > (best["score"], best["f1"], best["recall"]):
                best = row
                best_probs = oof_prob.copy()
    assert best is not None
    return best, grid_rows, best_probs


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--result-root", type=Path, default=DEFAULT_RESULT_ROOT)
    args = parser.parse_args()
    result_root = args.result_root if args.result_root.is_absolute() else REPO_ROOT / args.result_root
    receipts = require_component_dataset(result_root)
    rows = read_csv(result_root / "component_dataset/scar_components.csv")
    if not rows:
        raise RuntimeError("scar component dataset is empty")
    x, y, groups, ids = load_matrix(rows)
    best, grid_rows, oof_probs = crossfit_grid(x, y, groups)
    threshold = float(best["threshold"])
    decisions = []
    for row, prob in zip(rows, oof_probs):
        action = "retain" if prob >= threshold else "suppress"
        if action == "suppress" and int(row["component_label_positive"]) == 1:
            outcome = "harm_false_suppression"
        elif action == "suppress" and int(row["component_label_positive"]) == 0:
            outcome = "help_suppressed_fp"
        elif action == "retain" and int(row["component_label_positive"]) == 1:
            outcome = "help_retained_tp"
        else:
            outcome = "harm_retained_fp"
        decisions.append({
            "component_id": row["component_id"],
            "case_id": row["case_id"],
            "fold": row["fold"],
            "pathology": "scar",
            "gate_probability_retain": float(prob),
            "decision": action,
            "replace_allowed": False,
            "fallback": "nnU-Net_anchor_for_suppressed_or_missing_components",
            "component_label_positive": row["component_label_positive"],
            "oof_help_harm_label": outcome,
        })
    out_dir = result_root / "care_safescar_v1"
    write_csv(out_dir / "gate_hyperparameter_grid.csv", grid_rows)
    write_csv(out_dir / "component_decisions.csv", decisions)
    summary = metrics_for(y, np.asarray([1 if d["decision"] == "retain" else 0 for d in decisions], dtype=np.int64))
    receipt = {
        "status": "PASS",
        "model_type": "regularized_logistic_regression",
        "gate_training_case_grouped": True,
        "component_count": len(rows),
        "case_count": len(set(groups.tolist())),
        "feature_columns": FEATURE_COLUMNS,
        "hyperparameter_grid_size": len(grid_rows),
        "selected_C": best["C"],
        "selected_threshold": best["threshold"],
        "selected_score": best["score"],
        "oof_metrics": summary,
        "actions": ["retain", "suppress"],
        "replace_allowed": False,
        "edema_fallback": True,
        "oof_audit_status": receipts["oof"].get("status"),
        "validation_upload_performed": False,
    }
    write_json(out_dir / "gate_training_receipt.json", receipt)
    print(json.dumps(receipt, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
