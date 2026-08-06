from __future__ import annotations

import copy
import importlib.util
import json
import os
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

    def test_live_resume_records_command_env_and_exact_stdin(self) -> None:
        class FakePopen:
            calls = []

            def __init__(self, command, stdin, stdout, stderr, env):
                self.command = command
                self.env = env
                self.pid = 4242
                self.returncode = 0
                FakePopen.calls.append(self)

            def communicate(self, input):
                self.input = input
                return b"stdout-ok", b"stderr-ok"

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            receipt = RUNTIME.execute_live_resume(
                command=["/opt/codex", "exec", "-C", str(root / "worktree"), "resume", "thread-1", "-"],
                codex_home=str(root / "codex-home"),
                role="executor",
                task_id="smoke-task",
                state_root=root / "state",
                log_root=root / "logs",
                prompt_payload=b"exact repair prompt\n",
                prompt_path=root / "prompt.md",
                popen_factory=FakePopen,
            )
            self.assertEqual(FakePopen.calls[0].command[5], "thread-1")
            self.assertEqual(FakePopen.calls[0].env["CODEX_HOME"], str(root / "codex-home"))
            self.assertEqual(FakePopen.calls[0].input, b"exact repair prompt\n")
            self.assertEqual(receipt["exit_code"], 0)
            self.assertEqual(Path(receipt["stdout_log"]).read_bytes(), b"stdout-ok")
            self.assertEqual(Path(receipt["stderr_log"]).read_bytes(), b"stderr-ok")

    def test_watcher_rejects_stale_review_round(self) -> None:
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
            "expected_review_round": 3,
        }
        current = {
            "schema": RUNTIME.SCHEMA,
            "task_id": "smoke-task",
            "state": "PLANNER_REVISE_EXECUTOR",
            "review_round": 2,
            "request_nonce": "nonce-1",
            "frozen_contract_sha256": "b" * 64,
            "integration_commit_sha": "c" * 40,
        }
        result = RUNTIME.evaluate_watcher_event(args, request, current, {"processed_events": []})
        self.assertEqual(result["decision"], "INVALID_EVENT")
        self.assertIn("review_round_binding", result["failures"])

    def test_active_role_process_rejects_concurrent_resume(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            thread_file = root / "executor_thread_id"
            thread_file.write_text("thread-1\n", encoding="utf-8")
            role_plan = root / "role_plan.json"
            role_plan.write_text(
                json.dumps(
                    {
                        "roles": {
                            "executor": {
                                "thread_id_file": str(thread_file),
                                "codex_home": str(root / "home"),
                                "worktree": str(root / "worktree"),
                            }
                        }
                    }
                ),
                encoding="utf-8",
            )
            active_path = RUNTIME.active_process_path(root / "state", "smoke-task", "executor")
            active_path.parent.mkdir(parents=True)
            active_path.write_text(json.dumps({"pid": os.getpid(), "exit_code": None}), encoding="utf-8")
            args = argparse.Namespace(
                task_id="smoke-task",
                branch="develop",
                role_plan=str(role_plan),
                codex_bin="/opt/codex",
                state_root=root / "state",
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
            result = RUNTIME.evaluate_watcher_event(args, request, current, {"processed_events": []})
            self.assertEqual(result["decision"], "INVALID_EVENT")
            self.assertIn("executor:active_process", result["failures"])

    def test_watcher_restart_keeps_processed_state(self) -> None:
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
        receipt = {
            "task_id": "smoke-task",
            "decision": "DRY_RUN_RESUME",
            "event_key": "smoke-task:nonce-1:1:PLANNER_REVISE_EXECUTOR:" + "c" * 40,
            "updated_utc": "2026-08-05T00:00:00Z",
        }
        state = RUNTIME.update_watcher_state({"processed_events": []}, receipt)
        self.assertIn(receipt["event_key"], state["processed_events"])
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
        self.assertEqual(RUNTIME.evaluate_watcher_event(args, request, current, state)["decision"], "IGNORE")

    def test_planner_pass_stops_at_human_gate(self) -> None:
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
            "state": "PLANNER_PASS",
            "review_round": 4,
            "request_nonce": "nonce-1",
            "frozen_contract_sha256": "b" * 64,
            "integration_commit_sha": "c" * 40,
        }
        result = RUNTIME.evaluate_watcher_event(args, request, current, {"processed_events": []})
        self.assertEqual(result["decision"], "STOP_AT_HUMAN_GATE")

    def test_illegal_event_is_recorded_without_poisoning_next_event(self) -> None:
        invalid = {
            "task_id": "smoke-task",
            "decision": "INVALID_EVENT",
            "event_key": "bad-event",
            "failures": ["nonce_binding"],
            "updated_utc": "2026-08-05T00:00:00Z",
        }
        state = RUNTIME.update_watcher_state({"processed_events": []}, invalid)
        self.assertEqual(state["processed_events"], [])
        self.assertEqual(state["invalid_events"][0]["event_key"], "bad-event")

    def test_request_disabled_does_not_trigger_resume(self) -> None:
        args = argparse.Namespace(
            task_id="smoke-task",
            branch="develop",
            role_plan="/unused",
            codex_bin="/opt/codex",
            state_root=Path("/tmp"),
            session_receipt_root="/tmp/missing_receipts",
            dry_run=False,
            thread_id_override="",
        )
        request = {
            "schema": RUNTIME.SCHEMA,
            "enabled": False,
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
        self.assertEqual(result["decision"], "IGNORE_DISABLED")
        self.assertEqual(result["resume_commands"], [])

    def test_only_controller_is_allowed_to_push_develop(self) -> None:
        role_plan = {
            "integration_branch": "develop",
            "controller_pushes_integration_branch": True,
            "remote_role_branches_authorized": False,
            "roles": {"verifier": {}, "executor": {}},
        }
        self.assertEqual(RUNTIME.validate_role_plan_push_authority(role_plan), [])
        bad = copy.deepcopy(role_plan)
        bad["roles"]["executor"]["pushes_integration_branch"] = True
        self.assertIn("executor:pushes_integration_branch", RUNTIME.validate_role_plan_push_authority(bad))

    def test_visual_smoke_receipt_requires_scheduled_gpt_provenance(self) -> None:
        receipt = {
            "role": "planner_visual_smoke",
            "request_nonce": "nonce-1",
            "image_sha256": {
                "CARE-ASE": "a" * 64,
                "SRR-v3": "b" * 64,
                "MoSAIC": "c" * 64,
            },
            "answers": {
                "main_modules": "This answer is long enough to prove structured visual content.",
                "key_data_flow": "This answer is long enough to prove structured visual content.",
                "missing_modality_no_t2_safety": "This answer is long enough to prove structured visual content.",
                "explicitly_absent_components": "This answer is long enough to prove structured visual content.",
                "structural_differences": "This answer is long enough to prove structured visual content.",
            },
            "provenance": {"producer": "scheduled_gpt"},
        }
        self.assertEqual(
            RUNTIME.validate_visual_smoke_receipt(
                receipt,
                expected_role="planner_visual_smoke",
                request_nonce="nonce-1",
                expected_shas={"CARE-ASE": "a" * 64, "SRR-v3": "b" * 64, "MoSAIC": "c" * 64},
            ),
            [],
        )
        receipt["provenance"] = {"producer": "codex"}
        self.assertIn(
            "provenance:scheduled_gpt",
            RUNTIME.validate_visual_smoke_receipt(
                receipt,
                expected_role="planner_visual_smoke",
                request_nonce="nonce-1",
                expected_shas={"CARE-ASE": "a" * 64, "SRR-v3": "b" * 64, "MoSAIC": "c" * 64},
            ),
        )

    def test_visual_smoke_receipt_accepts_scheduled_planner_image_list_schema(self) -> None:
        receipt = {
            "role": "planner",
            "request_nonce": "nonce-1",
            "actual_visual_access": True,
            "access_context": "scheduled ChatGPT Planner visual review",
            "images": [
                {
                    "name": "CARE-ASE",
                    "sha256": "a" * 64,
                    "main_modules_visible": ["stock-compatible encoder and pathology branches"],
                    "key_dataflow": "Modalities enter a shared backbone and then branch into scar and edema routes.",
                    "missing_modality_and_no_t2_rules": ["No T2 excludes edema from final competition."],
                    "explicitly_absent_components": ["No Transformer block is shown."],
                },
                {
                    "name": "SRR-v3",
                    "sha256": "b" * 64,
                    "main_modules_visible": ["anchor logits and bounded residual correction"],
                    "key_dataflow": "Modality evidence is retrieved and written back through bounded correction.",
                    "missing_modality_and_no_t2_rules": ["Unavailable modalities are masked from retrieval."],
                    "explicitly_absent_components": ["No unrestricted replacement decoder is shown."],
                },
                {
                    "name": "MoSAIC",
                    "sha256": "c" * 64,
                    "main_modules_visible": ["coarse localization and independent pathology experts"],
                    "key_dataflow": "Coarse localization feeds fine pathology experts and output merging.",
                    "missing_modality_and_no_t2_rules": ["No explicit five-class no-T2 rule is visible."],
                    "explicitly_absent_components": ["No nnU-Net anchor residual correction is shown."],
                },
            ],
            "structural_differences": [
                "CARE-ASE is single-backbone reconstruction, SRR is anchor-bounded correction, and MoSAIC is coarse-to-fine experts."
            ],
        }
        self.assertEqual(
            RUNTIME.validate_visual_smoke_receipt(
                receipt,
                expected_role="planner_visual_smoke",
                request_nonce="nonce-1",
                expected_shas={"CARE-ASE": "a" * 64, "SRR-v3": "b" * 64, "MoSAIC": "c" * 64},
            ),
            [],
        )

    def test_visual_smoke_receipt_rejects_wrong_nonce_and_image_sha(self) -> None:
        receipt = {
            "role": "critic_visual_smoke",
            "request_nonce": "old-nonce",
            "image_sha256": {"CARE-ASE": "x", "SRR-v3": "b" * 64, "MoSAIC": "c" * 64},
            "answers": {},
            "provenance": {"producer": "scheduled_gpt"},
        }
        failures = RUNTIME.validate_visual_smoke_receipt(
            receipt,
            expected_role="critic_visual_smoke",
            request_nonce="new-nonce",
            expected_shas={"CARE-ASE": "a" * 64, "SRR-v3": "b" * 64, "MoSAIC": "c" * 64},
        )
        self.assertIn("request_nonce", failures)
        self.assertIn("image_sha256:CARE-ASE", failures)
        self.assertIn("answers:main_modules", failures)


if __name__ == "__main__":
    unittest.main()
