from __future__ import annotations

from collections.abc import Mapping
from typing import Any


def _reject(reason: str) -> dict[str, bool | str]:
    return {"accepted": False, "reason": reason}


def _evaluate_payload(payload: Any, expected_nonce: str) -> dict[str, bool | str]:
    if not isinstance(payload, Mapping):
        return _reject("payload must be a mapping")

    if payload.get("nonce") != expected_nonce:
        return _reject("nonce must exactly match expected nonce")

    if payload.get("mode") != "safe":
        return _reject("mode must be safe")

    value = payload.get("value")
    if type(value) is not int or value < 1:
        return _reject("value must be an integer greater than or equal to 1")

    return {"accepted": True, "reason": "payload accepted"}


def evaluate_payload(
    payload: Any,
    expected_nonce: str | None = None,
    bound_expected_nonce: str | None = None,
) -> dict[str, bool | str]:
    """Evaluate the Smoke B toy gate payload using fail-closed checks."""
    if bound_expected_nonce is not None:
        payload, expected_nonce = expected_nonce, bound_expected_nonce

    if expected_nonce is None:
        return _reject("nonce must exactly match expected nonce")

    return _evaluate_payload(payload, expected_nonce)
