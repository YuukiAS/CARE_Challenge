import torch

from tests.care_ase.test_canonical_full_volume_single_tile_path import TinyModel
from src.care_myocardium.inference.care_ase_r2_full_volume import predict_care_ase_r2_full_volume_logits


def test_canonical_full_volume_tiled_whole_parity_for_constant_model():
    image = torch.zeros((1, 3, 4, 8, 8))
    availability = torch.tensor([[1.0, 1.0, 1.0]])
    single = predict_care_ase_r2_full_volume_logits(TinyModel(), image, availability, patch_size=(8, 16, 16))
    tiled = predict_care_ase_r2_full_volume_logits(TinyModel(), image, availability, patch_size=(4, 4, 4), overlap=0.5)
    assert torch.allclose(single, tiled)
