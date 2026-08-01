from scripts.evaluation.complementarity.build_nnunet_mosaic_complementarity import (
    bucket_oof,
)


def test_bucket_priority_both_fail_before_delta():
    assert bucket_oof(0.10, 0.30) == "BOTH_FAIL"


def test_bucket_priority_both_good_before_delta():
    assert bucket_oof(0.95, 0.70) == "BOTH_GOOD"


def test_mosaic_rescues_threshold():
    assert bucket_oof(0.50, 0.55) == "MOSAIC_RESCUES"


def test_nnunet_protects_threshold():
    assert bucket_oof(0.55, 0.50) == "NNUNET_PROTECTS"


def test_near_tie_after_directional_thresholds():
    assert bucket_oof(0.50, 0.549) == "NEAR_TIE"


def test_no_selector_language_in_validation_bucket_names():
    validation_buckets = {
        "LOW_DISAGREEMENT",
        "MOSAIC_ADDS_EDEMA",
        "MOSAIC_ADDS_SCAR",
        "NNUNET_ONLY_EDEMA_DOMINANT",
        "NNUNET_ONLY_SCAR_DOMINANT",
        "MIXED_NO_GT_DISAGREEMENT",
    }
    forbidden = ("help", "harm", "rescue", "better", "candidate")
    assert not any(
        word in bucket.lower()
        for bucket in validation_buckets
        for word in forbidden
    )
