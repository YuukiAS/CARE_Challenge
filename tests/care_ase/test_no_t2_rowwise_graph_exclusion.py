import inspect

from src.care_myocardium.models.care_ase import CAREASE


def test_step0_parity_reports_edema_owned_call_counters():
    source = inspect.getsource(CAREASE.step0_parity_report)

    for token in (
        "edema_owned_forward_call_counts",
        "no_t2_edema_owned_row_call_count",
        "mixed_batch_rowwise_edema_execution",
        "no_t2_rows_excluded_by_indexing",
    ):
        assert token in source
