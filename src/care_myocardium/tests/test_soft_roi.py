import unittest

import numpy as np

from src.care_myocardium.refiner.soft_roi import build_candidate_mask, box_from_mask, extract_roi, restore_roi


class TestSoftROI(unittest.TestCase):
    def test_extract_restore_preserves_geometry(self) -> None:
        arr = np.arange(2 * 6 * 8 * 10, dtype=np.float32).reshape(2, 6, 8, 10)
        mask = np.zeros((6, 8, 10), dtype=bool)
        mask[2:4, 3:6, 4:8] = True
        box = box_from_mask(mask, margin=1)
        crop = extract_roi(arr, box)
        restored = restore_roi(crop, box, fill_value=-1)

        self.assertEqual(crop.shape, (2, 4, 5, 6))
        self.assertEqual(restored.shape, arr.shape)
        np.testing.assert_array_equal(restored[(..., *box.slices())], arr[(..., *box.slices())])
        self.assertTrue(np.all(restored[:, : box.starts[0]] == -1))

    def test_candidate_mask_uses_anatomy_fallback(self) -> None:
        proposal = np.zeros((5, 6, 7), dtype=bool)
        anatomy = np.zeros_like(proposal)
        anatomy[2, 3, 4] = True
        candidate, source = build_candidate_mask(proposal, anatomy, proposal_dilation=1, anatomy_dilation=1)
        self.assertEqual(source, "anatomy_fallback")
        self.assertTrue(candidate.any())
        self.assertTrue(candidate[2, 3, 4])

    def test_empty_mask_box_is_full_volume(self) -> None:
        mask = np.zeros((3, 4, 5), dtype=bool)
        box = box_from_mask(mask, margin=2)
        self.assertEqual(box.starts, (0, 0, 0))
        self.assertEqual(box.ends, (3, 4, 5))
        self.assertEqual(box.volume, 60)


if __name__ == "__main__":
    unittest.main()
