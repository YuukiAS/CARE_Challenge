from __future__ import annotations

import unittest

import torch

from src.care_myocardium.losses.srr_losses import retrieval_regularization
from src.care_myocardium.models.srr_v2_unet import ScaleRetrieval, SRRV2MyoPSUNet


class TestSRRDictionaryBank(unittest.TestCase):
    def test_scale_retrieval_contract_counts_and_masks(self) -> None:
        torch.manual_seed(11)
        block = ScaleRetrieval(8)
        self.assertEqual(block.n_experts, 16)
        self.assertEqual(
            block.slot_counts,
            {
                "shared": 4,
                "lge_private": 2,
                "t2_private": 2,
                "c0_private": 2,
                "interaction_lge_t2": 2,
                "interaction_lge_c0": 2,
                "interaction_t2_c0": 2,
            },
        )
        features = [torch.randn(2, 8, 4, 5, 6) for _ in range(3)]
        availability = torch.tensor([[1.0, 1.0, 1.0], [1.0, 0.0, 1.0]])
        anchor = torch.rand(2, 6, 4, 5, 6)
        routed, gates = block(features, availability, anchor)
        self.assertEqual(set(routed), {"anatomy", "scar", "edema"})
        for gate in gates.values():
            self.assertEqual(tuple(gate.shape), (2, 16))
            self.assertTrue(torch.allclose(gate.sum(dim=1), torch.ones(2), atol=1e-6))

        metadata = block.slot_metadata
        no_t2_row = 1
        for idx, spec in enumerate(metadata):
            group = str(spec["group"])
            if group == "t2_private" or "t2" in group and group.startswith("interaction_"):
                for gate in gates.values():
                    self.assertEqual(float(gate[no_t2_row, idx].detach()), 0.0)

    def test_model_reports_dictionary_diagnostics(self) -> None:
        torch.manual_seed(12)
        model = SRRV2MyoPSUNet(base_channels=4)
        model.eval()
        x = torch.randn(2, 3, 4, 6, 8)
        availability = torch.tensor([[1.0, 1.0, 1.0], [1.0, 0.0, 1.0]])
        anchor = torch.rand(2, 6, 4, 6, 8)
        with torch.no_grad():
            outputs = model(x, availability, anchor_features=anchor)
        self.assertEqual(tuple(outputs["logits"].shape), (2, 6, 4, 6, 8))
        self.assertEqual(outputs["dictionary_slot_counts"]["scale0"]["shared"], 4)
        self.assertIn("scar_scale0", outputs["dictionary_diagnostics"])
        diag = outputs["dictionary_diagnostics"]["scar_scale0"]
        self.assertIn("entropy_mean", diag)
        self.assertIn("inactive_slot_count", diag)
        self.assertIn("collapse_warning", diag)
        reg, metrics = retrieval_regularization(outputs["gates"])
        self.assertIsNotNone(reg)
        self.assertIn("scar_scale0_entropy", metrics)


if __name__ == "__main__":
    unittest.main()
