from pathlib import Path

from scripts.forensics.myowall_geometry_diagnostic.validate_geometry_diagnostic import ALLOWED_DECISIONS, MODES, REQUIRED


def test_required_outputs_include_atlas_and_casewise():
    assert "geometry_diagnostic_atlas.pdf" in REQUIRED
    assert "geometry_casewise_all_modes.csv" in REQUIRED
    assert "case_attribution.csv" in REQUIRED


def test_modes_cover_contract():
    assert MODES == {"G0_current_predicted", "G1_GT_anatomy", "G2_supported_denominator", "G3_repaired_predicted"}


def test_allowed_decisions_are_contract_limited():
    assert "GEOMETRY_EXTRACTION_REPAIRABLE" in ALLOWED_DECISIONS
    assert "STOP_GEOMETRY_NOT_RELIABLE" not in ALLOWED_DECISIONS
