from __future__ import annotations

from pathlib import Path

import numpy as np

from scripts.evaluation.care_myopath_full_volume_closure import full_volume_closure as fvc


def test_binary_metrics_empty_and_overlap():
    pred = np.zeros((3, 4, 5), dtype=bool)
    gt = np.zeros_like(pred)
    assert fvc.binary_dice(pred, gt) == 1.0
    assert fvc.hausdorff(pred, gt, (1.0, 1.0, 1.0), 95) == 0.0
    pred[1, 1, 1] = True
    gt[1, 1, 1] = True
    assert fvc.binary_dice(pred, gt) == 1.0
    assert fvc.precision(pred, gt) == 1.0
    assert fvc.recall(pred, gt) == 1.0


def test_lesion_and_remote_fp_metrics_are_3d():
    gt = np.zeros((8, 8, 8), dtype=bool)
    pred = np.zeros_like(gt)
    gt[1:3, 1:3, 1:3] = True
    pred[1, 1, 1] = True
    pred[7, 7, 7] = True
    lesion_recall, small_recall, n_lesions, n_small = fvc.lesion_recalls(pred, gt, (1.0, 1.0, 1.0))
    assert lesion_recall == 1.0
    assert n_lesions == 1
    assert n_small == 1
    assert small_recall == 1.0
    fp = fvc.fp_metrics(pred, gt, np.zeros_like(gt), (1.0, 1.0, 1.0))
    assert fp["remote_fp_count"] == 0


def test_known_bad_matrix_names():
    report = fvc.known_bad_report()
    names = {row["case"] for row in report["cases"]}
    assert "patch_proxy_as_full_volume" in names
    assert "checkpoint_sha_mismatch" in names
    assert "pending_job_as_completion" in names
    assert all(row["rejected"] for row in report["cases"])


def test_validate_rejects_missing_packet(tmp_path: Path):
    report = fvc.validate(tmp_path, write=False)
    assert report["status"] == "FAIL"
    assert any(err.startswith("missing_required_output") for err in report["errors"])
