from __future__ import annotations

import unittest

import torch

from src.care_myocardium.anchors.myops_decode import (
    CANONICAL_AVAILABILITY_ORDER,
    EDEMA_CLASS,
    LEGACY_PRESENCE_ORDER,
    MYOPS_COMPACT_TO_RAW,
    apply_no_t2_edema_policy_to_decoded,
    apply_no_t2_edema_policy_to_logits,
    decode_compact_logits,
    decode_myops_logits_for_export_policy,
    normalize_availability_order,
)


class TestMyoPSDecodeGuardrails(unittest.TestCase):
    def test_block_edema_removes_no_t2_edema_logit_and_decode(self) -> None:
        logits = torch.zeros(2, 6, 2, 2, 2)
        logits[:, 0] = 0.1
        logits[:, EDEMA_CLASS] = 10.0
        availability = torch.tensor(
            [
                [1.0, 0.0, 1.0],
                [1.0, 1.0, 1.0],
            ]
        )

        guarded = apply_no_t2_edema_policy_to_logits(logits, availability, policy="block_edema")
        decoded = decode_compact_logits(logits, availability, policy="block_edema")

        self.assertTrue(torch.all(guarded[0, EDEMA_CLASS] < -1.0e8).item())
        self.assertFalse(torch.any(decoded[0] == EDEMA_CLASS).item())
        self.assertTrue(torch.all(decoded[1] == EDEMA_CLASS).item())

    def test_t2_present_leaves_edema_path_available(self) -> None:
        logits = torch.zeros(1, 6, 2, 2, 2)
        logits[:, EDEMA_CLASS] = 5.0
        availability = torch.tensor([[1.0, 1.0, 0.0]])

        guarded = apply_no_t2_edema_policy_to_logits(logits, availability, policy="block_edema")
        decoded = decode_compact_logits(logits, availability, policy="block_edema")

        self.assertTrue(torch.equal(guarded, logits))
        self.assertTrue(torch.all(decoded == EDEMA_CLASS).item())

    def test_decoded_block_edema_removes_class_four_only_for_no_t2(self) -> None:
        decoded = torch.tensor(
            [
                [[[0, 4], [5, 4]]],
                [[[4, 4], [5, 0]]],
            ]
        )
        availability = torch.tensor([[1.0, 0.0, 1.0], [1.0, 1.0, 1.0]])

        guarded = apply_no_t2_edema_policy_to_decoded(decoded, availability, policy="block_edema")

        self.assertFalse(torch.any(guarded[0] == EDEMA_CLASS).item())
        self.assertTrue(torch.any(guarded[1] == EDEMA_CLASS).item())
        self.assertTrue(torch.any(guarded[0] == 5).item())

    def test_legacy_order_adapter_is_explicit(self) -> None:
        legacy = torch.tensor([[1.0, 0.0, 1.0]])  # C0,LGE,T2

        with self.assertRaisesRegex(ValueError, "requires allow_legacy_adapter=True"):
            normalize_availability_order(legacy, LEGACY_PRESENCE_ORDER)

        canonical = normalize_availability_order(
            legacy,
            LEGACY_PRESENCE_ORDER,
            allow_legacy_adapter=True,
        )
        self.assertEqual(CANONICAL_AVAILABILITY_ORDER, ("LGE", "T2", "C0"))
        self.assertTrue(torch.equal(canonical, torch.tensor([[0.0, 1.0, 1.0]])))

    def test_compact_to_raw_pathology_mapping_is_locked(self) -> None:
        self.assertEqual(MYOPS_COMPACT_TO_RAW[4], 1220)
        self.assertEqual(MYOPS_COMPACT_TO_RAW[5], 2221)

    def test_export_policy_reports_no_t2_before_after_counts_and_raw_labels(self) -> None:
        logits = torch.zeros(2, 6, 2, 2, 2)
        logits[:, 0] = 0.1
        logits[0, EDEMA_CLASS] = 8.0
        logits[1, 5] = 8.0
        availability = torch.tensor([[1.0, 0.0, 1.0], [1.0, 1.0, 1.0]])

        compact, raw, summary = decode_myops_logits_for_export_policy(
            logits,
            availability,
            policy="block_edema",
        )

        self.assertEqual(summary["no_t2_edema_voxels_before"], 8)
        self.assertEqual(summary["no_t2_edema_voxels_after"], 0)
        self.assertFalse(torch.any(compact[0] == EDEMA_CLASS).item())
        self.assertTrue(torch.all(raw[1] == MYOPS_COMPACT_TO_RAW[5]).item())
        self.assertEqual(summary["raw_edema_label"], 1220)
        self.assertEqual(summary["raw_scar_label"], 2221)


if __name__ == "__main__":
    unittest.main()
