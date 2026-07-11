from __future__ import annotations

import unittest

import torch

from src.care_myocardium.losses.srr_losses import (
    pattern_sip_integrativeness_loss,
    semantic_retrieval_regularization,
    srr_m6_expanded_total_loss,
)
from src.care_myocardium.models.srr_blocks import dictionary_slot_config, invalid_slot_diagnostics
from src.care_myocardium.models.srr_dictionary_memory import M10CrossFittedPrototypeMemory
from src.care_myocardium.models.srr_propref import SRRProposeRefineMyoPS
from src.care_myocardium.models.srr_spatial_dictionary import M10SlotBank, M10TwoPassSpatialDictionary


class TestSRRV3M10Fidelity(unittest.TestCase):
    def test_m10_dictionary_config_is_exact_16_slots(self) -> None:
        cfg = dictionary_slot_config("srr_v3_m10_16slot")
        self.assertEqual(cfg["shared_slots"], 4)
        self.assertEqual(cfg["private_slots"], {"LGE": 2, "T2": 2, "C0": 2})
        self.assertEqual(cfg["interaction_slots"], {"lge_t2": 2, "lge_c0": 2, "t2_c0": 2})

        bank = M10SlotBank(4)
        counts: dict[str, int] = {}
        for spec in bank.slot_metadata:
            counts[str(spec["group"])] = counts.get(str(spec["group"]), 0) + 1
        self.assertEqual(sum(counts.values()), 16)
        self.assertEqual(
            counts,
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

    def test_invalid_t2_slots_have_zero_values_gates_and_gradients(self) -> None:
        torch.manual_seed(20260711)
        features = [torch.randn(1, 4, 3, 4, 5, requires_grad=True) for _ in range(3)]
        availability = torch.tensor([[1.0, 0.0, 1.0]])
        dictionary = M10TwoPassSpatialDictionary(4, enable_pattern_sip=True)
        out = dictionary(features, availability)
        valid = out["valid_mask"]
        gates = out["gates"]
        experts = out["expert_outputs"]
        self.assertIsInstance(gates, dict)
        self.assertEqual(tuple(experts.shape[:3]), (1, 16, 4))

        invalid = (valid == 0).view(1, 16, 1, 1, 1, 1)
        self.assertEqual(float((experts.detach() * invalid).abs().max()), 0.0)
        for gate in gates.values():  # type: ignore[union-attr]
            self.assertEqual(invalid_slot_diagnostics(gate, valid)["max_invalid_weight"], 0.0)

        loss = out["scar_retrieved"].square().mean()
        self.assertIsInstance(loss, torch.Tensor)
        loss.backward()
        invalid_slot_indices = [
            int(spec["index"])
            for spec in dictionary.slot_metadata
            if str(spec["group"]) in {"t2_private", "interaction_lge_t2", "interaction_t2_c0"}
        ]
        for idx in invalid_slot_indices:
            grad_sum = 0.0
            for param in dictionary.bank.experts[idx].parameters():
                if param.grad is not None:
                    grad_sum += float(param.grad.detach().abs().sum())
            self.assertEqual(grad_sum, 0.0)

    def test_pattern_sip_is_not_semantic_retrieval_alias(self) -> None:
        torch.manual_seed(20260712)
        dictionary = M10TwoPassSpatialDictionary(4, enable_pattern_sip=True)
        features = [torch.randn(2, 4, 3, 4, 5) for _ in range(3)]
        availability = torch.tensor([[1.0, 1.0, 1.0], [1.0, 0.0, 1.0]])
        out = dictionary(features, availability)
        gates = out["gates"]
        metadata = {name: out["slot_metadata"] for name in gates}  # type: ignore[union-attr]
        valid = {name: out["valid_mask"] for name in gates}  # type: ignore[union-attr]
        semantic, semantic_metrics = semantic_retrieval_regularization(gates, metadata, valid)  # type: ignore[arg-type]
        psip, psip_metrics = pattern_sip_integrativeness_loss(gates, metadata, valid)  # type: ignore[arg-type]
        self.assertIsNotNone(semantic)
        self.assertIsNotNone(psip)
        self.assertIn("pattern_sip_integrativeness_loss", psip_metrics)
        self.assertIn("semantic_retrieval_loss", semantic_metrics)
        self.assertNotEqual(float(semantic.detach()), float(psip.detach()))  # type: ignore[union-attr]

    def test_cross_fitted_memory_rejects_no_t2_edema_updates(self) -> None:
        torch.manual_seed(20260713)
        memory = M10CrossFittedPrototypeMemory(4)
        rejected = memory.update(
            "edema",
            "negative",
            "normal_myocardium",
            torch.randn(5, 4),
            case_id="NoT2Case",
            t2_present=False,
        )
        accepted = memory.update(
            "scar",
            "positive",
            "lesion_core",
            torch.randn(6, 4),
            case_id="ScarCase",
            t2_present=True,
        )
        self.assertEqual(rejected.accepted_count, 0)
        self.assertEqual(rejected.reason, "REJECT_NO_T2_EDEMA_MEMORY")
        self.assertGreater(accepted.accepted_count, 0)
        self.assertEqual(int(memory.negative_counts[1].sum()), 0)
        query = memory.query(torch.randn(1, 4, 2, 3, 4), pathology="scar", case_id="ScarCase")
        self.assertEqual(tuple(query["positive_similarity"].shape), (1, 1, 2, 3, 4))
        self.assertNotIn(int(query["query_shard"]), [int(v) for v in query["source_shards"].detach().cpu().tolist()])

    def test_m10_propref_variant_wires_spatial_dictionary_and_final_probabilities(self) -> None:
        torch.manual_seed(20260714)
        model = SRRProposeRefineMyoPS(
            base_channels=4,
            variant="m10_d2_hierarchical_psip_propref",
            encoder_profile="safe_4scale",
        )
        x = torch.randn(2, 3, 4, 6, 8)
        availability = torch.tensor([[1.0, 1.0, 1.0], [1.0, 0.0, 1.0]])
        anchor = torch.softmax(torch.randn(2, 6, 4, 6, 8), dim=1)
        outputs = model(x, availability, anchor_features={"probabilities": anchor})

        self.assertEqual(outputs["final_output_base"], "SRR_PROPOSAL_REFINEMENT")
        self.assertEqual(outputs["m10_spatial_dictionary_status"], "enabled_two_pass_spatial")
        self.assertEqual(outputs["m10_spatial_pattern_sip_status"], "independent_enabled")
        for counts in outputs["dictionary_slot_counts"].values():
            self.assertEqual(sum(counts.values()), 16)
        self.assertEqual(float(outputs["m10_no_t2_edema_probability_max"].detach()), 0.0)
        self.assertTrue(torch.all(outputs["m10_final_probabilities"][1, 4] == 0).item())

        labels = torch.zeros(2, 4, 6, 8, dtype=torch.long)
        labels[0, 1:3, 2:5, 2:6] = 4
        labels[1, 1:3, 2:4, 2:4] = 5
        outputs["prototype_memory_alignment_loss"] = outputs["logits"].sum() * 0.0 + 0.123
        total, metrics = srr_m6_expanded_total_loss(outputs, labels, availability)
        self.assertTrue(torch.isfinite(total).item())
        self.assertIn("pattern_sip_integrativeness_loss", metrics)
        self.assertNotEqual(
            float(metrics["loss_pattern_sip_integrativeness"].detach()),
            float(metrics["loss_dictionary_entropy_coverage_load_balance"].detach()),
        )
        self.assertAlmostEqual(float(metrics["loss_memory_bank_update_or_alignment"].detach()), 0.123, places=5)
        self.assertNotEqual(
            float(metrics["loss_memory_bank_update_or_alignment"].detach()),
            float(metrics["loss_prototype_diversity_margin"].detach()),
        )


if __name__ == "__main__":
    unittest.main()
