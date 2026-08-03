import csv
import json
import subprocess
from pathlib import Path

import torch

from scripts.evaluation.care_ase.select_care_ase_r2_inner_checkpoint import select_checkpoint
from src.care_myocardium.inference.care_ase_r2_full_volume import (
    gaussian_importance_map,
    mirror_axis_combinations,
    predict_care_ase_r2_full_volume_logits,
)
from src.care_myocardium.training.care_ase_runtime import _slice_profile_by_source_z, source_z_mapping
from src.care_myocardium.training.care_ase_sampler import CAREASEDeterministicSampler


def test_v9_executor_plan_validates_with_contract_command():
    result = subprocess.run(
        [
            "./envs/env_CARE/bin/python",
            "scripts/ops/validate_executor_plan.py",
            "--plan",
            "prompts/tasks/20260803_care_ase_r2_last_hotfix_v9_executor_plan.yaml",
        ],
        cwd=Path(__file__).resolve().parents[2],
        text=True,
        capture_output=True,
        check=False,
    )
    assert result.returncode == 0, result.stderr


def test_full_volume_gaussian_importance_nonuniform_and_positive():
    weight = gaussian_importance_map((5, 7, 7))
    assert float(weight.min()) > 0.0
    assert float(weight.max()) > float(weight[..., 0, 0, 0])


class _MirrorAwareModel(torch.nn.Module):
    scar_area_reference = torch.tensor(0.2)
    edema_area_reference = torch.tensor(0.2)

    def extent_wall_ramp(self, _global_step):
        return 0.0

    def _sigmoid_logit_center(self, value, _center):
        return value

    def forward(self, image, availability, *, global_step, disable_extent_wall):
        assert disable_extent_wall is True
        logits = torch.zeros((image.shape[0], 6, *image.shape[-3:]), device=image.device)
        logits[:, 5:6] = image[:, :1]
        component = torch.zeros((image.shape[0], 1, *image.shape[-3:]), device=image.device)
        return {
            "final_logits": logits,
            "p_wall_union": torch.ones_like(component),
            "components": {
                "scar_extent_presence": component,
                "scar_extent_area": component,
                "edema_extent_presence": component,
                "edema_extent_area": component,
            },
        }


def test_full_volume_mirror_inverse_all_outputs():
    model = _MirrorAwareModel()
    image = torch.zeros((1, 3, 4, 4, 4), dtype=torch.float32)
    availability = torch.tensor([[1.0, 1.0, 1.0]], dtype=torch.float32)
    no_tta = predict_care_ase_r2_full_volume_logits(
        model, image, availability, patch_size=(4, 4, 4), use_gaussian=True, use_mirroring=False
    )
    tta = predict_care_ase_r2_full_volume_logits(
        model, image, availability, patch_size=(4, 4, 4), use_gaussian=True, use_mirroring=True, allowed_mirror_axes=(0, 1, 2)
    )
    assert mirror_axis_combinations((0, 1, 2))
    assert torch.allclose(no_tta, tta, atol=1e-6)


def test_source_z_profile_reverses_with_z_mirror():
    profile = torch.arange(10, dtype=torch.float32).numpy()
    source_z, valid = source_z_mapping(origin_z=2, output_z=4, full_z=10, z_mirrored=True)
    assert source_z == [5, 4, 3, 2]
    mapped = _slice_profile_by_source_z(profile, source_z, valid)
    assert mapped.tolist() == [5.0, 4.0, 3.0, 2.0]


def test_inner_monitor_imports_canonical_inference_and_rejects_old_root():
    text = Path("scripts/evaluation/care_ase/monitor_care_ase_r2_inner_trend.py").read_text(encoding="utf-8")
    assert "predict_care_ase_r2_full_volume_logits" in text
    assert "sliding_window_logits" not in text
    assert "20260803_care_ase_r2_full_fidelity_execution" not in text


def _packet(path: Path, step: int, scar: float, edema: float) -> None:
    payload = {
        "status": "PASS",
        "monitor_type": "ASYNC_INNER_TREND_ONLY",
        "checkpoint_step": step,
        "checkpoint_sha256": f"sha-{step}",
        "summary": {
            "scar_dice_mean": scar,
            "pure_edema_dice_mean": edema,
            "help_harm_vs_nnunet": {"scar": {"help": 0, "harm": 0}, "pure_edema": {"help": 0, "harm": 0}},
            "help_harm_vs_mosaic": {"scar": {"help": 0, "harm": 0}, "pure_edema": {"help": 0, "harm": 0}},
        },
    }
    path.write_text(json.dumps(payload), encoding="utf-8")


def test_fixed_checkpoint_selector_formula(tmp_path):
    paths = []
    for step in (4000, 6000, 8000, 10000, 12000, 14000):
        path = tmp_path / f"step{step}.json"
        _packet(path, step, 0.5, 0.5 + step / 100000.0)
        paths.append(path)
    selected = select_checkpoint(paths)
    assert selected["status"] == "PASS"
    assert selected["selected_checkpoint_step"] == 14000


def test_stage_c_case_group_semantics(monkeypatch):
    import src.care_myocardium.training.care_ase_sampler as sampler_module

    monkeypatch.setattr(
        sampler_module,
        "_load_hard_negative_manifest",
        lambda _repo_root, _fold: {
            "source": "canonical_patient_held_out_stock_nnunet_oof_only",
            "task_key": "20260803_care_ase_r2_last_hotfix_v9",
            "v9_manifest": True,
            "manifest_path": "unit-test-v9-manifest.json",
            "manifest_sha256": "unit-test",
            "cases": {},
        },
    )
    sampler = CAREASEDeterministicSampler(Path.cwd(), 1)
    bundle = sampler.descriptor_bundle_for_step(10000, microbatch_count=4)
    assert bundle.optimizer_step_stratum["case_group"] == "complete"
    assert bundle.optimizer_step_stratum["center_group"] in {"complete_centerB", "complete_centerC"}
    assert all(desc.case_group == "complete" for desc in bundle.micro_descriptors)
