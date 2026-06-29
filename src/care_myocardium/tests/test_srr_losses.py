from __future__ import annotations

import unittest

import torch

from src.care_myocardium.data.case_metadata import compact_to_raw_myops_mapping
from src.care_myocardium.losses.srr_losses import anatomy_loss, scar_loss, srr_total_loss, t2_masked_edema_loss
from src.care_myocardium.models.srr_myops import SRRMyoPSLite


class TestSRRLosses(unittest.TestCase):
    def test_t2_present_edema_loss_has_gradient(self) -> None:
        torch.manual_seed(4)
        model = SRRMyoPSLite(base_channels=8)
        x = torch.randn(1, 3, 6, 8, 8)
        availability = torch.tensor([[1.0, 1.0, 1.0]])
        labels = torch.zeros(1, 6, 8, 8, dtype=torch.long)
        labels[:, 2:4, 3:5, 3:5] = 4
        outputs = model(x, availability)
        outputs["edema_logits"].retain_grad()
        loss, metrics = srr_total_loss(outputs, labels, availability)
        loss.backward()
        self.assertGreater(float(outputs["edema_logits"].grad.abs().sum()), 0.0)
        self.assertGreater(float(metrics["edema"].detach()), 0.0)

    def test_no_t2_edema_dense_loss_is_zero(self) -> None:
        torch.manual_seed(5)
        logits = torch.randn(2, 1, 6, 8, 8, requires_grad=True)
        labels = torch.zeros(2, 6, 8, 8, dtype=torch.long)
        availability = torch.tensor([[1.0, 0.0, 1.0], [1.0, 0.0, 0.0]])
        loss = t2_masked_edema_loss(logits, labels, availability)
        self.assertEqual(float(loss.detach()), 0.0)
        loss.backward()
        self.assertEqual(float(logits.grad.abs().sum()), 0.0)

    def test_scar_head_gets_lge_only_gradient(self) -> None:
        torch.manual_seed(6)
        model = SRRMyoPSLite(base_channels=8)
        x = torch.randn(1, 3, 6, 8, 8)
        availability = torch.tensor([[1.0, 0.0, 0.0]])
        labels = torch.zeros(1, 6, 8, 8, dtype=torch.long)
        labels[:, 2:4, 3:5, 3:5] = 5
        outputs = model(x, availability)
        loss, _ = srr_total_loss(outputs, labels, availability)
        loss.backward()
        grad_sum = sum(float(p.grad.abs().sum()) for p in model.heads.scar.parameters() if p.grad is not None)
        self.assertGreater(grad_sum, 0.0)

    def test_ignore_label_voxels_do_not_contribute_to_core_losses(self) -> None:
        torch.manual_seed(9)
        labels = torch.zeros(1, 3, 4, 5, dtype=torch.long)
        labels[:, 0, 0, 0] = -1
        availability = torch.tensor([[1.0, 1.0, 1.0]])

        anatomy_a = torch.randn(1, 4, 3, 4, 5)
        anatomy_b = anatomy_a.clone()
        anatomy_b[:, :, 0, 0, 0] = torch.tensor([100.0, -100.0, 50.0, -50.0])
        self.assertTrue(torch.allclose(anatomy_loss(anatomy_a, labels), anatomy_loss(anatomy_b, labels)))

        scar_a = torch.randn(1, 1, 3, 4, 5)
        scar_b = scar_a.clone()
        scar_b[:, :, 0, 0, 0] = 100.0
        self.assertTrue(torch.allclose(scar_loss(scar_a, labels), scar_loss(scar_b, labels)))

        edema_a = torch.randn(1, 1, 3, 4, 5)
        edema_b = edema_a.clone()
        edema_b[:, :, 0, 0, 0] = -100.0
        self.assertTrue(torch.allclose(t2_masked_edema_loss(edema_a, labels, availability), t2_masked_edema_loss(edema_b, labels, availability)))

    def test_compact_label_mapping(self) -> None:
        mapping = compact_to_raw_myops_mapping()
        self.assertEqual(mapping[4], 1220)
        self.assertEqual(mapping[5], 2221)


if __name__ == "__main__":
    unittest.main()
