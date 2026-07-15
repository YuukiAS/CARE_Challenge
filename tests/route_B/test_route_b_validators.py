from pathlib import Path
import sys


REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from scripts.validation.route_B.validate_route_b_implementation import evaluate_fixture_payload


def test_known_bad_fixtures_fail_closed() -> None:
    fixture_root = Path("tests/route_B/known_bad")
    fixtures = sorted(fixture_root.glob("*.json"))
    assert fixtures, "known-bad fixtures are required"
    for path in fixtures:
        import json

        report = evaluate_fixture_payload(json.loads(path.read_text(encoding="utf-8")))
        assert report["status"] == "FAIL", path
