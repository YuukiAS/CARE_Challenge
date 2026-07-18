from __future__ import annotations

import pytest

from src.care_myocardium.route_B_round03.known_bad import FAILURE_KEYS, evaluate_known_bad


@pytest.mark.parametrize("name,key", sorted(FAILURE_KEYS.items()))
def test_known_bad_fixtures_fail_closed(name: str, key: str) -> None:
    with pytest.raises(Exception, match=key):
        evaluate_known_bad(name)


def test_valid_control_passes() -> None:
    assert evaluate_known_bad("valid_control") == "PASS"
