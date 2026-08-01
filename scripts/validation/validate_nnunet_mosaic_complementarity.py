#!/usr/bin/env python3
"""Strict validator for frozen nnU-Net/MoSAIC complementarity closure."""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Any

import pandas as pd


TASK_KEY = "20260801_care_nnunet_mosaic_complementarity_closure"
RESULT_DIR = Path("results") / TASK_KEY
FORBIDDEN_VALIDATION_WORDS = re.compile(
    r"\b(help|harm|rescue|better|candidate)\b", re.IGNORECASE
)


REQUIRED_FILES = [
    "oof_complementarity_casewise.csv",
    "oof_complementarity_bucket_summary.csv",
    "oof_center_subgroup_summary.csv",
    "oof_modality_subgroup_summary.csv",
    "oof_case_oracle_bounds.csv",
    "m10_diagnostic_casewise.csv",
    "m10_diagnostic_bucket_summary.csv",
    "m0_to_m10_recipe_transition.csv",
    "validation_disagreement_casewise.csv",
    "validation_disagreement_summary.json",
    "validation_frozen_inference_receipt.json",
    "hard_case_bucket_index.csv",
    "hard_case_atlas.md",
    "hard_case_visual_receipt.json",
    "complementarity_interpretation.md",
    "controller_context.json",
    "controller_ledger.csv",
    "controller_bootstrap_snapshot.md",
    "implementation_snapshot.md",
    "mapper_report_draft.md",
    "architecture_delta_draft.md",
    "mapper_report_final.md",
    "architecture_delta_final.md",
    "finalizer_state.json",
    "completion_check.md",
    "MANIFEST.md",
]


def fail(known_bad: list[dict[str, Any]], name: str, detail: str) -> None:
    known_bad.append({"check": name, "status": "FAIL", "detail": detail})


def pass_(known_bad: list[dict[str, Any]], name: str, detail: str = "PASS") -> None:
    known_bad.append({"check": name, "status": "PASS", "detail": detail})


def read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def validate(result_dir: Path) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    checks: list[dict[str, Any]] = []
    missing = [f for f in REQUIRED_FILES if not (result_dir / f).exists()]
    if missing:
        fail(checks, "required_files", f"missing {missing}")
    else:
        pass_(checks, "required_files")

    oof = pd.read_csv(result_dir / "oof_complementarity_casewise.csv")
    if set(oof["pathology"]) != {"scar", "pure_edema"}:
        fail(checks, "pathologies", f"unexpected {sorted(oof['pathology'].unique())}")
    else:
        pass_(checks, "pathologies")
    if "lesion_union" in set(oof["pathology"]):
        fail(checks, "no_lesion_union", "lesion_union present")
    else:
        pass_(checks, "no_lesion_union")
    scar_n = oof[oof["pathology"] == "scar"]["case_id"].nunique()
    edema_n = oof[oof["pathology"] == "pure_edema"]["case_id"].nunique()
    if scar_n != 220 or edema_n != 80:
        fail(checks, "population_counts", f"scar={scar_n}, pure_edema={edema_n}")
    else:
        pass_(checks, "population_counts", "scar=220 pure_edema=80")
    dup = int(oof.duplicated(["case_id", "pathology"]).sum())
    if dup:
        fail(checks, "unique_case_pathology", f"duplicates={dup}")
    else:
        pass_(checks, "unique_case_pathology")
    if not oof[oof["pathology"] == "pure_edema"]["T2_present"].all():
        fail(checks, "pure_edema_t2_denominator", "no-T2 row in pure edema")
    else:
        pass_(checks, "pure_edema_t2_denominator")
    if set(oof["nnunet_model_id"]) != {"nnunet_oof"} or set(oof["mosaic_model_id"]) != {
        "mosaic_clean_oof"
    }:
        fail(checks, "oof_model_ids", "wrong OOF model id")
    else:
        pass_(checks, "oof_model_ids")
    allowed_buckets = {
        "BOTH_FAIL",
        "BOTH_GOOD",
        "MOSAIC_RESCUES",
        "NNUNET_PROTECTS",
        "NEAR_TIE",
        "MIXED_TRADEOFF",
    }
    if not set(oof["bucket"]).issubset(allowed_buckets):
        fail(checks, "oof_bucket_names", f"bad {set(oof['bucket']) - allowed_buckets}")
    else:
        pass_(checks, "oof_bucket_names")

    bucket_summary = pd.read_csv(result_dir / "oof_complementarity_bucket_summary.csv")
    for pathology, expected in [("scar", 220), ("pure_edema", 80)]:
        got = int(
            bucket_summary[
                (bucket_summary["pathology"] == pathology)
                & (bucket_summary["population"] == "all_cases")
            ]["case_count"].sum()
        )
        if got != expected:
            fail(checks, f"bucket_sum_{pathology}", f"expected={expected} got={got}")
        else:
            pass_(checks, f"bucket_sum_{pathology}")

    oracle = pd.read_csv(result_dir / "oof_case_oracle_bounds.csv")
    if (oracle["selector_status"] == "CASE_ORACLE_UPPER_BOUND_ONLY_NOT_DEPLOYABLE").all():
        pass_(checks, "oracle_not_selector")
    else:
        fail(checks, "oracle_not_selector", "oracle status drifted")

    m10 = pd.read_csv(result_dir / "m10_diagnostic_casewise.csv")
    m10_rows = m10[m10["mosaic_stage_id"] == "M10"]
    if m10_rows["case_id"].nunique() != 80:
        fail(checks, "m10_case_count", str(m10_rows["case_id"].nunique()))
    else:
        pass_(checks, "m10_case_count")
    if not m10_rows["trained_on_case_possible"].astype(bool).all():
        fail(checks, "m10_trained_flag", "missing trained_on_case_possible")
    else:
        pass_(checks, "m10_trained_flag")
    if not m10_rows["not_valid_for_generalization_claim"].astype(bool).all():
        fail(checks, "m10_generalization_boundary", "missing boundary flag")
    else:
        pass_(checks, "m10_generalization_boundary")
    if set(m10_rows["evidence_tier"]) != {"IN_SAMPLE_FULL_RECIPE_DIAGNOSTIC"}:
        fail(checks, "m10_evidence_tier", str(set(m10_rows["evidence_tier"])))
    else:
        pass_(checks, "m10_evidence_tier")

    validation = pd.read_csv(result_dir / "validation_disagreement_casewise.csv")
    if validation["case_id"].tolist() != [f"Case10{i:02d}" for i in range(1, 16)]:
        fail(checks, "validation_case_set", ",".join(validation["case_id"].tolist()))
    else:
        pass_(checks, "validation_case_set")
    if not validation["geometry_equality"].astype(bool).all():
        fail(checks, "validation_geometry", "non-equal geometry")
    else:
        pass_(checks, "validation_geometry")
    validation_text = "\n".join(
        [
            (result_dir / "validation_disagreement_casewise.csv").read_text(
                encoding="utf-8"
            ),
            (result_dir / "validation_disagreement_summary.json").read_text(
                encoding="utf-8"
            ),
            (result_dir / "validation_frozen_inference_receipt.json").read_text(
                encoding="utf-8"
            ),
        ]
    )
    forbidden = sorted(set(m.group(0).lower() for m in FORBIDDEN_VALIDATION_WORDS.finditer(validation_text)))
    if forbidden:
        fail(checks, "validation_no_gt_words", f"forbidden words {forbidden}")
    else:
        pass_(checks, "validation_no_gt_words")
    receipt = read_json(result_dir / "validation_frozen_inference_receipt.json")
    if receipt.get("case_count") == 15 and receipt.get("new_gpu_job_submitted") is False:
        pass_(checks, "validation_reuse_receipt")
    else:
        fail(checks, "validation_reuse_receipt", json.dumps(receipt, sort_keys=True)[:500])

    context = read_json(result_dir / "controller_context.json")
    frozen = context.get("frozen_boundaries", {})
    if any(
        frozen.get(k) is not False
        for k in [
            "new_training_authorized",
            "threshold_tuning_authorized",
            "case_selector_authorized",
            "validation_upload_authorized",
            "docker_upload_authorized",
            "hosted_metric_claim_authorized",
        ]
    ):
        fail(checks, "frozen_boundaries", json.dumps(frozen, sort_keys=True))
    else:
        pass_(checks, "frozen_boundaries")
    if len(context.get("source_hashes", {})) < 10:
        fail(checks, "source_hashes", "missing bound source hashes")
    else:
        pass_(checks, "source_hashes")

    hard = pd.read_csv(result_dir / "hard_case_bucket_index.csv")
    if hard.empty:
        fail(checks, "hard_case_index", "empty")
    else:
        pass_(checks, "hard_case_index", f"rows={len(hard)}")

    failures = [c for c in checks if c["status"] != "PASS"]
    report = {
        "task_key": TASK_KEY,
        "result_dir": str(result_dir),
        "validator_status": "PASS" if not failures else "FAIL",
        "failures": failures,
        "checks": checks,
    }
    return report, checks


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--result_dir", type=Path, default=RESULT_DIR)
    parser.add_argument("--phase", default="final")
    args = parser.parse_args()
    report, checks = validate(args.result_dir)
    (args.result_dir / "strict_validator_report.json").write_text(
        json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    (args.result_dir / "known_bad_report.json").write_text(
        json.dumps(
            {
                "task_key": TASK_KEY,
                "known_bad_fixture_policy": "embedded hard checks",
                "checks": checks,
                "status": report["validator_status"],
            },
            indent=2,
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
    )
    print(json.dumps(report, indent=2, sort_keys=True))
    if report["validator_status"] != "PASS":
        raise SystemExit(1)


if __name__ == "__main__":
    main()
