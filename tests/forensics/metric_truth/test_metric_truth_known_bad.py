from __future__ import annotations

import csv
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
VALIDATOR = ROOT / "scripts/forensics/metric_truth/validate_metric_truth.py"

BASE_CORE_IDS = [
    "D0_INNER_SELECT_STOCK_GT_SCAR",
    "D0_INNER_SELECT_STOCK_GT_PURE_EDEMA",
    "D1_INNER_SELECT_DECODER_RESET_SCAR",
    "D1_INNER_SELECT_DECODER_RESET_PURE_EDEMA",
    "D2_INNER_SELECT_TOP_TRAIN_SCAR",
    "D2_INNER_SELECT_TOP_TRAIN_PURE_EDEMA",
    "D3_INNER_SELECT_FULL_SHORT_FT_SCAR",
    "D3_INNER_SELECT_FULL_SHORT_FT_PURE_EDEMA",
    "NNUNET_CLEAN_OOF_SCAR_220",
    "NNUNET_CLEAN_OOF_PURE_EDEMA_T2_80",
    "MOSAIC_CLEAN_OOF_SCAR_220",
    "MOSAIC_CLEAN_OOF_PURE_EDEMA_T2_80",
    "PRISM_W3_OUTER_ONCE_SCAR",
    "PRISM_W3_OUTER_ONCE_INTERNAL_EDEMA_ZONE",
    "NNUNET_FOLD0_OUTER_COMPARATOR_SCAR",
    "NNUNET_FOLD0_OUTER_COMPARATOR_INTERNAL_EDEMA_ZONE",
    "MOSAIC_HOSTED_SCAR_20260706_USER_ATTESTED",
    "MOSAIC_HOSTED_EDEMA_20260706_USER_ATTESTED",
    "MOSAIC_HOSTED_CINEMYOPS_20260708_CLOSEST_FINAL_RECIPE",
]

TABLE_FIELDS = [
    "score_contract_id", "model_id", "model_role", "checkpoint_sha256", "prediction_sha256",
    "case_set_id", "case_count", "train_relation", "population", "pathology", "label_semantics",
    "metric", "value", "ci_if_available", "threshold", "decode", "source_path", "evidence_grade",
    "allowed_comparison_group", "forbidden_comparison_group",
]
OCC_FIELDS = [
    "score_id", "value", "source_path", "source_sha256", "source_row_or_key", "model_id",
    "checkpoint_sha256", "prediction_sha256", "case_set_id", "case_count", "train_case_relationship",
    "population_role", "pathology_object", "label_definition", "metric_name", "metric_implementation",
    "physical_spacing_used", "empty_gt_policy", "positive_gt_only", "threshold", "decode_rule", "is_hosted",
    "is_clean_oof", "is_train_on_case", "is_prediction_parity", "claim_allowed", "notes",
]
SHA = "a" * 64


def write_csv(path: Path, rows: list[dict[str, str]], fields: list[str]) -> None:
    with path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fields, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def make_packet(tmp_path: Path) -> Path:
    d = tmp_path / "packet"
    d.mkdir()
    rows = []
    occ = []
    for sid in BASE_CORE_IDS:
        pathology = "scar"
        label = "official scar; internal label 5"
        population = "clean OOF all 220 cases"
        relation = "held-out from fold checkpoint"
        allowed = "clean OOF"
        evidence = "SOURCE_BOUND"
        checkpoint = SHA
        prediction = SHA[:32]
        if "PURE_EDEMA" in sid or "EDEMA" in sid:
            pathology = "official pure edema"
            label = "official pure edema; internal label 4"
            population = "T2-present denominator 80"
        if "EDEMA_ZONE" in sid:
            pathology = "internal edema-zone"
            label = "internal edema-zone; labels 4 or 5"
            population = "internal diagnostic outer once"
        if "D0" in sid or "D1" in sid or "D2" in sid or "D3" in sid:
            population = "fold0 frozen inner-select 12 cases"
            if "PURE_EDEMA" in sid:
                population += "; official pure edema semantics T2-present denominator"
            allowed = "inner-select decoder-reset diagnostic"
        if "OUTER" in sid:
            population = "fold0 outer once 44 cases"
            allowed = "fold0 outer once diagnostic"
        if "HOSTED" in sid:
            population = "hosted validation hidden official case set; official pure edema semantics T2-present where evaluator-defined"
            allowed = "hosted leaderboard reference"
            checkpoint = "NOT_APPLICABLE_HOSTED_HIDDEN"
            prediction = "NOT_RECOMPUTABLE_FROM_LOCAL_PREDICTION"
            evidence = "PARTIAL_HOSTED_BIND"
        if "MOSAIC_CLEAN" in sid:
            relation = "held-out OOF"
        if "M2" in sid:
            relation = "train-on-case full-data"
        rows.append({
            "score_contract_id": sid, "model_id": sid.split("_")[0], "model_role": "diagnostic",
            "checkpoint_sha256": checkpoint, "prediction_sha256": prediction, "case_set_id": population,
            "case_count": "80" if "80" in population else ("44" if "44" in population else ("12" if "12" in population else "220")),
            "train_relation": relation, "population": population, "pathology": pathology, "label_semantics": label,
            "metric": "Dice; reference evaluator; physical spacing=available for HD95 rows", "value": "0.5",
            "ci_if_available": "", "threshold": "fixed", "decode": "fixed", "source_path": "source.csv",
            "evidence_grade": evidence, "allowed_comparison_group": allowed,
            "forbidden_comparison_group": "D0 inner-select GT Dice vs clean OOF 220-case Dice; MoSAIC M2-M10 full-data train-on-case probe vs hosted validation; PRISM fold0 outer once vs future fold1 or validation selection; internal edema-zone vs official pure edema leaderboard",
        })
        occ.append({
            "score_id": sid, "value": "0.5", "source_path": "source.csv", "source_sha256": SHA,
            "source_row_or_key": sid, "model_id": sid.split("_")[0], "checkpoint_sha256": checkpoint,
            "prediction_sha256": prediction, "case_set_id": population, "case_count": rows[-1]["case_count"],
            "train_case_relationship": relation, "population_role": "hosted validation" if "HOSTED" in sid else population,
            "pathology_object": pathology, "label_definition": label, "metric_name": "Dice",
            "metric_implementation": "reference evaluator", "physical_spacing_used": "yes", "empty_gt_policy": "explicit",
            "positive_gt_only": "true" if "EDEMA" in sid else "false", "threshold": "fixed", "decode_rule": "fixed",
            "is_hosted": str("HOSTED" in sid).lower(), "is_clean_oof": str("CLEAN_OOF" in sid).lower(),
            "is_train_on_case": "false", "is_prediction_parity": "false", "claim_allowed": "true", "notes": "ok",
        })
    write_csv(d / "metric_truth_table.csv", rows, TABLE_FIELDS)
    write_csv(d / "score_occurrence_inventory.csv", occ, OCC_FIELDS)
    write_csv(d / "source_inventory.csv", [{"source_path": "source.csv", "source_sha256": SHA, "source_type": "csv", "notes": "fixture"}], ["source_path", "source_sha256", "source_type", "notes"])
    write_csv(d / "decoder_reset_score_lineage.csv", [{"score_contract_id": "D0_INNER_SELECT_STOCK_GT_SCAR", "lineage": "GT Dice"}], ["score_contract_id", "lineage"])
    (d / "decoder_reset_score_semantics.json").write_text(json.dumps({"d0_0p922_semantics": "GT Dice on frozen inner-select cases, not prediction parity"}) + "\n")
    (d / "metric_semantics_contract.json").write_text(json.dumps({"label_semantics": {"official_pure_edema": "internal label 4; official edema; T2-present denominator only", "internal_edema_zone": "internal labels 4 or 5; internal diagnostic only; not official edema"}}) + "\n")
    (d / "metric_truth_receipt.json").write_text(json.dumps({"metric_contract_status": "FAIL", "canonical_t2_present_count": 80, "forbidden_direct_comparisons": ["D0 inner-select GT Dice vs clean OOF 220-case Dice", "MoSAIC M2-M10 full-data train-on-case probe vs hosted validation", "PRISM fold0 outer once vs future fold1 or validation selection", "internal edema-zone vs official pure edema leaderboard"], "remaining_blockers": ["hosted package not fully bound"]}) + "\n")
    for name in ["score_lineage_report.md", "deep_research_score_corrections.md", "controller_report.md", "completion_check.md", "MANIFEST.md"]:
        (d / name).write_text("ok\n")
    return d


def run_validator(d: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run([sys.executable, str(VALIDATOR), "--result-dir", str(d)], cwd=ROOT, text=True, capture_output=True)


def test_valid_fixture_passes(tmp_path: Path) -> None:
    d = make_packet(tmp_path)
    proc = run_validator(d)
    assert proc.returncode == 0, proc.stderr


def mutate_table(d: Path, score_id: str, field: str, value: str) -> None:
    rows = list(csv.DictReader((d / "metric_truth_table.csv").open()))
    for row in rows:
        if row["score_contract_id"] == score_id:
            row[field] = value
    write_csv(d / "metric_truth_table.csv", rows, TABLE_FIELDS)


def mutate_occ(d: Path, score_id: str, field: str, value: str) -> None:
    rows = list(csv.DictReader((d / "score_occurrence_inventory.csv").open()))
    for row in rows:
        if row["score_id"] == score_id:
            row[field] = value
    write_csv(d / "score_occurrence_inventory.csv", rows, OCC_FIELDS)


def assert_rejected(d: Path, expected: str) -> None:
    proc = run_validator(d)
    assert proc.returncode != 0
    assert expected in proc.stderr


def test_reject_prediction_parity_as_gt_dice(tmp_path: Path) -> None:
    d = make_packet(tmp_path)
    mutate_occ(d, "D0_INNER_SELECT_STOCK_GT_SCAR", "is_prediction_parity", "true")
    assert_rejected(d, "prediction parity")


def test_reject_train_on_case_as_clean_oof(tmp_path: Path) -> None:
    d = make_packet(tmp_path)
    mutate_occ(d, "NNUNET_CLEAN_OOF_SCAR_220", "is_train_on_case", "true")
    assert_rejected(d, "train-on-case")


def test_reject_fold0_outer_as_selection_pool(tmp_path: Path) -> None:
    d = make_packet(tmp_path)
    mutate_table(d, "PRISM_W3_OUTER_ONCE_SCAR", "population", "inner selection reused from outer")
    assert_rejected(d, "inner row placed in outer")


def test_reject_edema_zone_as_official_edema(tmp_path: Path) -> None:
    d = make_packet(tmp_path)
    mutate_table(d, "PRISM_W3_OUTER_ONCE_INTERNAL_EDEMA_ZONE", "population", "official leaderboard edema")
    assert_rejected(d, "edema-zone")


def test_reject_no_t2_in_pure_edema_denominator(tmp_path: Path) -> None:
    d = make_packet(tmp_path)
    mutate_table(d, "NNUNET_CLEAN_OOF_PURE_EDEMA_T2_80", "population", "all cases includes no-T2")
    assert_rejected(d, "pure edema row")


def test_reject_hosted_score_without_hosted_population(tmp_path: Path) -> None:
    d = make_packet(tmp_path)
    mutate_occ(d, "MOSAIC_HOSTED_SCAR_20260706_USER_ATTESTED", "population_role", "local validation")
    assert_rejected(d, "hosted row")


def test_reject_checkpoint_name_instead_of_sha(tmp_path: Path) -> None:
    d = make_packet(tmp_path)
    mutate_table(d, "D0_INNER_SELECT_STOCK_GT_SCAR", "checkpoint_sha256", "checkpoint_final.pth")
    assert_rejected(d, "checkpoint name")


def test_reject_missing_case_count(tmp_path: Path) -> None:
    d = make_packet(tmp_path)
    mutate_table(d, "D0_INNER_SELECT_STOCK_GT_SCAR", "case_count", "")
    assert_rejected(d, "case_count missing")


def test_reject_missing_metric_implementation(tmp_path: Path) -> None:
    d = make_packet(tmp_path)
    mutate_table(d, "D0_INNER_SELECT_STOCK_GT_SCAR", "metric", "")
    assert_rejected(d, "metric implementation missing")


def test_reject_hd95_with_unknown_spacing(tmp_path: Path) -> None:
    d = make_packet(tmp_path)
    mutate_table(d, "D0_INNER_SELECT_STOCK_GT_SCAR", "metric", "Dice and HD95 mm; spacing=unknown")
    assert_rejected(d, "HD95")


def test_reject_missing_forbidden_d0_clean_comparison(tmp_path: Path) -> None:
    d = make_packet(tmp_path)
    receipt = json.loads((d / "metric_truth_receipt.json").read_text())
    receipt["forbidden_direct_comparisons"].remove("D0 inner-select GT Dice vs clean OOF 220-case Dice")
    (d / "metric_truth_receipt.json").write_text(json.dumps(receipt) + "\n")
    assert_rejected(d, "missing required forbidden")


def test_reject_missing_forbidden_mosaic_full_hosted_comparison(tmp_path: Path) -> None:
    d = make_packet(tmp_path)
    receipt = json.loads((d / "metric_truth_receipt.json").read_text())
    receipt["forbidden_direct_comparisons"].remove("MoSAIC M2-M10 full-data train-on-case probe vs hosted validation")
    (d / "metric_truth_receipt.json").write_text(json.dumps(receipt) + "\n")
    assert_rejected(d, "missing required forbidden")


def test_reject_pdf_prose_without_source_hash(tmp_path: Path) -> None:
    d = make_packet(tmp_path)
    mutate_occ(d, "D0_INNER_SELECT_STOCK_GT_SCAR", "source_sha256", "")
    assert_rejected(d, "source_sha256 missing")


def test_reject_pass_with_unresolved_core_score(tmp_path: Path) -> None:
    d = make_packet(tmp_path)
    receipt = json.loads((d / "metric_truth_receipt.json").read_text())
    receipt["metric_contract_status"] = "PASS"
    (d / "metric_truth_receipt.json").write_text(json.dumps(receipt) + "\n")
    assert_rejected(d, "PASS")
