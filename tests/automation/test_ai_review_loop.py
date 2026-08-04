from __future__ import annotations

import importlib.util
import json
from pathlib import Path
import subprocess
import tempfile
import unittest

SCRIPT_PATH = Path(__file__).resolve().parents[2] / "scripts" / "automation" / "ai_review_loop.py"
SPEC = importlib.util.spec_from_file_location("ai_review_loop", SCRIPT_PATH)
assert SPEC and SPEC.loader
LOOP = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(LOOP)


class AIReviewLoopTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.repo = Path(self.tmp.name)
        subprocess.run(["git", "init", "-b", "main"], cwd=self.repo, check=True, stdout=subprocess.DEVNULL)
        subprocess.run(["git", "config", "user.email", "test@example.com"], cwd=self.repo, check=True)
        subprocess.run(["git", "config", "user.name", "Test"], cwd=self.repo, check=True)
        (self.repo / "prompts" / "tasks").mkdir(parents=True)
        (self.repo / "src").mkdir()
        (self.repo / "prompts" / "tasks" / "contract.md").write_text("frozen contract\n", encoding="utf-8")
        (self.repo / "src" / "model.py").write_text("VALUE = 1\n", encoding="utf-8")
        subprocess.run(["git", "add", "."], cwd=self.repo, check=True)
        subprocess.run(["git", "commit", "-m", "base"], cwd=self.repo, check=True, stdout=subprocess.DEVNULL)
        self.base_sha = self.git("rev-parse", "HEAD")
        (self.repo / "src" / "model.py").write_text("VALUE = 2\n", encoding="utf-8")
        subprocess.run(["git", "add", "."], cwd=self.repo, check=True)
        subprocess.run(["git", "commit", "-m", "implementation"], cwd=self.repo, check=True, stdout=subprocess.DEVNULL)
        self.impl_sha = self.git("rev-parse", "HEAD")

    def tearDown(self) -> None:
        self.tmp.cleanup()

    def git(self, *args: str) -> str:
        return subprocess.check_output(["git", *args], cwd=self.repo, text=True).strip()

    def publish(self, enabled: bool = True) -> subprocess.CompletedProcess[str]:
        cmd = [
            "python",
            str(SCRIPT_PATH),
            "publish-request",
            "--repo-root",
            str(self.repo),
            "--task-id",
            "test-task",
            "--repository",
            "owner/repo",
            "--branch",
            "ai-review/test-task",
            "--contract-path",
            "prompts/tasks/contract.md",
            "--implementation-sha",
            self.impl_sha,
            "--base-sha",
            self.base_sha,
            "--critical-path",
            "src/**/*.py",
            "--context-path",
            "prompts/tasks/contract.md",
        ]
        if enabled:
            cmd.append("--enabled")
        return subprocess.run(cmd, cwd=self.repo, text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=False)

    def test_publish_and_validate_enabled_request(self) -> None:
        result = self.publish(enabled=True)
        self.assertEqual(result.returncode, 0, result.stderr)
        root = self.repo / "automation" / "ai_review_loop" / "tasks" / "test-task"
        request = json.loads((root / "REQUEST.json").read_text(encoding="utf-8"))
        current = json.loads((root / "CURRENT.json").read_text(encoding="utf-8"))
        self.assertTrue(request["enabled"])
        self.assertEqual(request["implementation_sha"], self.impl_sha)
        self.assertEqual(current["state"], "WAITING_FOR_GPT_REVIEW")
        validate = subprocess.run(
            ["python", str(SCRIPT_PATH), "validate", "--repo-root", str(self.repo)],
            cwd=self.repo,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=False,
        )
        self.assertEqual(validate.returncode, 0, validate.stderr)

    def test_disabled_request_cannot_emit_notification(self) -> None:
        result = self.publish(enabled=False)
        self.assertEqual(result.returncode, 0, result.stderr)
        emit = subprocess.run(
            [
                "python",
                str(SCRIPT_PATH),
                "emit-notification-brief",
                "--repo-root",
                str(self.repo),
                "--task-id",
                "test-task",
            ],
            cwd=self.repo,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=False,
        )
        self.assertNotEqual(emit.returncode, 0)
        self.assertIn("disabled", emit.stderr)

    def test_notification_contains_keyword_and_machine_binding(self) -> None:
        self.assertEqual(self.publish(enabled=True).returncode, 0)
        emit = subprocess.run(
            [
                "python",
                str(SCRIPT_PATH),
                "emit-notification-brief",
                "--repo-root",
                str(self.repo),
                "--task-id",
                "test-task",
            ],
            cwd=self.repo,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=False,
        )
        self.assertEqual(emit.returncode, 0, emit.stderr)
        path = self.repo / "results" / "ai_review_loop" / "test-task" / "round_001" / "notification_brief.json"
        payload = json.loads(path.read_text(encoding="utf-8"))
        self.assertIn(LOOP.KEYWORD, payload["key_conclusion"])
        self.assertIn(self.impl_sha, payload["next_step"])

    def test_contract_mutation_invalidates_request(self) -> None:
        self.assertEqual(self.publish(enabled=True).returncode, 0)
        (self.repo / "prompts" / "tasks" / "contract.md").write_text("changed contract\n", encoding="utf-8")
        validate = subprocess.run(
            ["python", str(SCRIPT_PATH), "validate", "--repo-root", str(self.repo)],
            cwd=self.repo,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=False,
        )
        self.assertNotEqual(validate.returncode, 0)
        self.assertIn("contract_sha", validate.stderr)

    def test_pass_cannot_contain_blockers(self) -> None:
        self.assertEqual(self.publish(enabled=True).returncode, 0)
        request = json.loads(
            (self.repo / "automation" / "ai_review_loop" / "tasks" / "test-task" / "REQUEST.json").read_text(encoding="utf-8")
        )
        review = {
            "schema": LOOP.SCHEMA,
            "task_id": request["task_id"],
            "review_round": request["review_round"],
            "request_nonce": request["loop_nonce"],
            "reviewed_implementation_sha": request["implementation_sha"],
            "reviewed_contract_sha256": request["contract_sha256"],
            "decision": "PASS",
            "blocking_findings": [{"id": "F001"}],
            "nonblocking_findings": [],
            "required_tests": [],
            "review_profiles_completed": request["review_profiles"],
            "created_utc": LOOP.now(),
        }
        errors = LOOP.review_errors(review, request)
        self.assertIn("pass_has_blockers", errors)


if __name__ == "__main__":
    unittest.main()
