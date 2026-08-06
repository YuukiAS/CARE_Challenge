from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
VALIDATOR = ROOT / "validators" / "care_ase_faithful" / "validate_contract_evidence.py"


class VerifierPackageTests(unittest.TestCase):
    def test_reference_evidence_passes(self) -> None:
        reference = subprocess.run(
            [sys.executable, str(VALIDATOR), "--emit-reference"],
            cwd=ROOT,
            text=True,
            capture_output=True,
            check=True,
        )
        with tempfile.TemporaryDirectory() as tmp:
            evidence_path = Path(tmp) / "reference_evidence.json"
            evidence_path.write_text(reference.stdout, encoding="utf-8")
            result = subprocess.run(
                [sys.executable, str(VALIDATOR), "--evidence", str(evidence_path)],
                cwd=ROOT,
                text=True,
                capture_output=True,
                check=False,
            )

        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        payload = json.loads(result.stdout)
        self.assertIs(payload["passed"], True)
        self.assertEqual(payload["failure_count"], 0)

    def test_all_protected_known_bad_cases_fail_closed(self) -> None:
        listed = subprocess.run(
            [sys.executable, str(VALIDATOR), "--list-known-bad"],
            cwd=ROOT,
            text=True,
            capture_output=True,
            check=True,
        )
        known_bad_cases = json.loads(listed.stdout)
        self.assertEqual(len(known_bad_cases), 24)

        for case in known_bad_cases:
            result = subprocess.run(
                [sys.executable, str(VALIDATOR), "--known-bad-id", case["id"]],
                cwd=ROOT,
                text=True,
                capture_output=True,
                check=False,
            )
            self.assertNotEqual(result.returncode, 0, case["id"])
            payload = json.loads(result.stdout)
            self.assertIs(payload["passed"], False)
            self.assertGreater(payload["failure_count"], 0)

    def test_generated_protected_manifest_records_all_nonzero_invocations(self) -> None:
        manifest_path = (
            ROOT
            / "results"
            / "agent_flow_v3"
            / "care-ase-faithful"
            / "verification"
            / "protected_known_bad_manifest.json"
        )
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        self.assertEqual(manifest["count"], 24)
        self.assertIs(manifest["all_returned_nonzero"], True)
        self.assertEqual(
            sorted(item["contract_category"] for item in manifest["known_bad_invocations"]),
            list(range(1, 25)),
        )
        for item in manifest["known_bad_invocations"]:
            self.assertNotEqual(item["exit_code"], 0, item["id"])
            self.assertIs(item["passed_fail_closed"], True)


if __name__ == "__main__":
    unittest.main()
