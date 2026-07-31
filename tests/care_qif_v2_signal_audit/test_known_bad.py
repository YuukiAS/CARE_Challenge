from __future__ import annotations

import pytest

from scripts.validation.validate_care_qif_v2_signal_audit import KNOWN_BAD_CASES, build_known_bad_report, validate_known_bad_fixture


@pytest.mark.parametrize("name", KNOWN_BAD_CASES)
def test_known_bad_fixture_is_rejected(name: str) -> None:
    assert validate_known_bad_fixture(name, {"known_bad": name, "accepted": False})
    assert not validate_known_bad_fixture(name, {"known_bad": name, "accepted": True})


def test_known_bad_report_covers_all_30_items() -> None:
    report = build_known_bad_report()
    assert report["status"] == "PASS"
    assert report["case_count"] == 30
    assert len(report["tests"]) == 30
