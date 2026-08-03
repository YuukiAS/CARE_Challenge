import inspect

from src.care_myocardium.models.care_ase import CAREASE


def test_step0_parity_excludes_class4_from_no_t2_argmax():
    source = inspect.getsource(CAREASE.step0_parity_report)

    assert "no_t2_decode_class_set" in source
    assert "[0, 1, 2, 3, 5]" in source
    assert "no_t2_stock_class4_zeroed_into_six_class_argmax" in source
    assert "stock_logits[:, 4:5] * availability" not in source
