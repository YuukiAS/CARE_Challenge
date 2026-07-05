from __future__ import annotations

import json
import tempfile
import unittest
from argparse import Namespace
from pathlib import Path

import numpy as np
import SimpleITK as sitk
import torch

from scripts.training.run_srr_propref_myops_fold0 import AnchoredCaseData, fit_and_load_runtime_prototype_bank
from src.care_myocardium.models.srr_propref import SRRProposeRefineMyoPS


class _Meta:
    def __init__(self, *, t2_present: bool = True) -> None:
        self.t2_present = bool(t2_present)
        self.center = "Toy"
        self.modality_group = "C0+LGE+T2" if t2_present else "C0+LGE"


def _case(case_id: str, cls: int, *, t2_present: bool = True) -> AnchoredCaseData:
    shape = (5, 8, 8)
    image = np.zeros((3, *shape), dtype=np.float32)
    image[0] = 1.0
    if t2_present:
        image[1] = 0.5
    image[2] = 0.25
    label_arr = np.zeros(shape, dtype=np.int64)
    label_arr[2:4, 3:6, 3:6] = 1
    label_arr[2, 4:6, 4:6] = cls
    anchor = np.zeros((6, *shape), dtype=np.float32)
    anchor[0] = 0.5
    anchor[cls] = 0.75
    component = np.zeros((2, *shape), dtype=np.float32)
    if cls == 5:
        component[0, label_arr == cls] = 1.0
    if cls == 4:
        component[1, label_arr == cls] = 1.0
    availability = np.asarray([1.0, 1.0 if t2_present else 0.0, 1.0], dtype=np.float32)
    return AnchoredCaseData(
        case_id=case_id,
        image=image,
        label_arr=label_arr,
        label_img=sitk.GetImageFromArray(label_arr.astype(np.uint8)),
        availability=availability,
        metadata=_Meta(t2_present=t2_present),
        anchor_probabilities=anchor,
        component_features=component,
        anchor_source=f"toy/{case_id}.npz",
        anchor_fold=0,
    )


class TestSRRRuntimePrototypeBank(unittest.TestCase):
    def test_formal_runner_helper_loads_real_runtime_bank(self) -> None:
        torch.manual_seed(13)
        model = SRRProposeRefineMyoPS(base_channels=4)
        args = Namespace(
            variant="srr_propref_shared_dual_dict",
            skip_prototype_bank_fit=False,
            prototype_bank_cases=2,
            seed=20260704,
        )
        with tempfile.TemporaryDirectory() as tmp:
            summary = fit_and_load_runtime_prototype_bank(
                model,
                [_case("ToyScar", 5), _case("ToyEdema", 4)],
                (5, 8, 8),
                torch.device("cpu"),
                args,
                Path(tmp),
            )
            written = json.loads((Path(tmp) / "prototype_bank_summary.json").read_text())

        self.assertEqual(summary["source"], "train_oof_runtime_features_fold0")
        self.assertEqual(written["case_count"], 2)
        self.assertEqual(model.scar_dictionary.prototype_source, "train_oof_runtime_features_fold0")
        self.assertEqual(model.edema_dictionary.prototype_source, "train_oof_runtime_features_fold0")
        self.assertEqual(written["hard_negative_counts"]["edema_no_t2_myocardium_negative_voxels"], 0)


if __name__ == "__main__":
    unittest.main()
