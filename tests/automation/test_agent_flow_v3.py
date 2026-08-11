from __future__ import annotations

import copy
import importlib.util
import json
import os
from pathlib import Path
import argparse
import subprocess
import tempfile
import unittest
from unittest import mock

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

SNAPSHOT_SCRIPT = ROOT / "scripts" / "automation" / "agent_flow_v3_snapshot.py"
SNAPSHOT_SPEC = importlib.util.spec_from_file_location("agent_flow_v3_snapshot", SNAPSHOT_SCRIPT)
assert SNAPSHOT_SPEC and SNAPSHOT_SPEC.loader
SNAPSHOT = importlib.util.module_from_spec(SNAPSHOT_SPEC)
SNAPSHOT_SPEC.loader.exec_module(SNAPSHOT)


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

    def test_stable_review_target_ignores_git_and_receipt_locators(self) -> None:
        stable_inputs = {
            "request_nonce": "nonce",
            "frozen_contract_sha256": "f" * 64,
            "requirement_ledger_sha256": "l" * 64,
            "implementation_critical_source_digest_sha256": "i" * 64,
            "verifier_critical_source_digest_sha256": "v" * 64,
        }
        first = SNAPSHOT.compute_review_target_id(stable_inputs)
        with_locator_noise = dict(stable_inputs)
        with_locator_noise.update(
            {
                "controller_merge_commit_sha": "a" * 40,
                "current_commit_sha": "b" * 40,
                "runtime_receipt_manifest_sha256": "r" * 64,
                "ci_receipt_commit_sha": "c" * 40,
            }
        )
        self.assertEqual(first, SNAPSHOT.compute_review_target_id(stable_inputs))
        self.assertEqual(first, SNAPSHOT.compute_review_target_id(with_locator_noise))
        self.assertNotIn("controller_merge_commit_sha", stable_inputs)

    def test_review_bundle_is_dag_child_not_snapshot_identity_input(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            repo = Path(tmpdir)
            for rel_path, payload in {
                "automation/agent_flow_v3/tasks/demo/CURRENT.json": {
                    "task_id": "demo",
                    "request_nonce": "nonce",
                    "frozen_contract_sha256": "f" * 64,
                },
                "automation/agent_flow_v3/tasks/demo/REQUIREMENT_LEDGER.json": {"requirements": []},
                "src/impl.py": {"impl": 1},
                "validators/verifier.py": {"verifier": 1},
                "results/demo/runtime.json": {"runtime": 1},
                "results/demo/verifier.json": {"verifier_receipt": 1},
                "results/demo/ci.json": {"ci": "success"},
            }.items():
                path = repo / rel_path
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text(json.dumps(payload, sort_keys=True), encoding="utf-8")
            args = argparse.Namespace(
                repo_root=repo,
                task_id="demo",
                current="automation/agent_flow_v3/tasks/demo/CURRENT.json",
                requirement_ledger="automation/agent_flow_v3/tasks/demo/REQUIREMENT_LEDGER.json",
                implementation_path=["src/impl.py"],
                verifier_path=["validators/verifier.py"],
                output="automation/agent_flow_v3/tasks/demo/SOURCE_SNAPSHOT.json",
            )
            snapshot = SNAPSHOT.build_source_snapshot(args)
            bundle_args = argparse.Namespace(
                repo_root=repo,
                snapshot="automation/agent_flow_v3/tasks/demo/SOURCE_SNAPSHOT.json",
                evidence=["results/demo/runtime.json", "results/demo/verifier.json", "results/demo/ci.json"],
                ci_pass=True,
                heavy_verifier_status="PASS",
                output="results/demo/REVIEW_BUNDLE.json",
            )
            bundle = SNAPSHOT.build_review_bundle(bundle_args)

            self.assertEqual(bundle["review_target_id"], snapshot["review_target_id"])
            self.assertEqual(0, SNAPSHOT.validate_snapshot(argparse.Namespace(repo_root=repo, snapshot=args.output)))
            self.assertEqual(0, SNAPSHOT.validate_bundle(argparse.Namespace(repo_root=repo, bundle=bundle_args.output)))

            old_target = snapshot["review_target_id"]
            (repo / "results/demo/ci.json").write_text(json.dumps({"ci": "success", "rerun": 2}), encoding="utf-8")
            updated_bundle = SNAPSHOT.build_review_bundle(bundle_args)
            reread_snapshot = json.loads((repo / args.output).read_text(encoding="utf-8"))
            self.assertEqual(old_target, reread_snapshot["review_target_id"])
            self.assertNotEqual(bundle["review_bundle_sha256"], updated_bundle["review_bundle_sha256"])

    def test_scheduled_planner_prompt_reviews_waiting_for_external_gpt(self) -> None:
        prompt = (ROOT / "automation" / "agent_flow_v3" / "planner_scheduled_task_prompt.md").read_text(
            encoding="utf-8"
        )
        self.assertIn("WAITING_FOR_EXTERNAL_GPT", prompt)
        self.assertIn("planner_review_packet_path", prompt)
        self.assertIn("implementation/integration SHA", prompt)

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

    def test_codex_resume_command_adds_git_common_dir(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            worktree = root / "worktree"
            common = root / ".git"
            worktree.mkdir()
            common.mkdir()
            with mock.patch.object(RUNTIME, "git", return_value=str(common)):
                command = RUNTIME.build_resume_command("/opt/codex", worktree, "thread-1")
            self.assertIn("--add-dir", command)
            self.assertIn(str(common), command)
            self.assertEqual(command[-4:], ["resume", "--all", "thread-1", "-"])

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

    def test_needs_user_scientific_choice_is_valid_exception_state(self) -> None:
        request = copy.deepcopy(self.template)
        request["frozen_contract_sha256"] = "a" * 64
        current = {
            "schema": "CARE_AGENT_FLOW_V3",
            "task_id": request["task_id"],
            "state": "NEEDS_USER_SCIENTIFIC_CHOICE",
            "review_round": 1,
            "request_nonce": "nonce",
            "frozen_contract_sha256": request["frozen_contract_sha256"],
            "integration_commit_sha": "b" * 40,
            "implementation_fingerprint_sha256": "c" * 64,
            "verifier_fingerprint_sha256": "d" * 64,
            "next_action": "AWAIT_HUMAN_DECISION_ON_TILE_LOCAL_EXACTNESS_CONTRACT",
            "updated_utc": "2026-08-05T00:00:00Z",
        }
        self.assertEqual(MODULE.validate_current(current, request, self.schema), [])

    def test_waiting_for_external_gpt_requires_deadline_metadata(self) -> None:
        request = copy.deepcopy(self.template)
        request["frozen_contract_sha256"] = "a" * 64
        current = {
            "schema": "CARE_AGENT_FLOW_V3",
            "task_id": request["task_id"],
            "state": "WAITING_FOR_EXTERNAL_GPT",
            "review_round": 1,
            "request_nonce": "nonce",
            "frozen_contract_sha256": request["frozen_contract_sha256"],
            "integration_commit_sha": "b" * 40,
            "implementation_fingerprint_sha256": None,
            "verifier_fingerprint_sha256": None,
            "next_action": "KEEP_FETCHING_ORIGIN_DEVELOP_UNTIL_EXPECTED_GPT_STATE_OR_ARTIFACT",
            "updated_utc": "2026-08-05T00:00:00Z",
        }
        failures = MODULE.validate_current(current, request, self.schema)
        self.assertIn("external_wait_missing:external_wait_started_utc", failures)
        current.update(
            {
                "external_wait_started_utc": "2026-08-05T00:00:00Z",
                "external_wait_deadline_utc": "2026-08-05T04:00:00Z",
                "expected_state_or_artifact": "planner review",
                "last_observed_remote_sha": "c" * 40,
                "last_poll_utc": "2026-08-05T00:10:00Z",
            }
        )
        self.assertEqual(MODULE.validate_current(current, request, self.schema), [])

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

    def test_production_role_receipt_requires_rollout_in_codex_home(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)

            def receipt(role: str, idx: int, rollout_home: Path | None = None) -> dict[str, object]:
                codex_home = root / f"{role}_home"
                codex_home.mkdir(exist_ok=True)
                thread_id = f"thread-{idx}"
                rollout_path = None
                if rollout_home is not None:
                    rollout_path = rollout_home / "sessions" / "2026" / "08" / "06" / f"rollout-{thread_id}.jsonl"
                    rollout_path.parent.mkdir(parents=True, exist_ok=True)
                    rollout_path.write_text("{}\n", encoding="utf-8")
                return {
                    "schema": RUNTIME.ROLE_RECEIPT_SCHEMA,
                    "role": role,
                    "thread_id": thread_id,
                    "codex_home": str(codex_home),
                    "worktree": str(root / f"{role}_worktree"),
                    "local_branch": f"local/{role}/test",
                    "pid_or_process_status": "production_thread_ready",
                    "log_path": str(root / f"{role}.log"),
                    "state_path": str(root / f"{role}.json"),
                    "write_scope": ["results/**"],
                    "forbidden_scope": ["src/**"],
                    "last_commit_sha": "a" * 40,
                    "started_utc": "2026-08-05T00:00:00Z",
                    "updated_utc": "2026-08-05T00:00:00Z",
                    "production_eligible": True,
                    "resume_verified": True,
                    "launch_command": "codex exec --json -C worktree -",
                    "launch_prompt_sha256": "b" * 64,
                    "launch_exit_code": 0,
                    "launch_started_utc": "2026-08-05T00:00:00Z",
                    "launch_finished_utc": "2026-08-05T00:00:01Z",
                    "resume_command": "codex exec -C worktree resume thread -",
                    "resume_prompt_sha256": "c" * 64,
                    "resume_exit_code": 0,
                    "resume_started_utc": "2026-08-05T00:00:02Z",
                    "resume_finished_utc": "2026-08-05T00:00:03Z",
                    "rollout_session_path": str(rollout_path) if rollout_path else "",
                }

            receipts = {
                role: receipt(role, idx)
                for idx, role in enumerate(("controller", "verifier", "executor"), start=1)
            }
            failures = RUNTIME.validate_role_receipts(receipts, require_production=True)
            self.assertIn("controller:rollout_missing", failures)
            self.assertIn("verifier:rollout_missing", failures)
            self.assertIn("executor:rollout_missing", failures)

            wrong_home = root / "wrong_home"
            receipts["controller"] = receipt("controller", 1, rollout_home=wrong_home)
            failures = RUNTIME.validate_role_receipts(receipts, require_production=True)
            self.assertIn("controller:rollout_wrong_codex_home", failures)

            receipts = {
                role: receipt(role, idx, rollout_home=root / f"{role}_home")
                for idx, role in enumerate(("controller", "verifier", "executor"), start=1)
            }
            self.assertEqual(RUNTIME.validate_role_receipts(receipts, require_production=True), [])

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
            self.assertIn("--all", receipt["resume_commands"][0]["command"])
            self.assertNotIn("--last", receipt["resume_commands"][0]["command"])

    def test_repair_prompt_can_load_from_git_ref_when_local_checkout_lags(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            subprocess.run(["git", "init"], cwd=root, check=True, stdout=subprocess.DEVNULL)
            subprocess.run(["git", "config", "user.email", "test@example.invalid"], cwd=root, check=True)
            subprocess.run(["git", "config", "user.name", "Test User"], cwd=root, check=True)
            prompt_path = root / "results" / "agent_flow_v3" / "smoke-task" / "planner_reviews" / "round_000.json"
            prompt_path.parent.mkdir(parents=True)
            prompt_payload = b'{"decision":"PLANNER_REVISE_EXECUTOR","required_repair":["add marker"]}\n'
            prompt_path.write_bytes(prompt_payload)
            subprocess.run(["git", "add", "."], cwd=root, check=True)
            subprocess.run(["git", "commit", "-m", "add prompt"], cwd=root, check=True, stdout=subprocess.DEVNULL)
            subprocess.run(["git", "branch", "develop"], cwd=root, check=True)
            prompt_path.unlink()

            payload, path, prompt_sha = RUNTIME.load_exact_repair_prompt(
                root,
                "smoke-task",
                "executor",
                {
                    "review_round": 0,
                    "repair_prompts": {
                        "executor": "results/agent_flow_v3/smoke-task/planner_reviews/round_000.json",
                    },
                },
                ref="develop",
            )

            self.assertEqual(payload, prompt_payload)
            self.assertEqual(path, prompt_path)
            self.assertEqual(prompt_sha, RUNTIME.sha_bytes(prompt_payload))

    def test_watcher_default_paths_follow_task_id(self) -> None:
        args = argparse.Namespace(
            repo_root=ROOT,
            task_id="gpt-loop-smoke-b",
            request_path=None,
            current_path=None,
            role_plan=None,
            session_receipt_root=None,
        )

        resolved = RUNTIME.resolve_watcher_paths(args)

        self.assertEqual(
            resolved.request_path,
            "automation/agent_flow_v3/tasks/gpt-loop-smoke-b/REQUEST.json",
        )
        self.assertEqual(
            resolved.current_path,
            "automation/agent_flow_v3/tasks/gpt-loop-smoke-b/CURRENT.json",
        )
        self.assertEqual(
            resolved.role_plan,
            "automation/agent_flow_v3/tasks/gpt-loop-smoke-b/ROLE_PLAN.json",
        )
        self.assertEqual(resolved.session_receipt_root, "results/agent_flow_v3/gpt-loop-smoke-b")

    def test_orchestrator_stage_key_is_not_remote_sha_scoped(self) -> None:
        current = {
            "request_nonce": "nonce-1",
            "review_round": 0,
            "state": "PLAN_FROZEN",
        }
        first = RUNTIME.stage_event_key("care-ase-faithful", current, "a" * 40)
        second = RUNTIME.stage_event_key("care-ase-faithful", current, "b" * 40)
        legacy_processed = {f"{first}:{'a' * 40}"}

        self.assertEqual(first, second)
        self.assertTrue(RUNTIME.stage_event_was_processed(second, legacy_processed))

        receipt = RUNTIME.evaluate_stage_event(
            task_id="care-ase-faithful",
            request={"enabled": True},
            current=current,
            visual_final=None,
            remote_sha="b" * 40,
            processed=legacy_processed,
            default_wait_hours=4,
        )
        self.assertEqual(receipt["decision"], "IGNORE_PROCESSED")

    def test_care_ase_plan_frozen_is_not_processed_without_controller_start(self) -> None:
        event = {
            "task_id": "care-ase-faithful",
            "state": "PLAN_FROZEN",
            "decision": "STAGE_READY",
        }

        self.assertFalse(RUNTIME.stage_event_should_mark_processed(event))

        visual_event = {
            "task_id": "care-visual-smoke",
            "state": "PLAN_FROZEN",
            "decision": "STAGE_READY",
        }
        self.assertTrue(RUNTIME.stage_event_should_mark_processed(visual_event))

    def test_care_ase_verifier_running_routes_to_freeze_integration(self) -> None:
        current = {
            "task_id": "care-ase-faithful",
            "request_nonce": "care-ase-nonce",
            "review_round": 0,
            "state": "VERIFIER_RUNNING",
            "frozen_contract_sha256": "a" * 64,
        }

        receipt = RUNTIME.evaluate_stage_event(
            task_id="care-ase-faithful",
            request={"enabled": True, "request_nonce": "care-ase-nonce", "frozen_contract_sha256": "a" * 64},
            current=current,
            visual_final=None,
            remote_sha="b" * 40,
            processed=set(),
            default_wait_hours=4,
        )

        self.assertEqual(receipt["decision"], "CONTROLLER_UPDATE_REQUIRED")
        self.assertIn("Verifier freeze", receipt["action"])

    def test_care_ase_verifier_frozen_is_not_processed_without_executor_start(self) -> None:
        event = {
            "task_id": "care-ase-faithful",
            "state": "VERIFIER_FROZEN",
            "decision": "STAGE_READY",
        }

        self.assertFalse(RUNTIME.stage_event_should_mark_processed(event))

    def test_care_ase_verifier_frozen_scope_complete_routes_to_verifier_recheck(self) -> None:
        current = {
            "task_id": "care-ase-faithful",
            "request_nonce": "care-ase-nonce",
            "review_round": 1,
            "state": "VERIFIER_FROZEN",
            "frozen_contract_sha256": "a" * 64,
        }

        receipt = RUNTIME.evaluate_stage_event(
            task_id="care-ase-faithful",
            request={"enabled": True, "request_nonce": "care-ase-nonce", "frozen_contract_sha256": "a" * 64},
            current=current,
            visual_final=None,
            remote_sha="b" * 40,
            processed=set(),
            default_wait_hours=4,
            care_ase_executor_needs_verifier_recheck=True,
        )

        self.assertEqual(receipt["decision"], "CONTROLLER_UPDATE_REQUIRED")
        self.assertIn("Verifier receipt recheck", receipt["action"])

    def test_care_ase_provenance_rebind_ready_routes_to_controller_update(self) -> None:
        current = {
            "task_id": "care-ase-faithful",
            "request_nonce": "care-ase-nonce",
            "review_round": 1,
            "state": "PROVENANCE_REBIND_REQUIRED",
            "frozen_contract_sha256": "a" * 64,
        }

        receipt = RUNTIME.evaluate_stage_event(
            task_id="care-ase-faithful",
            request={"enabled": True, "request_nonce": "care-ase-nonce", "frozen_contract_sha256": "a" * 64},
            current=current,
            visual_final=None,
            remote_sha="b" * 40,
            processed=set(),
            default_wait_hours=4,
            care_ase_executor_needs_verifier_recheck=True,
        )

        self.assertEqual(receipt["decision"], "CONTROLLER_UPDATE_REQUIRED")
        self.assertIn("provenance/runtime rebind", receipt["action"])

    def test_care_ase_provenance_rebind_local_commit_prevents_duplicate_start(self) -> None:
        current = {
            "task_id": "care-ase-faithful",
            "request_nonce": "care-ase-nonce",
            "review_round": 1,
            "state": "PROVENANCE_REBIND_REQUIRED",
            "frozen_contract_sha256": "a" * 64,
        }

        receipt = RUNTIME.evaluate_stage_event(
            task_id="care-ase-faithful",
            request={"enabled": True, "request_nonce": "care-ase-nonce", "frozen_contract_sha256": "a" * 64},
            current=current,
            visual_final=None,
            remote_sha="b" * 40,
            processed=set(),
            default_wait_hours=4,
            care_ase_executor_local_commit_pending_controller=True,
        )

        self.assertEqual(receipt["decision"], "MONITOR_ONLY")
        self.assertIn("instead of launching a duplicate", receipt["action"])

    def test_care_ase_executor_local_commit_pending_controller_prevents_duplicate_start(self) -> None:
        current = {
            "task_id": "care-ase-faithful",
            "request_nonce": "care-ase-nonce",
            "review_round": 1,
            "state": "VERIFIER_FROZEN",
            "frozen_contract_sha256": "a" * 64,
        }

        receipt = RUNTIME.evaluate_stage_event(
            task_id="care-ase-faithful",
            request={"enabled": True, "request_nonce": "care-ase-nonce", "frozen_contract_sha256": "a" * 64},
            current=current,
            visual_final=None,
            remote_sha="b" * 40,
            processed=set(),
            default_wait_hours=4,
            care_ase_executor_local_commit_pending_controller=True,
        )

        self.assertEqual(receipt["decision"], "MONITOR_ONLY")
        self.assertIn("instead of launching a duplicate", receipt["action"])

    def test_care_ase_executor_local_commit_pending_controller_detects_scope_valid_ahead_commit(self) -> None:
        current = {
            "task_id": "care-ase-faithful",
            "request_nonce": "care-ase-nonce",
            "review_round": 1,
            "state": "VERIFIER_FROZEN",
            "frozen_contract_sha256": "a" * 64,
        }
        args = argparse.Namespace(branch="develop")

        def fake_git(_repo: Path, *cmd: str) -> str:
            if cmd[0] == "fetch":
                return ""
            if cmd[:2] == ("rev-parse", "HEAD"):
                return "1" * 40
            if cmd[0] == "merge-base":
                return "0" * 40
            if cmd[:2] == ("diff", "--name-only"):
                return "src/care_myocardium/training/care_ase_runtime.py\n"
            raise AssertionError(cmd)

        with (
            mock.patch.object(
                RUNTIME,
                "load_care_ase_executor_binding",
                return_value=(
                    {},
                    {"write_scope": ["src/**", "results/agent_flow_v3/care-ase-faithful/implementation/**"]},
                    Path("/tmp/executor"),
                    "/tmp/codex-home",
                    "thread-1",
                ),
            ),
            mock.patch.object(Path, "is_dir", return_value=True),
            mock.patch.object(RUNTIME, "git_status_short", return_value=""),
            mock.patch.object(RUNTIME, "git", side_effect=fake_git),
        ):
            self.assertTrue(RUNTIME.care_ase_executor_local_commit_pending_controller(args, current))

    def test_care_ase_executor_pending_verifier_recheck_receipt_prevents_duplicate_start(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            worktree = Path(tmp) / "executor"
            implementation_dir = worktree / "results" / "agent_flow_v3" / "care-ase-faithful" / "implementation"
            implementation_dir.mkdir(parents=True)
            (implementation_dir / "result.md").write_text(
                "- status: `IMPLEMENTATION_EVIDENCE_READY_PENDING_VERIFIER_RECHECK`\n",
                encoding="utf-8",
            )
            (implementation_dir / "implementation_evidence_validation_result.json").write_text(
                json.dumps(
                    {
                        "passed": False,
                        "failure_count": 4,
                        "failures": [
                            "verifier_owned.executable.passed",
                            "verifier_owned.loss_semantic.injury_dice_bce_formula",
                            "verifier_owned.transaction.status",
                            "verifier_owned.transaction.hosted_ci_success",
                        ],
                    }
                ),
                encoding="utf-8",
            )
            (implementation_dir / "implementation_fingerprint.json").write_text(
                json.dumps(
                    {
                        "frozen_contract_sha256": "a" * 64,
                        "request_nonce": "care-ase-nonce",
                        "verifier_fingerprint_sha256": "b" * 64,
                        "implementation_fingerprint_sha256": "c" * 64,
                        "implementation_evidence_sha256": "d" * 64,
                        "source_manifest_sha256": "e" * 64,
                    }
                ),
                encoding="utf-8",
            )
            (implementation_dir / "implementation_evidence.json").write_text(
                json.dumps({"implementation_evidence_sha256": "d" * 64, "source_manifest_sha256": "e" * 64}),
                encoding="utf-8",
            )
            (implementation_dir / "implementation_source_manifest.json").write_text(
                json.dumps(
                    {
                        "frozen_contract_sha256": "a" * 64,
                        "request_nonce": "care-ase-nonce",
                        "source_manifest_sha256": "e" * 64,
                    }
                ),
                encoding="utf-8",
            )
            (implementation_dir / "runtime_asset_manifest.json").write_text("{}", encoding="utf-8")

            current = {
                "task_id": "care-ase-faithful",
                "request_nonce": "care-ase-nonce",
                "review_round": 1,
                "state": "VERIFIER_FROZEN",
                "frozen_contract_sha256": "a" * 64,
                "verifier_fingerprint_sha256": "b" * 64,
            }
            args = argparse.Namespace(branch="develop")

            def fake_git(_repo: Path, *cmd: str) -> str:
                if cmd[0] == "fetch":
                    return ""
                if cmd[:2] == ("rev-parse", "HEAD"):
                    return "1" * 40
                if cmd[0] == "merge-base":
                    return "0" * 40
                if cmd[:2] == ("diff", "--name-only"):
                    return "src/care_myocardium/training/care_ase_trainer.py\n"
                raise AssertionError(cmd)

            with (
                mock.patch.object(
                    RUNTIME,
                    "load_care_ase_executor_binding",
                    return_value=(
                        {},
                        {"write_scope": ["src/**", "results/agent_flow_v3/care-ase-faithful/implementation/**"]},
                        worktree,
                        "/tmp/codex-home",
                        "thread-1",
                    ),
                ),
                mock.patch.object(RUNTIME, "validate_role_plan_push_authority", return_value=[]),
                mock.patch.object(RUNTIME, "git_status_short", return_value=""),
                mock.patch.object(RUNTIME, "role_rollout_goal_complete", return_value={"status": "complete"}),
                mock.patch.object(RUNTIME, "git", side_effect=fake_git),
                mock.patch.object(RUNTIME, "git_commit_subject", return_value="executor: repair care ase loss semantics"),
            ):
                self.assertTrue(RUNTIME.care_ase_executor_scope_complete_pending_verifier_recheck_available(args, current))

            with (
                mock.patch.object(
                    RUNTIME,
                    "load_care_ase_executor_binding",
                    return_value=(
                        {},
                        {"write_scope": ["src/**", "results/agent_flow_v3/care-ase-faithful/implementation/**"]},
                        worktree,
                        "/tmp/codex-home",
                        "thread-1",
                    ),
                ),
                mock.patch.object(RUNTIME, "validate_role_plan_push_authority", return_value=[]),
                mock.patch.object(RUNTIME, "git_status_short", return_value=""),
                mock.patch.object(RUNTIME, "role_rollout_goal_complete", return_value=None),
                mock.patch.object(RUNTIME, "role_active_process", return_value=None),
                mock.patch.object(RUNTIME, "git", side_effect=fake_git),
                mock.patch.object(RUNTIME, "git_commit_subject", return_value="executor: repair care ase loss semantics"),
            ):
                completion = RUNTIME.validate_care_ase_executor_completion(
                    args=args,
                    request={"enabled": True, "request_nonce": "care-ase-nonce", "frozen_contract_sha256": "a" * 64},
                    current=current,
                    allow_verifier_recheck=True,
                )

            self.assertTrue(completion["requires_verifier_recheck"])
            self.assertIsNone(completion["goal_complete"])

            validation_path = implementation_dir / "implementation_evidence_validation_result.json"
            validation = json.loads(validation_path.read_text(encoding="utf-8"))
            validation["failures"].append("implementation.loss_formula.contract_violation")
            validation_path.write_text(json.dumps(validation), encoding="utf-8")

            with (
                mock.patch.object(
                    RUNTIME,
                    "load_care_ase_executor_binding",
                    return_value=(
                        {},
                        {"write_scope": ["src/**", "results/agent_flow_v3/care-ase-faithful/implementation/**"]},
                        worktree,
                        "/tmp/codex-home",
                        "thread-1",
                    ),
                ),
                mock.patch.object(RUNTIME, "validate_role_plan_push_authority", return_value=[]),
                mock.patch.object(RUNTIME, "git_status_short", return_value=""),
                mock.patch.object(RUNTIME, "role_rollout_goal_complete", return_value={"status": "complete"}),
                mock.patch.object(RUNTIME, "git", side_effect=fake_git),
                mock.patch.object(RUNTIME, "git_commit_subject", return_value="executor: repair care ase loss semantics"),
            ):
                self.assertFalse(RUNTIME.care_ase_executor_scope_complete_pending_verifier_recheck_available(args, current))

    def test_care_ase_stale_verifier_receipt_failures_route_to_recheck_not_executor_restart(self) -> None:
        failures = [
            "verifier_owned.executable.reviewed_verifier_fingerprint",
            "verifier_owned.executable.passed",
            "verifier_owned.executable.status",
            "verifier_owned.executable.runtime_binding_sha:architecture_signature",
            "verifier_owned.executable.runtime_binding_sha:checkpoint_resume_probe",
            "verifier_owned.partial_hw.cross_z_partial_feature_grad_zero",
            "verifier_owned.partial_hw.cross_z_partial_feature_grad_abs_zero",
            "verifier_owned.eligible_normalization.status",
            "verifier_owned.eligible_normalization.edema_no_t2_invariant",
            "verifier_owned.eligible_normalization.injury_no_t2_invariant",
            "verifier_owned.eligible_normalization.conditional_final_unequal_groups",
            "verifier_owned.transaction.reviewed_verifier_fingerprint",
            "verifier_owned.transaction.status",
            "verifier_owned.transaction.no_failures",
            "verifier_owned.transaction.hosted_ci_success",
            "verifier_owned.transaction.no_stale_planner_reuse",
        ]

        self.assertTrue(
            RUNTIME.care_ase_validation_failures_require_verifier_recheck(
                {"passed": False, "failure_count": len(failures), "failures": failures}
            )
        )
        self.assertFalse(
            RUNTIME.care_ase_validation_failures_require_verifier_recheck(
                {"passed": False, "failure_count": len(failures) + 1, "failures": failures + ["implementation.loss_formula.contract_violation"]}
            )
        )

    def test_care_ase_fail_closed_uncited_tile_local_threshold_does_not_route_to_user_choice(self) -> None:
        current = {
            "task_id": "care-ase-faithful",
            "request_nonce": "care-ase-nonce",
            "review_round": 1,
            "state": "VERIFIER_FROZEN",
            "frozen_contract_sha256": "a" * 64,
            "verifier_fingerprint_sha256": "b" * 64,
        }
        fail_closed = {
            "status": "FAIL_CLOSED",
            "implementation_complete": False,
            "request_nonce": "care-ase-nonce",
            "frozen_contract_sha256": "a" * 64,
            "verifier_fingerprint_sha256": "b" * 64,
            "reason": "true tile-local forwards do not match; reintroducing full-support pseudo-tiling is forbidden",
            "diagnostic_executable_verifier": {
                "exit_code": 2,
                "verifier_fingerprint_sha256": "b" * 64,
                "full_support_pseudo_tiling_detected": False,
                "remaining_executor_relevant_failures": [
                    "single_vs_forced_multi_tile_full_volume",
                    "tile_local_forward_instrumentation",
                ],
            },
        }

        self.assertFalse(RUNTIME.care_ase_fail_closed_requires_user_scientific_choice(fail_closed, current))

        receipt = RUNTIME.evaluate_stage_event(
            task_id="care-ase-faithful",
            request={"enabled": True, "request_nonce": "care-ase-nonce", "frozen_contract_sha256": "a" * 64},
            current=current,
            visual_final=None,
            remote_sha="c" * 40,
            processed=set(),
            default_wait_hours=4,
            care_ase_executor_needs_user_scientific_choice=RUNTIME.care_ase_fail_closed_requires_user_scientific_choice(fail_closed, current),
        )

        self.assertEqual(receipt["decision"], "STAGE_READY")
        self.assertIn("start persistent CARE-ASE Executor", receipt["action"])

    def test_care_ase_user_scientific_choice_requires_cited_contract_conflict(self) -> None:
        current = {
            "task_id": "care-ase-faithful",
            "request_nonce": "care-ase-nonce",
            "review_round": 1,
            "state": "VERIFIER_FROZEN",
            "frozen_contract_sha256": "a" * 64,
            "verifier_fingerprint_sha256": "b" * 64,
        }
        fail_closed = {
            "status": "FAIL_CLOSED",
            "implementation_complete": False,
            "request_nonce": "care-ase-nonce",
            "frozen_contract_sha256": "a" * 64,
            "verifier_fingerprint_sha256": "b" * 64,
            "diagnostic_executable_verifier": {
                "exit_code": 2,
                "verifier_fingerprint_sha256": "b" * 64,
                "remaining_executor_relevant_failures": ["contract_internal_conflict"],
            },
            "scientific_choice_contract_citations": [
                {
                    "contract_source_path": "automation/agent_flow_v3/tasks/care-ase-faithful/FROZEN_CONTRACT.md",
                    "contract_field_or_exact_clause": "section A",
                    "logical_derivation": "requires incompatible architecture A",
                },
                {
                    "contract_source_path": "automation/agent_flow_v3/tasks/care-ase-faithful/FROZEN_CONTRACT.md",
                    "contract_field_or_exact_clause": "section B",
                    "logical_derivation": "requires incompatible architecture B",
                },
            ],
            "scientific_contract_fields_requiring_change": ["architecture.high_resolution_paths"],
            "scientific_semantics_changed_by_required_decision": ["architecture"],
            "same_scope_repairs_exhausted": {
                "executor_repair": True,
                "verifier_repair": True,
                "runtime_repair": True,
                "transaction_rebind": True,
            },
        }

        self.assertTrue(RUNTIME.care_ase_fail_closed_requires_user_scientific_choice(fail_closed, current))

    def test_care_ase_user_scientific_choice_rejects_verifier_added_uncited_threshold(self) -> None:
        current = {
            "task_id": "care-ase-faithful",
            "request_nonce": "care-ase-nonce",
            "review_round": 1,
            "state": "VERIFIER_FROZEN",
            "frozen_contract_sha256": "a" * 64,
            "verifier_fingerprint_sha256": "b" * 64,
        }
        fail_closed = {
            "status": "FAIL_CLOSED",
            "implementation_complete": False,
            "request_nonce": "care-ase-nonce",
            "frozen_contract_sha256": "a" * 64,
            "verifier_fingerprint_sha256": "b" * 64,
            "diagnostic_executable_verifier": {
                "exit_code": 2,
                "verifier_fingerprint_sha256": "b" * 64,
                "remaining_executor_relevant_failures": ["VERIFIER_ADDED_UNCITED_NUMERIC_THRESHOLD"],
            },
            "scientific_choice_contract_citations": [
                {
                    "contract_source_path": "automation/agent_flow_v3/tasks/care-ase-faithful/FROZEN_CONTRACT.md",
                    "contract_field_or_exact_clause": "section A",
                    "logical_derivation": "requires incompatible architecture A",
                },
                {
                    "contract_source_path": "automation/agent_flow_v3/tasks/care-ase-faithful/FROZEN_CONTRACT.md",
                    "contract_field_or_exact_clause": "section B",
                    "logical_derivation": "requires incompatible architecture B",
                },
            ],
            "scientific_contract_fields_requiring_change": ["architecture.high_resolution_paths"],
            "scientific_semantics_changed_by_required_decision": ["architecture"],
            "same_scope_repairs_exhausted": {
                "executor_repair": True,
                "verifier_repair": True,
                "runtime_repair": True,
                "transaction_rebind": True,
            },
        }

        self.assertFalse(RUNTIME.care_ase_fail_closed_requires_user_scientific_choice(fail_closed, current))

    def test_care_ase_user_scientific_choice_rejects_available_same_scope_repairs(self) -> None:
        current = {
            "task_id": "care-ase-faithful",
            "request_nonce": "care-ase-nonce",
            "review_round": 1,
            "state": "VERIFIER_FROZEN",
            "frozen_contract_sha256": "a" * 64,
            "verifier_fingerprint_sha256": "b" * 64,
        }
        fail_closed = {
            "status": "FAIL_CLOSED",
            "implementation_complete": False,
            "request_nonce": "care-ase-nonce",
            "frozen_contract_sha256": "a" * 64,
            "verifier_fingerprint_sha256": "b" * 64,
            "diagnostic_executable_verifier": {
                "exit_code": 2,
                "verifier_fingerprint_sha256": "b" * 64,
                "remaining_executor_relevant_failures": ["contract_internal_conflict"],
            },
            "scientific_choice_contract_citations": [
                {
                    "contract_source_path": "automation/agent_flow_v3/tasks/care-ase-faithful/FROZEN_CONTRACT.md",
                    "contract_field_or_exact_clause": "section A",
                    "logical_derivation": "requires incompatible architecture A",
                },
                {
                    "contract_source_path": "automation/agent_flow_v3/tasks/care-ase-faithful/FROZEN_CONTRACT.md",
                    "contract_field_or_exact_clause": "section B",
                    "logical_derivation": "requires incompatible architecture B",
                },
            ],
            "scientific_contract_fields_requiring_change": ["architecture.high_resolution_paths"],
            "scientific_semantics_changed_by_required_decision": ["architecture"],
            "same_scope_repairs_exhausted": {
                "executor_repair": False,
                "verifier_repair": True,
                "runtime_repair": True,
                "transaction_rebind": True,
            },
        }

        self.assertFalse(RUNTIME.care_ase_fail_closed_requires_user_scientific_choice(fail_closed, current))

    def test_care_ase_fail_closed_can_route_same_scope_verifier_recheck(self) -> None:
        current = {
            "task_id": "care-ase-faithful",
            "request_nonce": "care-ase-nonce",
            "review_round": 1,
            "state": "VERIFIER_FROZEN",
            "frozen_contract_sha256": "a" * 64,
            "verifier_fingerprint_sha256": "b" * 64,
        }
        fail_closed = {
            "status": "FAIL_CLOSED",
            "implementation_complete": False,
            "request_nonce": "care-ase-nonce",
            "frozen_contract_sha256": "a" * 64,
            "verifier_fingerprint_sha256": "b" * 64,
            "closed_findings": {
                "disable_flag_final_logit_contribution_sites": [],
                "implementation_flags_match_verifier_owned_removal": True,
                "authority_oracle_all_required_groups_have_verifier_owned_delta": True,
                "formal_training_started": False,
                "outer_accessed": False,
                "docker_or_upload": False,
            },
            "remaining_blocker": {
                "id": "VERIFIER_LEGACY_FRESH_MODEL_DISABLE_FLAG_DELTA_CONFLICT",
                "needed_next_role": "verifier",
            },
            "current_reentry_recheck": {
                "implementation_decision": "no_contract_compliant_executor_repair_available_for_unchanged_verifier_fingerprint"
            },
        }

        self.assertTrue(RUNTIME.care_ase_fail_closed_requires_verifier_recheck(fail_closed, current))
        self.assertFalse(RUNTIME.care_ase_fail_closed_requires_user_scientific_choice(fail_closed, current))

    def test_care_ase_verifier_recheck_required_is_not_processed_before_start(self) -> None:
        event = {
            "task_id": "care-ase-faithful",
            "state": "VERIFIER_RECHECK_REQUIRED",
            "decision": "STAGE_READY",
        }

        self.assertFalse(RUNTIME.stage_event_should_mark_processed(event))

        receipt = RUNTIME.evaluate_stage_event(
            task_id="care-ase-faithful",
            request={"enabled": True},
            current={"request_nonce": "nonce", "review_round": 1, "state": "VERIFIER_RECHECK_REQUIRED"},
            visual_final=None,
            remote_sha="b" * 40,
            processed=set(),
            default_wait_hours=4,
        )

        self.assertEqual(receipt["decision"], "STAGE_READY")
        self.assertIn("Verifier recheck", receipt["action"])

    def test_care_ase_verifier_recheck_processed_event_retries_when_launch_exited(self) -> None:
        current = {
            "task_id": "care-ase-faithful",
            "request_nonce": "care-ase-nonce",
            "review_round": 1,
            "state": "VERIFIER_RECHECK_REQUIRED",
            "frozen_contract_sha256": "a" * 64,
        }
        event_key = "care-ase-faithful:care-ase-nonce:1:VERIFIER_RECHECK_REQUIRED:review.json"
        processed = {event_key}

        with mock.patch.object(RUNTIME, "care_ase_role_launch_satisfied", return_value=False):
            self.assertTrue(
                RUNTIME.care_ase_verifier_recheck_needs_exact_resume_retry(
                    Path("/tmp/stage"),
                    current,
                    processed,
                    event_key,
                    verifier_recheck_complete=False,
                )
            )

        with mock.patch.object(RUNTIME, "care_ase_role_launch_satisfied", return_value=True):
            self.assertFalse(
                RUNTIME.care_ase_verifier_recheck_needs_exact_resume_retry(
                    Path("/tmp/stage"),
                    current,
                    processed,
                    event_key,
                    verifier_recheck_complete=False,
                )
            )

        with mock.patch.object(RUNTIME, "care_ase_role_launch_satisfied", return_value=False):
            self.assertFalse(
                RUNTIME.care_ase_verifier_recheck_needs_exact_resume_retry(
                    Path("/tmp/stage"),
                    current,
                    processed,
                    event_key,
                    verifier_recheck_complete=True,
                )
            )

    def test_care_ase_verifier_recheck_complete_routes_to_controller_update(self) -> None:
        for state in ("VERIFIER_RECHECK_REQUIRED", "POST_CI_VERIFIER_RECHECK_REQUIRED"):
            with self.subTest(state=state):
                receipt = RUNTIME.evaluate_stage_event(
                    task_id="care-ase-faithful",
                    request={"enabled": True},
                    current={"request_nonce": "nonce", "review_round": 1, "state": state},
                    visual_final=None,
                    remote_sha="b" * 40,
                    processed=set(),
                    default_wait_hours=4,
                    care_ase_verifier_recheck_complete=True,
                )

                self.assertEqual(receipt["decision"], "CONTROLLER_UPDATE_REQUIRED")
                self.assertIn("Verifier recheck receipts", receipt["action"])

    def test_care_ase_verifier_recheck_local_artifacts_prevent_duplicate_start(self) -> None:
        receipt = RUNTIME.evaluate_stage_event(
            task_id="care-ase-faithful",
            request={"enabled": True},
            current={"request_nonce": "nonce", "review_round": 1, "state": "VERIFIER_RECHECK_REQUIRED"},
            visual_final=None,
            remote_sha="b" * 40,
            processed=set(),
            default_wait_hours=4,
            care_ase_verifier_recheck_complete=False,
            care_ase_verifier_recheck_local_artifacts=True,
        )

        self.assertEqual(receipt["decision"], "MONITOR_ONLY")
        self.assertIn("instead of launching a duplicate", receipt["action"])

    def test_care_ase_verifier_recheck_provenance_gap_allows_controller_integration_without_goal_complete(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            verifier_worktree = root / "verifier"
            verification_dir = verifier_worktree / "results/agent_flow_v3/care-ase-faithful/verification"
            verification_dir.mkdir(parents=True)
            thread_file = root / "verifier_thread_id"
            thread_file.write_text("thread-1", encoding="utf-8")
            role_plan = {
                "integration_branch": "develop",
                "controller_pushes_integration_branch": True,
                "remote_role_branches_authorized": False,
                "roles": {
                    "controller": {"push_authority": "develop"},
                    "verifier": {
                        "worktree": str(verifier_worktree),
                        "codex_home": str(root / "codex-home"),
                        "thread_id_file": str(thread_file),
                        "write_scope": ["results/agent_flow_v3/care-ase-faithful/verification/**"],
                        "pushes_integration_branch": False,
                    },
                    "executor": {"push_authority": "none", "pushes_integration_branch": False},
                }
            }
            (root / "role_plan.json").write_text(json.dumps(role_plan), encoding="utf-8")
            failures = [
                "transaction.runtime_manifest.request_nonce",
                "transaction.runtime_manifest.integration_commit_sha",
                "transaction.runtime_manifest.artifact_missing:implementation_evidence",
                "transaction.runtime_manifest.artifact_sha256:implementation_evidence",
                "transaction.hosted_ci.head_sha_not_exact_integration",
                "transaction.hosted_ci.conclusion",
            ]
            for name, payload in {
                "executable_verifier_receipt.json": {
                    "status": "FAIL_CLOSED",
                    "passed": False,
                    "implementation_fingerprint_sha256": "i" * 64,
                    "failures": failures,
                },
                "transaction_gate_receipt.json": {
                    "status": "FAIL_CLOSED",
                    "implementation_fingerprint_sha256": "i" * 64,
                    "failures": failures,
                },
                "integrated_implementation_validation_result.json": {
                    "passed": False,
                    "failure_count": 7,
                    "failures": [
                        "verifier_owned.executable.passed",
                        "verifier_owned.executable.status",
                        "verifier_owned.transaction.status",
                        "verifier_owned.transaction.no_failures",
                        "verifier_owned.transaction.hosted_ci_success",
                        "verifier_owned.transaction.hosted_ci_exact_reviewed_integration",
                        "verifier_owned.transaction.no_stale_planner_reuse",
                    ],
                },
                "verifier_fingerprint.json": {"fingerprint_sha256": "v" * 64},
            }.items():
                (verification_dir / name).write_text(json.dumps(payload), encoding="utf-8")
            changed_paths = "\n".join(
                [
                    "results/agent_flow_v3/care-ase-faithful/verification/executable_verifier_receipt.json",
                    "results/agent_flow_v3/care-ase-faithful/verification/transaction_gate_receipt.json",
                    "results/agent_flow_v3/care-ase-faithful/verification/integrated_implementation_validation_result.json",
                    "results/agent_flow_v3/care-ase-faithful/verification/verifier_fingerprint.json",
                ]
            )

            def fake_git(_repo: Path, *cmd: str) -> str:
                if cmd[0] == "fetch":
                    return ""
                if cmd[:2] == ("rev-parse", "HEAD"):
                    return "1" * 40
                if cmd[0] == "merge-base":
                    return "0" * 40
                if cmd[:2] == ("diff", "--name-only"):
                    return changed_paths + "\n"
                raise AssertionError(cmd)

            args = argparse.Namespace(
                repo_root=root,
                controller_role_plan="role_plan.json",
                branch="develop",
                state_root=root / "state" / "stage_orchestrator",
            )
            current = {
                "state": "VERIFIER_RECHECK_REQUIRED",
                "request_nonce": "nonce",
                "frozen_contract_sha256": "f" * 64,
                "implementation_fingerprint_sha256": "i" * 64,
                "verifier_fingerprint_sha256": "v" * 64,
            }
            request = {"enabled": True, "request_nonce": "nonce", "frozen_contract_sha256": "f" * 64}

            with (
                mock.patch.object(RUNTIME, "git", side_effect=fake_git),
                mock.patch.object(RUNTIME, "git_status_short", return_value=""),
                mock.patch.object(RUNTIME, "role_rollout_goal_complete", return_value=None),
                mock.patch.object(RUNTIME, "role_active_process", return_value=None),
                mock.patch.object(RUNTIME, "git_commit_subject", return_value="verification: refresh care ase recheck receipts"),
            ):
                completion = RUNTIME.validate_care_ase_verifier_recheck_completion(
                    args=args,
                    request=request,
                    current=current,
                )

            self.assertIsNone(completion["goal_complete"])
            self.assertTrue(completion["pre_ci_transaction_pending"])

    def test_care_ase_verifier_recheck_allows_only_pre_ci_transaction_failure(self) -> None:
        executable = {
            "status": "FAIL_CLOSED",
            "passed": False,
            "failure_count": 3,
            "failures": [
                "transaction.verifier_source_changed_after_reviewed_integration",
                "transaction.hosted_ci.head_sha_not_exact_integration",
                "transaction.hosted_ci.conclusion",
            ],
        }
        transaction = {
            "status": "FAIL_CLOSED",
            "failure_count": 3,
            "failures": [
                "transaction.verifier_source_changed_after_reviewed_integration",
                "transaction.hosted_ci.head_sha_not_exact_integration",
                "transaction.hosted_ci.conclusion",
            ],
        }
        integrated = {
            "passed": False,
            "failure_count": 7,
            "failures": [
                "verifier_owned.executable.passed",
                "verifier_owned.executable.status",
                "verifier_owned.transaction.status",
                "verifier_owned.transaction.no_failures",
                "verifier_owned.transaction.hosted_ci_success",
                "verifier_owned.transaction.hosted_ci_exact_reviewed_integration",
                "verifier_owned.transaction.planner_packet_bound_to_reviewed_integration",
                "verifier_owned.transaction.no_stale_planner_reuse",
            ],
        }

        self.assertTrue(RUNTIME.care_ase_verifier_pre_ci_transaction_pending(executable, transaction))
        self.assertTrue(RUNTIME.care_ase_integrated_validation_pre_ci_acceptable(integrated))

        executable["failures"] = [
            "transaction.hosted_ci.head_sha_not_exact_integration",
            "transaction.hosted_ci.conclusion",
        ]
        transaction["failures"] = [
            "transaction.hosted_ci.head_sha_not_exact_integration",
            "transaction.hosted_ci.conclusion",
        ]
        self.assertTrue(RUNTIME.care_ase_verifier_pre_ci_transaction_pending(executable, transaction))
        executable["failures"] = [
            "transaction.runtime_manifest.request_nonce",
            "transaction.runtime_manifest.integration_commit_sha",
            "transaction.runtime_manifest.artifact_missing:implementation_evidence",
            "transaction.runtime_manifest.artifact_sha256:implementation_evidence",
            "transaction.current_runtime_input_bundle.integration_commit_sha",
            "transaction.current_runtime_identity_receipt.integration_commit_sha",
            "transaction.checkpoint_resume.integration_commit_sha",
            "transaction.current.hosted_ci_actual_head_sha_not_exact_integration",
            "transaction.hosted_ci.head_sha_not_exact_integration",
            "transaction.hosted_ci.conclusion",
        ]
        transaction["failures"] = list(executable["failures"])
        self.assertTrue(RUNTIME.care_ase_verifier_pre_ci_transaction_pending(executable, transaction))
        self.assertTrue(RUNTIME.care_ase_transaction_failures_require_provenance_rebind(executable["failures"]))

        executable["failures"] = ["executable_probe.failed:required_module_final_logit_interventions"]
        self.assertFalse(RUNTIME.care_ase_verifier_pre_ci_transaction_pending(executable, transaction))

        hosted_ci_only = [
            "transaction.current.hosted_ci_actual_head_sha_not_exact_integration",
            "transaction.hosted_ci.head_sha_not_exact_integration",
            "transaction.hosted_ci.conclusion",
        ]
        self.assertFalse(RUNTIME.care_ase_transaction_failures_require_provenance_rebind(hosted_ci_only))

    def test_care_ase_integrated_validation_allows_planner_packet_rebind_only(self) -> None:
        integrated = {
            "passed": False,
            "failure_count": 4,
            "failures": [
                "verifier_owned.transaction.hosted_ci_success",
                "verifier_owned.transaction.hosted_ci_exact_reviewed_integration",
                "verifier_owned.transaction.planner_packet_bound_to_reviewed_integration",
                "verifier_owned.transaction.no_stale_planner_reuse",
            ],
        }

        self.assertTrue(RUNTIME.care_ase_integrated_validation_pre_ci_acceptable(integrated))

    def test_care_ase_provenance_rebind_preserves_reviewed_integration_target(self) -> None:
        self.assertEqual(
            RUNTIME.care_ase_reviewed_integration_sha_after_executor_merge(
                {"state": "PROVENANCE_REBIND_REQUIRED", "integration_commit_sha": "reviewed"},
                "new-merge",
            ),
            "reviewed",
        )
        self.assertEqual(
            RUNTIME.care_ase_reviewed_integration_sha_after_executor_merge(
                {"state": "VERIFIER_FROZEN", "integration_commit_sha": "old"},
                "new-merge",
            ),
            "new-merge",
        )

    def test_github_actions_success_payload_requires_exact_head_and_success(self) -> None:
        payload = {
            "workflow_runs": [
                {
                    "id": 1,
                    "head_sha": "a" * 40,
                    "status": "completed",
                    "conclusion": "failure",
                    "name": "CARE Agent-Flow v3 deterministic CI",
                    "html_url": "https://example.invalid/fail",
                },
                {
                    "id": 2,
                    "head_sha": "b" * 40,
                    "status": "completed",
                    "conclusion": "success",
                    "name": "Unrelated workflow",
                    "path": ".github/workflows/unrelated.yml",
                    "html_url": "https://example.invalid/unrelated",
                },
                {
                    "id": 3,
                    "head_sha": "a" * 40,
                    "status": "completed",
                    "conclusion": "success",
                    "name": "",
                    "path": ".github/workflows/care_agent_flow_v3_deterministic_ci.yml",
                    "html_url": "https://example.invalid/pass",
                },
            ]
        }

        observed = RUNTIME.github_actions_success_from_runs_payload(payload, "a" * 40)
        self.assertIsNotNone(observed)
        self.assertEqual(observed["ci_run_id"], 3)
        self.assertEqual(observed["ci_status"], "PASS_EXACT_HOSTED_CHECKOUT_VERIFIED")
        self.assertIsNone(RUNTIME.github_actions_success_from_runs_payload(payload, "b" * 40))

    def test_role_commit_scope_rejects_forbidden_or_outside_paths(self) -> None:
        role_data = {
            "write_scope": ["tests/**", "validators/**", "results/agent_flow_v3/care-ase-faithful/verification/**"],
            "forbidden_scope": ["src/**", "jobs/**"],
        }

        failures = RUNTIME.validate_role_commit_scope(
            [
                "tests/care_ase_faithful/test_verifier_package.py",
                "src/care_myocardium/model.py",
                "docs/unowned.md",
            ],
            role_data,
        )

        self.assertIn("forbidden_path:src/care_myocardium/model.py", failures)
        self.assertIn("outside_write_scope:docs/unowned.md", failures)

    def test_controller_start_command_uses_exact_thread_without_last(self) -> None:
        command = RUNTIME.build_controller_start_command(
            "/opt/codex",
            Path("/tmp/controller-worktree"),
            "thread-123",
        )

        self.assertEqual(
            command,
            ["/opt/codex", "exec", "-C", "/tmp/controller-worktree", "resume", "thread-123", "-"],
        )
        self.assertNotIn("--last", command)

    def test_orchestrator_routes_smoke_b_planner_pass_to_care_ase_activation(self) -> None:
        current = {
            "request_nonce": "smoke-b-nonce",
            "review_round": 1,
            "state": "PLANNER_PASS",
            "integration_commit_sha": "c" * 40,
        }

        receipt = RUNTIME.evaluate_stage_event(
            task_id="gpt-loop-smoke-b",
            request={"enabled": True},
            current=current,
            visual_final=None,
            remote_sha="d" * 40,
            processed=set(),
            default_wait_hours=4,
        )

        self.assertEqual(receipt["decision"], "CONTROLLER_UPDATE_REQUIRED")
        self.assertIn("arm care-ase-faithful", receipt["action"])

    def test_orchestrator_waiting_event_records_external_gpt_metadata(self) -> None:
        current = {
            "request_nonce": "smoke-b-nonce",
            "review_round": 1,
            "state": "WAITING_FOR_EXTERNAL_GPT",
            "integration_commit_sha": "c" * 40,
            "external_wait_started_utc": "2026-08-06T07:43:52Z",
            "external_wait_deadline_utc": "2999-08-06T11:43:52Z",
            "expected_state_or_artifact": "true scheduled Planner round 1 decision",
            "last_observed_remote_sha": "b" * 40,
            "last_poll_utc": "2026-08-06T07:43:52Z",
            "updated_utc": "2026-08-06T07:43:52Z",
        }

        receipt = RUNTIME.evaluate_stage_event(
            task_id="gpt-loop-smoke-b",
            request={"enabled": True},
            current=current,
            visual_final=None,
            remote_sha="d" * 40,
            processed=set(),
            default_wait_hours=4,
        )

        self.assertEqual(receipt["decision"], "WAITING_FOR_EXTERNAL_GPT")
        self.assertEqual(receipt["external_wait_started_utc"], "2026-08-06T07:43:52Z")
        self.assertEqual(receipt["external_wait_deadline_utc"], "2999-08-06T11:43:52Z")
        self.assertEqual(receipt["expected_state_or_artifact"], "true scheduled Planner round 1 decision")
        self.assertEqual(receipt["last_observed_remote_sha"], "d" * 40)
        self.assertRegex(receipt["last_poll_utc"], r"^\d{4}-\d{2}-\d{2}T")
        self.assertNotEqual(receipt["last_poll_utc"], "2026-08-06T07:43:52Z")
        self.assertNotEqual(receipt["updated_utc"], "2026-08-06T07:43:52Z")

    def test_orchestrator_plan_requested_records_external_gpt_wait_metadata(self) -> None:
        current = {
            "task_id": "care-ase-faithful",
            "request_nonce": "care-ase-nonce",
            "review_round": 0,
            "state": "PLAN_REQUESTED",
        }

        receipt = RUNTIME.evaluate_stage_event(
            task_id="care-ase-faithful",
            request={"enabled": True},
            current=current,
            visual_final=None,
            remote_sha="e" * 40,
            processed=set(),
            default_wait_hours=4,
        )

        self.assertEqual(receipt["decision"], "WAITING_FOR_EXTERNAL_GPT")
        self.assertEqual(receipt["state"], "PLAN_REQUESTED")
        self.assertIn("Scheduled Planner", receipt["expected_state_or_artifact"])
        self.assertEqual(receipt["last_observed_remote_sha"], "e" * 40)
        started = RUNTIME.parse_utc(receipt["external_wait_started_utc"])
        deadline = RUNTIME.parse_utc(receipt["external_wait_deadline_utc"])
        self.assertGreaterEqual((deadline - started).total_seconds(), 4 * 3600)

    def test_care_ase_ci_pass_routes_to_stable_planner_wait(self) -> None:
        current = {
            "task_id": "care-ase-faithful",
            "request_nonce": "care-ase-nonce",
            "review_round": 1,
            "state": "CI_RUNNING",
            "ci_status": "PASS",
            "ci_checked_commit_sha": "e" * 40,
            "frozen_contract_sha256": "a" * 64,
            "implementation_fingerprint_sha256": "b" * 64,
            "verifier_fingerprint_sha256": "c" * 64,
            "executor_integration_merge_sha": "d" * 40,
        }

        receipt = RUNTIME.evaluate_stage_event(
            task_id="care-ase-faithful",
            request={"enabled": True},
            current=current,
            visual_final=None,
            remote_sha="e" * 40,
            processed=set(),
            default_wait_hours=4,
        )

        self.assertEqual(receipt["decision"], "CONTROLLER_UPDATE_REQUIRED")
        self.assertIn("CI_PASS", receipt["action"])
        self.assertIn("WAITING_FOR_EXTERNAL_GPT", receipt["action"])

    def test_ci_pass_wait_transaction_is_not_human_approval_gate(self) -> None:
        current = {
            "task_id": "care-ase-faithful",
            "request_nonce": "care-ase-nonce",
            "review_round": 2,
            "state": "CI_RUNNING",
            "ci_status": "PASS",
            "ci_checked_commit_sha": "e" * 40,
            "frozen_contract_sha256": "a" * 64,
            "implementation_fingerprint_sha256": "b" * 64,
            "verifier_fingerprint_sha256": "c" * 64,
            "executor_integration_merge_sha": "d" * 40,
        }

        receipt = RUNTIME.evaluate_stage_event(
            task_id="care-ase-faithful",
            request={"enabled": True},
            current=current,
            visual_final=None,
            remote_sha="e" * 40,
            processed=set(),
            default_wait_hours=4,
        )

        self.assertEqual(receipt["decision"], "CONTROLLER_UPDATE_REQUIRED")
        self.assertIn("authorized", receipt["action"])
        self.assertIn("WAITING_FOR_EXTERNAL_GPT", receipt["action"])
        self.assertNotEqual(receipt["decision"], "OPERATIONALLY_BLOCKED")
        self.assertNotIn("human", receipt["action"].lower())

    def test_care_ase_stale_ci_pass_keeps_waiting_for_ci(self) -> None:
        current = {
            "task_id": "care-ase-faithful",
            "request_nonce": "care-ase-nonce",
            "review_round": 1,
            "state": "CI_RUNNING",
            "ci_status": "PASS",
            "ci_checked_commit_sha": "d" * 40,
            "frozen_contract_sha256": "a" * 64,
            "implementation_fingerprint_sha256": "b" * 64,
            "verifier_fingerprint_sha256": "c" * 64,
            "executor_integration_merge_sha": "d" * 40,
        }

        receipt = RUNTIME.evaluate_stage_event(
            task_id="care-ase-faithful",
            request={"enabled": True},
            current=current,
            visual_final=None,
            remote_sha="e" * 40,
            processed=set(),
            default_wait_hours=4,
        )

        self.assertEqual(receipt["decision"], "WAITING_FOR_CI")

    def test_fail_closed_verifier_freeze_allows_executor_repair_start(self) -> None:
        freeze = {
            "state_for_controller": "VERIFIER_FROZEN",
            "current_reviewed_implementation_expected_fail_closed": True,
            "executable_verifier_production_exit_code": 2,
            "integrated_implementation_validation_exit_code": 2,
            "protected_known_bad_all_nonzero": True,
            "runtime_mutation_all_nonzero": True,
        }

        self.assertTrue(RUNTIME.verifier_freeze_allows_executor_after_controller_freeze(freeze))

    def test_incomplete_fail_closed_verifier_freeze_does_not_allow_executor(self) -> None:
        freeze = {
            "state_for_controller": "VERIFIER_FROZEN",
            "current_reviewed_implementation_expected_fail_closed": True,
            "executable_verifier_production_exit_code": 2,
            "integrated_implementation_validation_exit_code": 2,
            "protected_known_bad_all_nonzero": True,
            "runtime_mutation_all_nonzero": False,
        }

        self.assertFalse(RUNTIME.verifier_freeze_allows_executor_after_controller_freeze(freeze))

    def test_care_ase_wait_transaction_clears_stale_planner_review_fields(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp)
            current_path = repo / "automation/agent_flow_v3/tasks/care-ase-faithful/CURRENT.json"
            ci_receipt_path = repo / "results/agent_flow_v3/care-ase-faithful/controller_ci_receipt.json"
            current_path.parent.mkdir(parents=True)
            ci_receipt_path.parent.mkdir(parents=True)
            current = {
                "schema": RUNTIME.SCHEMA,
                "task_id": "care-ase-faithful",
                "request_nonce": "care-ase-nonce",
                "review_round": 1,
                "state": "CI_RUNNING",
                "ci_status": "PASS",
                "ci_checked_commit_sha": "e" * 40,
                "ci_run_id": 12345,
                "ci_run_url": "https://github.example/actions/runs/12345",
                "ci_run_actual_head_sha": "e" * 40,
                "ci_workflow_name": "CARE Agent-Flow v3 deterministic CI",
                "frozen_contract_sha256": "a" * 64,
                "implementation_fingerprint_sha256": "b" * 64,
                "verifier_fingerprint_sha256": "c" * 64,
                "executor_integration_merge_sha": "d" * 40,
                "executor_local_commit_sha": "1" * 40,
                "verifier_integration_merge_sha": "2" * 40,
                "verifier_freeze_receipt_commit_sha": "3" * 40,
                "planner_decision": "PLANNER_REVISE_BOTH",
                "planner_review_artifact": "results/agent_flow_v3/care-ase-faithful/planner_reviews/round_001.json",
                "planner_review_artifact_commit_sha": "4" * 40,
                "planner_review_input_integration_sha": "5" * 40,
                "planner_review_input_implementation_fingerprint_sha256": "6" * 64,
                "planner_review_input_verifier_fingerprint_sha256": "7" * 64,
                "repair_prompt_path": "automation/agent_flow_v3/tasks/care-ase-faithful/repairs/round_001_executor.md",
                "repair_prompt_sha256": "8" * 64,
                "repair_prompts": {"executor": "automation/agent_flow_v3/tasks/care-ase-faithful/repairs/round_001_executor.md"},
                "external_wait_closed_utc": "2026-08-06T18:05:32Z",
            }
            current_path.write_text(json.dumps(current), encoding="utf-8")
            ci_receipt_path.write_text(json.dumps({"schema": "old", "task_id": "care-ase-faithful"}), encoding="utf-8")
            args = argparse.Namespace(branch="develop", default_wait_hours=4)

            with mock.patch.object(RUNTIME, "ensure_clean_ff_to_remote", return_value="e" * 40), mock.patch.object(
                RUNTIME,
                "commit_and_push",
                return_value={"commit_sha": "f" * 40},
            ):
                RUNTIME.apply_care_ase_ci_pass_planner_wait_update(
                    args=args,
                    repo=repo,
                    current=current,
                    remote_sha="e" * 40,
                )

            updated = json.loads(current_path.read_text(encoding="utf-8"))
            ci_receipt = json.loads(ci_receipt_path.read_text(encoding="utf-8"))
            ready_receipt = json.loads(
                (
                    repo
                    / "results/agent_flow_v3/care-ase-faithful/controller_ready_for_planner_review_receipt.json"
                ).read_text(encoding="utf-8")
            )
            planner_packet = json.loads(
                (
                    repo
                    / "results/agent_flow_v3/care-ase-faithful/planner_review_packet.json"
                ).read_text(encoding="utf-8")
            )
            self.assertEqual(updated["state"], "WAITING_FOR_EXTERNAL_GPT")
            self.assertEqual(updated["integration_commit_sha"], "e" * 40)
            self.assertEqual(planner_packet["integration_commit_sha"], "e" * 40)
            self.assertEqual(planner_packet["current_state_after_commit"], "WAITING_FOR_EXTERNAL_GPT")
            self.assertEqual(planner_packet["ready_state_reached_before_wait"], "READY_FOR_PLANNER_REVIEW")
            self.assertEqual(planner_packet["ci_checked_commit_sha"], "e" * 40)
            self.assertEqual(planner_packet["ci_run_actual_head_sha"], "e" * 40)
            self.assertEqual(planner_packet["ci_run_id"], 12345)
            self.assertEqual(updated["ci_run_actual_head_sha"], "e" * 40)
            self.assertEqual(updated["ci_run_id"], 12345)
            self.assertEqual(ci_receipt["github_actions_head_sha"], "e" * 40)
            self.assertEqual(ci_receipt["github_actions_run_id"], 12345)
            self.assertIsNone(updated["planner_decision"])
            self.assertIsNone(updated["planner_review_artifact"])
            self.assertIsNone(updated["planner_review_artifact_commit_sha"])
            self.assertIsNone(updated["planner_review_input_integration_sha"])
            self.assertIsNone(updated["repair_prompt_sha256"])
            self.assertEqual(updated["repair_prompts"], {})
            self.assertIsNone(updated["external_wait_closed_utc"])
            self.assertIsNotNone(updated["external_wait_started_utc"])
            self.assertIsNotNone(updated["external_wait_deadline_utc"])
            self.assertEqual(updated["next_action"], "WAIT_FOR_SCHEDULED_PLANNER_REVIEW_ON_ORIGIN_DEVELOP")
            superseded = updated["superseded_planner_review_before_current_wait"]
            self.assertEqual(superseded["planner_decision"], "PLANNER_REVISE_BOTH")
            self.assertEqual(
                superseded["planner_review_artifact"],
                "results/agent_flow_v3/care-ase-faithful/planner_reviews/round_001.json",
            )
            self.assertFalse(ci_receipt["human_approval_required_for_wait_transaction"])
            self.assertEqual(
                ci_receipt["approval_scope"],
                "current_frozen_contract_and_request_nonce_ci_pass_to_waiting_for_external_gpt",
            )
            self.assertTrue(ready_receipt["wait_transaction_ci_policy"]["status_commit_may_trigger_ci_after_wait_starts"])
            self.assertEqual(
                ready_receipt["wait_transaction_ci_policy"]["planner_review_binding"],
                "implementation_and_integration_sha_that_already_passed_ci",
            )

    def test_orchestrator_reuses_existing_wait_deadline_for_same_event(self) -> None:
        current = {
            "task_id": "care-ase-faithful",
            "request_nonce": "care-ase-nonce",
            "review_round": 0,
            "state": "PLAN_REQUESTED",
        }
        previous_wait = {
            "task_id": "care-ase-faithful",
            "event_key": "care-ase-faithful:care-ase-nonce:0:PLAN_REQUESTED",
            "remote_sha": "a" * 40,
            "external_wait_started_utc": "2026-08-06T09:15:35Z",
            "external_wait_deadline_utc": "2026-08-06T13:15:35Z",
            "expected_state_or_artifact": "old expected Planner artifact",
        }

        merged = RUNTIME.merge_existing_wait_metadata(current, previous_wait)
        receipt = RUNTIME.evaluate_stage_event(
            task_id="care-ase-faithful",
            request={"enabled": True},
            current=merged,
            visual_final=None,
            remote_sha="b" * 40,
            processed=set(),
            default_wait_hours=4,
        )

        self.assertEqual(receipt["decision"], "WAITING_FOR_EXTERNAL_GPT")
        self.assertEqual(receipt["external_wait_started_utc"], "2026-08-06T09:15:35Z")
        self.assertEqual(receipt["external_wait_deadline_utc"], "2026-08-06T13:15:35Z")
        self.assertEqual(receipt["expected_state_or_artifact"], "old expected Planner artifact")
        self.assertEqual(receipt["last_observed_remote_sha"], "b" * 40)

    def test_orchestrator_processed_key_accepts_new_artifact_suffix(self) -> None:
        processed = {
            "gpt-loop-smoke-b:smoke-b-nonce:1:PLANNER_PASS",
        }
        event_key = (
            "gpt-loop-smoke-b:smoke-b-nonce:1:PLANNER_PASS:"
            "results/agent_flow_v3/gpt-loop-smoke-b/planner_reviews/round_001.json"
        )
        self.assertTrue(RUNTIME.stage_event_was_processed(event_key, processed))

    def test_orchestrator_remove_processed_key_accepts_artifact_suffix(self) -> None:
        processed = {
            "care-ase-faithful:nonce:1:PLANNER_REVISE_BOTH",
            "other:event",
        }
        event_key = (
            "care-ase-faithful:nonce:1:PLANNER_REVISE_BOTH:"
            "results/agent_flow_v3/care-ase-faithful/planner_reviews/round_001_reentry_001.json"
        )
        self.assertEqual(RUNTIME.remove_stage_processed_event(event_key, processed), {"other:event"})

    def test_orchestrator_keeps_generic_planner_pass_at_human_gate(self) -> None:
        current = {
            "request_nonce": "nonce-1",
            "review_round": 1,
            "state": "PLANNER_PASS",
            "integration_commit_sha": "c" * 40,
        }

        receipt = RUNTIME.evaluate_stage_event(
            task_id="care-ase-faithful",
            request={"enabled": True},
            current=current,
            visual_final=None,
            remote_sha="d" * 40,
            processed=set(),
            default_wait_hours=4,
        )

        self.assertEqual(receipt["decision"], "STOP_AT_HUMAN_GATE")

    def test_smoke_b_planner_pass_requires_exact_current_bindings(self) -> None:
        request = {
            "task_id": "gpt-loop-smoke-b",
            "request_nonce": "nonce-1",
        }
        current = {
            "task_id": "gpt-loop-smoke-b",
            "state": "PLANNER_PASS",
            "request_nonce": "nonce-1",
            "review_round": 1,
            "frozen_contract_sha256": "a" * 64,
            "integration_commit_sha": "b" * 40,
            "implementation_fingerprint_sha256": "c" * 64,
            "verifier_fingerprint_sha256": "d" * 64,
        }
        review = {
            "schema": "CARE_AGENT_FLOW_V3_PLANNER_REVIEW",
            "task_id": "gpt-loop-smoke-b",
            "decision": "PLANNER_PASS",
            "request_nonce": "nonce-1",
            "review_round": 1,
            "frozen_contract_sha256": "a" * 64,
            "integration_commit_sha": "e" * 40,
            "implementation_fingerprint_sha256": "c" * 64,
            "verifier_fingerprint_sha256": "d" * 64,
            "blocking_findings": [],
        }

        failures = RUNTIME.validate_smoke_b_planner_pass(review, request=request, current=current)

        self.assertIn("integration_commit_sha", failures)

    def test_smoke_b_final_receipt_passes_with_exact_planner_bindings(self) -> None:
        request = {
            "task_id": "gpt-loop-smoke-b",
            "request_nonce": "nonce-1",
        }
        current = {
            "task_id": "gpt-loop-smoke-b",
            "state": "PLANNER_PASS",
            "request_nonce": "nonce-1",
            "review_round": 1,
            "frozen_contract_sha256": "a" * 64,
            "integration_commit_sha": "b" * 40,
            "implementation_fingerprint_sha256": "c" * 64,
            "verifier_fingerprint_sha256": "d" * 64,
        }
        review = {
            "schema": "CARE_AGENT_FLOW_V3_PLANNER_REVIEW",
            "task_id": "gpt-loop-smoke-b",
            "decision": "PLANNER_PASS",
            "request_nonce": "nonce-1",
            "review_round": 1,
            "frozen_contract_sha256": "a" * 64,
            "integration_commit_sha": "b" * 40,
            "implementation_fingerprint_sha256": "c" * 64,
            "verifier_fingerprint_sha256": "d" * 64,
            "blocking_findings": [],
        }

        receipt = RUNTIME.build_smoke_b_final_receipt(
            request=request,
            current=current,
            review=review,
            review_path="results/agent_flow_v3/gpt-loop-smoke-b/planner_reviews/round_001.json",
            review_commit_sha="e" * 40,
        )

        self.assertEqual(receipt["status"], "PASS")
        self.assertEqual(receipt["failures"], [])

    def test_prepare_care_ase_activation_requires_visual_and_smoke_b_pass(self) -> None:
        request = {
            "task_id": "care-ase-faithful",
            "enabled": False,
            "frozen_contract_sha256": None,
        }
        current = {
            "task_id": "care-ase-faithful",
            "state": "PLAN_REQUESTED",
            "review_round": 0,
            "request_nonce": "bootstrap",
            "frozen_contract_sha256": None,
            "integration_commit_sha": None,
            "implementation_fingerprint_sha256": None,
            "verifier_fingerprint_sha256": None,
            "next_action": "CONFIGURE_VISUAL_SOURCES_AND_SCHEDULED_TASKS_THEN_ENABLE_REQUEST",
            "updated_utc": "2026-08-05T00:00:00Z",
        }
        visual_sources = {
            "schema": "CARE_VISUAL_SOURCES_V1",
            "task_id": "care-ase-faithful",
            "ready_for_scheduled_visual_review": False,
        }
        visual_final = {"status": "PASS", "request_nonce": "visual-nonce"}
        smoke_b_final = {"status": "PASS", "request_nonce": "smoke-b-nonce"}

        armed_request, armed_current, armed_visual_sources, activation_state, failures = RUNTIME.prepare_care_ase_activation_after_smoke_b(
            request=request,
            current=current,
            visual_sources=visual_sources,
            visual_smoke_final=visual_final,
            smoke_b_final=smoke_b_final,
            activation_nonce="care-ase-20260806T000000Z",
            frozen_contract_sha256=None,
        )

        self.assertEqual(failures, [])
        self.assertIs(armed_request["enabled"], True)
        self.assertEqual(armed_request["request_nonce"], "care-ase-20260806T000000Z")
        self.assertIsNone(armed_request["frozen_contract_sha256"])
        self.assertEqual(armed_current["state"], "PLAN_REQUESTED")
        self.assertEqual(armed_current["next_action"], "WAIT_FOR_TRUE_SCHEDULED_PLANNER_AND_CRITIC")
        self.assertIs(armed_visual_sources["ready_for_scheduled_visual_review"], True)
        self.assertEqual(activation_state["status"], "ARMED")
        self.assertIn("no CARE-ASE implementation started by activation", activation_state["forbidden_actions_confirmed"])

    def test_activate_care_ase_after_smoke_b_uses_explicit_parameters(self) -> None:
        smoke_request = {
            "task_id": "gpt-loop-smoke-b",
            "request_nonce": "smoke-b-nonce",
        }
        smoke_current = {
            "task_id": "gpt-loop-smoke-b",
            "state": "PLANNER_PASS",
            "request_nonce": "smoke-b-nonce",
            "review_round": 1,
            "frozen_contract_sha256": "a" * 64,
            "integration_commit_sha": "b" * 40,
            "implementation_fingerprint_sha256": "c" * 64,
            "verifier_fingerprint_sha256": "d" * 64,
        }
        planner_review = {
            "schema": "CARE_AGENT_FLOW_V3_PLANNER_REVIEW",
            "task_id": "gpt-loop-smoke-b",
            "decision": "PLANNER_PASS",
            "request_nonce": "smoke-b-nonce",
            "review_round": 1,
            "frozen_contract_sha256": "a" * 64,
            "integration_commit_sha": "b" * 40,
            "implementation_fingerprint_sha256": "c" * 64,
            "verifier_fingerprint_sha256": "d" * 64,
            "blocking_findings": [],
        }
        care_request = {
            "task_id": "care-ase-faithful",
            "enabled": False,
            "frozen_contract_sha256": None,
        }
        care_current = {
            "task_id": "care-ase-faithful",
            "state": "PLAN_REQUESTED",
            "review_round": 0,
            "request_nonce": "bootstrap",
            "frozen_contract_sha256": None,
            "integration_commit_sha": None,
            "implementation_fingerprint_sha256": None,
            "verifier_fingerprint_sha256": None,
            "next_action": "CONFIGURE_VISUAL_SOURCES_AND_SCHEDULED_TASKS_THEN_ENABLE_REQUEST",
            "updated_utc": "2026-08-05T00:00:00Z",
        }
        visual_sources = {
            "schema": "CARE_VISUAL_SOURCES_V1",
            "task_id": "care-ase-faithful",
            "ready_for_scheduled_visual_review": False,
        }
        visual_final = {"status": "PASS", "request_nonce": "visual-nonce"}
        remote_objects = {
            "automation/agent_flow_v3/tasks/gpt-loop-smoke-b/REQUEST.json": smoke_request,
            "automation/agent_flow_v3/tasks/gpt-loop-smoke-b/CURRENT.json": smoke_current,
            "automation/agent_flow_v3/tasks/care-ase-faithful/REQUEST.json": care_request,
            "automation/agent_flow_v3/tasks/care-ase-faithful/CURRENT.json": care_current,
            "automation/agent_flow_v3/tasks/care-ase-faithful/VISUAL_SOURCES.json": visual_sources,
            "results/agent_flow_v3/care-visual-smoke/visual_smoke_final.json": visual_final,
        }

        def fake_git_show_json(_repo: Path, _ref: str, rel_path: str) -> dict[str, object]:
            return remote_objects[rel_path]

        with tempfile.TemporaryDirectory() as tmp, \
            mock.patch.object(RUNTIME, "git_show_json", side_effect=fake_git_show_json), \
            mock.patch.object(RUNTIME, "git_show_text_or_none", return_value=json.dumps(planner_review)), \
            mock.patch.object(RUNTIME, "git", return_value="e" * 40):
            result = RUNTIME.activate_care_ase_after_smoke_b(
                repo=Path(tmp),
                branch="develop",
                ref="HEAD",
                activation_nonce="care-ase-test",
                dry_run=True,
            )

        self.assertEqual(result["status"], "DRY_RUN")
        self.assertEqual(result["branch"], "develop")
        self.assertEqual(result["request_nonce"], "care-ase-test")

    def test_activate_care_ase_after_smoke_b_noops_when_already_armed(self) -> None:
        remote_objects = {
            "automation/agent_flow_v3/tasks/gpt-loop-smoke-b/REQUEST.json": {
                "task_id": "gpt-loop-smoke-b",
                "request_nonce": "smoke-b-nonce",
            },
            "automation/agent_flow_v3/tasks/gpt-loop-smoke-b/CURRENT.json": {
                "task_id": "gpt-loop-smoke-b",
                "state": "PLANNER_PASS",
                "request_nonce": "smoke-b-nonce",
                "review_round": 1,
            },
            "automation/agent_flow_v3/tasks/care-ase-faithful/REQUEST.json": {
                "task_id": "care-ase-faithful",
                "enabled": True,
                "request_nonce": "care-ase-existing",
                "frozen_contract_sha256": "a" * 64,
            },
            "automation/agent_flow_v3/tasks/care-ase-faithful/CURRENT.json": {
                "task_id": "care-ase-faithful",
                "state": "WAITING_FOR_EXTERNAL_GPT",
                "request_nonce": "care-ase-existing",
            },
            "automation/agent_flow_v3/tasks/care-ase-faithful/VISUAL_SOURCES.json": {
                "schema": "CARE_VISUAL_SOURCES_V1"
            },
            "results/agent_flow_v3/care-visual-smoke/visual_smoke_final.json": {"status": "PASS"},
        }

        def fake_git_show_json(_repo: Path, _ref: str, rel_path: str) -> dict[str, object]:
            return remote_objects[rel_path]

        with tempfile.TemporaryDirectory() as tmp, \
            mock.patch.object(RUNTIME, "git_show_json", side_effect=fake_git_show_json), \
            mock.patch.object(RUNTIME, "git_show_text_or_none") as show_text:
            result = RUNTIME.activate_care_ase_after_smoke_b(
                repo=Path(tmp),
                branch="develop",
                ref="HEAD",
                activation_nonce="care-ase-new-forbidden",
                dry_run=True,
            )

        self.assertEqual(result["status"], "NOOP_ALREADY_ARMED")
        self.assertEqual(result["request_nonce"], "care-ase-existing")
        self.assertEqual(result["updated_paths"], [])
        show_text.assert_not_called()

    def test_smoke_b_pass_controller_update_commits_activation(self) -> None:
        activation = {
            "updated_paths": [
                "results/agent_flow_v3/gpt-loop-smoke-b/gpt_loop_smoke_final.json",
                "automation/agent_flow_v3/tasks/care-ase-faithful/REQUEST.json",
            ],
            "request_nonce": "care-ase-test",
        }
        commit = {"status": "COMMITTED_AND_PUSHED", "commit_sha": "b" * 40, "pushed": True}

        with tempfile.TemporaryDirectory() as tmp, \
            mock.patch.object(RUNTIME, "ensure_clean_ff_to_remote", return_value="a" * 40) as clean_ff, \
            mock.patch.object(RUNTIME, "activate_care_ase_after_smoke_b", return_value=activation) as activate, \
            mock.patch.object(RUNTIME, "commit_and_push", return_value=commit) as commit_push:
            result = RUNTIME.apply_smoke_b_pass_controller_update(Path(tmp), "develop")

        self.assertEqual(result["status"], "APPLIED")
        self.assertEqual(result["head_before_update"], "a" * 40)
        clean_ff.assert_called_once()
        activate.assert_called_once()
        commit_push.assert_called_once()
        self.assertEqual(result["commit"], commit)

    def test_smoke_b_pass_controller_update_noop_does_not_commit(self) -> None:
        activation = {
            "updated_paths": [],
            "request_nonce": "care-ase-existing",
            "status": "NOOP_ALREADY_ARMED",
        }

        with tempfile.TemporaryDirectory() as tmp, \
            mock.patch.object(RUNTIME, "ensure_clean_ff_to_remote", return_value="a" * 40), \
            mock.patch.object(RUNTIME, "activate_care_ase_after_smoke_b", return_value=activation), \
            mock.patch.object(RUNTIME, "git", return_value="b" * 40), \
            mock.patch.object(RUNTIME, "commit_and_push") as commit_push:
            result = RUNTIME.apply_smoke_b_pass_controller_update(Path(tmp), "develop")

        self.assertEqual(result["status"], "APPLIED")
        self.assertEqual(result["activation"]["status"], "NOOP_ALREADY_ARMED")
        self.assertEqual(result["commit"]["status"], "NO_CHANGES")
        commit_push.assert_not_called()

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

    def test_waiting_watcher_uses_bound_planner_review_artifact_event(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            repo = root / "repo"
            repo.mkdir()
            subprocess.check_call(["git", "init"], cwd=repo, stdout=subprocess.DEVNULL)
            subprocess.check_call(["git", "config", "user.email", "test@example.invalid"], cwd=repo)
            subprocess.check_call(["git", "config", "user.name", "Agent Flow Test"], cwd=repo)
            task_dir = repo / "automation/agent_flow_v3/tasks/care-ase-faithful"
            review_dir = repo / "results/agent_flow_v3/care-ase-faithful/planner_reviews"
            repair_dir = task_dir / "repairs"
            review_dir.mkdir(parents=True)
            repair_dir.mkdir(parents=True)
            verifier_prompt = repair_dir / "round_001_reentry_001_verifier.md"
            executor_prompt = repair_dir / "round_001_reentry_001_executor.md"
            verifier_prompt.write_text("verifier repair\n", encoding="utf-8")
            executor_prompt.write_text("executor repair\n", encoding="utf-8")
            review_path = review_dir / "round_001_reentry_001.json"
            review_path.write_text(
                json.dumps(
                    {
                        "schema": "CARE_AGENT_FLOW_V3_PLANNER_REVIEW",
                        "task_id": "care-ase-faithful",
                        "request_nonce": "nonce-1",
                        "review_round": 1,
                        "review_reentry": "round_001_reentry_001",
                        "decision": "PLANNER_REVISE_BOTH",
                        "frozen_contract_sha256": "a" * 64,
                        "integration_commit_sha": "b" * 40,
                        "implementation_fingerprint_sha256": "c" * 64,
                        "verifier_fingerprint_sha256": "d" * 64,
                        "created_utc": "2026-08-07T01:26:00Z",
                    }
                ),
                encoding="utf-8",
            )
            subprocess.check_call(["git", "add", "."], cwd=repo)
            subprocess.check_call(["git", "commit", "-m", "planner review"], cwd=repo, stdout=subprocess.DEVNULL)
            request = {
                "schema": RUNTIME.SCHEMA,
                "enabled": True,
                "task_id": "care-ase-faithful",
                "integration_branch": "develop",
                "request_nonce": "nonce-1",
                "frozen_contract_sha256": "a" * 64,
            }
            current = {
                "schema": RUNTIME.SCHEMA,
                "task_id": "care-ase-faithful",
                "state": "WAITING_FOR_EXTERNAL_GPT",
                "review_round": 1,
                "request_nonce": "nonce-1",
                "frozen_contract_sha256": "a" * 64,
                "integration_commit_sha": "b" * 40,
                "implementation_fingerprint_sha256": "c" * 64,
                "verifier_fingerprint_sha256": "d" * 64,
            }
            overlay = RUNTIME.planner_review_artifact_event(
                repo=repo,
                ref="HEAD",
                task_id="care-ase-faithful",
                request=request,
                current=current,
                remote_sha="e" * 40,
            )
            self.assertIsNotNone(overlay)
            assert overlay is not None
            self.assertEqual(overlay["state"], "PLANNER_REVISE_BOTH")
            self.assertEqual(
                overlay["planner_review_artifact"],
                "results/agent_flow_v3/care-ase-faithful/planner_reviews/round_001_reentry_001.json",
            )
            self.assertEqual(overlay["watcher_target_roles_override"], ["verifier"])
            self.assertEqual(overlay["watcher_deferred_target_roles"], ["executor"])
            self.assertEqual(
                overlay["repair_prompts"]["verifier"],
                "automation/agent_flow_v3/tasks/care-ase-faithful/repairs/round_001_reentry_001_verifier.md",
            )

            thread_file = root / "verifier_thread_id"
            thread_file.write_text("verifier-thread\n", encoding="utf-8")
            role_plan = root / "role_plan.json"
            role_plan.write_text(
                json.dumps(
                    {
                        "roles": {
                            "verifier": {
                                "thread_id_file": str(thread_file),
                                "codex_home": str(root / "verifier_home"),
                                "worktree": str(root / "verifier_worktree"),
                            },
                            "executor": {
                                "thread_id_file": str(root / "executor_thread_id"),
                                "codex_home": str(root / "executor_home"),
                                "worktree": str(root / "executor_worktree"),
                            },
                        }
                    }
                ),
                encoding="utf-8",
            )
            args = argparse.Namespace(
                task_id="care-ase-faithful",
                branch="develop",
                role_plan=str(role_plan),
                codex_bin="/opt/codex",
                state_root=root / "state",
                session_receipt_root=str(root / "missing_receipts"),
                dry_run=True,
                thread_id_override="",
            )
            receipt = RUNTIME.evaluate_watcher_event(args, request, overlay, {"processed_events": []})
            self.assertEqual(receipt["decision"], "DRY_RUN_RESUME")
            self.assertEqual(receipt["target_roles"], ["verifier"])
            self.assertEqual(receipt["deferred_target_roles"], ["executor"])
            self.assertEqual(receipt["resume_commands"][0]["role"], "verifier")
            self.assertIn("round_001_reentry_001.json", receipt["event_key"])

    def test_waiting_watcher_accepts_stable_review_snapshot_artifact_without_integration_sha(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            repo = root / "repo"
            repo.mkdir()
            subprocess.check_call(["git", "init"], cwd=repo, stdout=subprocess.DEVNULL)
            subprocess.check_call(["git", "config", "user.email", "test@example.invalid"], cwd=repo)
            subprocess.check_call(["git", "config", "user.name", "Agent Flow Test"], cwd=repo)
            task_dir = repo / "automation/agent_flow_v3/tasks/portable-task"
            review_dir = repo / "results/agent_flow_v3/portable-task/planner_reviews"
            repair_dir = task_dir / "repairs"
            review_dir.mkdir(parents=True)
            repair_dir.mkdir(parents=True)
            (repair_dir / "round_001_reentry_002_executor.md").write_text("executor repair\n", encoding="utf-8")
            review_path = review_dir / "round_001_reentry_002.json"
            review_path.write_text(
                json.dumps(
                    {
                        "schema": "CARE_AGENT_FLOW_V3_PLANNER_REVIEW",
                        "task_id": "portable-task",
                        "request_nonce": "nonce-1",
                        "review_round": 1,
                        "review_reentry": "round_001_reentry_002",
                        "decision": "PLANNER_REVISE_EXECUTOR",
                        "frozen_contract_sha256": "a" * 64,
                        "requirement_ledger_sha256": "b" * 64,
                        "review_target_id": "c" * 64,
                        "review_bundle_sha256": "d" * 64,
                        "ci_pass": True,
                        "created_utc": "2026-08-11T08:30:00Z",
                    }
                ),
                encoding="utf-8",
            )
            subprocess.check_call(["git", "add", "."], cwd=repo)
            subprocess.check_call(["git", "commit", "-m", "stable planner review"], cwd=repo, stdout=subprocess.DEVNULL)
            request = {
                "schema": RUNTIME.SCHEMA,
                "enabled": True,
                "task_id": "portable-task",
                "integration_branch": "develop",
                "request_nonce": "nonce-1",
                "frozen_contract_sha256": "a" * 64,
            }
            current = {
                "schema": RUNTIME.SCHEMA,
                "task_id": "portable-task",
                "state": "WAITING_FOR_EXTERNAL_GPT",
                "review_identity_model": "STABLE_REVIEW_SNAPSHOT",
                "review_round": 1,
                "request_nonce": "nonce-1",
                "frozen_contract_sha256": "a" * 64,
                "requirement_ledger_sha256": "b" * 64,
                "review_target_id": "c" * 64,
                "review_bundle_sha256": "d" * 64,
                "integration_commit_sha": "e" * 40,
                "implementation_fingerprint_sha256": "f" * 64,
                "verifier_fingerprint_sha256": "1" * 64,
            }
            overlay = RUNTIME.planner_review_artifact_event(
                repo=repo,
                ref="HEAD",
                task_id="portable-task",
                request=request,
                current=current,
                remote_sha="2" * 40,
            )
            self.assertIsNotNone(overlay)
            assert overlay is not None
            self.assertEqual(overlay["state"], "PLANNER_REVISE_EXECUTOR")
            self.assertEqual(overlay["integration_commit_sha"], "e" * 40)
            self.assertEqual(overlay["planner_review_input_review_target_id"], "c" * 64)
            self.assertEqual(overlay["planner_review_input_review_bundle_sha256"], "d" * 64)

            thread_file = root / "executor_thread_id"
            thread_file.write_text("executor-thread\n", encoding="utf-8")
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
                task_id="portable-task",
                branch="develop",
                role_plan=str(role_plan),
                codex_bin="/opt/codex",
                state_root=root / "state",
                session_receipt_root=str(root / "missing_receipts"),
                dry_run=True,
                thread_id_override="",
            )
            receipt = RUNTIME.evaluate_watcher_event(args, request, overlay, {"processed_events": []})
            self.assertEqual(receipt["decision"], "DRY_RUN_RESUME")
            self.assertEqual(receipt["target_roles"], ["executor"])
            self.assertIn("round_001_reentry_002.json", receipt["event_key"])

    def test_waiting_watcher_accepts_stable_review_snapshot_nested_binding(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            repo = root / "repo"
            repo.mkdir()
            subprocess.check_call(["git", "init"], cwd=repo, stdout=subprocess.DEVNULL)
            subprocess.check_call(["git", "config", "user.email", "test@example.invalid"], cwd=repo)
            subprocess.check_call(["git", "config", "user.name", "Agent Flow Test"], cwd=repo)
            review_dir = repo / "results/agent_flow_v3/portable-task/planner_reviews"
            repair_dir = repo / "automation/agent_flow_v3/tasks/portable-task/repairs"
            review_dir.mkdir(parents=True)
            repair_dir.mkdir(parents=True)
            (repair_dir / "round_001_reentry_003_verifier.md").write_text("verifier repair\n", encoding="utf-8")
            review_path = review_dir / "round_001_reentry_003.json"
            review_path.write_text(
                json.dumps(
                    {
                        "schema": "CARE_AGENT_FLOW_V3_PLANNER_REVIEW",
                        "task_id": "portable-task",
                        "request_nonce": "nonce-1",
                        "review_round": 1,
                        "review_reentry": "round_001_reentry_003",
                        "decision": "PLANNER_REVISE_VERIFIER",
                        "binding": {
                            "review_identity_model": "STABLE_REVIEW_SNAPSHOT",
                            "frozen_contract_sha256": "a" * 64,
                            "requirement_ledger_sha256": "b" * 64,
                            "review_target_id": "c" * 64,
                            "review_bundle_sha256": "d" * 64,
                            "stable_review_ci_status": "PASS",
                        },
                        "created_utc": "2026-08-11T09:05:48Z",
                    }
                ),
                encoding="utf-8",
            )
            subprocess.check_call(["git", "add", "."], cwd=repo)
            subprocess.check_call(["git", "commit", "-m", "nested stable planner review"], cwd=repo, stdout=subprocess.DEVNULL)
            request = {
                "schema": RUNTIME.SCHEMA,
                "enabled": True,
                "task_id": "portable-task",
                "integration_branch": "develop",
                "request_nonce": "nonce-1",
                "frozen_contract_sha256": "a" * 64,
            }
            current = {
                "schema": RUNTIME.SCHEMA,
                "task_id": "portable-task",
                "state": "WAITING_FOR_EXTERNAL_GPT",
                "review_identity_model": "STABLE_REVIEW_SNAPSHOT",
                "review_round": 1,
                "request_nonce": "nonce-1",
                "frozen_contract_sha256": "a" * 64,
                "requirement_ledger_sha256": "b" * 64,
                "review_target_id": "c" * 64,
                "review_bundle_sha256": "d" * 64,
                "integration_commit_sha": "e" * 40,
            }
            overlay = RUNTIME.planner_review_artifact_event(
                repo=repo,
                ref="HEAD",
                task_id="portable-task",
                request=request,
                current=current,
                remote_sha="2" * 40,
            )
            self.assertIsNotNone(overlay)
            assert overlay is not None
            self.assertEqual(overlay["state"], "PLANNER_REVISE_VERIFIER")
            self.assertEqual(overlay["integration_commit_sha"], "e" * 40)
            self.assertEqual(overlay["planner_review_input_requirement_ledger_sha256"], "b" * 64)
            self.assertEqual(overlay["planner_review_input_review_target_id"], "c" * 64)
            self.assertEqual(overlay["planner_review_input_review_bundle_sha256"], "d" * 64)
            self.assertEqual(
                overlay["repair_prompts"]["verifier"],
                "automation/agent_flow_v3/tasks/portable-task/repairs/round_001_reentry_003_verifier.md",
            )

    def test_waiting_watcher_rejects_wrong_stable_review_target(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            repo = root / "repo"
            repo.mkdir()
            subprocess.check_call(["git", "init"], cwd=repo, stdout=subprocess.DEVNULL)
            subprocess.check_call(["git", "config", "user.email", "test@example.invalid"], cwd=repo)
            subprocess.check_call(["git", "config", "user.name", "Agent Flow Test"], cwd=repo)
            review_dir = repo / "results/agent_flow_v3/portable-task/planner_reviews"
            review_dir.mkdir(parents=True)
            (review_dir / "round_001.json").write_text(
                json.dumps(
                    {
                        "schema": "CARE_AGENT_FLOW_V3_PLANNER_REVIEW",
                        "task_id": "portable-task",
                        "request_nonce": "nonce-1",
                        "review_round": 1,
                        "decision": "PLANNER_PASS",
                        "frozen_contract_sha256": "a" * 64,
                        "requirement_ledger_sha256": "b" * 64,
                        "review_target_id": "9" * 64,
                        "review_bundle_sha256": "d" * 64,
                        "ci_pass": True,
                        "created_utc": "2026-08-11T08:31:00Z",
                    }
                ),
                encoding="utf-8",
            )
            subprocess.check_call(["git", "add", "."], cwd=repo)
            subprocess.check_call(["git", "commit", "-m", "wrong stable target"], cwd=repo, stdout=subprocess.DEVNULL)
            request = {
                "schema": RUNTIME.SCHEMA,
                "enabled": True,
                "task_id": "portable-task",
                "integration_branch": "develop",
                "request_nonce": "nonce-1",
                "frozen_contract_sha256": "a" * 64,
            }
            current = {
                "schema": RUNTIME.SCHEMA,
                "task_id": "portable-task",
                "state": "WAITING_FOR_EXTERNAL_GPT",
                "review_identity_model": "STABLE_REVIEW_SNAPSHOT",
                "review_round": 1,
                "request_nonce": "nonce-1",
                "frozen_contract_sha256": "a" * 64,
                "requirement_ledger_sha256": "b" * 64,
                "review_target_id": "c" * 64,
                "review_bundle_sha256": "d" * 64,
            }
            overlay = RUNTIME.planner_review_artifact_event(
                repo=repo,
                ref="HEAD",
                task_id="portable-task",
                request=request,
                current=current,
                remote_sha="2" * 40,
            )
            self.assertIsNone(overlay)

    def test_reentry_event_without_exact_prompt_uses_planner_artifact_not_old_round_prompt(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            repo = root / "repo"
            repo.mkdir()
            subprocess.check_call(["git", "init"], cwd=repo, stdout=subprocess.DEVNULL)
            subprocess.check_call(["git", "config", "user.email", "test@example.invalid"], cwd=repo)
            subprocess.check_call(["git", "config", "user.name", "Agent Flow Test"], cwd=repo)
            task_dir = repo / "automation/agent_flow_v3/tasks/portable-task"
            review_dir = repo / "results/agent_flow_v3/portable-task/planner_reviews"
            repair_dir = task_dir / "repairs"
            review_dir.mkdir(parents=True)
            repair_dir.mkdir(parents=True)
            (repair_dir / "round_001_verifier.md").write_text("stale old prompt\n", encoding="utf-8")
            review_path = review_dir / "round_001_reentry_005.json"
            review_path.write_text(
                json.dumps(
                    {
                        "schema": "CARE_AGENT_FLOW_V3_PLANNER_REVIEW",
                        "task_id": "portable-task",
                        "request_nonce": "nonce-1",
                        "review_round": 1,
                        "review_reentry": "round_001_reentry_005",
                        "decision": "PLANNER_REVISE_VERIFIER",
                        "frozen_contract_sha256": "a" * 64,
                        "integration_commit_sha": "b" * 40,
                        "implementation_fingerprint_sha256": "c" * 64,
                        "verifier_fingerprint_sha256": "d" * 64,
                        "created_utc": "2026-08-08T10:06:19Z",
                    }
                ),
                encoding="utf-8",
            )
            subprocess.check_call(["git", "add", "."], cwd=repo)
            subprocess.check_call(["git", "commit", "-m", "planner reentry"], cwd=repo, stdout=subprocess.DEVNULL)
            request = {
                "schema": RUNTIME.SCHEMA,
                "enabled": True,
                "task_id": "portable-task",
                "integration_branch": "develop",
                "request_nonce": "nonce-1",
                "frozen_contract_sha256": "a" * 64,
            }
            current = {
                "schema": RUNTIME.SCHEMA,
                "task_id": "portable-task",
                "state": "WAITING_FOR_EXTERNAL_GPT",
                "review_round": 1,
                "request_nonce": "nonce-1",
                "frozen_contract_sha256": "a" * 64,
                "integration_commit_sha": "b" * 40,
                "implementation_fingerprint_sha256": "c" * 64,
                "verifier_fingerprint_sha256": "d" * 64,
            }
            overlay = RUNTIME.planner_review_artifact_event(
                repo=repo,
                ref="HEAD",
                task_id="portable-task",
                request=request,
                current=current,
                remote_sha="e" * 40,
            )
            self.assertIsNotNone(overlay)
            assert overlay is not None
            self.assertEqual(overlay["state"], "PLANNER_REVISE_VERIFIER")
            self.assertEqual(overlay["repair_prompts"], {})
            payload, path, _sha = RUNTIME.load_exact_repair_prompt(
                repo,
                "portable-task",
                "verifier",
                overlay,
                ref="HEAD",
            )
            self.assertEqual(path, repo / "results/agent_flow_v3/portable-task/planner_reviews/round_001_reentry_005.json")
            self.assertIn(b"PLANNER_REVISE_VERIFIER", payload)

    def test_care_ase_reentry_current_routes_verifier_before_executor(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            thread_file = root / "verifier_thread_id"
            thread_file.write_text("verifier-thread\n", encoding="utf-8")
            role_plan = root / "role_plan.json"
            role_plan.write_text(
                json.dumps(
                    {
                        "roles": {
                            "verifier": {
                                "thread_id_file": str(thread_file),
                                "codex_home": str(root / "verifier_home"),
                                "worktree": str(root / "verifier_worktree"),
                            },
                            "executor": {
                                "thread_id_file": str(root / "executor_thread_id"),
                                "codex_home": str(root / "executor_home"),
                                "worktree": str(root / "executor_worktree"),
                            },
                        }
                    }
                ),
                encoding="utf-8",
            )
            args = argparse.Namespace(
                task_id="care-ase-faithful",
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
                "task_id": "care-ase-faithful",
                "integration_branch": "develop",
                "request_nonce": "nonce-1",
                "frozen_contract_sha256": "a" * 64,
            }
            current = {
                "schema": RUNTIME.SCHEMA,
                "task_id": "care-ase-faithful",
                "state": "PLANNER_REVISE_BOTH",
                "review_round": 1,
                "request_nonce": "nonce-1",
                "frozen_contract_sha256": "a" * 64,
                "integration_commit_sha": "b" * 40,
                "planner_review_artifact": "results/agent_flow_v3/care-ase-faithful/planner_reviews/round_001_reentry_001.json",
                "repair_prompts": {
                    "verifier": "automation/agent_flow_v3/tasks/care-ase-faithful/repairs/round_001_reentry_001_verifier.md",
                    "executor": "automation/agent_flow_v3/tasks/care-ase-faithful/repairs/round_001_reentry_001_executor.md",
                },
            }
            receipt = RUNTIME.evaluate_watcher_event(args, request, current, {"processed_events": []})
            self.assertEqual(receipt["decision"], "DRY_RUN_RESUME")
            self.assertEqual(receipt["target_roles"], ["verifier"])
            self.assertEqual(receipt["deferred_target_roles"], ["executor"])
            self.assertEqual([item["role"] for item in receipt["resume_commands"]], ["verifier"])

    def test_watcher_allows_verified_thread_file_supersession_of_stale_receipt(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            state_root = root / "state"
            task_state = state_root / "care-ase-faithful"
            task_state.mkdir(parents=True)
            thread_file = task_state / "verifier_thread_id"
            thread_file.write_text("new-verifier-thread\n", encoding="utf-8")
            codex_home = root / "verifier_home"
            rollout_dir = codex_home / "sessions" / "2026" / "08" / "07"
            rollout_dir.mkdir(parents=True)
            (rollout_dir / "rollout-2026-08-07T00-00-00-new-verifier-thread.jsonl").write_text(
                "{}\n",
                encoding="utf-8",
            )
            worktree = root / "verifier_worktree"
            worktree.mkdir()
            subprocess.check_call(["git", "init"], cwd=worktree, stdout=subprocess.DEVNULL)
            (task_state / "verifier_launch_receipt.json").write_text(
                json.dumps(
                    {
                        "role": "verifier",
                        "thread_id": "new-verifier-thread",
                        "codex_home": str(codex_home),
                        "worktree": str(worktree),
                    }
                ),
                encoding="utf-8",
            )
            receipt_root = root / "receipts"
            receipt_root.mkdir()
            (receipt_root / "verifier_session_receipt.json").write_text(
                json.dumps({"role": "verifier", "thread_id": "old-verifier-thread"}),
                encoding="utf-8",
            )
            role_plan = root / "role_plan.json"
            role_plan.write_text(
                json.dumps(
                    {
                        "roles": {
                            "verifier": {
                                "thread_id_file": str(thread_file),
                                "codex_home": str(codex_home),
                                "worktree": str(worktree),
                            }
                        }
                    }
                ),
                encoding="utf-8",
            )
            args = argparse.Namespace(
                task_id="care-ase-faithful",
                branch="develop",
                role_plan=str(role_plan),
                codex_bin="/opt/codex",
                state_root=state_root,
                session_receipt_root=str(receipt_root),
                dry_run=True,
                thread_id_override="",
            )
            request = {
                "schema": RUNTIME.SCHEMA,
                "enabled": True,
                "task_id": "care-ase-faithful",
                "integration_branch": "develop",
                "request_nonce": "nonce-1",
                "frozen_contract_sha256": "a" * 64,
            }
            current = {
                "schema": RUNTIME.SCHEMA,
                "task_id": "care-ase-faithful",
                "state": "PLANNER_REVISE_VERIFIER",
                "review_round": 1,
                "request_nonce": "nonce-1",
                "frozen_contract_sha256": "a" * 64,
                "integration_commit_sha": "b" * 40,
            }
            receipt = RUNTIME.evaluate_watcher_event(args, request, current, {"processed_events": []})
            self.assertEqual(receipt["decision"], "DRY_RUN_RESUME")
            self.assertEqual(receipt["failures"], [])
            self.assertTrue(receipt["resume_commands"][0]["session_receipt_superseded_by_thread_file"])

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

            def __init__(self, command, stdin, stdout, stderr, env, cwd):
                self.command = command
                self.env = env
                self.cwd = cwd
                self.pid = 4242
                self.returncode = 0
                FakePopen.calls.append(self)

            def communicate(self, input):
                self.input = input
                return b"stdout-ok", b"stderr-ok"

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            receipt = RUNTIME.execute_live_resume(
                command=RUNTIME.build_resume_command("/opt/codex", root / "worktree", "thread-1"),
                codex_home=str(root / "codex-home"),
                role="executor",
                task_id="smoke-task",
                state_root=root / "state",
                log_root=root / "logs",
                prompt_payload=b"exact repair prompt\n",
                prompt_path=root / "prompt.md",
                popen_factory=FakePopen,
            )
            self.assertEqual(FakePopen.calls[0].command[5], "--all")
            self.assertEqual(FakePopen.calls[0].command[6], "thread-1")
            self.assertNotIn("--last", FakePopen.calls[0].command)
            self.assertEqual(FakePopen.calls[0].env["CODEX_HOME"], str(root / "codex-home"))
            self.assertEqual(FakePopen.calls[0].env["CODEX_PERSISTENT_HOME"], str(root / "codex-home"))
            self.assertEqual(FakePopen.calls[0].env["CODEX_HOME_OVERRIDE"], str(root / "codex-home"))
            self.assertEqual(FakePopen.calls[0].env["CODEX_RESPECT_CODEX_HOME"], "1")
            self.assertEqual(FakePopen.calls[0].env["CODEX_USE_RUNTIME_HOME"], "0")
            self.assertEqual(FakePopen.calls[0].env["CODEX_REPO_ROOT"], str(root / "worktree"))
            self.assertEqual(FakePopen.calls[0].env["CODEX_RESPECT_REPO_ROOT"], "1")
            self.assertEqual(FakePopen.calls[0].cwd, str(root / "worktree"))
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
            with mock.patch.object(RUNTIME, "pid_looks_like_codex", return_value=True):
                result = RUNTIME.evaluate_watcher_event(args, request, current, {"processed_events": []})
            self.assertEqual(result["decision"], "INVALID_EVENT")
            self.assertIn("executor:active_process", result["failures"])

    def test_stale_bash_pane_active_process_does_not_block_resume(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            active_path = RUNTIME.active_process_path(root / "state", "smoke-task", "executor")
            active_path.parent.mkdir(parents=True)
            active_path.write_text(json.dumps({"pid": os.getpid(), "exit_code": None}), encoding="utf-8")
            with mock.patch.object(RUNTIME, "pid_looks_like_codex", return_value=False), mock.patch.object(
                RUNTIME, "process_has_child", return_value=False
            ):
                self.assertIsNone(RUNTIME.role_active_process(root / "state", "smoke-task", "executor"))

    def test_role_worktree_current_allows_clean_local_branch_containing_remote(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            remote = root / "remote.git"
            seed = root / "seed"
            worktree = root / "worktree"
            subprocess.check_call(["git", "init", "--bare", str(remote)], stdout=subprocess.DEVNULL)
            subprocess.check_call(["git", "clone", str(remote), str(seed)], stdout=subprocess.DEVNULL)
            subprocess.check_call(["git", "config", "user.email", "test@example.com"], cwd=seed)
            subprocess.check_call(["git", "config", "user.name", "Test"], cwd=seed)
            (seed / "README.md").write_text("base\n", encoding="utf-8")
            subprocess.check_call(["git", "add", "README.md"], cwd=seed)
            subprocess.check_call(["git", "commit", "-m", "base"], cwd=seed, stdout=subprocess.DEVNULL)
            subprocess.check_call(["git", "branch", "-M", "develop"], cwd=seed)
            subprocess.check_call(["git", "push", "origin", "develop"], cwd=seed, stdout=subprocess.DEVNULL)
            subprocess.check_call(["git", "clone", "-b", "develop", str(remote), str(worktree)], stdout=subprocess.DEVNULL)
            subprocess.check_call(["git", "config", "user.email", "test@example.com"], cwd=worktree)
            subprocess.check_call(["git", "config", "user.name", "Test"], cwd=worktree)
            (worktree / "local.txt").write_text("local\n", encoding="utf-8")
            subprocess.check_call(["git", "add", "local.txt"], cwd=worktree)
            subprocess.check_call(["git", "commit", "-m", "local"], cwd=worktree, stdout=subprocess.DEVNULL)

            head = RUNTIME.ensure_role_worktree_current(worktree, "develop")

            self.assertEqual(head, RUNTIME.git(worktree, "rev-parse", "HEAD"))

    def test_role_worktree_current_merges_clean_diverged_role_branch(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            remote = root / "remote.git"
            seed = root / "seed"
            worktree = root / "worktree"
            subprocess.check_call(["git", "init", "--bare", str(remote)], stdout=subprocess.DEVNULL)
            subprocess.check_call(["git", "clone", str(remote), str(seed)], stdout=subprocess.DEVNULL)
            subprocess.check_call(["git", "config", "user.email", "test@example.com"], cwd=seed)
            subprocess.check_call(["git", "config", "user.name", "Test"], cwd=seed)
            (seed / "README.md").write_text("base\n", encoding="utf-8")
            subprocess.check_call(["git", "add", "README.md"], cwd=seed)
            subprocess.check_call(["git", "commit", "-m", "base"], cwd=seed, stdout=subprocess.DEVNULL)
            subprocess.check_call(["git", "branch", "-M", "develop"], cwd=seed)
            subprocess.check_call(["git", "push", "origin", "develop"], cwd=seed, stdout=subprocess.DEVNULL)
            subprocess.check_call(["git", "clone", "-b", "develop", str(remote), str(worktree)], stdout=subprocess.DEVNULL)
            subprocess.check_call(["git", "config", "user.email", "test@example.com"], cwd=worktree)
            subprocess.check_call(["git", "config", "user.name", "Test"], cwd=worktree)
            (worktree / "local.txt").write_text("local\n", encoding="utf-8")
            subprocess.check_call(["git", "add", "local.txt"], cwd=worktree)
            subprocess.check_call(["git", "commit", "-m", "role local"], cwd=worktree, stdout=subprocess.DEVNULL)
            (seed / "remote.txt").write_text("remote\n", encoding="utf-8")
            subprocess.check_call(["git", "add", "remote.txt"], cwd=seed)
            subprocess.check_call(["git", "commit", "-m", "remote advance"], cwd=seed, stdout=subprocess.DEVNULL)
            subprocess.check_call(["git", "push", "origin", "develop"], cwd=seed, stdout=subprocess.DEVNULL)

            head = RUNTIME.ensure_role_worktree_current(worktree, "develop")

            self.assertEqual(head, RUNTIME.git(worktree, "rev-parse", "HEAD"))
            self.assertTrue((worktree / "local.txt").is_file())
            self.assertTrue((worktree / "remote.txt").is_file())
            subprocess.check_call(["git", "merge-base", "--is-ancestor", "origin/develop", "HEAD"], cwd=worktree)

    def test_executor_merge_conflict_can_be_deferred_to_exact_role(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            remote = root / "remote.git"
            seed = root / "seed"
            worktree = root / "worktree"
            subprocess.check_call(["git", "init", "--bare", str(remote)], stdout=subprocess.DEVNULL)
            subprocess.check_call(["git", "clone", str(remote), str(seed)], stdout=subprocess.DEVNULL)
            subprocess.check_call(["git", "config", "user.email", "test@example.com"], cwd=seed)
            subprocess.check_call(["git", "config", "user.name", "Test"], cwd=seed)
            (seed / "src").mkdir()
            (seed / "src" / "model.py").write_text("base\n", encoding="utf-8")
            subprocess.check_call(["git", "add", "src/model.py"], cwd=seed)
            subprocess.check_call(["git", "commit", "-m", "base"], cwd=seed, stdout=subprocess.DEVNULL)
            subprocess.check_call(["git", "branch", "-M", "develop"], cwd=seed)
            subprocess.check_call(["git", "push", "origin", "develop"], cwd=seed, stdout=subprocess.DEVNULL)
            subprocess.check_call(["git", "clone", "-b", "develop", str(remote), str(worktree)], stdout=subprocess.DEVNULL)
            subprocess.check_call(["git", "config", "user.email", "test@example.com"], cwd=worktree)
            subprocess.check_call(["git", "config", "user.name", "Test"], cwd=worktree)
            (worktree / "src" / "model.py").write_text("executor\n", encoding="utf-8")
            subprocess.check_call(["git", "add", "src/model.py"], cwd=worktree)
            subprocess.check_call(["git", "commit", "-m", "executor local"], cwd=worktree, stdout=subprocess.DEVNULL)
            (seed / "src" / "model.py").write_text("develop\n", encoding="utf-8")
            subprocess.check_call(["git", "add", "src/model.py"], cwd=seed)
            subprocess.check_call(["git", "commit", "-m", "develop advance"], cwd=seed, stdout=subprocess.DEVNULL)
            subprocess.check_call(["git", "push", "origin", "develop"], cwd=seed, stdout=subprocess.DEVNULL)

            with self.assertRaises(RUNTIME.RuntimeErrorV3) as raised:
                RUNTIME.ensure_role_worktree_current(worktree, "develop")

            self.assertIn("role_worktree_merge_conflict", str(raised.exception))
            self.assertEqual(RUNTIME.git_status_short(worktree), "")
            sync = RUNTIME.defer_executor_merge_conflict_to_role(worktree, "develop", raised.exception)
            self.assertEqual(sync["status"], "MERGE_CONFLICT_DEFERRED_TO_EXECUTOR")
            self.assertEqual(sync["overlapping_changed_paths"], ["src/model.py"])
            head, sync = RUNTIME.prepare_executor_worktree_for_start(worktree, "develop")
            self.assertEqual(head, RUNTIME.git(worktree, "rev-parse", "HEAD"))
            self.assertEqual(sync["status"], "MERGE_CONFLICT_DEFERRED_TO_EXECUTOR")
            self.assertEqual(sync["unmerged_paths"], ["src/model.py"])
            prompt = RUNTIME.build_care_ase_executor_start_prompt(
                {
                    "request_nonce": "nonce",
                    "frozen_contract_sha256": "a" * 64,
                    "verifier_fingerprint_sha256": "b" * 64,
                    "state": "VERIFIER_FROZEN",
                },
                worktree_sync=sync,
            ).decode("utf-8")
            self.assertIn("MERGE_CONFLICT_DEFERRED_TO_EXECUTOR", prompt)
            self.assertIn("reconcile origin/develop into this Executor branch", prompt)

    def test_completed_resume_receipt_is_detected_but_not_active(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            active_path = RUNTIME.active_process_path(root / "state", "smoke-task", "verifier")
            active_path.parent.mkdir(parents=True)
            active_path.write_text(
                json.dumps({"role": "verifier", "pid": os.getpid(), "exit_code": 0}),
                encoding="utf-8",
            )
            self.assertIsNone(RUNTIME.role_active_process(root / "state", "smoke-task", "verifier"))
            receipt = RUNTIME.completed_role_resume_receipt(root / "state", "smoke-task", "verifier")
            self.assertIsNotNone(receipt)
            assert receipt is not None
            self.assertEqual(receipt["role"], "verifier")

    def test_stale_already_running_launch_receipt_does_not_satisfy_role_launch(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            receipt_path = RUNTIME.care_ase_role_launch_receipt_path(root / "stage_orchestrator", "executor")
            receipt_path.parent.mkdir(parents=True)
            receipt_path.write_text(
                json.dumps(
                    {
                        "task_id": "care-ase-faithful",
                        "role": "executor",
                        "request_nonce": "nonce-1",
                        "frozen_contract_sha256": "a" * 64,
                        "status": "ALREADY_RUNNING",
                        "pane_pid": os.getpid(),
                        "prompt_path": str(root / "current_prompt.md"),
                    }
                ),
                encoding="utf-8",
            )
            current = {"request_nonce": "nonce-1", "frozen_contract_sha256": "a" * 64}
            with mock.patch.object(RUNTIME, "is_pid_running", return_value=True), mock.patch.object(
                RUNTIME, "process_command_line", return_value=f"bash -c codex < {root / 'old_prompt.md'}"
            ):
                self.assertFalse(
                    RUNTIME.care_ase_role_launch_satisfied(root / "stage_orchestrator", current, "executor")
                )

    def test_stale_bash_pane_launch_receipt_does_not_satisfy_role_launch(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            stage_root = root / "stage_orchestrator"
            receipt_path = RUNTIME.care_ase_role_launch_receipt_path(stage_root, "executor")
            active_path = RUNTIME.active_process_path(stage_root.parent, "care-ase-faithful", "executor")
            receipt_path.parent.mkdir(parents=True)
            active_path.parent.mkdir(parents=True, exist_ok=True)
            payload = {
                "task_id": "care-ase-faithful",
                "role": "executor",
                "request_nonce": "nonce-1",
                "frozen_contract_sha256": "a" * 64,
                "status": "STARTED",
                "pane_pid": os.getpid(),
                "prompt_path": str(root / "current_prompt.md"),
            }
            receipt_path.write_text(json.dumps(payload), encoding="utf-8")
            active_path.write_text(json.dumps({**payload, "pid": os.getpid(), "exit_code": None}), encoding="utf-8")
            current = {"request_nonce": "nonce-1", "frozen_contract_sha256": "a" * 64}
            with mock.patch.object(RUNTIME, "is_pid_running", return_value=True), mock.patch.object(
                RUNTIME, "process_has_child", return_value=False
            ):
                self.assertFalse(RUNTIME.care_ase_role_launch_satisfied(stage_root, current, "executor"))

    def test_watcher_dry_run_does_not_consume_event(self) -> None:
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
        self.assertNotIn(receipt["event_key"], state["processed_events"])
        live_state = RUNTIME.update_watcher_state(
            {"processed_events": []},
            {**receipt, "decision": "LIVE_RESUME", "resume_results": []},
        )
        self.assertIn(receipt["event_key"], live_state["processed_events"])
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
        self.assertEqual(RUNTIME.evaluate_watcher_event(args, request, current, live_state)["decision"], "IGNORE")

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
            "task_id": "care-visual-smoke",
            "role": "planner_visual_smoke",
            "request_nonce": "nonce-1",
            "source_manifest_path": "automation/agent_flow_v3/tasks/care-visual-smoke/VISUAL_SOURCES.json",
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
                expected_task_id="care-visual-smoke",
                expected_role="planner_visual_smoke",
                request_nonce="nonce-1",
                expected_shas={"CARE-ASE": "a" * 64, "SRR-v3": "b" * 64, "MoSAIC": "c" * 64},
                expected_source_manifest_path="automation/agent_flow_v3/tasks/care-visual-smoke/VISUAL_SOURCES.json",
            ),
            [],
        )
        receipt["provenance"] = {"producer": "codex"}
        self.assertIn(
            "provenance:scheduled_gpt",
            RUNTIME.validate_visual_smoke_receipt(
                receipt,
                expected_task_id="care-visual-smoke",
                expected_role="planner_visual_smoke",
                request_nonce="nonce-1",
                expected_shas={"CARE-ASE": "a" * 64, "SRR-v3": "b" * 64, "MoSAIC": "c" * 64},
                expected_source_manifest_path="automation/agent_flow_v3/tasks/care-visual-smoke/VISUAL_SOURCES.json",
            ),
        )

    def test_visual_smoke_receipt_accepts_scheduled_planner_image_list_schema(self) -> None:
        receipt = {
            "task_id": "care-visual-smoke",
            "role": "planner",
            "request_nonce": "nonce-1",
            "actual_visual_access": True,
            "access_context": "scheduled ChatGPT Planner visual review",
            "source_manifest_path": "automation/agent_flow_v3/tasks/care-visual-smoke/VISUAL_SOURCES.json",
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
                expected_task_id="care-visual-smoke",
                expected_role="planner_visual_smoke",
                request_nonce="nonce-1",
                expected_shas={"CARE-ASE": "a" * 64, "SRR-v3": "b" * 64, "MoSAIC": "c" * 64},
                expected_source_manifest_path="automation/agent_flow_v3/tasks/care-visual-smoke/VISUAL_SOURCES.json",
            ),
            [],
        )

    def test_visual_smoke_receipt_accepts_scheduled_critic_field_names(self) -> None:
        receipt = {
            "task_id": "care-visual-smoke",
            "role": "critic",
            "request_nonce": "nonce-1",
            "actual_visual_access": True,
            "access_context": "scheduled ChatGPT Critic visual review",
            "source_manifest_path": "automation/agent_flow_v3/tasks/care-visual-smoke/VISUAL_SOURCES.json",
            "images": [
                {
                    "name": "CARE-ASE",
                    "sha256": "a" * 64,
                    "main_modules_visible": ["stock-compatible encoder and pathology branches"],
                    "key_dataflow": "Modalities enter a shared backbone and then branch into scar and edema routes.",
                    "missing_modality_and_no_t2_rules": ["No T2 excludes edema from final competition."],
                    "explicitly_absent_from_figure": ["No Transformer block is shown."],
                },
                {
                    "name": "SRR-v3",
                    "sha256": "b" * 64,
                    "main_modules_visible": ["anchor logits and bounded residual correction"],
                    "key_dataflow": "Modality evidence is retrieved and written back through bounded correction.",
                    "missing_modality_and_no_t2_rules": ["Unavailable modalities are masked from retrieval."],
                    "explicitly_absent_from_figure": ["No unrestricted replacement decoder is shown."],
                },
                {
                    "name": "MoSAIC",
                    "sha256": "c" * 64,
                    "main_modules_visible": ["coarse localization and independent pathology experts"],
                    "key_dataflow": "Coarse localization feeds fine pathology experts and output merging.",
                    "missing_modality_and_no_t2_rules": ["No explicit five-class no-T2 rule is visible."],
                    "explicitly_absent_from_figure": ["No nnU-Net anchor residual correction is shown."],
                },
            ],
            "cross_architecture_judgment": [
                "CARE-ASE is single-backbone reconstruction, SRR is anchor-bounded correction, and MoSAIC is coarse-to-fine experts."
            ],
        }
        self.assertEqual(
            RUNTIME.validate_visual_smoke_receipt(
                receipt,
                expected_task_id="care-visual-smoke",
                expected_role="critic_visual_smoke",
                request_nonce="nonce-1",
                expected_shas={"CARE-ASE": "a" * 64, "SRR-v3": "b" * 64, "MoSAIC": "c" * 64},
                expected_source_manifest_path="automation/agent_flow_v3/tasks/care-visual-smoke/VISUAL_SOURCES.json",
            ),
            [],
        )

    def test_critic_freeze_receipt_binds_visual_receipt_and_sources(self) -> None:
        receipt = {
            "task_id": "care-visual-smoke",
            "request_nonce": "nonce-1",
            "frozen_contract_sha256": "d" * 64,
            "critic_visual_receipt_commit_sha": "e" * 40,
            "critic_decision": "PLAN_FROZEN",
            "visual_sources_reviewed": [
                {"name": "CARE-ASE", "sha256": "a" * 64, "actual_visual_access": True},
                {"name": "SRR-v3", "sha256": "b" * 64, "actual_visual_access": True},
                {"name": "MoSAIC", "sha256": "c" * 64, "actual_visual_access": True},
            ],
        }
        self.assertEqual(
            RUNTIME.validate_critic_freeze_receipt(
                receipt,
                expected_task_id="care-visual-smoke",
                request_nonce="nonce-1",
                expected_contract_sha="d" * 64,
                expected_visual_receipt_commit_sha="e" * 40,
                expected_shas={"CARE-ASE": "a" * 64, "SRR-v3": "b" * 64, "MoSAIC": "c" * 64},
            ),
            [],
        )
        receipt["critic_visual_receipt_commit_sha"] = "f" * 40
        self.assertIn(
            "critic_visual_receipt_commit_sha",
            RUNTIME.validate_critic_freeze_receipt(
                receipt,
                expected_task_id="care-visual-smoke",
                request_nonce="nonce-1",
                expected_contract_sha="d" * 64,
                expected_visual_receipt_commit_sha="e" * 40,
                expected_shas={"CARE-ASE": "a" * 64, "SRR-v3": "b" * 64, "MoSAIC": "c" * 64},
            ),
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
            expected_task_id="care-visual-smoke",
            expected_role="critic_visual_smoke",
            request_nonce="new-nonce",
            expected_shas={"CARE-ASE": "a" * 64, "SRR-v3": "b" * 64, "MoSAIC": "c" * 64},
            expected_source_manifest_path="automation/agent_flow_v3/tasks/care-visual-smoke/VISUAL_SOURCES.json",
        )
        self.assertIn("request_nonce", failures)
        self.assertIn("image_sha256:CARE-ASE", failures)
        self.assertIn("answers:main_modules", failures)

    def _generic_requirement_ledger(self) -> dict[str, object]:
        return {
            "schema": "AGENT_FLOW_V3_REQUIREMENT_LEDGER",
            "task_id": "portable-task",
            "request_nonce": "nonce-1",
            "frozen_contract_sha256": "a" * 64,
            "requirements": [
                {
                    "requirement_id": "REQ_RUNTIME_001",
                    "source_path": "contracts/frozen.md",
                    "source_clause_or_field": "runtime exact resume",
                    "requirement_text": "Checkpoint resume must be exact.",
                    "requirement_type": "RUNTIME",
                    "blocking": True,
                    "owner_role": "executor",
                    "verification_allowed": True,
                    "numeric_threshold": None,
                    "threshold_source": None,
                    "scientific_rationale": "Resume fidelity is required by the task.",
                    "derived_invariants": [
                        {
                            "parent_requirement_ids": ["REQ_RUNTIME_001"],
                            "logical_derivation": "Exact resume requires optimizer, scheduler and RNG continuity.",
                            "why_necessary": "Otherwise the next step is not a resume.",
                            "whether_it_changes_scientific_semantics": False,
                            "blocking": True,
                        }
                    ],
                    "change_requires_contract_revision": True,
                },
                {
                    "requirement_id": "REQ_INFERENCE_001",
                    "source_path": "contracts/frozen.md",
                    "source_clause_or_field": "canonical inference path",
                    "requirement_text": "Public inference must use the canonical path.",
                    "requirement_type": "INFERENCE",
                    "blocking": True,
                    "owner_role": "executor",
                    "verification_allowed": True,
                    "numeric_threshold": {"application_count": 1},
                    "threshold_source": "contract states exactly one application",
                    "scientific_rationale": "Canonical inference defines deployment behavior.",
                    "derived_invariants": [],
                    "change_requires_contract_revision": True,
                },
                {
                    "requirement_id": "REQ_SCIENCE_001",
                    "source_path": "contracts/frozen.md",
                    "source_clause_or_field": "mutually exclusive method choice",
                    "requirement_text": "The frozen task cannot choose between two valid scientific alternatives.",
                    "requirement_type": "SCIENTIFIC",
                    "blocking": True,
                    "owner_role": "planner",
                    "verification_allowed": False,
                    "numeric_threshold": None,
                    "threshold_source": None,
                    "scientific_rationale": "This represents a real user-owned science decision.",
                    "derived_invariants": [],
                    "change_requires_contract_revision": True,
                },
            ],
            "open_scientific_choices": [],
        }

    def test_role_authority_policy_and_templates_exist(self) -> None:
        for rel in (
            "automation/agent_flow_v3/ROLE_AUTHORITY_POLICY.md",
            "automation/agent_flow_v3/templates/role_authority_policy.md",
            "automation/agent_flow_v3/templates/requirement_ledger.template.json",
            "automation/agent_flow_v3/templates/task_profile.template.json",
            "automation/agent_flow_v3/templates/routing_policy.template.json",
        ):
            self.assertTrue((ROOT / rel).is_file(), rel)

    def test_requirement_ledger_template_and_care_ledger_are_valid(self) -> None:
        template = json.loads(
            (ROOT / "automation/agent_flow_v3/templates/requirement_ledger.template.json").read_text(
                encoding="utf-8"
            )
        )
        care_ledger = json.loads(
            (ROOT / "automation/agent_flow_v3/tasks/care-ase-faithful/REQUIREMENT_LEDGER.json").read_text(
                encoding="utf-8"
            )
        )
        self.assertEqual(MODULE.validate_requirement_ledger(template, self.schema), [])
        self.assertEqual(MODULE.validate_requirement_ledger(care_ledger, self.schema), [])

    def test_generic_verifier_invents_uncited_numeric_threshold_is_rejected(self) -> None:
        finding = {
            "classification": "IMPLEMENTATION_BUG",
            "blocking": True,
            "observed_violation": "two runtime contexts differ by more than an invented epsilon",
            "verification_method": "numeric comparison",
            "numeric_threshold": 0.000001,
        }
        failures = MODULE.validate_verifier_finding(finding, self._generic_requirement_ledger(), self.schema)
        self.assertIn("verifier_blocking_finding_missing:requirement_id", failures)
        self.assertIn("verifier_blocking_numeric_threshold_missing_source", failures)

    def test_generic_verifier_diagnostic_cannot_be_blocking_without_requirement_id(self) -> None:
        finding = {
            "classification": "DIAGNOSTIC_ANOMALY",
            "blocking": True,
            "observed_violation": "diagnostic drift",
            "verification_method": "probe",
        }
        failures = MODULE.validate_verifier_finding(finding, self._generic_requirement_ledger(), self.schema)
        self.assertIn("verifier_diagnostic_must_not_block", failures)
        self.assertIn("verifier_blocking_finding_missing:requirement_id", failures)

    def test_generic_derived_invariant_without_logical_derivation_is_rejected(self) -> None:
        ledger = self._generic_requirement_ledger()
        requirements = ledger["requirements"]
        assert isinstance(requirements, list)
        first = requirements[0]
        assert isinstance(first, dict)
        first["derived_invariants"] = [
            {
                "parent_requirement_ids": ["REQ_RUNTIME_001"],
                "why_necessary": "missing derivation",
                "whether_it_changes_scientific_semantics": False,
            }
        ]
        self.assertIn(
            "requirement[0]:derived[0]:missing:logical_derivation",
            MODULE.validate_requirement_ledger(ledger, self.schema),
        )

    def test_generic_controller_cannot_map_verifier_fail_to_human_choice(self) -> None:
        decision = {
            "classification": "VERIFIER_CONTRACT_DRIFT",
            "route": "user",
            "target_role_or_state": "NEEDS_USER_SCIENTIFIC_CHOICE",
            "planner_adjudication": {"classification": "VERIFIER_CONTRACT_DRIFT"},
            "scientific_contract_fields_requiring_change": ["contract.method"],
            "scientific_alternatives": ["A", "B"],
            "requirement_ids": ["REQ_INFERENCE_001"],
            "same_scope_repairs_exhausted": {
                "executor_repair": True,
                "verifier_repair": True,
                "runtime_repair": True,
                "transaction_rebind": True,
            },
            "caused_by_verifier_added_requirement": True,
        }
        failures = MODULE.validate_controller_routing_decision(
            decision, self._generic_requirement_ledger(), self.schema
        )
        self.assertIn("routing:route", failures)
        self.assertIn("human_gate_requires_scientific_choice_classification", failures)
        self.assertIn("human_gate_requires_planner_scientific_choice", failures)
        self.assertIn("human_gate_cannot_use_verifier_added_requirement", failures)

    def test_generic_controller_cannot_map_runtime_failure_to_human_choice(self) -> None:
        decision = {
            "classification": "RUNTIME_ENVIRONMENT_FAILURE",
            "route": "controller_runtime_repair",
            "target_role_or_state": "NEEDS_USER_SCIENTIFIC_CHOICE",
            "planner_adjudication": {"classification": "RUNTIME_ENVIRONMENT_FAILURE"},
            "scientific_contract_fields_requiring_change": ["runtime.python"],
            "scientific_alternatives": ["repair env", "change contract"],
            "requirement_ids": ["REQ_RUNTIME_001"],
            "same_scope_repairs_exhausted": {
                "executor_repair": True,
                "verifier_repair": True,
                "runtime_repair": False,
                "transaction_rebind": True,
            },
        }
        failures = MODULE.validate_controller_routing_decision(
            decision, self._generic_requirement_ledger(), self.schema
        )
        self.assertIn("human_gate_requires_scientific_choice_classification", failures)
        self.assertIn("human_gate_same_scope_repairs_not_exhausted", failures)

    def test_generic_executor_test_aware_epsilon_is_detected(self) -> None:
        result = {
            "status": "PASS",
            "test_aware_behavior_detected": True,
            "normal_public_path_exercised": True,
            "test_awareness_indicators": ["adds epsilon only when verifier flag is set"],
        }
        failures = MODULE.validate_executor_result(result)
        self.assertIn("executor_test_aware_pass_forbidden", failures)
        self.assertIn("executor_test_awareness_indicators_forbid_pass", failures)

    def test_generic_planner_adjudicates_executor_verifier_disagreement(self) -> None:
        review = {
            "schema": "AGENT_FLOW_V3_CONTRACT_INTERPRETATION_REVIEW",
            "decision": "VERIFIER_CONTRACT_DRIFT",
            "classification": "VERIFIER_CONTRACT_DRIFT",
            "requirement_ids": ["REQ_INFERENCE_001"],
            "planner_read_set": [
                "frozen_contract",
                "requirement_ledger",
                "verifier_finding",
                "executor_evidence",
                "implementation",
            ],
        }
        self.assertEqual(MODULE.validate_contract_interpretation_review(review, self.schema), [])

    def test_generic_critic_freezing_contradictory_requirements_is_rejected(self) -> None:
        freeze = {
            "critic_decision": "PLAN_FROZEN",
            "requirement_ledger_sha256": "a" * 64,
            "contradictions": ["REQ_A conflicts with REQ_B"],
            "numeric_threshold_audit": [],
        }
        self.assertIn(
            "critic_freeze_has_contradictory_requirements",
            MODULE.validate_critic_freeze(freeze, self._generic_requirement_ledger(), self.schema),
        )

    def test_generic_stale_ci_transaction_routes_to_provenance_repair(self) -> None:
        transaction = {
            "request_nonce": "nonce",
            "frozen_contract_sha": "a" * 64,
            "requirement_ledger_sha": "b" * 64,
            "integration_sha": "c" * 40,
            "implementation_fingerprint": "d" * 64,
            "verifier_source_fingerprint": "e" * 64,
            "verifier_runtime_fingerprint": "f" * 64,
            "runtime_receipt_manifest_sha": "1" * 64,
            "ci_exact_head_sha": "2" * 40,
            "review_round": 1,
            "classification_on_failure": "SCIENTIFIC_CHOICE_REQUIRED",
            "route_on_failure": "user",
        }
        failures = MODULE.validate_transaction_binding(transaction)
        self.assertIn("transaction_stale_ci_must_be_provenance_gap", failures)
        self.assertIn("transaction_stale_ci_must_route_controller", failures)

        transaction["classification_on_failure"] = "PROVENANCE_BINDING_GAP"
        transaction["route_on_failure"] = "controller"
        self.assertNotIn("transaction_stale_ci_must_be_provenance_gap", MODULE.validate_transaction_binding(transaction))

    def test_generic_missing_rollout_routes_to_operational_recovery(self) -> None:
        decision = {
            "classification": "OPERATIONAL_FAILURE",
            "route": "controller_same_scope_recovery",
            "target_role_or_state": "controller",
        }
        self.assertEqual(
            MODULE.validate_controller_routing_decision(decision, self._generic_requirement_ledger(), self.schema),
            [],
        )

    def test_generic_same_scope_implementation_bug_routes_to_executor(self) -> None:
        decision = {
            "classification": "IMPLEMENTATION_BUG",
            "route": "executor",
            "target_role_or_state": "executor",
        }
        self.assertEqual(
            MODULE.validate_controller_routing_decision(decision, self._generic_requirement_ledger(), self.schema),
            [],
        )

    def test_generic_actual_scientific_alternatives_allow_human_gate(self) -> None:
        decision = {
            "classification": "SCIENTIFIC_CHOICE_REQUIRED",
            "route": "user",
            "target_role_or_state": "NEEDS_USER_SCIENTIFIC_CHOICE",
            "planner_adjudication": {"classification": "SCIENTIFIC_CHOICE_REQUIRED"},
            "scientific_contract_fields_requiring_change": ["contract.method_family"],
            "scientific_alternatives": ["method A", "method B"],
            "requirement_ids": ["REQ_SCIENCE_001"],
            "same_scope_repairs_exhausted": {
                "executor_repair": True,
                "verifier_repair": True,
                "runtime_repair": True,
                "transaction_rebind": True,
            },
            "caused_by_verifier_added_requirement": False,
        }
        self.assertEqual(
            MODULE.validate_controller_routing_decision(decision, self._generic_requirement_ledger(), self.schema),
            [],
        )

    def test_generic_role_authority_write_boundary_violations_are_rejected(self) -> None:
        cases = [
            ("controller", "implementation_edit"),
            ("verifier", "implementation_edit"),
            ("executor", "verifier_edit"),
            ("planner", "runtime_implementation"),
            ("critic", "runtime_implementation"),
        ]
        for role, attempted_authority in cases:
            with self.subTest(role=role):
                self.assertIn(
                    f"authority_violation:{role}:{attempted_authority}",
                    MODULE.validate_role_authority_event(
                        {"role": role, "attempted_authority": attempted_authority}
                    ),
                )

    def test_generic_fail_closed_without_repair_route_is_rejected(self) -> None:
        failures = MODULE.validate_fail_closed_routing(
            {"status": "FAIL_CLOSED", "classification": "IMPLEMENTATION_BUG"},
            self.schema,
        )
        self.assertIn("fail_closed_missing_repair_route", failures)

    def test_generic_blocked_without_typed_classification_is_rejected(self) -> None:
        failures = MODULE.validate_fail_closed_routing({"status": "BLOCKED", "reason": "unclear"}, self.schema)
        self.assertIn("generic_blocked_missing_classification", failures)


if __name__ == "__main__":
    unittest.main()
