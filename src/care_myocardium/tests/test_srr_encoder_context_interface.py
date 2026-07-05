import unittest

import torch

from src.care_myocardium.models.srr_propref import SRRProposeRefineMyoPS


def _parameter_count(model: torch.nn.Module) -> int:
    return int(sum(param.numel() for param in model.parameters()))


class TestSRREncoderContextInterface(unittest.TestCase):
    def test_strong_profile_is_four_scale_and_callable(self) -> None:
        model = SRRProposeRefineMyoPS(base_channels=4, encoder_profile="strong_4scale")
        model.eval()
        x = torch.randn(1, 3, 5, 16, 16)
        availability = torch.tensor([[1.0, 1.0, 1.0]])
        anchor = {"probabilities": torch.softmax(torch.randn(1, 6, 5, 16, 16), dim=1)}
        component = {
            "scar_component": torch.zeros(1, 1, 5, 16, 16),
            "edema_component": torch.zeros(1, 1, 5, 16, 16),
        }
        with torch.no_grad():
            out = model(x, availability, anchor_features=anchor, component_features=component)
        self.assertEqual(out["logits"].shape, (1, 6, 5, 16, 16))
        self.assertEqual(out["encoder_profile"], "strong_4scale")
        self.assertEqual(tuple(out["encoder_scale_channels"]), (4, 8, 16, 32))
        self.assertEqual(len(model.retrieval), 4)
        self.assertEqual(set(out["dictionary_slot_counts"]), {"scale0", "scale1", "scale2", "scale3"})

    def test_strong_profile_has_more_capacity_than_tiny(self) -> None:
        tiny = SRRProposeRefineMyoPS(base_channels=4, encoder_profile="tiny_3scale")
        strong = SRRProposeRefineMyoPS(base_channels=4, encoder_profile="strong_4scale")
        self.assertGreater(_parameter_count(strong), _parameter_count(tiny))
        self.assertEqual(strong.encoder_scale_channels, [4, 8, 16, 32])
        self.assertEqual(tiny.encoder_scale_channels, [4, 8, 16])

    def test_context_shape_mismatch_is_rejected(self) -> None:
        model = SRRProposeRefineMyoPS(base_channels=4, encoder_profile="strong_4scale")
        x = torch.randn(1, 3, 5, 16, 16)
        availability = torch.tensor([[1.0, 1.0, 1.0]])
        bad_anchor = {"probabilities": torch.zeros(1, 6, 5, 15, 16)}
        with self.assertRaisesRegex(ValueError, "spatial shape"):
            model(x, availability, anchor_features=bad_anchor)

    def test_anchor_context_changes_retrieval_gate(self) -> None:
        torch.manual_seed(7)
        model = SRRProposeRefineMyoPS(base_channels=4, encoder_profile="strong_4scale")
        model.eval()
        x = torch.randn(1, 3, 5, 16, 16)
        availability = torch.tensor([[1.0, 1.0, 1.0]])
        zero_anchor = {"probabilities": torch.zeros(1, 6, 5, 16, 16)}
        informative_anchor = {"probabilities": torch.softmax(torch.randn(1, 6, 5, 16, 16), dim=1)}
        with torch.no_grad():
            out_zero = model(x, availability, anchor_features=zero_anchor)
            out_info = model(x, availability, anchor_features=informative_anchor)
        diffs = [
            (out_zero["gates"][name] - out_info["gates"][name]).abs().sum()
            for name in out_zero["gates"]
        ]
        self.assertGreater(float(torch.stack(diffs).sum()), 0.0)

    def test_missing_modality_strong_encoder_is_closed(self) -> None:
        model = SRRProposeRefineMyoPS(base_channels=4, encoder_profile="strong_4scale")
        image = torch.randn(1, 1, 5, 16, 16)
        present = torch.tensor([0.0])
        features = model.encoders[1](image, present)
        self.assertEqual(len(features), 4)
        for feature in features:
            self.assertEqual(float(feature.detach().abs().max()), 0.0)


if __name__ == "__main__":
    unittest.main()
