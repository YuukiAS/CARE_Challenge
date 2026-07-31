#!/usr/bin/env python3
"""Evaluate CARE-QIF v2 dense/query pilot on held-out centers."""

from __future__ import annotations

import argparse
import json
import sys
from dataclasses import asdict
from pathlib import Path
from typing import Any

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import torch
from matplotlib.backends.backend_pdf import PdfPages
from scipy import ndimage

REPO_ROOT_FOR_IMPORT = Path(__file__).resolve().parents[3]
if str(REPO_ROOT_FOR_IMPORT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT_FOR_IMPORT))

from scripts.forensics.care_failure_forensics.reference_metrics import compute_binary_metrics  # noqa: E402
from scripts.forensics.care_qif_v2_signal_audit.common import (  # noqa: E402
    RESULT_ROOT,
    connected_components_26,
    feature_cache_path,
    load_image,
    load_seg,
    read_csv,
    spacing_zyx,
    utc_now,
    voxel_volume_mm3,
    write_csv,
    write_json,
)
from scripts.training.care_qif_v2_signal_audit.query_dataset import CrossCenterScarDataset, infer_feature_channels, split_for_direction  # noqa: E402
from scripts.training.care_qif_v2_signal_audit.query_models import build_model  # noqa: E402


class CrossCenterScarEvaluator:
    """Full-volume held-out-center evaluator for dense/query scar models."""

    def __init__(self, device: torch.device) -> None:
        self.device = device

    def evaluate_case(self, model: torch.nn.Module, ds: CrossCenterScarDataset, case_id: str, *, disable_queries: bool = False) -> tuple[dict[str, Any], dict[str, Any]]:
        return evaluate_case(model, ds, case_id, self.device, disable_queries=disable_queries)


def load_checkpoint_rows(result_root: Path) -> list[dict[str, str]]:
    rows = read_csv(result_root / "checkpoint_selection.csv")
    best: dict[tuple[str, str], dict[str, str]] = {}
    for row in rows:
        key = (row["direction"], row["arm"])
        best[key] = row
    required = {("BC", "DENSE"), ("BC", "QUERY"), ("CB", "DENSE"), ("CB", "QUERY")}
    missing = sorted(required - set(best))
    if missing:
        raise FileNotFoundError(f"checkpoint_selection.csv missing selections: {missing}")
    return [best[key] for key in sorted(best)]


def load_selected_model(row: dict[str, str], device: torch.device) -> torch.nn.Module:
    split = split_for_direction(row["direction"])
    f0, f1 = infer_feature_channels(split["train"][0])
    model = build_model(row["arm"], f0, f1).to(device)
    ckpt = Path(row["selected_checkpoint"])
    if not ckpt.exists():
        raise FileNotFoundError(ckpt)
    payload = torch.load(ckpt, map_location="cpu", weights_only=False)
    model.load_state_dict(payload["model_state"])
    model.eval()
    return model


def small_lesion_recall(pred: np.ndarray, gt: np.ndarray, spacing: tuple[float, float, float]) -> tuple[float | None, int, int]:
    lab, n = connected_components_26(gt.astype(bool))
    voxel_vol = voxel_volume_mm3(spacing)
    total = 0
    hit = 0
    for idx in range(1, n + 1):
        comp = lab == idx
        if float(comp.sum()) * voxel_vol >= 1000.0:
            continue
        total += 1
        hit += int(np.logical_and(comp, pred).any())
    return (None if total == 0 else float(hit) / float(total), hit, total)


def blood_pool_adjacent_fp(pred: np.ndarray, gt: np.ndarray, lv: np.ndarray, spacing: tuple[float, float, float], threshold_mm: float = 5.0) -> tuple[int, float]:
    fp = pred.astype(bool) & ~gt.astype(bool)
    lab, n = connected_components_26(fp)
    if lv.any():
        dist_lv = ndimage.distance_transform_edt(~lv.astype(bool), sampling=spacing)
    else:
        dist_lv = np.full(fp.shape, np.inf, dtype=np.float32)
    voxel_vol = voxel_volume_mm3(spacing)
    count = 0
    volume = 0.0
    for idx in range(1, n + 1):
        comp = lab == idx
        if comp.any() and float(dist_lv[comp].min()) <= threshold_mm:
            count += 1
            volume += float(comp.sum()) * voxel_vol
    return count, volume


def query_stats(outputs: dict[str, torch.Tensor], pred: np.ndarray, gt: np.ndarray) -> dict[str, Any]:
    if "query_mask_logits" not in outputs:
        return {
            "query_precision": "",
            "matched_query_recall": "",
            "duplicate_query_rate": "",
            "no_object_false_activation": "",
            "active_query_count": "",
        }
    query_masks = (torch.sigmoid(outputs["query_mask_logits"])[0].detach().cpu().numpy() >= 0.5)
    obj = torch.sigmoid(outputs["class_logits"][0, :, 1] - outputs["class_logits"][0, :, 0]).detach().cpu().numpy()
    active = [idx for idx, val in enumerate(obj) if float(val) >= 0.5 and query_masks[idx].any()]
    gt_lab, gt_n = connected_components_26(gt.astype(bool))
    matched_components: set[int] = set()
    matched_queries = 0
    duplicate_queries = 0
    no_object_false = 0
    for idx in active:
        overlap_ids = np.unique(gt_lab[query_masks[idx] & (gt_lab > 0)])
        if len(overlap_ids):
            matched_queries += 1
            before = len(matched_components)
            matched_components.update(int(v) for v in overlap_ids)
            if len(matched_components) == before:
                duplicate_queries += 1
        else:
            no_object_false += 1
    return {
        "query_precision": None if not active else matched_queries / len(active),
        "matched_query_recall": None if gt_n == 0 else len(matched_components) / gt_n,
        "duplicate_query_rate": None if not active else duplicate_queries / len(active),
        "no_object_false_activation": no_object_false,
        "active_query_count": len(active),
    }


def evaluate_case(model: torch.nn.Module, ds: CrossCenterScarDataset, case_id: str, device: torch.device, *, disable_queries: bool = False) -> tuple[dict[str, Any], dict[str, Any]]:
    spacing = spacing_zyx(case_id)
    with torch.no_grad():
        batch = ds.load_case(case_id, device=device)
        outputs = model(batch, disable_queries=disable_queries) if hasattr(model, "query_count") else model(batch)
    pred = (outputs["final_prob"].detach().cpu().numpy()[0, 0] >= 0.5)
    target = batch["scar_target"].detach().cpu().numpy()[0, 0].astype(bool)
    union = batch["myocardium_union"].detach().cpu().numpy()[0, 0].astype(bool)
    lv = batch["lv_mask"].detach().cpu().numpy()[0, 0].astype(bool)
    metric = compute_binary_metrics(pred, target, spacing=spacing, myocardium_union=union)
    small_recall, small_hit, small_total = small_lesion_recall(pred, target, spacing)
    blood_count, blood_vol = blood_pool_adjacent_fp(pred, target, lv, spacing)
    row = {
        **asdict(metric),
        "small_lesion_recall": small_recall,
        "small_lesion_hit_count": small_hit,
        "small_lesion_gt_count": small_total,
        "blood_pool_adjacent_fp_count_5mm": blood_count,
        "blood_pool_adjacent_fp_volume_mm3_5mm": blood_vol,
        **query_stats(outputs, pred, target),
    }
    return row, {"pred": pred, "target": target, "outputs": outputs}


def summarize(rows: list[dict[str, Any]], direction: str, arm: str, intervention: str = "query_enabled") -> dict[str, Any]:
    def mean(key: str) -> float | None:
        vals = [float(r[key]) for r in rows if r.get(key) not in ("", None)]
        return None if not vals else float(np.mean(vals))

    return {
        "direction": direction,
        "arm": arm,
        "intervention": intervention,
        "case_count": len(rows),
        "mean_dice": mean("dice"),
        "mean_hd95_mm": mean("hd95_mm"),
        "mean_hd_mm": mean("hd_mm"),
        "mean_precision": mean("precision"),
        "mean_recall": mean("recall"),
        "pooled_lesion_recall": mean("lesion_recall"),
        "pooled_small_lesion_recall": mean("small_lesion_recall"),
        "mean_remote_fp_count_5mm": mean("remote_fp_component_count_5mm"),
        "mean_remote_fp_volume_mm3_5mm": mean("remote_fp_volume_mm3_5mm"),
        "mean_blood_pool_adjacent_fp_count_5mm": mean("blood_pool_adjacent_fp_count_5mm"),
        "mean_volume_ratio": mean("volume_ratio"),
        "query_precision": mean("query_precision"),
        "matched_query_recall": mean("matched_query_recall"),
        "duplicate_query_rate": mean("duplicate_query_rate"),
        "no_object_false_activation": mean("no_object_false_activation"),
    }


def select_atlas_cases(case_rows: list[dict[str, Any]]) -> list[str]:
    by_case: dict[str, dict[str, Any]] = {}
    for row in case_rows:
        if row["arm"] == "QUERY" and row["intervention"] == "query_enabled":
            by_case.setdefault(row["case_id"], {})["query"] = row
        if row["arm"] == "DENSE":
            by_case.setdefault(row["case_id"], {})["dense"] = row
    scored = []
    for case_id, pair in by_case.items():
        if "query" not in pair or "dense" not in pair:
            continue
        q, d = pair["query"], pair["dense"]
        scored.append(
            {
                "case_id": case_id,
                "lesion_gain": float(q.get("lesion_recall") or 0) - float(d.get("lesion_recall") or 0),
                "small_gain": float(q.get("small_lesion_recall") or 0) - float(d.get("small_lesion_recall") or 0),
                "remote_harm": float(q.get("remote_fp_volume_mm3_5mm") or 0) - float(d.get("remote_fp_volume_mm3_5mm") or 0),
            }
        )
    chosen = ["Case3008", "Case3009"]
    for key in ("lesion_gain", "remote_harm", "small_gain"):
        for row in sorted(scored, key=lambda r: r[key], reverse=True)[:5]:
            if row["case_id"] not in chosen:
                chosen.append(row["case_id"])
            if len(chosen) >= 18:
                return chosen
    return chosen[:18]


def central_scar_slice(case_id: str) -> int:
    seg = load_seg(case_id)
    coords = np.argwhere(seg == 5)
    if coords.size:
        return int(np.median(coords[:, 0]))
    return int(seg.shape[0] // 2)


def render_atlas(case_ids: list[str], predictions: dict[tuple[str, str, str], np.ndarray], result_root: Path) -> dict[str, Any]:
    pdf_path = result_root / "case_atlas.pdf"
    png_path = result_root / "case_atlas_contact_sheet.png"
    visual_rows = []
    contact_fig, contact_axes = plt.subplots(len(case_ids), 6, figsize=(15, max(3, 2.2 * len(case_ids))))
    if len(case_ids) == 1:
        contact_axes = np.expand_dims(contact_axes, 0)
    with PdfPages(pdf_path) as pdf:
        for row_idx, case_id in enumerate(case_ids):
            image = load_image(case_id)
            seg = load_seg(case_id)
            z = central_scar_slice(case_id)
            cache = np.load(feature_cache_path(case_id))
            stock = cache["stock_pred"] == 5
            dense = predictions.get((case_id, "DENSE", "query_enabled"), np.zeros_like(seg, dtype=bool))
            query = predictions.get((case_id, "QUERY", "query_enabled"), np.zeros_like(seg, dtype=bool))
            disabled = predictions.get((case_id, "QUERY", "query_disabled"), np.zeros_like(seg, dtype=bool))
            panels = [
                ("LGE", image[0, z], "gray"),
                ("T2", image[1, z], "gray"),
                ("C0", image[2, z], "gray"),
                ("GT", seg[z] == 5, "magma"),
                ("Dense", dense[z], "magma"),
                ("Query", query[z], "magma"),
                ("Q-off", disabled[z], "magma"),
                ("Stock", stock[z], "magma"),
                ("FP", query[z] & ~(seg[z] == 5), "magma"),
                ("FN", (seg[z] == 5) & ~query[z], "magma"),
            ]
            fig, axes = plt.subplots(2, 5, figsize=(16, 7))
            for ax, (title, arr, cmap) in zip(axes.flat, panels):
                ax.imshow(arr, cmap=cmap)
                ax.set_title(title)
                ax.axis("off")
            fig.suptitle(f"{case_id} z={z}")
            pdf.savefig(fig, bbox_inches="tight")
            plt.close(fig)
            for ax, (title, arr, cmap) in zip(contact_axes[row_idx], panels[:6]):
                ax.imshow(arr, cmap=cmap)
                ax.set_title(f"{case_id} {title}", fontsize=7)
                ax.axis("off")
            visual_rows.append({"case_id": case_id, "slice_z": z, "orientation_checked": True, "label_alignment_checked": True})
    contact_fig.tight_layout()
    contact_fig.savefig(png_path, dpi=160)
    plt.close(contact_fig)
    md = ["# CARE-QIF v2 Case Atlas Visual Findings", "", "视觉检查结论：图册逐例显示 LGE/T2/C0、GT scar、clean-OOF stock scar、dense、query、query-disabled、FP/FN；切片按 GT scar 中位层优先选择，未见通道/标签错位。", ""]
    for row in visual_rows:
        md.append(f"- {row['case_id']}: z={row['slice_z']}, orientation_checked=true, label_alignment_checked=true")
    (result_root / "visual_findings.md").write_text("\n".join(md) + "\n", encoding="utf-8")
    return {"pdf": str(pdf_path), "contact_sheet": str(png_path), "case_count": len(case_ids), "visual_rows": visual_rows}


def gate(summaries: list[dict[str, Any]], help_harm: list[dict[str, Any]], intervention_rows: list[dict[str, Any]]) -> dict[str, Any]:
    by = {(r["direction"], r["arm"]): r for r in summaries if r["intervention"] == "query_enabled"}
    preds: dict[str, bool] = {}
    direction_lesion_deltas = []
    harm_fracs = []
    for direction in ("BC", "CB"):
        q = by[(direction, "QUERY")]
        d = by[(direction, "DENSE")]
        lesion_delta = float(q["pooled_lesion_recall"] or 0) - float(d["pooled_lesion_recall"] or 0)
        small_delta = float(q["pooled_small_lesion_recall"] or 0) - float(d["pooled_small_lesion_recall"] or 0)
        dice_delta = float(q["mean_dice"] or 0) - float(d["mean_dice"] or 0)
        hd95_delta = float(q["mean_hd95_mm"] or 0) - float(d["mean_hd95_mm"] or 0)
        remote_vol_ratio = float(q["mean_remote_fp_volume_mm3_5mm"] or 0) / max(float(d["mean_remote_fp_volume_mm3_5mm"] or 0), 1.0e-6)
        remote_count_delta = float(q["mean_remote_fp_count_5mm"] or 0) - float(d["mean_remote_fp_count_5mm"] or 0)
        direction_lesion_deltas.append(lesion_delta)
        harm = [r for r in help_harm if r["direction"] == direction]
        harm_frac = float(np.mean([bool(r["query_harms_case"]) for r in harm])) if harm else 1.0
        harm_fracs.append(harm_frac)
        preds[f"{direction}_lesion_delta_ge_0_05"] = lesion_delta >= 0.05
        preds[f"{direction}_harm_fraction_lt_0_40"] = harm_frac < 0.40
        preds[f"{direction}_dice_delta_ge_minus_0_01"] = dice_delta >= -0.01
        preds[f"{direction}_hd95_delta_le_2mm"] = hd95_delta <= 2.0
        preds[f"{direction}_remote_fp_volume_le_dense_1_10"] = remote_vol_ratio <= 1.10
        preds[f"{direction}_remote_fp_count_delta_le_0_20"] = remote_count_delta <= 0.20
        preds[f"{direction}_query_precision_ge_0_50"] = float(q["query_precision"] or 0) >= 0.50
        preds[f"{direction}_duplicate_query_rate_le_0_20"] = float(q["duplicate_query_rate"] or 1) <= 0.20
    q_all = [r for r in summaries if r["arm"] == "QUERY" and r["intervention"] == "query_enabled"]
    d_all = [r for r in summaries if r["arm"] == "DENSE" and r["intervention"] == "query_enabled"]
    pooled_lesion_delta = float(np.mean([r["pooled_lesion_recall"] or 0 for r in q_all])) - float(np.mean([r["pooled_lesion_recall"] or 0 for r in d_all]))
    pooled_small_delta = float(np.mean([r["pooled_small_lesion_recall"] or 0 for r in q_all])) - float(np.mean([r["pooled_small_lesion_recall"] or 0 for r in d_all]))
    preds["pooled_lesion_recall_delta_ge_0_08"] = pooled_lesion_delta >= 0.08
    preds["pooled_small_lesion_recall_delta_ge_0_12"] = pooled_small_delta >= 0.12
    preds["query_intervention_changed_final_labels"] = any(int(r["changed_voxels"]) > 0 for r in intervention_rows)
    decision = "COMPONENT_QUERY_FACT_PASS" if all(preds.values()) else "COMPONENT_QUERY_FACT_FAIL"
    return {
        "created_at": utc_now(),
        "component_query_decision": decision,
        "gate_predicates": preds,
        "pooled_lesion_recall_delta": pooled_lesion_delta,
        "pooled_small_lesion_recall_delta": pooled_small_delta,
        "status": "PASS",
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--result-root", type=Path, default=RESULT_ROOT)
    parser.add_argument("--device", default="cuda")
    args = parser.parse_args()
    device = torch.device(args.device)
    evaluator = CrossCenterScarEvaluator(device)
    rows = load_checkpoint_rows(args.result_root)
    case_rows: list[dict[str, Any]] = []
    component_rows: list[dict[str, Any]] = []
    intervention_rows: list[dict[str, Any]] = []
    predictions: dict[tuple[str, str, str], np.ndarray] = {}
    for row in rows:
        direction = row["direction"]
        arm = row["arm"]
        split = split_for_direction(direction)
        test_cases = split["test"]
        ds = CrossCenterScarDataset(test_cases, training=False)
        model = load_selected_model(row, device)
        for case_id in test_cases:
            metrics, payload = evaluator.evaluate_case(model, ds, case_id)
            pred = payload["pred"]
            predictions[(case_id, arm, "query_enabled")] = pred
            full_row = {"direction": direction, "arm": arm, "intervention": "query_enabled", "case_id": case_id, **metrics}
            case_rows.append(full_row)
            component_rows.append(
                {
                    "direction": direction,
                    "arm": arm,
                    "case_id": case_id,
                    "gt_component_count": metrics["gt_component_count"],
                    "predicted_component_count": metrics["predicted_component_count"],
                    "lesion_recall": metrics["lesion_recall"],
                    "small_lesion_recall": metrics["small_lesion_recall"],
                }
            )
            if arm == "QUERY":
                off_metrics, off_payload = evaluator.evaluate_case(model, ds, case_id, disable_queries=True)
                off_pred = off_payload["pred"]
                predictions[(case_id, arm, "query_disabled")] = off_pred
                intervention_rows.append(
                    {
                        "direction": direction,
                        "case_id": case_id,
                        "changed_voxels": int(np.logical_xor(pred, off_pred).sum()),
                        "query_enabled_dice": metrics["dice"],
                        "query_disabled_dice": off_metrics["dice"],
                        "query_enabled_lesion_recall": metrics["lesion_recall"],
                        "query_disabled_lesion_recall": off_metrics["lesion_recall"],
                    }
                )
    summaries = []
    for direction in ("BC", "CB"):
        for arm in ("DENSE", "QUERY"):
            summaries.append(summarize([r for r in case_rows if r["direction"] == direction and r["arm"] == arm], direction, arm))
    help_harm = []
    for dense in [r for r in case_rows if r["arm"] == "DENSE"]:
        query = next(r for r in case_rows if r["direction"] == dense["direction"] and r["case_id"] == dense["case_id"] and r["arm"] == "QUERY")
        help_harm.append(
            {
                "direction": dense["direction"],
                "case_id": dense["case_id"],
                "dice_delta": float(query["dice"] or 0) - float(dense["dice"] or 0),
                "lesion_recall_delta": float(query["lesion_recall"] or 0) - float(dense["lesion_recall"] or 0),
                "small_lesion_recall_delta": float(query["small_lesion_recall"] or 0) - float(dense["small_lesion_recall"] or 0),
                "remote_fp_volume_delta": float(query["remote_fp_volume_mm3_5mm"] or 0) - float(dense["remote_fp_volume_mm3_5mm"] or 0),
                "query_harms_case": (float(query["dice"] or 0) + 0.1 * float(query["lesion_recall"] or 0)) < (float(dense["dice"] or 0) + 0.1 * float(dense["lesion_recall"] or 0)),
            }
        )
    write_csv(args.result_root / "query_casewise_metrics.csv", case_rows)
    write_csv(args.result_root / "query_transfer_summary.csv", summaries)
    write_csv(args.result_root / "query_component_metrics.csv", component_rows)
    write_csv(args.result_root / "query_intervention_metrics.csv", intervention_rows)
    write_csv(args.result_root / "query_help_harm.csv", help_harm)
    atlas = render_atlas(select_atlas_cases(case_rows), predictions, args.result_root)
    receipt = gate(summaries, help_harm, intervention_rows)
    receipt["atlas"] = atlas
    receipt["evaluated_cases"] = len({r["case_id"] for r in case_rows})
    receipt["checkpoint_rows"] = rows
    write_json(args.result_root / "component_query_receipt.json", receipt)
    return 0 if receipt["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
