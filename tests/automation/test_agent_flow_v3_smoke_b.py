from __future__ import annotations

import importlib
from collections.abc import Mapping
import unittest


EXPECTED_NONCE = "smoke-b-20260806T062800Z"


class SmokeBToyGateTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        module = importlib.import_module("automation.agent_flow_v3.smoke_b.toy_gate")
        cls.evaluate_payload = module.evaluate_payload

    def assert_gate_result(self, result, *, accepted: bool, reason_contains: str | None = None) -> None:
        if isinstance(result, Mapping):
            result_accepted = result.get("accepted")
            reason = result.get("reason")
        else:
            result_accepted = getattr(result, "accepted", None)
            reason = getattr(result, "reason", None)

        self.assertIs(result_accepted, accepted)
        self.assertIsInstance(reason, str)
        self.assertNotEqual(reason.strip(), "")
        if reason_contains is not None:
            self.assertIn(reason_contains, reason.lower())

    def test_accepts_exact_nonce_safe_mode_and_positive_integer_value(self) -> None:
        result = self.evaluate_payload(
            {"nonce": EXPECTED_NONCE, "mode": "safe", "value": 1},
            EXPECTED_NONCE,
        )

        self.assert_gate_result(result, accepted=True)

    def test_rejects_missing_nonce(self) -> None:
        result = self.evaluate_payload(
            {"mode": "safe", "value": 1},
            EXPECTED_NONCE,
        )

        self.assert_gate_result(result, accepted=False, reason_contains="nonce")

    def test_rejects_wrong_nonce(self) -> None:
        result = self.evaluate_payload(
            {"nonce": "wrong-nonce", "mode": "safe", "value": 1},
            EXPECTED_NONCE,
        )

        self.assert_gate_result(result, accepted=False, reason_contains="nonce")

    def test_rejects_unsafe_mode(self) -> None:
        result = self.evaluate_payload(
            {"nonce": EXPECTED_NONCE, "mode": "unsafe", "value": 1},
            EXPECTED_NONCE,
        )

        self.assert_gate_result(result, accepted=False, reason_contains="mode")

    def test_rejects_non_integer_value(self) -> None:
        for value in ("1", 1.0, True, None):
            with self.subTest(value=value):
                result = self.evaluate_payload(
                    {"nonce": EXPECTED_NONCE, "mode": "safe", "value": value},
                    EXPECTED_NONCE,
                )

                self.assert_gate_result(result, accepted=False, reason_contains="value")

    def test_rejects_value_less_than_one(self) -> None:
        for value in (0, -1):
            with self.subTest(value=value):
                result = self.evaluate_payload(
                    {"nonce": EXPECTED_NONCE, "mode": "safe", "value": value},
                    EXPECTED_NONCE,
                )

                self.assert_gate_result(result, accepted=False, reason_contains="value")

    def test_rejects_non_mapping_payload(self) -> None:
        for payload in (None, [], "not-a-mapping", 1):
            with self.subTest(payload=payload):
                result = self.evaluate_payload(payload, EXPECTED_NONCE)

                self.assert_gate_result(result, accepted=False, reason_contains="payload")
