from src.care_myocardium.models.care_ase import build_care_ase_for_fold
from src.care_myocardium.training.care_ase_trainer import parameter_group_coverage


def test_parameter_group_independent_oracle_covers_anatomy_top_and_aliases():
    model = build_care_ase_for_fold(2)
    coverage = parameter_group_coverage(model)

    assert coverage["status"] == "PASS"
    assert coverage["duplicate_count"] == 0
    assert coverage["missing_count"] == 0
    assert coverage["wrong_group_count"] == 0
    assert coverage["unexpected_alias_count"] == 0
    rows = coverage["parameters"]
    anatomy_top = [
        row
        for row in rows
        if row["canonical_name"].startswith(
            ("anatomy_top_transpconvs.", "anatomy_top_stages.", "anatomy_top_seg_layers.")
        )
    ]
    assert anatomy_top
    assert {row["group"] for row in anatomy_top} == {"anatomy_decoder"}
    assert {row["expected_group"] for row in anatomy_top} == {"anatomy_decoder"}
