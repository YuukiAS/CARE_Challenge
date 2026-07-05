import unittest

import torch

from src.care_myocardium.models.srr_propref import AnatomyDistanceROIPrior, CropSoftROIRefinementHead


class TestAnatomyDistanceROIPrior(unittest.TestCase):
    def _anatomy_logits(self) -> torch.Tensor:
        logits = torch.full((1, 4, 5, 8, 8), -6.0)
        logits[:, 0] = 4.0
        logits[:, 1, 2, 2:6, 2:6] = 5.0
        logits[:, 2, 2, 3:5, 3:5] = 6.0
        logits[:, 3, 2, 5:7, 3:5] = 6.0
        return logits

    def test_distance_maps_match_anatomy_shape(self) -> None:
        prior = AnatomyDistanceROIPrior(distance_steps=4)
        availability = torch.tensor([[1.0, 1.0, 1.0]])
        out = prior(self._anatomy_logits(), None, availability)
        for key in (
            "p_union",
            "p_lv",
            "p_rv",
            "union_distance",
            "lv_distance",
            "rv_distance",
            "scar_soft_gate",
            "edema_soft_gate",
            "uncertainty",
        ):
            self.assertEqual(tuple(out[key].shape), (1, 1, 5, 8, 8))
        self.assertLess(float(out["union_distance"][0, 0, 2, 4, 4]), float(out["union_distance"][0, 0, 0, 0, 0]))

    def test_remote_proposal_is_downweighted_not_deleted(self) -> None:
        prior = AnatomyDistanceROIPrior(distance_steps=4)
        availability = torch.tensor([[1.0, 1.0, 1.0]])
        context = prior(self._anatomy_logits(), None, availability)
        head = CropSoftROIRefinementHead(
            2,
            pathology="scar",
            modality_index=0,
            roi_kernel=3,
            crop_margin=1,
            min_crop_shape=(3, 4, 4),
            residual_scale=0.1,
            roi_threshold=0.2,
            containment_penalty=0.2,
        )
        proposal = torch.full((1, 1, 5, 8, 8), -8.0)
        proposal[:, :, 0, 0, 0] = 8.0
        proposal[:, :, 2, 4, 4] = 8.0
        zeros = torch.zeros_like(proposal)
        roi, _, _ = head.soft_roi(proposal, context["scar_soft_gate_logits"], zeros, zeros, zeros, anatomy_context=context)
        remote = float(roi[0, 0, 0, 0, 0])
        central = float(roi[0, 0, 2, 4, 4])
        self.assertGreater(remote, 0.0)
        self.assertLess(remote, central)

    def test_empty_union_uses_bounded_center_fallback_not_full_volume(self) -> None:
        anatomy_logits = torch.full((1, 4, 5, 8, 8), -8.0)
        anatomy_logits[:, 0] = 8.0
        availability = torch.tensor([[1.0, 1.0, 1.0]])
        context = AnatomyDistanceROIPrior(distance_steps=4)(anatomy_logits, None, availability)
        head = CropSoftROIRefinementHead(
            2,
            pathology="scar",
            modality_index=0,
            roi_kernel=3,
            crop_margin=1,
            min_crop_shape=(3, 4, 4),
            residual_scale=0.1,
            roi_threshold=0.2,
            containment_penalty=0.2,
        )
        image = torch.zeros((1, 3, 5, 8, 8))
        features = torch.zeros((1, 2, 5, 8, 8))
        logits = torch.full((1, 1, 5, 8, 8), -8.0)
        zeros = torch.zeros_like(logits)
        _, _, roi, crop_mask, _, stats = head(
            image,
            features,
            logits,
            logits,
            context["scar_soft_gate_logits"],
            availability,
            anchor_evidence=zeros,
            component_evidence=zeros,
            pos_similarity=zeros,
            neg_similarity=zeros,
            anatomy_context=context,
        )
        self.assertLess(float(roi.mean()), 0.01)
        self.assertEqual(float(stats.detach()[0, 7]), 2.0)
        self.assertLess(float(crop_mask.mean()), 1.0)

    def test_refiner_reports_bounded_crop_bounds_and_masked_residual(self) -> None:
        availability = torch.tensor([[1.0, 1.0, 1.0]])
        context = AnatomyDistanceROIPrior(distance_steps=4)(self._anatomy_logits(), None, availability)
        head = CropSoftROIRefinementHead(
            2,
            pathology="scar",
            modality_index=0,
            roi_kernel=3,
            crop_margin=1,
            min_crop_shape=(3, 4, 4),
            residual_scale=0.1,
            roi_threshold=0.2,
            containment_penalty=0.2,
        )
        image = torch.zeros((1, 3, 5, 8, 8))
        image[:, 0, 2, 3:5, 3:5] = 1.0
        features = torch.zeros((1, 2, 5, 8, 8))
        evidence = torch.zeros((1, 1, 5, 8, 8))
        proposal = torch.full_like(evidence, -8.0)
        proposal[:, :, 2, 4, 4] = 8.0
        zeros = torch.zeros_like(evidence)
        _, residual, _, crop_mask, bounds, stats = head(
            image,
            features,
            evidence,
            proposal,
            context["scar_soft_gate_logits"],
            availability,
            anchor_evidence=zeros,
            component_evidence=zeros,
            pos_similarity=zeros,
            neg_similarity=zeros,
            anatomy_context=context,
        )
        z0, z1, y0, y1, x0, x1 = [int(v) for v in bounds[0].tolist()]
        self.assertLess(z0, z1)
        self.assertLess(y0, y1)
        self.assertLess(x0, x1)
        stats_cpu = stats.detach()
        self.assertLess(float(stats_cpu[0, 3]), 1.0)
        self.assertEqual(float(stats_cpu[0, 6]), 0.0)
        self.assertGreater(float(crop_mask.sum()), 0.0)
        self.assertTrue(torch.all(residual[crop_mask == 0] == 0))

    def test_no_t2_blocks_edema_gate_and_refiner(self) -> None:
        availability = torch.tensor([[1.0, 0.0, 1.0]])
        context = AnatomyDistanceROIPrior(distance_steps=4)(self._anatomy_logits(), None, availability)
        self.assertEqual(float(context["edema_soft_gate"].max()), 0.0)
        head = CropSoftROIRefinementHead(
            2,
            pathology="edema",
            modality_index=1,
            roi_kernel=3,
            crop_margin=1,
            min_crop_shape=(3, 4, 4),
            residual_scale=0.1,
            roi_threshold=0.2,
            containment_penalty=0.2,
        )
        image = torch.zeros((1, 3, 5, 8, 8))
        features = torch.zeros((1, 2, 5, 8, 8))
        logits = torch.zeros((1, 1, 5, 8, 8))
        zeros = torch.zeros_like(logits)
        final, _, _, _, _, stats = head(
            image,
            features,
            logits,
            logits,
            context["edema_soft_gate_logits"],
            availability,
            anchor_evidence=zeros,
            component_evidence=zeros,
            pos_similarity=zeros,
            neg_similarity=zeros,
            anatomy_context=context,
        )
        self.assertTrue(torch.all(final == -20.0))
        self.assertEqual(float(stats.detach()[0, 7]), 3.0)


if __name__ == "__main__":
    unittest.main()
