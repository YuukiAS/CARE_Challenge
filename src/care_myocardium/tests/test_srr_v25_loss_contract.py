from __future__ import annotations

import unittest

import torch

from src.care_myocardium.losses.srr_v25_loss_contract import srr_v25_preflight_loss
from src.care_myocardium.models.srr_propref import SRRProposeRefineMyoPS


class TestSRRV25LossContract(unittest.TestCase):
    def test_prefight_loss_has_distinct_scar_and_edema_gradients(self) -> None:
        torch.manual_seed(20260704)
        model = SRRProposeRefineMyoPS(base_channels=4, variant="srr_propref_shared_dual_dict")
        x = torch.randn(2, 3, 5, 7, 9)
        availability = torch.tensor(
            [
                [1.0, 1.0, 1.0],
                [1.0, 0.0, 1.0],
            ]
        )
        labels = torch.zeros(2, 5, 7, 9, dtype=torch.long)
        labels[0, 1:4, 2:6, 2:7] = 4
        labels[0, 2:4, 3:5, 4:6] = 5
        labels[1, 1:3, 2:5, 2:4] = 5
        labels[1, 0, 0, 0] = 2
        labels[1, 0, 0, 1] = 3

        outputs = model(x, availability)
        outputs["scar_logits"].retain_grad()
        outputs["edema_logits"].retain_grad()
        loss, metrics = srr_v25_preflight_loss(outputs, labels, availability)
        loss.backward()

        self.assertGreater(float(outputs["scar_logits"].grad.abs().sum()), 0.0)
        self.assertGreater(float(outputs["edema_logits"].grad[0].abs().sum()), 0.0)
        self.assertEqual(float(outputs["edema_logits"].grad[1].abs().sum()), 0.0)
        self.assertGreater(float(metrics["scar_proposal_precision_bce_dice"].detach()), 0.0)
        self.assertGreater(float(metrics["scar_outside_myocardium_fp"].detach()), 0.0)
        self.assertGreater(float(metrics["edema_refine_t2_masked_bce_dice"].detach()), 0.0)
        self.assertEqual(float(metrics["edema_no_t2_negative_voxels"].detach()), 0.0)
        self.assertEqual(float(metrics["no_T2_edema_voxels"].detach()), 0.0)

    def test_all_no_t2_edema_terms_are_zero_without_negative_loss(self) -> None:
        torch.manual_seed(20260705)
        model = SRRProposeRefineMyoPS(base_channels=4, variant="srr_propref_scar_precision")
        x = torch.randn(2, 3, 5, 7, 9)
        availability = torch.tensor(
            [
                [1.0, 0.0, 1.0],
                [1.0, 0.0, 0.0],
            ]
        )
        labels = torch.zeros(2, 5, 7, 9, dtype=torch.long)
        labels[:, 2:4, 3:5, 3:5] = 5

        outputs = model(x, availability)
        outputs["edema_logits"].retain_grad()
        loss, metrics = srr_v25_preflight_loss(outputs, labels, availability)
        loss.backward()

        self.assertEqual(float(metrics["edema_t2_supervised_voxels"].detach()), 0.0)
        self.assertEqual(float(metrics["edema_no_t2_negative_voxels"].detach()), 0.0)
        self.assertEqual(float(metrics["edema_refine_t2_masked_bce_dice"].detach()), 0.0)
        self.assertEqual(float(metrics["edema_proposal_t2_masked_bce_dice"].detach()), 0.0)
        self.assertEqual(float(outputs["edema_logits"].grad.abs().sum()), 0.0)


if __name__ == "__main__":
    unittest.main()
