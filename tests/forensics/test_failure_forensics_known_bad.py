from scripts.forensics.care_failure_forensics.reference_metrics import run_known_bad


def test_reference_metric_known_bad_fixtures_pass():
    report = run_known_bad()
    failed = [name for name, item in report.items() if not item.get("passed")]
    assert not failed
