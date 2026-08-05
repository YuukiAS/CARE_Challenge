from __future__ import annotations

import copy
import importlib.util
import json
from pathlib import Path
import argparse
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / "scripts" / "automation" / "validate_agent_flow_v3.py"
SPEC = importlib.util.spec_from_file_location("validate_agent_flow_v3", SCRIPT)
assert SPEC and SPEC.loader
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)

RUNTIME_SCRIPT = ROOT / "scripts" / "automation" / "agent_flow_v3_runtime.py"
RUNTIME_SPEC = importlib.util.spec_from_file_location("agent_flow_v3_runtime", RUNTIME_SCRIPT)
assert RUNTIME_SPEC and RUNTIME_SPEC.loader
RUNTIME = importlib.util.module_from_spec(RUNTIME_SPEC)
RUNTIME_SPEC.loader.exec_module(RUNTIME)


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

    def test_role_receipt_thread_overlap_is_rejected(self) -> None:
        base = {
            "schema": RUNTIME.ROLE_RECEIPT_SCHEMA,
            "thread_id": "thread-a",
            "codex_home": "/tmp/home-a",
            "worktree": "/tmp/worktree-a",
            "local_branch": "local/controller/test",
            "pid_or_process_status": "created_for_smoke",
            "log_path": "/tmp/log-a.txt",
            "state_path": "/tmp/state-a.json",
            "write_scope": ["automation/agent_flow_v3/tasks/test/**"],
            "forbidden_scope": ["src/**"],
            "last_commit_sha": "a" * 40,
            "started_utc": "2026-08-05T00:00:00Z",
            "updated_utc": "2026-08-05T00:00:00Z",
        }
        receipts = {
            "controller": dict(base, role="controller"),
            "verifier": dict(
                base,
                role="verifier",
                codex_home="/tmp/home-b",
                worktree="/tmp/worktree-b",
                local_branch="local/verifier/test",
            ),
            "executor": dict(
                base,
                role="executor",
                thread_id="thread-c",
                codex_home="/tmp/home-c",
                worktree="/tmp/worktree-c",
                local_branch="local/executor/test",
            ),
        }
        self.assertIn("duplicate:thread_id", RUNTIME.validate_role_receipts(receipts))

    def test_watcher_routes_executor_revision_to_exact_thread(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            thread_file = root / "executor_thread_id"
            thread_file.write_text("exec-thread-123\n", encoding="utf-8")
            role_plan = root / "role_plan.json"
            role_plan.write_text(
                json.dumps(
                    {
                        "roles": {
                            "executor": {
                                "thread_id_file": str(thread_file),
                                "codex_home": str(root / "executor_home"),
                                "worktree": str(root / "executor_worktree"),
                            }
                        }
                    }
                ),
                encoding="utf-8",
            )
            args = argparse.Namespace(
                task_id="smoke-task",
                branch="develop",
                role_plan=str(role_plan),
                codex_bin="/opt/codex",
                state_root=root,
                session_receipt_root=str(root / "missing_receipts"),
                dry_run=True,
                thread_id_override="",
            )
            request = {
                "schema": RUNTIME.SCHEMA,
                "enabled": True,
                "task_id": "smoke-task",
                "integration_branch": "develop",
                "request_nonce": "nonce-1",
                "frozen_contract_sha256": "b" * 64,
            }
            current = {
                "schema": RUNTIME.SCHEMA,
                "task_id": "smoke-task",
                "state": "PLANNER_REVISE_EXECUTOR",
                "review_round": 1,
                "request_nonce": "nonce-1",
                "frozen_contract_sha256": "b" * 64,
                "integration_commit_sha": "c" * 40,
            }
            receipt = RUNTIME.evaluate_watcher_event(args, request, current, {"processed_events": []})
            self.assertEqual(receipt["decision"], "DRY_RUN_RESUME")
            self.assertEqual(receipt["target_roles"], ["executor"])
            self.assertIn("exec-thread-123", receipt["resume_commands"][0]["command"])

    def test_watcher_rejects_old_nonce(self) -> None:
        args = argparse.Namespace(
            task_id="smoke-task",
            branch="develop",
            role_plan="/unused",
            codex_bin="/opt/codex",
            state_root=Path("/tmp"),
            session_receipt_root="/tmp/missing_receipts",
            dry_run=True,
            thread_id_override="",
        )
        request = {
            "schema": RUNTIME.SCHEMA,
            "enabled": True,
            "task_id": "smoke-task",
            "integration_branch": "develop",
            "request_nonce": "new-nonce",
            "frozen_contract_sha256": "b" * 64,
        }
        current = {
            "schema": RUNTIME.SCHEMA,
            "task_id": "smoke-task",
            "state": "PLANNER_REVISE_EXECUTOR",
            "review_round": 1,
            "request_nonce": "old-nonce",
            "frozen_contract_sha256": "b" * 64,
            "integration_commit_sha": "c" * 40,
        }
        receipt = RUNTIME.evaluate_watcher_event(args, request, current, {"processed_events": []})
        self.assertEqual(receipt["decision"], "INVALID_EVENT")
        self.assertIn("nonce_binding", receipt["failures"])

    def test_watcher_ignores_duplicate_event(self) -> None:
        args = argparse.Namespace(
            task_id="smoke-task",
            branch="develop",
            role_plan="/unused",
            codex_bin="/opt/codex",
            state_root=Path("/tmp"),
            session_receipt_root="/tmp/missing_receipts",
            dry_run=True,
            thread_id_override="",
        )
        request = {
            "schema": RUNTIME.SCHEMA,
            "enabled": True,
            "task_id": "smoke-task",
            "integration_branch": "develop",
            "request_nonce": "nonce-1",
            "frozen_contract_sha256": "b" * 64,
        }
        current = {
            "schema": RUNTIME.SCHEMA,
            "task_id": "smoke-task",
            "state": "PLANNER_REVISE_EXECUTOR",
            "review_round": 1,
            "request_nonce": "nonce-1",
            "frozen_contract_sha256": "b" * 64,
            "integration_commit_sha": "c" * 40,
        }
        event_key = "smoke-task:nonce-1:1:PLANNER_REVISE_EXECUTOR:" + "c" * 40
        receipt = RUNTIME.evaluate_watcher_event(args, request, current, {"processed_events": [event_key]})
        self.assertEqual(receipt["decision"], "IGNORE")

    def test_watcher_rejects_thread_id_not_bound_to_receipt(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            thread_file = root / "executor_thread_id"
            thread_file.write_text("wrong-thread\n", encoding="utf-8")
            role_plan = root / "role_plan.json"
            role_plan.write_text(
                json.dumps(
                    {
                        "roles": {
                            "executor": {
                                "thread_id_file": str(thread_file),
                                "codex_home": str(root / "executor_home"),
                                "worktree": str(root / "executor_worktree"),
                            }
                        }
                    }
                ),
                encoding="utf-8",
            )
            receipt_root = root / "receipts"
            receipt_root.mkdir()
            (receipt_root / "executor_session_receipt.json").write_text(
                json.dumps({"thread_id": "correct-thread"}),
                encoding="utf-8",
            )
            args = argparse.Namespace(
                task_id="smoke-task",
                branch="develop",
                role_plan=str(role_plan),
                codex_bin="/opt/codex",
                state_root=root,
                session_receipt_root=str(receipt_root),
                dry_run=True,
                thread_id_override="",
            )
            request = {
                "schema": RUNTIME.SCHEMA,
                "enabled": True,
                "task_id": "smoke-task",
                "integration_branch": "develop",
                "request_nonce": "nonce-1",
                "frozen_contract_sha256": "b" * 64,
            }
            current = {
                "schema": RUNTIME.SCHEMA,
                "task_id": "smoke-task",
                "state": "PLANNER_REVISE_EXECUTOR",
                "review_round": 1,
                "request_nonce": "nonce-1",
                "frozen_contract_sha256": "b" * 64,
                "integration_commit_sha": "c" * 40,
            }
            result = RUNTIME.evaluate_watcher_event(args, request, current, {"processed_events": []})
            self.assertEqual(result["decision"], "INVALID_EVENT")
            self.assertIn("executor:thread_id_receipt_mismatch", result["failures"])

    def test_watcher_rejects_stale_integration_sha(self) -> None:
        args = argparse.Namespace(
            task_id="smoke-task",
            branch="develop",
            role_plan="/unused",
            codex_bin="/opt/codex",
            state_root=Path("/tmp"),
            session_receipt_root="/tmp/missing_receipts",
            dry_run=True,
            thread_id_override="",
        )
        request = {
            "schema": RUNTIME.SCHEMA,
            "enabled": True,
            "task_id": "smoke-task",
            "integration_branch": "develop",
            "request_nonce": "nonce-1",
            "frozen_contract_sha256": "b" * 64,
            "expected_integration_commit_sha": "d" * 40,
        }
        current = {
            "schema": RUNTIME.SCHEMA,
            "task_id": "smoke-task",
            "state": "PLANNER_REVISE_EXECUTOR",
            "review_round": 1,
            "request_nonce": "nonce-1",
            "frozen_contract_sha256": "b" * 64,
            "integration_commit_sha": "c" * 40,
        }
        result = RUNTIME.evaluate_watcher_event(args, request, current, {"processed_events": []})
        self.assertEqual(result["decision"], "INVALID_EVENT")
        self.assertIn("integration_commit_binding", result["failures"])


if __name__ == "__main__":
    unittest.main()
