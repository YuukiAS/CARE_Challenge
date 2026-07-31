#!/usr/bin/env python3
"""Run fixed cross-center logistic-regression intensity probes."""

from __future__ import annotations

import argparse
import csv
import sys
from collections import defaultdict
from pathlib import Path
from typing import Any

import numpy as np
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import average_precision_score, roc_auc_score
from sklearn.preprocessing import StandardScaler

REPO_ROOT_FOR_IMPORT = Path(__file__).resolve().parents[3]
if str(REPO_ROOT_FOR_IMPORT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT_FOR_IMPORT))

from scripts.forensics.care_qif_v2_signal_audit.common import RESULT_ROOT, SEED, read_csv, sha256_file, utc_now, write_csv, write_json  # noqa: E402
from scripts.forensics.care_qif_v2_signal_audit.intensity_features import feature_volume  # noqa: E402


def sample_train_voxels(x: np.ndarray, y: np.ndarray, valid: np.ndarray, case_id: str) -> tuple[np.ndarray, np.ndarray]:
    rng = np.random.default_rng(int(__import__("hashlib").sha256(f"{SEED}:{case_id}".encode()).hexdigest()[:12], 16))
    pos = np.flatnonzero(valid.reshape(-1) & (y.reshape(-1) == 1))
    neg = np.flatnonzero(valid.reshape(-1) & (y.reshape(-1) == 0))
    if len(pos) > 4096:
        pos = rng.choice(pos, size=4096, replace=False)
    if len(neg) > 4096:
        neg = rng.choice(neg, size=4096, replace=False)
    idx = np.concatenate([pos, neg])
    rng.shuffle(idx)
    return x.reshape(-1, x.shape[-1])[idx], y.reshape(-1)[idx].astype(np.int64)


def metric_pair(y_true: np.ndarray, score: np.ndarray) -> dict[str, Any]:
    prevalence = float(np.mean(y_true)) if y_true.size else 0.0
    if len(np.unique(y_true)) < 2:
        return {"AUROC": "", "AUPRC": "", "prevalence": prevalence, "AUPRC_lift": ""}
    auroc = float(roc_auc_score(y_true, score))
    auprc = float(average_precision_score(y_true, score))
    return {
        "AUROC": auroc,
        "AUPRC": auprc,
        "prevalence": prevalence,
        "AUPRC_lift": float(auprc / max(prevalence, 1.0e-12)),
    }


def fit_transfer(rows: list[dict[str, str]], *, train_center: str, test_center: str, target: str, context: str, model: str) -> tuple[list[dict[str, Any]], dict[str, Any], list[dict[str, Any]]]:
    train_cases = [r["case_id"] for r in rows if r["center"] == train_center]
    test_cases = [r["case_id"] for r in rows if r["center"] == test_center]
    x_parts: list[np.ndarray] = []
    y_parts: list[np.ndarray] = []
    feature_meta: list[dict[str, Any]] = []
    for case_id in train_cases:
        x, y, valid, meta = feature_volume(case_id, target=target, context=context, model=model)
        sx, sy = sample_train_voxels(x, y, valid, case_id)
        x_parts.append(sx)
        y_parts.append(sy)
        feature_meta.append({**meta, "center": train_center, "usage": "train_sampled", "sampled_voxels": len(sy)})
    x_train = np.concatenate(x_parts, axis=0)
    y_train = np.concatenate(y_parts, axis=0)
    scaler = StandardScaler()
    x_train = scaler.fit_transform(x_train)
    clf = LogisticRegression(C=1.0, class_weight="balanced", max_iter=2000, random_state=SEED)
    clf.fit(x_train, y_train)
    case_rows: list[dict[str, Any]] = []
    pooled_y: list[np.ndarray] = []
    pooled_s: list[np.ndarray] = []
    for case_id in test_cases:
        x, y, valid, meta = feature_volume(case_id, target=target, context=context, model=model)
        xv = x.reshape(-1, x.shape[-1])[valid.reshape(-1)]
        yv = y.reshape(-1)[valid.reshape(-1)].astype(np.int64)
        score = clf.predict_proba(scaler.transform(xv))[:, 1]
        m = metric_pair(yv, score)
        case_rows.append(
            {
                "direction": f"{train_center}->{test_center}",
                "train_center": train_center,
                "test_center": test_center,
                "case_id": case_id,
                "target": target,
                "context": context,
                "probe_model": model,
                "valid_voxels": int(yv.size),
                "positive_voxels": int(yv.sum()),
                **m,
            }
        )
        feature_meta.append({**meta, "center": test_center, "usage": "held_out_full_voxel_eval", "sampled_voxels": 0})
        pooled_y.append(yv)
        pooled_s.append(score.astype(np.float32))
    pooled_metric = metric_pair(np.concatenate(pooled_y), np.concatenate(pooled_s))
    aurocs = [float(r["AUROC"]) for r in case_rows if r["AUROC"] != ""]
    auprcs = [float(r["AUPRC"]) for r in case_rows if r["AUPRC"] != ""]
    lifts = [float(r["AUPRC_lift"]) for r in case_rows if r["AUPRC_lift"] != ""]
    summary = {
        "direction": f"{train_center}->{test_center}",
        "train_center": train_center,
        "test_center": test_center,
        "target": target,
        "context": context,
        "probe_model": model,
        "train_cases": len(train_cases),
        "test_cases": len(test_cases),
        "macro_case_AUROC": float(np.mean(aurocs)) if aurocs else "",
        "macro_case_AUPRC": float(np.mean(auprcs)) if auprcs else "",
        "macro_case_AUPRC_lift": float(np.mean(lifts)) if lifts else "",
        "pooled_AUROC": pooled_metric["AUROC"],
        "pooled_AUPRC": pooled_metric["AUPRC"],
        "pooled_AUPRC_lift": pooled_metric["AUPRC_lift"],
        "median_per_case_AUROC": float(np.median(aurocs)) if aurocs else "",
        "q25_per_case_AUROC": float(np.percentile(aurocs, 25)) if aurocs else "",
        "coef_count": int(clf.coef_.shape[1]),
        "scaler_fit_center": train_center,
        "threshold_fit_on_test_center": False,
    }
    coef_rows = [
        {
            "direction": f"{train_center}->{test_center}",
            "target": target,
            "context": context,
            "probe_model": model,
            "feature_index": idx,
            "coefficient": float(value),
        }
        for idx, value in enumerate(clf.coef_[0])
    ]
    return case_rows, summary, feature_meta + coef_rows


def gate_receipt(summaries: list[dict[str, Any]]) -> dict[str, Any]:
    by_key = {(r["target"], r["context"], r["probe_model"], r["direction"]): r for r in summaries}

    def f(row: dict[str, Any], key: str) -> float:
        return float(row[key])

    predicates: dict[str, bool] = {}
    decisions = {}
    for target in ("scar", "injury"):
        dep = [by_key[(target, "DEPLOYABLE_CONTEXT", "rank_composite", "CenterB->CenterC")], by_key[(target, "DEPLOYABLE_CONTEXT", "rank_composite", "CenterC->CenterB")]]
        gt = [by_key[(target, "GT_CONTEXT", "rank_composite", "CenterB->CenterC")], by_key[(target, "GT_CONTEXT", "rank_composite", "CenterC->CenterB")]]
        raw = [by_key[(target, "DEPLOYABLE_CONTEXT", "raw", "CenterB->CenterC")], by_key[(target, "DEPLOYABLE_CONTEXT", "raw", "CenterC->CenterB")]]
        name = target
        predicates[f"{name}_both_direction_macro_auroc_ge_0_65"] = all(f(r, "macro_case_AUROC") >= 0.65 for r in dep)
        predicates[f"{name}_both_direction_auprc_lift_ge_2"] = all(f(r, "macro_case_AUPRC_lift") >= 2.0 for r in dep)
        predicates[f"{name}_median_auroc_ge_0_70_both_centers"] = all(f(r, "median_per_case_AUROC") >= 0.70 for r in dep)
        predicates[f"{name}_CenterC_q25_auroc_ge_0_60"] = f(dep[0], "q25_per_case_AUROC") >= 0.60
        predicates[f"{name}_deployable_no_more_than_0_05_below_gt"] = all(f(g, "macro_case_AUROC") - f(d, "macro_case_AUROC") <= 0.05 for d, g in zip(dep, gt))
        deltas = [f(d, "macro_case_AUROC") - f(r, "macro_case_AUROC") for d, r in zip(dep, raw)]
        predicates[f"{name}_rank_improves_raw_one_direction_and_not_worse_other"] = max(deltas) >= 0.03 and min(deltas) >= -0.02
        decisions[target] = "PASS" if all(value for key, value in predicates.items() if key.startswith(f"{name}_")) else "FAIL"
    if decisions["scar"] == "PASS" and decisions["injury"] == "PASS":
        token = "INTENSITY_SIGNAL_PASS_BOTH"
    elif decisions["scar"] == "PASS":
        token = "INTENSITY_SIGNAL_PASS_SCAR_ONLY"
    elif decisions["injury"] == "PASS":
        token = "INTENSITY_SIGNAL_PASS_INJURY_ONLY"
    else:
        token = "INTENSITY_SIGNAL_FAIL_BOTH"
    return {
        "created_at": utc_now(),
        "scar_decision": decisions["scar"],
        "injury_decision": decisions["injury"],
        "intensity_signal_decision": token,
        "gate_predicates": predicates,
        "status": "PASS",
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--result-root", type=Path, default=RESULT_ROOT)
    args = parser.parse_args()
    rows = read_csv(args.result_root / "oof_backbone_manifest.csv")
    case_rows: list[dict[str, Any]] = []
    summaries: list[dict[str, Any]] = []
    manifest_rows: list[dict[str, Any]] = []
    coef_rows: list[dict[str, Any]] = []
    for target in ("scar", "injury"):
        for context in ("GT_CONTEXT", "DEPLOYABLE_CONTEXT"):
            for model in ("raw", "rank_composite"):
                for train_center, test_center in (("CenterB", "CenterC"), ("CenterC", "CenterB")):
                    print(f"intensity_fit_start target={target} context={context} model={model} direction={train_center}->{test_center}", flush=True)
                    crows, summary, extra = fit_transfer(rows, train_center=train_center, test_center=test_center, target=target, context=context, model=model)
                    print(f"intensity_fit_done target={target} context={context} model={model} direction={train_center}->{test_center}", flush=True)
                    case_rows.extend(crows)
                    summaries.append(summary)
                    manifest_rows.extend([r for r in extra if "feature_names" in r])
                    coef_rows.extend([r for r in extra if "coefficient" in r])

    # Secondary center-stratified five-fold descriptive probe, using deployable rank composite.
    secondary: list[dict[str, Any]] = []
    by_center = defaultdict(list)
    for row in rows:
        by_center[row["center"]].append(row["case_id"])
    folds = []
    for fold_id in range(5):
        fold_cases = []
        for center in sorted(by_center):
            fold_cases.extend(sorted(by_center[center])[fold_id::5])
        folds.append(set(fold_cases))
    for target in ("scar", "injury"):
        for fold_id, test_set in enumerate(folds):
            train_centers = "CenterB+CenterC"
            test_rows = [r for r in rows if r["case_id"] in test_set]
            train_rows = [r for r in rows if r["case_id"] not in test_set]
            tmp_rows = [{**r, "center": "TRAIN"} for r in train_rows] + [{**r, "center": "TEST"} for r in test_rows]
            print(f"intensity_secondary_start target={target} fold={fold_id}", flush=True)
            crows, summary, _extra = fit_transfer(tmp_rows, train_center="TRAIN", test_center="TEST", target=target, context="DEPLOYABLE_CONTEXT", model="rank_composite")
            print(f"intensity_secondary_done target={target} fold={fold_id}", flush=True)
            secondary.append({**summary, "secondary_fold": fold_id, "train_center": train_centers, "test_center": "center_stratified_heldout"})
    write_csv(args.result_root / "intensity_casewise_metrics.csv", case_rows)
    write_csv(args.result_root / "intensity_transfer_summary.csv", summaries + secondary)
    context_rows = []
    for target in ("scar", "injury"):
        for direction in ("CenterB->CenterC", "CenterC->CenterB"):
            gt = next(r for r in summaries if r["target"] == target and r["direction"] == direction and r["context"] == "GT_CONTEXT" and r["probe_model"] == "rank_composite")
            dep = next(r for r in summaries if r["target"] == target and r["direction"] == direction and r["context"] == "DEPLOYABLE_CONTEXT" and r["probe_model"] == "rank_composite")
            raw = next(r for r in summaries if r["target"] == target and r["direction"] == direction and r["context"] == "DEPLOYABLE_CONTEXT" and r["probe_model"] == "raw")
            context_rows.append(
                {
                    "target": target,
                    "direction": direction,
                    "gt_macro_case_AUROC": gt["macro_case_AUROC"],
                    "deployable_macro_case_AUROC": dep["macro_case_AUROC"],
                    "deployable_minus_gt_AUROC": float(dep["macro_case_AUROC"]) - float(gt["macro_case_AUROC"]),
                    "rank_minus_raw_AUROC": float(dep["macro_case_AUROC"]) - float(raw["macro_case_AUROC"]),
                }
            )
    write_csv(args.result_root / "intensity_context_comparison.csv", context_rows)
    write_csv(args.result_root / "intensity_feature_manifest.csv", manifest_rows)
    write_json(
        args.result_root / "intensity_feature_manifest.json",
        {
            "created_at": utc_now(),
            "feature_rows": manifest_rows,
            "status": "PASS" if manifest_rows else "FAIL",
        },
    )
    write_csv(args.result_root / "intensity_probe_coefficients.csv", coef_rows)
    receipt = gate_receipt(summaries)
    receipt["inputs"] = {
        "oof_manifest_sha256": sha256_file(args.result_root / "oof_backbone_manifest.csv"),
        "feature_cache_manifest_sha256": sha256_file(args.result_root / "feature_cache_manifest.csv"),
    }
    write_json(args.result_root / "intensity_signal_receipt.json", receipt)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
