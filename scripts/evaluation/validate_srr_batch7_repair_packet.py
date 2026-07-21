#!/usr/bin/env python3
"""Fail-closed validator for the Batch7 mechanism-closure repair packet."""

from __future__ import annotations

import argparse
import csv
import json
import sys
from pathlib import Path
from typing import Any

import yaml
import torch

REPO_ROOT = Path(__file__).resolve().parents[2]
MONITOR_TOKENS = ("NEEDS_MONITOR", "PENDING_MONITOR", "JOB_SUBMITTED", "PENDING_PRIORITY", "RUNNING", "AWAITING_SACCT")
FORBIDDEN_TOKENS = ("placeholder", "copied_from_formal", "continuation_gate_or_final_intervention_placeholder")
REQUIRED_MEMORY_STATE_KEYS = (
    "cross_fitted_memory.positive_mu",
    "cross_fitted_memory.negative_mu",
    "cross_fitted_memory.positive_counts",
    "cross_fitted_memory.negative_counts",
    "cross_fitted_memory.positive_delta",
    "cross_fitted_memory.negative_delta",
)


def repo_path(raw: str | Path) -> Path:
    path = Path(raw)
    return path if path.is_absolute() else REPO_ROOT / path


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def write_json(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def text_contains(path: Path, tokens: tuple[str, ...]) -> list[str]:
    if not path.is_file():
        return []
    text = path.read_text(encoding="utf-8", errors="ignore")
    return [token for token in tokens if token in text]


def validate_packet(result_root: Path, cfg: dict[str, Any], *, final: bool) -> list[str]:
    errors: list[str] = []
    modes = [str(mode) for mode in cfg["intervention_execution"]["modes"]]
    required = [
        "intervention_runner_contract.json",
        "intervention_casewise_metrics.csv",
        "intervention_summary.csv",
        "intervention_prediction_manifest.csv",
        "proposal_refiner_metrics.csv",
        "source_arbiter_metrics.csv",
    ]
    required.extend(
        [
            "semantic_memory_manifest.json",
            "semantic_memory_category_counts.csv",
            "semantic_memory_tensor_hashes.csv",
            "semantic_memory_valid_masks.csv",
            "discovery_independence.csv",
        ]
        if final
        else []
    )
    for name in required:
        path = result_root / name
        if not path.is_file() or path.stat().st_size == 0:
            errors.append(f"missing_or_empty:{name}")
    for path in result_root.glob("*.csv"):
        for token in text_contains(path, FORBIDDEN_TOKENS):
            errors.append(f"forbidden_token:{path.name}:{token}")
    for path in [result_root / "completion_check.md", result_root / "controller_report.md", result_root / "finalizer_state.json"]:
        for token in text_contains(path, MONITOR_TOKENS):
            errors.append(f"monitor_token_in_completion:{path.name}:{token}")
    manifest_path = result_root / "intervention_prediction_manifest.csv"
    if manifest_path.is_file():
        rows = read_csv(manifest_path)
        expected_cases = int(cfg["intervention_execution"]["case_count"])
        by_mode: dict[str, list[dict[str, str]]] = {mode: [] for mode in modes}
        for row in rows:
            by_mode.setdefault(row.get("mode", ""), []).append(row)
            pred = repo_path(row.get("prediction_path", ""))
            if not pred.is_file():
                errors.append(f"missing_prediction:{row.get('mode')}:{row.get('case_id')}")
            if row.get("prediction_sha256") and row.get("output_sha256_from_inference") and row["prediction_sha256"] != row["output_sha256_from_inference"]:
                errors.append(f"prediction_hash_mismatch:{row.get('mode')}:{row.get('case_id')}")
        roots: dict[str, str] = {}
        hash_sets: dict[str, tuple[str, ...]] = {}
        for mode in modes:
            mode_rows = by_mode.get(mode, [])
            if len(mode_rows) != expected_cases:
                errors.append(f"mode_case_count:{mode}:{len(mode_rows)}!={expected_cases}")
                continue
            roots[mode] = str(mode_rows[0].get("prediction_root", ""))
            if any(row.get("prediction_root") != roots[mode] for row in mode_rows):
                errors.append(f"mode_multiple_prediction_roots:{mode}")
            hash_sets[mode] = tuple(sorted(str(row.get("prediction_sha256", "")) for row in mode_rows))
        if len(set(roots.values())) != len([root for root in roots.values() if root]):
            errors.append("shared_prediction_root_between_modes")
        equivalent = {tuple(pair) for pair in cfg["intervention_execution"].get("expected_equivalent_pairs", [])}
        equivalent |= {tuple(reversed(pair)) for pair in equivalent}
        for i, left in enumerate(modes):
            for right in modes[i + 1 :]:
                if left in hash_sets and right in hash_sets and hash_sets[left] == hash_sets[right] and (left, right) not in equivalent:
                    errors.append(f"identical_prediction_hash_sets_unexpected:{left}:{right}")
    casewise_path = result_root / "intervention_casewise_metrics.csv"
    if casewise_path.is_file():
        rows = read_csv(casewise_path)
        for mode in ("anchor_identity", "production_gate_closed"):
            selected = [row for row in rows if row.get("mode") == mode]
            if not selected:
                errors.append(f"missing_casewise_mode:{mode}")
            for row in selected:
                if int(float(row.get("changed_voxels_vs_anchor", "1") or 1)) != 0:
                    errors.append(f"identity_changed_voxels_nonzero:{mode}:{row.get('case_id')}:{row.get('pathology')}")
        required_delta_modes = {
            "proposal_only_gate_one",
            "refiner_only_gate_one",
            "learned_source_gate_one",
            "production_gate_one",
            "prototype_maps_off",
            "semantic_negative_memory_off",
            "no_anchor_diagnostic",
        }
        for mode in required_delta_modes:
            if not any(row.get("mode") == mode and row.get("dice_delta_vs_anchor") not in {"", None} for row in rows):
                errors.append(f"empty_required_metric_mode:{mode}")
    if (result_root / "semantic_memory_manifest.json").is_file():
        manifest = json.loads((result_root / "semantic_memory_manifest.json").read_text(encoding="utf-8"))
        if manifest.get("source_checkpoint_sha256") != cfg["source_checkpoints"]["batch7"]["sha256"]:
            errors.append("semantic_memory_wrong_checkpoint_sha")
        if int(manifest.get("source_case_count", -1)) != int(cfg["training_data"]["train_case_count"]):
            errors.append("semantic_memory_wrong_source_case_count")
        if manifest.get("validation_intersection"):
            errors.append("semantic_memory_validation_leakage")
        if int(manifest.get("deterministic_axis_random_repeat_formal_contribution", 1)) != 0:
            errors.append("semantic_memory_deterministic_formal_contribution")
        if not bool(manifest.get("no_t2_edema_memory_count_zero", False)):
            errors.append("semantic_memory_no_t2_edema_vectors_accepted")
        asset_path = repo_path(manifest.get("asset_path", ""))
        if not asset_path.is_file():
            errors.append("semantic_memory_asset_missing")
        else:
            asset = torch.load(asset_path, map_location="cpu", weights_only=False)
            state = dict(asset.get("model_memory_state", asset))
            missing = [key for key in REQUIRED_MEMORY_STATE_KEYS if key not in state]
            unexpected = [
                key
                for key, value in state.items()
                if not key.startswith(("cross_fitted_memory.", "scar_dictionary.", "edema_dictionary."))
                or not isinstance(value, torch.Tensor)
            ]
            if missing:
                errors.append(f"semantic_memory_asset_missing_required_state:{','.join(missing)}")
            if unexpected:
                errors.append(f"semantic_memory_asset_unexpected_state:{','.join(unexpected[:8])}")
    if (result_root / "semantic_memory_valid_masks.csv").is_file():
        rows = read_csv(result_root / "semantic_memory_valid_masks.csv")
        categories = {(row.get("pathology"), row.get("category")) for row in rows}
        for category in cfg["semantic_memory"]["scar_categories"]:
            if ("scar", category) not in categories:
                errors.append(f"missing_scar_semantic_category:{category}")
        for category in cfg["semantic_memory"]["edema_categories_t2_present_only"]:
            if ("edema", category) not in categories:
                errors.append(f"missing_edema_semantic_category:{category}")
    if (result_root / "discovery_independence.csv").is_file():
        rows = read_csv(result_root / "discovery_independence.csv")
        if not rows:
            errors.append("empty_discovery_independence")
        for row in rows:
            if float(row.get("discovery_logits_max_abs_delta", "inf") or "inf") > 1e-6:
                errors.append(f"discovery_anchor_invariance_fail:{row.get('case_id')}")
            if float(row.get("confirmation_logits_max_abs_delta", "0") or 0) <= 1e-5:
                errors.append(f"confirmation_anchor_sensitivity_fail:{row.get('case_id')}")
            if float(row.get("discovery_logits_abs_max", "0") or 0) <= 0:
                errors.append(f"discovery_logits_zero:{row.get('case_id')}")
    if (result_root / "gradient_authority.csv").is_file():
        rows = read_csv(result_root / "gradient_authority.csv")
        required = {
            ("scar", "scar_dictionary"),
            ("scar", "scar_evidence_head"),
            ("scar", "spatial_dictionary"),
            ("edema", "edema_dictionary"),
            ("edema", "edema_evidence_head"),
            ("edema", "spatial_dictionary"),
        }
        totals = {key: 0.0 for key in required}
        case_evidence: set[tuple[str, str, str, str]] = set()
        for row in rows:
            key = (str(row.get("pathology", "")), str(row.get("parameter_group", "")))
            if key in totals:
                totals[key] += float(row.get("grad_abs_sum", "0") or 0)
            case_evidence.add(
                (
                    str(row.get("pathology", "")),
                    str(row.get("case_id", "")),
                    str(row.get("case_t2_present", "")),
                    str(row.get("case_has_edema_label", "")),
                )
            )
        for key, value in totals.items():
            if value <= 0.0:
                errors.append(f"gradient_authority_zero:{key[0]}:{key[1]}")
        if not any(pathology == "edema" and t2_present == "True" and has_edema == "True" for pathology, _case, t2_present, has_edema in case_evidence):
            errors.append("gradient_authority_missing_t2_present_edema_case")
    intervention_root = repo_path(cfg["paths"]["intervention_root"])
    for mode in cfg["intervention_execution"].get("modes", []):
        manifest_path = intervention_root / str(mode) / "prediction_manifest.json"
        if not manifest_path.is_file():
            continue
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        asset_receipt = manifest.get("semantic_memory_asset", {})
        if asset_receipt:
            if asset_receipt.get("missing_required_memory_keys"):
                errors.append(f"inference_asset_missing_required:{mode}")
            if asset_receipt.get("invalid_asset_keys"):
                errors.append(f"inference_asset_invalid_keys:{mode}")
            if asset_receipt.get("shape_mismatch_keys"):
                errors.append(f"inference_asset_shape_mismatch:{mode}")
    return errors


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", default="configs/srr_production/myops_batch7_repair.yaml")
    parser.add_argument("--result-root", default="results/20260721_srr_batch7_mechanism_closure_repair")
    parser.add_argument("--known-bad-root", default="results/20260721_srr_batch7_upstream_candidate_quality")
    parser.add_argument("--final", action="store_true")
    parser.add_argument("--write-status", action="store_true")
    args = parser.parse_args()
    cfg = yaml.safe_load(repo_path(args.config).read_text(encoding="utf-8"))
    result_root = repo_path(args.result_root)
    errors = validate_packet(result_root, cfg, final=args.final)
    known_bad_errors = validate_packet(repo_path(args.known_bad_root), cfg, final=False) if args.known_bad_root else []
    known_bad_rejected = bool(known_bad_errors)
    if not known_bad_rejected:
        errors.append("known_bad_old_batch7_packet_not_rejected")
    status = {
        "status": "PASS" if not errors else "FAIL",
        "errors": errors,
        "known_bad_root": args.known_bad_root,
        "known_bad_rejected": known_bad_rejected,
        "known_bad_error_count": len(known_bad_errors),
        "known_bad_errors_sample": known_bad_errors[:16],
        "final_mode": bool(args.final),
    }
    if args.write_status:
        write_json(result_root / "validator_status.json", status)
        write_json(result_root / "intervention_known_bad_results.json", status)
        (result_root / "validator_semantics.md").write_text(
            "# Batch7 Repair Validator Semantics\n\n"
            "The validator fails closed on missing mode predictions, shared prediction roots, duplicate non-equivalent prediction hash sets, "
            "nonzero identity/gate-closed changes, placeholder/copied tokens, empty component metrics, semantic-memory leakage, "
            "deterministic formal memory contribution, and anchor-dependent discovery logits.\n",
            encoding="utf-8",
        )
    if errors:
        for error in errors:
            print(f"ERROR: {error}", file=sys.stderr)
        return 1
    print("Batch7 repair packet validator passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
