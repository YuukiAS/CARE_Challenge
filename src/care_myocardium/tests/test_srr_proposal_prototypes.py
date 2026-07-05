from __future__ import annotations

import unittest
from argparse import Namespace

import torch

from src.care_myocardium.models.proposal_prototypes import build_prototype_bank_from_labeled_features
from src.care_myocardium.models.srr_propref import CropSoftROIRefinementHead, SRRProposeRefineMyoPS


def _loss_args() -> Namespace:
    return Namespace(
        anatomy_weight=1.0,
        scar_weight=1.0,
        edema_weight=1.0,
        proposal_margin=0.25,
        component_proposal_margin=0.35,
        component_proposal_weight=0.20,
        semantic_retrieval_weight=0.04,
        semantic_coverage_weight=0.03,
        semantic_integrative_weight=0.02,
        baseline_preservation_weight=0.10,
        baseline_preservation_confidence=0.80,
        baseline_gate_harm_weight=0.25,
        margin_weight=0.30,
        proposal_weight=0.45,
        roi_weight=0.25,
        roi_remote_weight=0.05,
    )


class TestSRRProposalPrototypes(unittest.TestCase):
    def test_pathology_aware_decode_is_support_constrained(self) -> None:
        from scripts.training.run_srr_propref_myops_fold0 import _decode_pathology_aware

        logits = torch.full((1, 6, 3, 5, 5), -8.0)
        logits[:, 0] = 8.0
        scar_logits = torch.full((1, 1, 3, 5, 5), 8.0)
        edema_logits = torch.full((1, 1, 3, 5, 5), -8.0)
        scar_roi = torch.zeros((1, 1, 3, 5, 5))
        scar_crop = torch.zeros_like(scar_roi)
        scar_proposal = torch.full_like(scar_roi, -8.0)
        scar_roi[:, :, 1, 2, 2] = 1.0
        scar_proposal[:, :, 1, 2, 2] = 8.0
        outputs = {
            "logits": logits,
            "anatomy_logits": torch.zeros((1, 4, 3, 5, 5)),
            "scar_logits": scar_logits,
            "edema_logits": edema_logits,
            "scar_soft_roi": scar_roi,
            "edema_soft_roi": torch.zeros_like(scar_roi),
            "scar_crop_region_mask": scar_crop,
            "edema_crop_region_mask": torch.zeros_like(scar_roi),
            "scar_proposal_logits": scar_proposal,
            "edema_proposal_logits": torch.full_like(scar_roi, -8.0),
        }

        decoded = _decode_pathology_aware(outputs, scar_threshold=0.5, edema_threshold=0.5)

        self.assertEqual(int((decoded == 5).sum()), 1)
        self.assertEqual(int(decoded[0, 1, 2, 2]), 5)
        self.assertTrue(torch.all(decoded[decoded != 5] == 0).item())

    def test_crop_soft_roi_refiner_uses_bounded_original_modality_crop(self) -> None:
        torch.manual_seed(10)
        head = CropSoftROIRefinementHead(
            channels=4,
            pathology="scar",
            modality_index=0,
            roi_kernel=3,
            crop_margin=1,
            min_crop_shape=(3, 4, 4),
            residual_scale=0.5,
            roi_threshold=0.2,
            containment_penalty=0.2,
        )
        image = torch.randn(1, 3, 6, 8, 10)
        features = torch.randn(1, 4, 6, 8, 10)
        evidence = torch.full((1, 1, 6, 8, 10), -3.0)
        proposal = torch.full_like(evidence, -8.0)
        proposal[:, :, 2:4, 3:5, 4:6] = 8.0
        anatomy = torch.full_like(evidence, -4.0)
        anatomy[:, :, 1:5, 2:6, 3:7] = 4.0
        anchor = torch.zeros_like(evidence)
        anchor[:, :, 2:4, 3:5, 4:6] = 1.0
        component = anchor.clone()
        pos = anchor.clone()
        neg = torch.zeros_like(evidence)
        availability = torch.tensor([[1.0, 1.0, 1.0]])

        final, residual, roi, crop_mask, bounds, stats = head(
            image,
            features,
            evidence,
            proposal,
            anatomy,
            availability,
            anchor_evidence=anchor,
            component_evidence=component,
            pos_similarity=pos,
            neg_similarity=neg,
        )

        self.assertEqual(tuple(final.shape), tuple(evidence.shape))
        self.assertGreater(float(crop_mask.sum()), 0.0)
        self.assertLess(float(crop_mask.mean()), 1.0)
        self.assertTrue(torch.all(residual[crop_mask == 0] == 0).item())
        self.assertGreater(float(roi.max()), 0.2)
        self.assertLess(int(bounds[0, 1] - bounds[0, 0]) * int(bounds[0, 3] - bounds[0, 2]) * int(bounds[0, 5] - bounds[0, 4]), 6 * 8 * 10)
        self.assertEqual(float(stats[0, 7].detach()), 0.0)

    def test_builder_excludes_no_t2_myocardium_from_edema_negatives(self) -> None:
        torch.manual_seed(11)
        scar_features = torch.randn(2, 4, 4, 5, 6)
        edema_features = torch.randn(2, 4, 4, 5, 6)
        labels = torch.zeros(2, 4, 5, 6, dtype=torch.long)
        labels[:, 1:3, 1:4, 1:5] = 1
        labels[:, 1, 2, 2] = 5
        labels[0, 2, 3, 3] = 4
        labels[:, :, 0, 0] = 2
        availability = torch.tensor([[1.0, 1.0, 1.0], [1.0, 0.0, 1.0]])
        anchor = torch.zeros(2, 6, 4, 5, 6)
        anchor[:, 5, 0, 0, 0] = 0.9
        anchor[0, 4, 0, 1, 0] = 0.9

        bank = build_prototype_bank_from_labeled_features(
            scar_features=scar_features,
            edema_features=edema_features,
            labels=labels,
            availability=availability,
            anchor_probabilities=anchor,
            scar_positive_count=3,
            scar_negative_count=4,
            edema_positive_count=3,
            edema_negative_count=4,
            source="unit_train_tensor",
        )

        self.assertEqual(tuple(bank.scar_positive.shape), (3, 4))
        self.assertEqual(tuple(bank.edema_negative.shape), (4, 4))
        self.assertGreater(bank.counts["scar_positive"], 0)
        self.assertGreater(bank.counts["edema_positive"], 0)
        self.assertGreater(bank.counts["edema_negative"], 0)
        self.assertEqual(bank.hard_negative_counts["edema_no_t2_myocardium_negative_voxels"], 0)

    def test_propref_forward_uses_loaded_bank_and_blocks_no_t2_edema(self) -> None:
        torch.manual_seed(12)
        model = SRRProposeRefineMyoPS(base_channels=4)
        x = torch.randn(2, 3, 4, 6, 8)
        availability = torch.tensor([[1.0, 1.0, 1.0], [1.0, 0.0, 1.0]])
        anchor = torch.zeros(2, 6, 4, 6, 8)
        anchor[:, 5, 1:3, 2:4, 2:5] = 0.8
        anchor[:, 4, 2:4, 3:5, 3:6] = 0.8
        component = {
            "scar_component": (anchor[:, 5:6] > 0.5).float(),
            "edema_component": (anchor[:, 4:5] > 0.5).float(),
        }
        with torch.no_grad():
            features, _, _, _ = model._evidence_features(x, availability, anchor)
        labels = torch.zeros(2, 4, 6, 8, dtype=torch.long)
        labels[:, 1:3, 2:5, 2:6] = 1
        labels[:, 1, 3, 3] = 5
        labels[0, 2, 4, 4] = 4
        bank = build_prototype_bank_from_labeled_features(
            scar_features=features["scar"],
            edema_features=features["edema"],
            labels=labels,
            availability=availability,
            anchor_probabilities=anchor,
            scar_positive_count=6,
            scar_negative_count=6,
            edema_positive_count=8,
            edema_negative_count=6,
            source="unit_train_forward_features",
        )
        model.scar_dictionary.load_prototype_bank(
            positive=bank.scar_positive,
            negative=bank.scar_negative,
            source=bank.source,
        )
        model.edema_dictionary.load_prototype_bank(
            positive=bank.edema_positive,
            negative=bank.edema_negative,
            source=bank.source,
        )

        outputs = model(x, availability, anchor_features=anchor, component_features=component)
        self.assertEqual(tuple(outputs["scar_proposal_logits"].shape), (2, 1, 4, 6, 8))
        self.assertEqual(tuple(outputs["scar_crop_bounds_zyx"].shape), (2, 6))
        self.assertEqual(tuple(outputs["edema_crop_bounds_zyx"].shape), (2, 6))
        self.assertEqual(outputs["prototype_source"]["scar"], "unit_train_forward_features")
        self.assertTrue(torch.isfinite(outputs["scar_anchor_evidence"]).all().item())
        self.assertTrue(torch.isfinite(outputs["edema_component_evidence"]).all().item())
        no_t2_edema_volume = torch.sigmoid(outputs["edema_proposal_logits"][1]).sum().detach()
        self.assertLess(float(no_t2_edema_volume), 1e-5)
        self.assertTrue(torch.all(outputs["edema_logits"][1] <= -20.0).item())
        self.assertEqual(float(outputs["edema_roi_stats"][1, 7].detach()), 3.0)
        random_proto_parameters = [
            name
            for name, _ in model.named_parameters()
            if name.endswith("positive") or name.endswith("negative") or "negative_memory_" in name
        ]
        self.assertEqual(random_proto_parameters, [])


    def test_propref_loss_reports_component_ranking_terms(self) -> None:
        from scripts.training.run_srr_propref_myops_fold0 import propref_loss

        torch.manual_seed(15)
        model = SRRProposeRefineMyoPS(base_channels=4, variant="srr_propref_shared_dual_dict")
        x = torch.randn(2, 3, 4, 6, 8)
        availability = torch.tensor([[1.0, 1.0, 1.0], [1.0, 0.0, 1.0]])
        labels = torch.zeros(2, 4, 6, 8, dtype=torch.long)
        labels[0, 1:3, 2:5, 2:6] = 4
        labels[0, 1, 3, 3] = 5
        labels[1, 1:3, 2:4, 2:4] = 5
        anchor = torch.zeros(2, 6, 4, 6, 8)
        anchor[:, 5, 1:3, 2:4, 2:5] = 0.8
        anchor[0, 4, 1:3, 2:5, 2:6] = 0.8
        component = {
            "scar_component": (anchor[:, 5:6] > 0.5).float(),
            "edema_component": (anchor[:, 4:5] > 0.5).float(),
        }
        outputs = model(x, availability, anchor_features=anchor, component_features=component)
        args = _loss_args()
        loss, metrics = propref_loss(outputs, labels, availability, "proposal_dictionary", args)
        self.assertTrue(torch.isfinite(loss).item())
        self.assertIn("scar_component_ranking_loss", metrics)
        self.assertIn("edema_component_ranking_loss", metrics)
        self.assertIn("component_proposal_ranking_loss", metrics)
        self.assertGreaterEqual(float(metrics["scar_component_ranking_loss"].detach()), 0.0)
        self.assertGreaterEqual(float(metrics["edema_component_ranking_loss"].detach()), 0.0)

    def test_no_t2_edema_component_ranking_is_zero(self) -> None:
        from scripts.training.run_srr_propref_myops_fold0 import propref_loss

        torch.manual_seed(16)
        model = SRRProposeRefineMyoPS(base_channels=4, variant="srr_propref_shared_dual_dict")
        x = torch.randn(1, 3, 4, 6, 8)
        availability = torch.tensor([[1.0, 0.0, 1.0]])
        labels = torch.zeros(1, 4, 6, 8, dtype=torch.long)
        labels[0, 1:3, 2:4, 2:4] = 5
        outputs = model(x, availability)
        args = _loss_args()
        _, metrics = propref_loss(outputs, labels, availability, "proposal_dictionary", args)
        self.assertEqual(float(metrics["edema_component_ranking_loss"].detach()), 0.0)


if __name__ == "__main__":
    unittest.main()
