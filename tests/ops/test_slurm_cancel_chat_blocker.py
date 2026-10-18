from __future__ import annotations

import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest import mock

from scripts.evaluation import watch_care_srr_cascade_formal_race as cascade
from scripts.evaluation import watch_srr_v3_m7_routing as m7
from scripts.evaluation import watch_srr_v3_m8_myops_race as m8
from scripts.ops import slurm_cancel_normal_entry as normal_entry
from scripts.route_B_round04 import watch_B1_race as b1
from scripts.target_domain_gap_closure import monitor_interactive_takeover as takeover


def blocked(job_id: str, code: int = 75) -> subprocess.CompletedProcess[str]:
    return subprocess.CompletedProcess(["scancel", job_id], code, "", "interactive confirmation required")


class NormalEntryTests(unittest.TestCase):
    def test_rejects_non_exact_job_id_without_subprocess(self) -> None:
        with mock.patch.object(normal_entry.subprocess, "run") as run:
            result = normal_entry.guarded_scancel("123,456")
        self.assertEqual(result.returncode, 64)
        run.assert_not_called()

    def test_uses_only_project_guard_resolution(self) -> None:
        completed = subprocess.CompletedProcess(["scancel", "123"], 75, "", "blocked")
        with (
            mock.patch.object(normal_entry.shutil, "which", return_value=str(normal_entry.GUARD)),
            mock.patch.object(normal_entry.subprocess, "run", return_value=completed) as run,
        ):
            result = normal_entry.guarded_scancel("123")
        self.assertEqual(result.returncode, 75)
        self.assertEqual(run.call_args.args[0], ["scancel", "123"])
        self.assertEqual(run.call_args.kwargs["env"]["PATH"].split(":", 1)[0], str(normal_entry.GUARD_DIR))


class WatcherPropagationTests(unittest.TestCase):
    def test_b1_nonzero_does_not_mark_loser_cancelled(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            state = root / "state.json"
            ledger = root / "ledger.csv"
            argv = ["watch", "--job", "a100-gpu:11", "--job", "htzhulab:22"]

            def job_state(job_id: str) -> dict[str, str]:
                return {"job_id": job_id, "state": "RUNNING" if job_id == "11" else "PENDING"}

            with (
                mock.patch.object(sys, "argv", argv),
                mock.patch.object(b1, "STATE", state),
                mock.patch.object(b1, "LEDGER", ledger),
                mock.patch.object(b1, "run", return_value=subprocess.CompletedProcess([], 0, "head\n", "")),
                mock.patch.object(b1, "squeue_state", side_effect=job_state),
                mock.patch.object(b1, "guarded_scancel", return_value=blocked("22")),
            ):
                code = b1.main()

            self.assertEqual(code, 75)
            payload = json.loads(state.read_text(encoding="utf-8"))
            self.assertEqual(payload["status"], "CANCEL_BLOCKED")
            self.assertEqual(payload["cancelled_partitions"], [])

    def test_m7_propagates_nonzero(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            log = Path(temp) / "m7.log"
            argv = [
                "watch",
                "--a100-job",
                "11",
                "--htzhulab-job",
                "22",
                "--log-file",
                str(log),
                "--max-iterations",
                "1",
            ]
            rows = [("11", "a100-gpu", "RUNNING", "None"), ("22", "htzhulab", "PENDING", "Priority")]
            with (
                mock.patch.object(sys, "argv", argv),
                mock.patch.object(m7, "job_lines", return_value=rows),
                mock.patch.object(m7, "guarded_scancel", return_value=blocked("22")),
            ):
                self.assertEqual(m7.main(), 75)

    def test_m8_propagates_nonzero(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            log = Path(temp) / "m8.log"
            argv = [
                "watch",
                "--htzhulab-job-id",
                "22",
                "--a100-job-id",
                "11",
                "--log-path",
                str(log),
                "--max-checks",
                "1",
            ]

            def states(job_id: str) -> list[tuple[str, str, str, str]]:
                state = "PENDING" if job_id == "22" else "RUNNING"
                return [(job_id, "htzhulab" if job_id == "22" else "a100-gpu", state, "reason")]

            with (
                mock.patch.object(sys, "argv", argv),
                mock.patch.object(m8, "states", side_effect=states),
                mock.patch.object(m8, "guarded_scancel", return_value=blocked("22")),
            ):
                self.assertEqual(m8.main(), 75)

    def test_takeover_nonzero_skips_accounting_wait_and_launch(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            argv = ["watch", "--interactive-job-id", "11", "--m1-queue-job-id", "22", "--max-polls", "1"]
            with (
                mock.patch.object(sys, "argv", argv),
                mock.patch.object(takeover, "RUNTIME_ROOT", root / "runtime"),
                mock.patch.object(takeover, "RESULT_ROOT", root / "results"),
                mock.patch.object(takeover, "squeue_state", side_effect=["RUNNING", "PENDING"]),
                mock.patch.object(takeover, "pid_running", return_value=False),
                mock.patch.object(takeover, "guarded_scancel", return_value=blocked("22")),
                mock.patch.object(takeover, "sacct_state") as accounting,
                mock.patch.object(takeover, "launch_m1") as launch,
            ):
                self.assertEqual(takeover.main(), 75)
            accounting.assert_not_called()
            launch.assert_not_called()
            payload = json.loads((root / "results/interactive_takeover_monitor_state.json").read_text(encoding="utf-8"))
            self.assertEqual(payload["status"], "CANCEL_BLOCKED")

    def test_cascade_stops_current_round_on_nonzero(self) -> None:
        pairs = [
            {"logical_run_id": "first", "a100_job": "11", "htzhulab_job": "22"},
            {"logical_run_id": "second", "a100_job": "33", "htzhulab_job": "44"},
        ]
        snapshot = {
            "11": {"state": "RUNNING"},
            "22": {"state": "PENDING"},
            "33": {"state": "RUNNING"},
            "44": {"state": "PENDING"},
        }
        with (
            mock.patch.object(cascade, "merged_snapshot", return_value=snapshot),
            mock.patch.object(cascade, "guarded_scancel", return_value=blocked("22")) as cancel,
        ):
            payload = cascade.evaluate_once(pairs, dry_run=False)
        self.assertEqual(payload["decision"], "CANCEL_BLOCKED")
        self.assertEqual(payload["exit_code"], 75)
        self.assertEqual(len(payload["actions"]), 1)
        cancel.assert_called_once_with("22", dry_run=False)


if __name__ == "__main__":
    unittest.main()
