from __future__ import annotations

import unittest

import torch

from src.care_myocardium.models.srr_myops import SRRMyoPSLite


class TestSRRShapes(unittest.TestCase):
    def test_real_modality_combinations_forward(self) -> None:
        torch.manual_seed(1)
        model = SRRMyoPSLite(base_channels=8)
        x = torch.randn(3, 3, 8, 12, 10)
        availability = torch.tensor(
            [
                [1.0, 1.0, 1.0],  # C0+LGE+T2 in Dataset501 order LGE,T2,C0
                [1.0, 0.0, 1.0],  # C0+LGE
                [1.0, 0.0, 0.0],  # LGE-only
            ]
        )
        outputs = model(x, availability)
        self.assertEqual(tuple(outputs["logits"].shape), (3, 6, 8, 12, 10))
        self.assertEqual(tuple(outputs["scar_logits"].shape), (3, 1, 8, 12, 10))
        self.assertEqual(tuple(outputs["edema_logits"].shape), (3, 1, 8, 12, 10))
        for gate in outputs["gates"].values():
            self.assertTrue(torch.isfinite(gate).all().item())
            self.assertTrue(torch.allclose(gate.sum(dim=1), torch.ones(3), atol=1e-6))

    def test_proposal_head_outputs_candidate_maps(self) -> None:
        torch.manual_seed(7)
        model = SRRMyoPSLite(base_channels=8, dictionary_mode="cross_modal_interaction_dictionary", proposal_mode="proposal_anatomy_distance")
        x = torch.randn(2, 3, 6, 10, 12)
        availability = torch.tensor([[1.0, 1.0, 1.0], [1.0, 0.0, 1.0]])
        outputs = model(x, availability)
        for key in (
            "scar_proposal_logits",
            "edema_proposal_logits",
            "scar_pos_similarity",
            "scar_neg_similarity",
            "edema_pos_similarity",
            "edema_neg_similarity",
            "scar_uncertainty",
            "edema_uncertainty",
            "local_anatomy_confidence",
        ):
            self.assertEqual(tuple(outputs[key].shape), (2, 1, 6, 10, 12))
            self.assertTrue(torch.isfinite(outputs[key]).all().item())
        self.assertEqual(outputs["proposal_mode"], "proposal_anatomy_distance")


if __name__ == "__main__":
    unittest.main()
