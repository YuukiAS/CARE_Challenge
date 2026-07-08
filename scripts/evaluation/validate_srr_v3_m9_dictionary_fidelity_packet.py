#!/usr/bin/env python3
"""Fail-closed validator for M9 SRR dictionary fidelity packets."""

from __future__ import annotations

import argparse
import csv
import re
import shutil
import sys
import tempfile
from pathlib import Path


READY_STATE = "M9_READY_FOR_REVIEW"
ALLOWED_STATES = {
    READY_STATE,
    "M9_NEEDS_EVIDENCE",
    "M9_NEEDS_REVISION",
    "M9_SCIENTIFIC_UNDERTRAINED",
    "M9_NEEDS_MONITOR",
    "M9_RESOURCE_BLOCKED",
    "M9_BLOCKED_PROJECT_ROUTE_DIAGRAMS_UNAVAILABLE",
}
MONITOR_TOKENS = {"NEEDS_MONITOR", "PENDING_MONITOR", "JOB_SUBMITTED", "PENDING_PRIORITY", "RUNNING", "AWAITING_SACCT"}
FORBIDDEN_READY_PHRASES = {"validation upload", "hosted metric claim", "leaderboard-ready", "fold expansion", "M10"}
REQUIRED_FILES = [
    "result.md",
    "completion_check.md",
    "review_request.md",
    "MANIFEST.md",
    "commands_run.md",
    "m9_loss_weight_wiring_test_report.md",
    "m9_metric_aligned_checkpoint_selection.csv",
    "m9_nnunet_role_audit.md",
    "m9_dictionary_fidelity_matrix.csv",
    "m9_candidate_assembly_matrix.csv",
    "m9_cine_final_output_manifest.csv",
    "m9_cine_frame0_vs_temporal_help_harm.csv",
    "m9_route_promotion_decision.md",
    "m9_next_required_action.md",
]


def read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8") if path.is_file() else ""


def read_csv(path: Path) -> list[dict[str, str]]:
    if not path.is_file():
        return []
    with path.open(newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def completion_state(packet: Path) -> str:
    text = read_text(packet / "completion_check.md")
    match = re.search(r"status:\s*`?([A-Z0-9_]+)`?", text)
    return match.group(1) if match else "EVIDENCE_NOT_FOUND"


def validate(packet: Path) -> list[str]:
    errors: list[str] = []
    state = completion_state(packet)
    if state not in ALLOWED_STATES:
        errors.append(f"invalid completion state: {state}")
    for file_name in REQUIRED_FILES:
        if not (packet / file_name).is_file():
            errors.append(f"missing required file: {file_name}")
    all_md = "\n".join(read_text(path) for path in packet.glob("*.md"))
    if "M8_FOLLOWUP_AUDITED_NO_DEPLOYABLE_REPAIR_SCIENTIFIC_UNRESOLVED" not in all_md:
        errors.append("missing M8 follow-up review token")
    if "SRR_MAIN_NOT_ANCHOR_RESIDUAL" not in all_md:
        errors.append("missing SRR-main final-output evidence token")
    if "CONTEXT_TEACHER_SAFETY_CONTROL_ONLY" not in all_md:
        errors.append("missing nnU-Net role audit token")
    if (packet / "review.md").exists():
        errors.append("executor packet must not contain review.md")
    if state == READY_STATE:
        upper_md = all_md.upper()
        for token in MONITOR_TOKENS:
            if token in upper_md:
                errors.append(f"ready packet contains monitor token: {token}")
        lower_md = all_md.lower()
        for phrase in FORBIDDEN_READY_PHRASES:
            if phrase.lower() in lower_md and f"not {phrase.lower()}" not in lower_md and f"no {phrase.lower()}" not in lower_md:
                errors.append(f"ready packet contains forbidden phrase: {phrase}")
        loss_report = read_text(packet / "m9_loss_weight_wiring_test_report.md")
        if "total_loss_changed: `true`" not in loss_report or "gradient_norm_changed: `true`" not in loss_report:
            errors.append("loss-weight wiring report does not prove total loss and gradient change")
        selection = read_csv(packet / "m9_metric_aligned_checkpoint_selection.csv")
        if not selection or any("patch_loss_only" in " ".join(row.values()).lower() for row in selection):
            errors.append("checkpoint selection is missing or patch-loss-only")
        nnunet_audit = read_text(packet / "m9_nnunet_role_audit.md")
        if "final_logits = nnunet_anchor_logits + bounded_srr_delta" in nnunet_audit:
            errors.append("formal M9 candidate uses forbidden anchor-residual final logits")
        cine_manifest = read_csv(packet / "m9_cine_final_output_manifest.csv")
        if not cine_manifest or not any(row.get("case_count") not in {"", "0"} for row in cine_manifest):
            errors.append("ready packet lacks Cine final-output rows")
    return errors


def run_selftest() -> tuple[int, list[dict[str, str]]]:
    rows: list[dict[str, str]] = []
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        good = root / "good"
        good.mkdir()
        for file_name in REQUIRED_FILES:
            path = good / file_name
            if file_name.endswith(".csv"):
                path.write_text("status,case_count\nFOUND_LOCAL_FINAL_OUTPUTS,1\n", encoding="utf-8")
            else:
                path.write_text(
                    "status: `M9_READY_FOR_REVIEW`\n"
                    "M8_FOLLOWUP_AUDITED_NO_DEPLOYABLE_REPAIR_SCIENTIFIC_UNRESOLVED\n"
                    "SRR_MAIN_NOT_ANCHOR_RESIDUAL\n"
                    "CONTEXT_TEACHER_SAFETY_CONTROL_ONLY\n"
                    "total_loss_changed: `true`\n"
                    "gradient_norm_changed: `true`\n"
                    "No validation upload, no hosted metric claim, no fold expansion, no M10.\n",
                    encoding="utf-8",
                )
        (good / "m9_metric_aligned_checkpoint_selection.csv").write_text(
            "candidate_id,selection_metric,selected_checkpoint\nm9,metric_aligned_composite,checkpoint_best.pt\n",
            encoding="utf-8",
        )
        good_errors = validate(good)
        rows.append({"fixture": "good", "expected": "pass", "actual_error_count": str(len(good_errors)), "status": "PASS" if not good_errors else "FAIL"})
        mutations = {
            "missing_followup_token": lambda p: [
                md_path.write_text(
                    md_path.read_text(encoding="utf-8").replace(
                        "M8_FOLLOWUP_AUDITED_NO_DEPLOYABLE_REPAIR_SCIENTIFIC_UNRESOLVED",
                        "M8_FOLLOWUP_TOKEN_REMOVED",
                    ),
                    encoding="utf-8",
                )
                for md_path in p.glob("*.md")
            ],
            "missing_required_file": lambda p: (p / "m9_nnunet_role_audit.md").unlink(),
            "review_written": lambda p: (p / "review.md").write_text("bad\n", encoding="utf-8"),
            "patch_loss_only": lambda p: (p / "m9_metric_aligned_checkpoint_selection.csv").write_text(
                "candidate_id,selection_metric,selected_checkpoint\nm9,patch_loss_only,checkpoint_best.pt\n",
                encoding="utf-8",
            ),
        }
        for name, mutate in mutations.items():
            bad = root / name
            shutil.copytree(good, bad)
            mutate(bad)
            errors = validate(bad)
            rows.append({"fixture": name, "expected": "fail", "actual_error_count": str(len(errors)), "status": "PASS" if errors else "FAIL"})
    failures = sum(1 for row in rows if row["status"] != "PASS")
    return failures, rows


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("packet", nargs="?", default="results/20260708_srr_v3_m9_dictionary_fidelity_repair_training")
    parser.add_argument("--self-test", action="store_true")
    args = parser.parse_args()
    if args.self_test:
        failures, rows = run_selftest()
        writer = csv.DictWriter(sys.stdout, fieldnames=["fixture", "expected", "actual_error_count", "status"], lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)
        raise SystemExit(1 if failures else 0)
    errors = validate(Path(args.packet))
    for error in errors:
        print(f"ERROR: {error}")
    print(f"error_count={len(errors)}")
    raise SystemExit(1 if errors else 0)


if __name__ == "__main__":
    main()
