from __future__ import annotations

import unittest

import torch

from src.care_myocardium.models.srr_myops import SRRMyoPSLite


class TestSRRMissingness(unittest.TestCase):
    def test_absent_modality_extreme_values_do_not_change_output(self) -> None:
        torch.manual_seed(2)
        model = SRRMyoPSLite(base_channels=8)
        model.eval()
        availability = torch.tensor([[1.0, 0.0, 1.0]])  # T2 absent
        x_base = torch.randn(1, 3, 6, 8, 8)
        x_extreme = x_base.clone()
        x_base[:, 1] = 0.0
        x_extreme[:, 1] = 1.0e6
        with torch.no_grad():
            y_base = model(x_base, availability)["logits"]
            y_extreme = model(x_extreme, availability)["logits"]
        self.assertLess(float((y_base - y_extreme).abs().max()), 1e-5)

    def test_unavailable_private_experts_have_zero_gate_weight(self) -> None:
        torch.manual_seed(3)
        model = SRRMyoPSLite(base_channels=8)
        availability = torch.tensor([[1.0, 0.0, 0.0]])  # LGE-only
        outputs = model(torch.randn(1, 3, 6, 8, 8), availability)
        for name, gate in outputs["gates"].items():
            metadata = outputs["dictionary_slot_metadata"][name]
            for idx, spec in enumerate(metadata):
                group = spec["group"]
                if group in {"t2_private", "c0_private"} or str(group).startswith("interaction_"):
                    self.assertEqual(float(gate[0, idx].detach()), 0.0)


if __name__ == "__main__":
    unittest.main()
