from __future__ import annotations

import importlib.util
import re
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
ADAPTER = REPO_ROOT / "scripts" / "ops" / "slurm_safe_cancel.py"
REACHABLE_WATCHERS = (
    REPO_ROOT / "scripts" / "route_B_round04" / "watch_B1_race.py",
    REPO_ROOT / "scripts" / "evaluation" / "watch_care_srr_cascade_formal_race.py",
    REPO_ROOT / "scripts" / "evaluation" / "watch_srr_v3_m7_routing.py",
    REPO_ROOT / "scripts" / "evaluation" / "watch_srr_v3_m8_myops_race.py",
    REPO_ROOT / "scripts" / "target_domain_gap_closure" / "monitor_interactive_takeover.py",
)


def load_adapter():
    spec = importlib.util.spec_from_file_location("care_slurm_safe_cancel", ADAPTER)
    module = importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    spec.loader.exec_module(module)
    return module


class SlurmSafeCancelAdapterTests(unittest.TestCase):
    def test_closed_result_mapping(self) -> None:
        adapter = load_adapter()
        allowed = adapter.classify_safe_cancel_result(
            {"decision": "ALLOW_OWNED_UNPROTECTED", "reason": "ok", "executed": True}
        )
        protected = adapter.classify_safe_cancel_result(
            {"decision": "REQUIRE_FRESH_HUMAN", "reason": "protected_target", "executed": False}
        )
        denied = adapter.classify_safe_cancel_result(
            {"decision": "DENY_UNKNOWN_OR_FORBIDDEN", "reason": "unknown", "executed": False}
        )
        malformed = adapter.classify_safe_cancel_result(
            {"decision": "DENY_UNKNOWN_OR_FORBIDDEN", "reason": "bad_response", "executed": True}
        )
        self.assertEqual(allowed["action"], "SAFE_CANCEL_EXECUTED")
        self.assertFalse(allowed["retain_target"])
        self.assertEqual(protected["action"], "RETAIN_REQUEST_FRESH_HUMAN")
        self.assertTrue(protected["retain_target"])
        self.assertEqual(denied["action"], "RETAIN_DENIED")
        self.assertTrue(denied["retain_target"])
        self.assertFalse(malformed["executed"])
        self.assertTrue(malformed["retain_target"])

    def test_reachable_watchers_have_no_direct_scancel_fallback(self) -> None:
        direct_call = re.compile(r"(?:run|run_command|subprocess\.run|subprocess\.Popen)\s*\(\s*\[\s*[\"']scancel")
        for path in REACHABLE_WATCHERS:
            source = path.read_text(encoding="utf-8")
            with self.subTest(path=path):
                self.assertIsNone(direct_call.search(source))
                self.assertIn("safe_cancel_pending_job", source)

    def test_authority_surfaces_route_through_safe_cancel(self) -> None:
        paths = (
            REPO_ROOT / "AGENTS.md",
            REPO_ROOT / ".agents" / "skills" / "slurm-routing-partition" / "SKILL.md",
            REPO_ROOT / "prompts" / "tasks" / "20260801_care_target_domain_race_gap_closure_controller.md",
            REPO_ROOT / "prompts" / "blueprints" / "CARE_target_domain_race_gap_closure_20260801.md",
        )
        for path in paths:
            with self.subTest(path=path):
                self.assertIn("safe-cancel", path.read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()
