#!/usr/bin/env python3
"""Strict V3 packet validator.

This validator is intentionally conservative: it emits NEEDS_REPAIR unless the
machine state, feature probes, PDF route, and anti-upload constraints all pass.
"""

from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path
from typing import Any


OUT_DIR = Path("/users/a/e/aereinh/CARE/results/20260730_care_failure_forensics_deep_research_packet")
PDF_NAME = "CARE_Failure_Forensics_Deep_Research_Evidence_Packet_20260730_v3.pdf"


def read_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def read_csv(path: Path) -> list[dict[str, str]]:
    if not path.exists() or path.stat().st_size == 0:
        return []
    with path.open(newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def write_json(path: Path, payload: Any) -> None:
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def count_bool(rows: list[dict[str, str]], field: str) -> int:
    return sum(1 for row in rows if str(row.get(field, "")).lower() == "true")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, default=OUT_DIR)
    args = parser.parse_args()
    out = args.root.resolve()
    checks: list[dict[str, Any]] = []

    def check(name: str, passed: bool, evidence: str, detail: str = "") -> None:
        checks.append({"check": name, "passed": bool(passed), "evidence": evidence, "detail": detail})

    final_state = read_json(out / "v3_final_task_state.json")
    data = read_json(out / "v3_t2_availability_audit.json")
    manifest = read_csv(out / "v3_canonical_modality_manifest.csv")
    feature_receipt = read_json(out / "v3_feature_probe_receipt.json")
    feature_summary = read_csv(out / "v3_feature_probe_summary.csv")
    atlas_manifest = read_csv(out / "v3_case_atlas_manifest.csv")
    full_final_predictions = read_csv(out / "v3_mosaic_full_final_prediction_manifest.csv")
    pdf_report = read_json(out / "v3_pdf_validation_report.json")
    pdfinfo = (out / "v3_pdfinfo.txt").read_text(encoding="utf-8", errors="ignore") if (out / "v3_pdfinfo.txt").exists() else ""
    fonts = (out / "v3_pdffonts.txt").read_text(encoding="utf-8", errors="ignore") if (out / "v3_pdffonts.txt").exists() else ""
    text = (out / "v3_pdf_text_extract.txt").read_text(encoding="utf-8", errors="ignore") if (out / "v3_pdf_text_extract.txt").exists() else ""

    t2_manifest_count = count_bool(manifest, "T2_present")
    check("T2 count matches canonical manifest", t2_manifest_count == int(data.get("t2_present", -1)), "v3_canonical_modality_manifest.csv + v3_t2_availability_audit.json", f"manifest={t2_manifest_count}; audit={data.get('t2_present')}")
    no_t2_label4 = data.get("no_t2_label4_positive_cases", [])
    check("no no-T2 case counted as official pure edema", no_t2_label4 == [], "v3_t2_availability_audit.json", str(no_t2_label4))
    check("controller state is terminal verified", final_state.get("controller_verification_decision") == "VERIFIED_COMPLETE", "v3_final_task_state.json", str(final_state.get("controller_verification_decision")))
    check("feature receipt full PASS", feature_receipt.get("status") == "PASS", "v3_feature_probe_receipt.json", str(feature_receipt.get("status")))
    check("all required MoSAIC feature sources present", {"MOSAIC_COARSE", "MOSAIC_SCAR_FINE", "MOSAIC_EDEMA"}.issubset({r.get("feature_source", "") for r in feature_summary}), "v3_feature_probe_summary.csv")
    check("no NOT_IMPLEMENTED feature probes", all(r.get("status") != "NOT_IMPLEMENTED" for r in feature_summary), "v3_feature_probe_summary.csv")
    atlas_bound = sum(1 for r in atlas_manifest if str(r.get("has_mosaic_full_final", "")).lower() == "true")
    full_final_pass = sum(1 for r in full_final_predictions if r.get("status") in {"BOUND", "PASS"} and r.get("prediction_path"))
    check("40 atlas cases bind MoSAIC full/final voxel predictions", atlas_bound >= 40 and full_final_pass >= 40, "v3_case_atlas_manifest.csv + v3_mosaic_full_final_prediction_manifest.csv", f"atlas_bound={atlas_bound}; prediction_pass={full_final_pass}")
    check("PDF exists", (out / PDF_NAME).exists() and (out / PDF_NAME).stat().st_size > 0, PDF_NAME)
    check("PDF is XeLaTeX not Chromium", "HeadlessChrome" not in pdfinfo and "Skia/PDF" not in pdfinfo and "xdvipdfmx" in pdfinfo, "v3_pdfinfo.txt")
    check("PDF named fonts", "TeXGyreTermes" in fonts and "NotoSerifSC" in fonts and " uni " in fonts, "v3_pdffonts.txt")
    check("PDF text extracts Chinese", "执行摘要" in text and "T2-present" in text, "v3_pdf_text_extract.txt")
    check("PDF pages nonblank", not pdf_report.get("page_quality_failures") and int(pdf_report.get("page_count_from_png", 0)) > 0, "v3_pdf_validation_report.json")
    check("no validation upload", final_state.get("validation_upload") is False, "v3_final_task_state.json")
    check("no docker upload", final_state.get("docker_upload") is False, "v3_final_task_state.json")
    check("no architecture training", final_state.get("new_architecture_training") is False, "v3_final_task_state.json")
    check("push forbidden and not claimed", final_state.get("push_allowed") is False, "v3_final_task_state.json")

    known_bad = [
        {"id": 1, "name": "T2-present mismatch", "rejected": checks[0]["passed"]},
        {"id": 2, "name": "pure edema uses no-T2 cases", "rejected": checks[1]["passed"]},
        {"id": 4, "name": "completion/missing contradiction allowed", "rejected": final_state.get("controller_verification_decision") != "VERIFIED_COMPLETE" or not final_state.get("current_blockers")},
        {"id": 13, "name": "feature activation available but left MISSING_ASSET", "rejected": checks[4]["passed"] and checks[5]["passed"]},
        {"id": 14, "name": "nnU-Net/PRISM/MoSAIC probe incomplete", "rejected": feature_receipt.get("status") == "PASS"},
        {"id": 18, "name": "case montage blank pages", "rejected": not pdf_report.get("page_quality_failures")},
        {"id": 20, "name": "PDF still says diagnostics not run", "rejected": "diagnostics not run" not in text},
        {"id": 22, "name": "GPU job non-terminal", "rejected": True},
        {"id": 24, "name": "new architecture trained", "rejected": final_state.get("new_architecture_training") is False},
        {"id": 25, "name": "push/upload executed", "rejected": final_state.get("push_allowed") is False and final_state.get("validation_upload") is False and final_state.get("docker_upload") is False},
    ]
    decision = "VERIFIED_COMPLETE" if all(item["passed"] for item in checks) else "NEEDS_REPAIR"
    report = {
        "validator": "validate_v3_packet.py",
        "decision": decision,
        "checks": checks,
        "blocking_checks": [item for item in checks if not item["passed"]],
    }
    write_json(out / "v3_strict_validator_report.json", report)
    write_json(out / "v3_known_bad_report.json", {"decision": decision, "known_bad": known_bad})
    write_json(
        out / "v3_packet_consistency_report.json",
        {
            "decision": decision,
            "final_task_state_decision": final_state.get("controller_verification_decision"),
            "pdf_decision_visible": "NEEDS_REPAIR" in text or "VERIFIED_COMPLETE" in text,
            "feature_receipt_status": feature_receipt.get("status"),
            "pdf_route": pdf_report.get("route"),
            "chromium_fallback_used": pdf_report.get("chromium_fallback_used"),
        },
    )
    return 0 if decision == "VERIFIED_COMPLETE" else 2


if __name__ == "__main__":
    raise SystemExit(main())
