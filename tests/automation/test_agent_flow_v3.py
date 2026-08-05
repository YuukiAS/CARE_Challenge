from __future__ import annotations

import copy
import importlib.util
import json
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / "scripts" / "automation" / "validate_agent_flow_v3.py"
SPEC = importlib.util.spec_from_file_location("validate_agent_flow_v3", SCRIPT)
assert SPEC and SPEC.loader
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


class AgentFlowV3ValidationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.schema = json.loads(
            (ROOT / "automation" / "agent_flow_v3" / "schema.json").read_text(encoding="utf-8")
        )
        cls.template = json.loads(
            (ROOT / "automation" / "agent_flow_v3" / "task_template.json").read_text(encoding="utf-8")
        )

    def test_template_is_valid(self) -> None:
        self.assertEqual(MODULE.validate_request(self.template, self.schema), [])

    def test_duplicate_worktree_is_rejected(self) -> None:
        request = copy.deepcopy(self.template)
        request["role_sessions"]["executor"]["worktree"] = request["role_sessions"]["verifier"]["worktree"]
        self.assertIn(
            "role_field_not_unique:worktree",
            MODULE.validate_request(request, self.schema),
        )

    def test_controller_cannot_edit_implementation(self) -> None:
        request = copy.deepcopy(self.template)
        request["role_sessions"]["controller"]["may_edit_implementation"] = True
        self.assertIn(
            "controller:may_edit_implementation",
            MODULE.validate_request(request, self.schema),
        )

    def test_executor_cannot_edit_verification(self) -> None:
        request = copy.deepcopy(self.template)
        request["role_sessions"]["executor"]["may_edit_verification"] = True
        self.assertIn(
            "executor:may_edit_verification",
            MODULE.validate_request(request, self.schema),
        )

    def test_planner_pass_requires_exact_bindings(self) -> None:
        request = copy.deepcopy(self.template)
        request["frozen_contract_sha256"] = "a" * 64
        current = {
            "schema": "CARE_AGENT_FLOW_V3",
            "task_id": request["task_id"],
            "state": "PLANNER_PASS",
            "review_round": 1,
            "request_nonce": "nonce",
            "frozen_contract_sha256": request["frozen_contract_sha256"],
            "integration_commit_sha": None,
            "implementation_fingerprint_sha256": None,
            "verifier_fingerprint_sha256": None,
            "next_action": "AWAIT_HUMAN_DECISION",
            "updated_utc": "2026-08-05T00:00:00Z",
        }
        self.assertIn(
            "planner_pass_missing_exact_bindings",
            MODULE.validate_current(current, request, self.schema),
        )


if __name__ == "__main__":
    unittest.main()
