import json

import pytest

from scripts.training.care_ase.run_care_ase_r2_chunk import verify_checkpoint_verified_receipt


def test_resume_requires_verified_checkpoint_receipt(tmp_path):
    ckpt = tmp_path / "checkpoint_step00001.pt"
    ckpt.write_bytes(b"checkpoint")
    with pytest.raises(RuntimeError, match="verified receipt"):
        verify_checkpoint_verified_receipt(ckpt, {"fold": 1, "global_optimizer_step": 1})


def test_verified_checkpoint_receipt_must_match_sha(tmp_path, monkeypatch):
    ckpt = tmp_path / "checkpoint_step00001.pt"
    ckpt.write_bytes(b"checkpoint")
    verified = ckpt.with_suffix(ckpt.suffix + ".verified.json")
    verified.write_text(
        json.dumps(
            {
                "status": "PASS",
                "checkpoint_sha256": "wrong",
                "fold": 1,
                "global_step": 1,
                "contract_sha256": "contract",
                "full_reload_logit_parity": "PASS",
                "verification_rng_transparency": "PASS",
            }
        ),
        encoding="utf-8",
    )
    with pytest.raises(RuntimeError, match="checkpoint_sha256"):
        verify_checkpoint_verified_receipt(
            ckpt,
            {"fold": 1, "global_optimizer_step": 1, "effective_contract_sha256": "contract"},
        )
