import torch

from src.care_myocardium.inference.care_ase_r2_full_volume import predict_care_ase_r2_full_volume_logits


class TinyModel(torch.nn.Module):
    scar_area_reference = torch.tensor(0.2)
    edema_area_reference = torch.tensor(0.2)

    @staticmethod
    def extent_wall_ramp(_step):
        return 0.0

    @staticmethod
    def _sigmoid_logit_center(probability, reference):
        return torch.logit(probability.clamp(0.01, 0.99)) - torch.logit(torch.as_tensor(reference, device=probability.device).clamp(0.01, 0.99))

    def forward(self, image, availability, *, global_step=14000, disable_extent_wall=False, **_kwargs):
        assert disable_extent_wall is True
        spatial = image.shape[-3:]
        logits = torch.zeros((image.shape[0], 6, *spatial), device=image.device)
        components = {key: torch.zeros((image.shape[0], 1, *spatial), device=image.device) for key in ("scar_extent_presence", "scar_extent_area", "edema_extent_presence", "edema_extent_area")}
        return {"final_logits": logits, "p_wall_union": torch.ones((image.shape[0], 1, *spatial), device=image.device) * 0.5, "components": components}


def test_single_tile_uses_canonical_disable_local_extent_path():
    image = torch.zeros((1, 3, 4, 8, 8))
    availability = torch.tensor([[1.0, 1.0, 1.0]])
    logits = predict_care_ase_r2_full_volume_logits(TinyModel(), image, availability, patch_size=(8, 16, 16))
    assert logits.shape == (1, 6, 4, 8, 8)
