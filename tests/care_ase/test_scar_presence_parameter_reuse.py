import torch

from src.care_myocardium.models.care_ase import build_care_ase_for_fold


def test_scar_extent_presence_reuses_quarter_occupancy_tensor():
    model = build_care_ase_for_fold(2)
    sample = torch.zeros(1, 3, 8, 64, 64)
    availability = torch.ones(1, 3)

    outputs = model(sample, availability, global_step=0)
    components = outputs["components"]

    assert components["scar_extent_presence"] is components["scar_quarter_occupancy"]
    assert components["scar_extent_presence"].data_ptr() == components["scar_quarter_occupancy"].data_ptr()
