from __future__ import annotations

import unittest

import torch

from src.care_myocardium.losses.srr_losses import retrieval_regularization, semantic_retrieval_regularization
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


    def test_semantic_regularizer_prefers_task_specific_slot_families(self) -> None:
        torch.manual_seed(13)
        block = ScaleRetrieval(8)
        metadata = {"scar_scale0": block.slot_metadata, "edema_scale0": block.slot_metadata}
        valid = block.block.bank.availability_mask(torch.ones(2, 3))
        gates_bad = {
            "scar_scale0": torch.full((2, block.n_experts), 1.0 / block.n_experts),
            "edema_scale0": torch.full((2, block.n_experts), 1.0 / block.n_experts),
        }
        gates_good = {name: gate.clone() * 0.01 for name, gate in gates_bad.items()}
        for idx, spec in enumerate(block.slot_metadata):
            group = str(spec["group"])
            if group == "lge_private" or group.startswith("interaction_lge"):
                gates_good["scar_scale0"][:, idx] = 1.0
            if group == "t2_private" or group in {"interaction_lge_t2", "interaction_t2_c0"}:
                gates_good["edema_scale0"][:, idx] = 1.0
        for name in gates_good:
            gates_good[name] = gates_good[name] / gates_good[name].sum(dim=1, keepdim=True)

        bad_loss, bad_metrics = semantic_retrieval_regularization(gates_bad, metadata, {"scar_scale0": valid, "edema_scale0": valid})
        good_loss, good_metrics = semantic_retrieval_regularization(gates_good, metadata, {"scar_scale0": valid, "edema_scale0": valid})
        self.assertIsNotNone(bad_loss)
        self.assertIsNotNone(good_loss)
        self.assertLess(float(good_loss.detach()), float(bad_loss.detach()))
        self.assertIn("scar_scale0_semantic_family_mass", good_metrics)
        self.assertIn("edema_scale0_semantic_interaction_mass", good_metrics)

    def test_propref_outputs_feed_semantic_retrieval_regularizer(self) -> None:
        from src.care_myocardium.models.srr_propref import SRRProposeRefineMyoPS

        torch.manual_seed(14)
        model = SRRProposeRefineMyoPS(base_channels=4, encoder_profile="tiny_3scale")
        x = torch.randn(2, 3, 4, 6, 8)
        availability = torch.tensor([[1.0, 1.0, 1.0], [1.0, 0.0, 1.0]])
        anchor = torch.rand(2, 6, 4, 6, 8)
        with torch.no_grad():
            outputs = model(x, availability, anchor_features=anchor)
        loss, metrics = semantic_retrieval_regularization(
            outputs["gates"],
            outputs["dictionary_slot_metadata"],
            outputs["gate_valid_masks"],
        )
        self.assertIsNotNone(loss)
        self.assertTrue(torch.isfinite(loss).item())
        self.assertIn("semantic_retrieval_loss", metrics)
        no_t2_row = 1
        metadata = outputs["dictionary_slot_metadata"]["edema_scale0"]
        valid = outputs["gate_valid_masks"]["edema_scale0"]
        for idx, spec in enumerate(metadata):
            group = str(spec["group"])
            if group == "t2_private" or ("t2" in group and group.startswith("interaction_")):
                self.assertEqual(float(valid[no_t2_row, idx].detach()), 0.0)


if __name__ == "__main__":
    unittest.main()
