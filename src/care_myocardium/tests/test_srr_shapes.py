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


if __name__ == "__main__":
    unittest.main()
