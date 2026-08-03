from src.care_myocardium.training.care_ase_trainer import checkpoint_receipt


def test_checkpoint_receipt_exposes_last_completed_step_for_resume_credit(tmp_path):
    payload = {
        "schema_version": 4,
        "global_optimizer_step": 1000,
        "accumulation_microbatch_cursor": 0,
        "stage_id": "A",
        "stage_step": 1000,
        "complete_center_cursor": 0,
        "complete_pathology_cursor": 0,
        "scar_focus_cursor": 0,
        "edema_focus_cursor": 0,
        "extent_wall_ramp_value": 1.0,
        "next_batch_descriptor_sha256": "next",
        "last_completed_optimizer_step": 1000,
    }
    path = tmp_path / "checkpoint_step01000.pt"
    path.write_bytes(b"x")
    receipt = checkpoint_receipt(path, payload)
    assert receipt["global_optimizer_step"] == 1000
