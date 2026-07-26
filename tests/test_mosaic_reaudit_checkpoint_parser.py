from __future__ import annotations

from pathlib import Path

import torch

from scripts.evaluation.reaudit_mosaic_fold0_fairness import safe_checkpoint_metadata, select_pathology_checkpoint


def test_safe_checkpoint_metadata_reads_epoch_without_unpickle(tmp_path: Path) -> None:
    ckpt = tmp_path / "best.pt"
    torch.save({"model_state": {"w": torch.zeros(1)}, "epoch": 190, "scar_dice": 0.5164}, ckpt)

    meta = safe_checkpoint_metadata(ckpt)

    assert meta["exists"] is True
    assert meta["epoch"] == 190
    assert meta["scar_dice"] == 0.5164
    assert len(meta["sha256"]) == 64


def test_select_pathology_checkpoint_prefers_best_scar(tmp_path: Path) -> None:
    fine_dir = tmp_path / "fine_scar"
    fine_dir.mkdir()
    (fine_dir / "best_pathology.pt").write_bytes(b"pathology")
    (fine_dir / "best_scar.pt").write_bytes(b"scar")

    selected, reason = select_pathology_checkpoint(fine_dir)

    assert selected == fine_dir / "best_scar.pt"
    assert reason == "upstream_prefers_best_scar_when_present"
