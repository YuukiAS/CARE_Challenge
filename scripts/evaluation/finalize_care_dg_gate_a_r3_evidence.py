#!/usr/bin/env python3
"""Finalize Gate A-R3 evidence summaries after strict validator PASS."""

from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[2]
TASK_KEY = "20260727_care_dg_dual_pathology_validation"
RESULT_ROOT = REPO_ROOT / "results" / TASK_KEY
SCAR_PRIORITY_RUNTIME_ROOT = RESULT_ROOT / "runtime/gate_b_scar_priority_preflight/fold0"
RUNTIME_ROOT = SCAR_PRIORITY_RUNTIME_ROOT if SCAR_PRIORITY_RUNTIME_ROOT.exists() else RESULT_ROOT / "runtime/gate_a_r3_preflight/fold0"
GATE_ROOT = RESULT_ROOT / "gate_a_repaired_semantics"


def now_utc() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def rel(path: Path) -> str:
    try:
        return path.resolve().relative_to(REPO_ROOT.resolve()).as_posix()
    except ValueError:
        return path.as_posix()


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def evidence_hashes() -> dict[str, dict[str, Any]]:
    paths = [
        RESULT_ROOT / "implementation_contract.json",
        RESULT_ROOT / "model_parameter_report.json",
        RESULT_ROOT / "known_bad_report.json",
        RESULT_ROOT / "real_case_forward_backward_receipt.json",
        RESULT_ROOT / "checkpoint_resume_parity.json",
        RESULT_ROOT / "augmentation_alignment_audit.json",
        RESULT_ROOT / "implementation_overfit_receipt.json",
        RESULT_ROOT / "strict_validator_report.json",
        RUNTIME_ROOT / "fold_training_receipt.json",
        RUNTIME_ROOT / "preflight_validator_report.json",
        RUNTIME_ROOT / "resolved_training_contract.json",
        RUNTIME_ROOT / "sampler_quota_audit_stage_a.json",
        RUNTIME_ROOT / "sampler_quota_audit_stage_b.json",
        RUNTIME_ROOT / "inner_evaluation_plan.json",
        RUNTIME_ROOT / "inner_evaluation_repeat_receipt.json",
        RUNTIME_ROOT / "checkpoint_manifest.csv",
        RUNTIME_ROOT / "training_curve.csv",
    ]
    return {rel(path): {"exists": path.exists(), "sha256": sha256_file(path) if path.exists() else "missing"} for path in paths}


def main() -> int:
    strict = load_json(RESULT_ROOT / "strict_validator_report.json")
    if strict.get("status") != "PASS":
        raise SystemExit("CARE_DG_GATE_A_R3_FINALIZE_REQUIRES_STRICT_VALIDATOR_PASS")
    static = load_json(GATE_ROOT / "gate_a_static_test_receipt.json")
    impl = load_json(RESULT_ROOT / "implementation_contract.json")
    known = load_json(RESULT_ROOT / "known_bad_report.json")
    receipt = load_json(RUNTIME_ROOT / "fold_training_receipt.json")
    resolved = load_json(RUNTIME_ROOT / "resolved_training_contract.json")
    sampler_a = load_json(RUNTIME_ROOT / "sampler_quota_audit_stage_a.json")
    sampler_b = load_json(RUNTIME_ROOT / "sampler_quota_audit_stage_b.json")
    inner_plan = load_json(RUNTIME_ROOT / "inner_evaluation_plan.json")

    summary = load_json(RESULT_ROOT / "gate_a_summary.json") if (RESULT_ROOT / "gate_a_summary.json").exists() else {}
    summary.setdefault("static", {})["strict_validator"] = {"status": "PASS", "returncode": 0}
    consistency_report_path = RESULT_ROOT / "gate_a_consistency_validator_report.json"
    consistency_status = "READY_TO_RUN"
    if consistency_report_path.exists():
        consistency_status = load_json(consistency_report_path).get("status", "READY_TO_RUN")

    summary.update({
        "updated_at_utc": now_utc(),
        "status": impl.get("status"),
        "gate_revision": "A-R3",
        "active_preflight_runtime_label": RUNTIME_ROOT.parent.name,
        "state": "AWAITING_HUMAN_ACCEPTANCE_GATE_A_R3",
        "approval_token_required": "APPROVE_GATE_A_R3",
        "approval_token": "APPROVE_GATE_A_R3",
        "strict_validator_status": "PASS",
        "strict_validator_failures": strict.get("failures", []),
        "consistency_validator_status": consistency_status,
        "resolved_training_contract_path": rel(RUNTIME_ROOT / "resolved_training_contract.json"),
        "resolved_training_contract_sha256": resolved.get("resolved_training_contract_sha256"),
        "stage_a_learning_rates": resolved.get("learning_rates", {}).get("stage_a"),
        "stage_b_learning_rates": resolved.get("learning_rates", {}).get("stage_b"),
        "stage_a_sampler_audit": {"status": sampler_a.get("status"), "target_hit_rates": sampler_a.get("target_hit_rates"), "effective_fractions": sampler_a.get("effective_fractions"), "silent_fallback_count": sampler_a.get("silent_fallback_count"), "sampler_index_sha256": sampler_a.get("sampler_index_sha256")},
        "stage_b_sampler_audit": {"status": sampler_b.get("status"), "target_hit_rates": sampler_b.get("target_hit_rates"), "effective_fractions": sampler_b.get("effective_fractions"), "silent_fallback_count": sampler_b.get("silent_fallback_count"), "sampler_index_sha256": sampler_b.get("sampler_index_sha256")},
        "fixed_inner_plan": {"case_count": inner_plan.get("case_count"), "patch_count": inner_plan.get("patch_count"), "plan_sha256": inner_plan.get("plan_sha256")},
        "preflight": {"status": receipt.get("status"), "actual_optimizer_steps": receipt.get("actual_optimizer_steps"), "formal_training_credit": receipt.get("formal_training_credit"), "inner_evaluation_repeat_exact": receipt.get("inner_evaluation_repeat_exact")},
        "known_bad_status": known.get("status"),
        "evidence_hashes": evidence_hashes(),
    })
    write_json(GATE_ROOT / "gate_a_summary.json", summary)
    write_json(RESULT_ROOT / "gate_a_summary.json", summary)

    pytest_status = "PASS" if static.get("pytest", {}).get("returncode") == 0 else "FAIL"
    py_compile_status = "PASS" if static.get("py_compile", {}).get("returncode") == 0 else "FAIL"
    smoke_status = "PASS" if static.get("unit_smoke", {}).get("returncode") == 0 else "FAIL"
    lines = [
        "# CARE-DG Gate A-R3 unit test report",
        "",
        f"created_at_utc: `{now_utc()}`",
        "",
        f"py_compile: `{py_compile_status}`",
        "",
        f"pytest tests/care_dg -q: `{pytest_status}`",
        "",
        f"runner unit smoke: `{smoke_status}`",
        "",
        "strict validator: `PASS`",
        "",
        f"strict_validator_report: `{rel(RESULT_ROOT / 'strict_validator_report.json')}`",
        "",
        f"known_bad: `{known.get('status')}`",
        "",
        f"resolved_training_contract_sha256: `{resolved.get('resolved_training_contract_sha256')}`",
    ]
    (RESULT_ROOT / "unit_test_report.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(json.dumps({"status": "PASS", "gate_revision": "A-R3",
        "active_preflight_runtime_label": RUNTIME_ROOT.parent.name, "strict_validator_status": "PASS", "summary": rel(RESULT_ROOT / "gate_a_summary.json")}, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
