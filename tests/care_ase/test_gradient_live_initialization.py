import math

import torch

from src.care_myocardium.models.care_ase import build_care_ase_for_fold


def _max_abs(parameters):
    return max(float(param.detach().abs().max()) for param in parameters)


def test_v5_modality_and_dilation_initialization_are_live():
    model = build_care_ase_for_fold(2)

    adapter_final = model.edema_lge_half_adapter.net[-1]
    dilation_final = model.edema_dilation_context.dilated["1"][-1]

    assert _max_abs([adapter_final.weight]) > 0.0
    assert _max_abs([dilation_final.weight]) > 0.0
    assert math.isclose(float(model.scar_c0_gate().detach()), 0.2, rel_tol=0.0, abs_tol=1.0e-6)
    assert math.isclose(float(model.edema_c0_gate().detach()), 0.2, rel_tol=0.0, abs_tol=1.0e-6)
    assert math.isclose(float(model.edema_lge_gate().detach()), 0.05, rel_tol=0.0, abs_tol=1.0e-6)

    projection_weights = [
        *[proj.weight for proj in model.scar_branch.half_projections.projections.values()],
        *[proj.weight for proj in model.scar_branch.full_projections.projections.values()],
        *[proj.weight for proj in model.edema_branch.half_projections.projections.values()],
        *[proj.weight for proj in model.edema_branch.full_projections.projections.values()],
    ]
    assert _max_abs(projection_weights) == 0.0
    registry = model.named_evidence_projection_registry()
    assert registry["shared_multi_source_projection_count"] == 0
    assert registry["missing_named_projection_count"] == 0
    assert registry["duplicate_named_projection_count"] == 0
