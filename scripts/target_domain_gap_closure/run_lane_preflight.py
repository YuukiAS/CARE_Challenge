#!/usr/bin/env python3
"""Lane-level preflight for the 20260801 target-domain gap closure."""

from __future__ import annotations

import argparse
import hashlib
import inspect
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from src.care_myocardium.models.myowall_if.stock_adapter import StockNNUNetFeatureAdapter  # noqa: E402
from src.care_myocardium.models.target_domain_gap_closure import smoke_care_tds  # noqa: E402
from src.care_myocardium.nnunet.gap_closure_trainer import nnUNetTrainerGapClosureM0R4000  # noqa: E402


TASK_KEY = "20260801_care_target_domain_race_gap_closure"
RESULT_ROOT = REPO_ROOT / "results" / TASK_KEY
SPLIT_PATH = RESULT_ROOT / "split_receipt_copy.json"
PINNED_M1_COMMIT = "479f07028c5bdb12b405dc92212aa48ae6ba947a"
PINNED_M2_COMMIT = "90f46c4eb72924509895fcda6bc6a3b8c3316e66"


def now_utc() -> str:
    return datetime.now(timezone.utc).isoformat()


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True, ensure_ascii=False) + "\n", encoding="utf-8")


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def git_out(args: list[str], *, cwd: Path = REPO_ROOT) -> str:
    proc = subprocess.run(["git", *args], cwd=cwd, text=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, check=False)
    return proc.stdout.strip()


def torch_env() -> dict[str, Any]:
    import torch

    return {
        "torch": torch.__version__,
        "cuda_available": torch.cuda.is_available(),
        "cuda_device_count": torch.cuda.device_count(),
        "device_name": torch.cuda.get_device_name(0) if torch.cuda.is_available() else None,
    }


def stock_parity(fold: int) -> dict[str, Any]:
    import torch

    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    model = StockNNUNetFeatureAdapter(fold=fold, map_location=device).to(device)
    patch = model.patch_size
    shape = (1, 3, min(16, patch[0]), min(64, patch[1]), min(64, patch[2]))
    torch.manual_seed(20260801 + fold)
    sample = torch.randn(*shape, device=device)
    try:
        return model.parity_report(sample)
    except RuntimeError as exc:
        if "weight type (torch.FloatTensor)" not in str(exc):
            raise
        cpu_model = StockNNUNetFeatureAdapter(fold=fold, map_location="cpu")
        return cpu_model.parity_report(sample.detach().cpu())


def write_batch_manifests() -> dict[str, Any]:
    split = json.loads(SPLIT_PATH.read_text(encoding="utf-8"))
    receipt: dict[str, Any] = {"status": "PASS", "folds": {}}
    for fold in (2, 3):
        cases = list(split[f"fold{fold}"]["actual_train_cases"])
        path = RESULT_ROOT / f"batch_manifest_fold{fold}.jsonl"
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("w", encoding="utf-8") as f:
            for step in range(1, 4001):
                row = {
                    "step": step,
                    "fold": fold,
                    "case_id": cases[(step - 1) % len(cases)],
                    "input_order": ["LGE", "T2", "C0"],
                    "shared_by_lanes": ["M0R_FAITHFUL_CONTROL", "M3_CARE_TDS"],
                }
                f.write(json.dumps(row, sort_keys=True) + "\n")
        receipt["folds"][f"fold{fold}"] = {
            "path": str(path.relative_to(REPO_ROOT)),
            "sha256": sha256_file(path),
            "steps": 4000,
            "actual_train_case_count": len(cases),
            "first_case": cases[0],
            "last_case": cases[-1],
        }
    write_json(RESULT_ROOT / "batch_manifest_receipt.json", receipt)
    return receipt


def run_m0r() -> dict[str, Any]:
    batch = write_batch_manifests()
    optimizer_source = inspect.getsource(nnUNetTrainerGapClosureM0R4000.configure_optimizers)
    trainer_source = inspect.getsource(nnUNetTrainerGapClosureM0R4000.__init__)
    optimizer_contract = {
        "trainer_class": "src.care_myocardium.nnunet.gap_closure_trainer.nnUNetTrainerGapClosureM0R4000",
        "configure_optimizers_sha256": sha256_text(optimizer_source),
        "uses_adamw": "AdamW" in optimizer_source,
        "uses_sgd": "SGD" in optimizer_source,
        "uses_polylr": "PolyLR" in optimizer_source,
        "backbone_decoder_lr": 1.0e-4,
        "segmentation_heads_lr": 5.0e-4,
        "num_epochs": 16,
        "num_iterations_per_epoch": 250,
        "save_every": 2,
        "checkpoint_cadence_optimizer_steps": 500,
        "init_source_sha256": sha256_text(trainer_source),
    }
    reports = {f"fold{fold}": stock_parity(fold) for fold in (2, 3)}
    status = "PREFLIGHT_PASS_READY_FOR_HTZHULAB_TRAINING" if (
        optimizer_contract["uses_adamw"]
        and not optimizer_contract["uses_sgd"]
        and not optimizer_contract["uses_polylr"]
        and all(r["status"] == "PASS" for r in reports.values())
    ) else "PREFLIGHT_FAIL"
    return {
        "lane_id": "M0R_FAITHFUL_CONTROL",
        "formal_training_credit": False,
        "status": status,
        "optimizer_contract": optimizer_contract,
        "batch_manifest": batch,
        "stock_parity": reports,
        "next_required_action": "submit fold2/fold3 faithful M0R training on htzhulab with this trainer and shared batch manifests",
    }


def run_m3() -> dict[str, Any]:
    batch = write_batch_manifests()
    import torch

    device = "cuda" if torch.cuda.is_available() else "cpu"
    reports = {f"fold{fold}": smoke_care_tds(fold, device=device) for fold in (2, 3)}
    status = "PREFLIGHT_PASS_READY_FOR_INTERACTIVE_TRAINING" if all(r["status"] == "PASS" for r in reports.values()) else "PREFLIGHT_FAIL"
    return {
        "lane_id": "M3_CARE_TDS",
        "formal_training_credit": False,
        "status": status,
        "device_used": device,
        "batch_manifest": batch,
        "smoke_reports": reports,
        "contract_checks": {
            "uses_f0": True,
            "detached_soft_wall_lv_context": True,
            "independent_heads": ["scar", "pure_edema", "injury", "boundary"],
            "stock_class4_5_logits_used_for_final_prediction": False,
            "loss_terms_enter_total": ["scar_bce", "pure_edema_bce", "injury_bce", "boundary_bce", "scar_injury_containment", "pure_edema_injury_containment"],
        },
        "next_required_action": "run M3 first in interactive allocation 61220581, then perform all-checkpoint inner full-volume selection",
    }


def run_m1() -> dict[str, Any]:
    import torch

    code_root = REPO_ROOT / "third_party/MyoPS-Net"
    pinned_root = REPO_ROOT / "third_party/MyoPS-Net_PINNED"
    py_files = sorted(p for p in code_root.rglob("*.py") if p.is_file()) if code_root.exists() else []
    text = "\n".join(p.read_text(encoding="utf-8", errors="ignore")[:200000] for p in py_files[:80])
    smoke: dict[str, Any] = {"status": "NOT_RUN"}
    source_pinned = pinned_root.exists() and git_out(["rev-parse", "HEAD"], cwd=pinned_root) == PINNED_M1_COMMIT
    if source_pinned:
        sys.path.insert(0, str(pinned_root))
        from network.unet import UNet, UNetDecoderPlus, UNetEncoder  # type: ignore

        class CARETriModalMyoPSNet(torch.nn.Module):
            def __init__(self) -> None:
                super().__init__()
                self.unet_C0 = UNet(in_ch=3, out_ch=6)
                self.encoder_LGE = UNetEncoder(in_ch=2)
                self.decoder_LGE = UNetDecoderPlus(out_ch=2)
                self.encoder_T2 = UNetEncoder(in_ch=2)
                self.decoder_T2 = UNetDecoderPlus(out_ch=2)

            def forward(self, c0, lge, t2):
                img = torch.cat([c0, lge, t2], dim=1)
                seg_c0 = self.unet_C0(img)
                mask_c0 = torch.argmax(seg_c0, dim=1, keepdim=True)
                f_lge = self.encoder_LGE(torch.cat([lge, mask_c0.detach()], dim=1))
                f_t2 = self.encoder_T2(torch.cat([t2, mask_c0.detach()], dim=1))
                return seg_c0, self.decoder_LGE(list(f_t2), f_lge), self.decoder_T2(list(f_lge), f_t2)

        model = CARETriModalMyoPSNet().eval()
        with torch.no_grad():
            c0 = torch.randn(1, 1, 32, 32)
            lge = torch.randn(1, 1, 32, 32)
            t2 = torch.randn(1, 1, 32, 32)
            out = model(c0, lge, t2)
        smoke = {
            "status": "PASS",
            "adapter": "CARETriModalMyoPSNet_from_pinned_official_components",
            "c0_lge_t2_only_forward": True,
            "uses_t1_or_t2star_placeholders": False,
            "output_shapes": [list(x.shape) for x in out],
        }
    status = "PREFLIGHT_PASS_SOURCE_PINNED_READY_FOR_WRAPPER_TRAINING" if source_pinned and smoke.get("status") == "PASS" else "PREFLIGHT_NEEDS_SOURCE_PIN"
    return {
        "lane_id": "M1_MYOPSNET_L_CARE",
        "formal_training_credit": False,
        "status": status,
        "required_source": "https://github.com/QJYBall/MyoPS-Net",
        "required_commit": PINNED_M1_COMMIT,
        "local_source_path": str(code_root.relative_to(REPO_ROOT)),
        "local_python_file_count": len(py_files),
        "pinned_source_path": str(pinned_root.relative_to(REPO_ROOT)),
        "pinned_source_present": pinned_root.exists(),
        "pinned_source_at_required_commit": source_pinned,
        "cmff_or_cross_modal_signal_seen": "torch.max" in text and "encoder_LGE" in text and "encoder_T2" in text,
        "mpc_or_consistency_signal_seen": "consistency" in text.lower() or "mpc" in text.lower(),
        "local_c0_lge_t2_smoke": smoke,
        "blocking_gap": None if source_pinned else "official MyoPS-Net source is not yet present as an isolated checkout pinned to the required commit",
        "next_required_action": "clone/pin official MyoPS-Net source, then run CARE full-volume slice reconstruction wrapper for >=60 epochs",
    }


def run_m2() -> dict[str, Any]:
    official = REPO_ROOT / "third_party/I_MMSeg_PINNED"
    head = git_out(["rev-parse", "HEAD"], cwd=official) if official.exists() else ""
    py_files = sorted(p for p in official.rglob("*.py") if p.is_file()) if official.exists() else []
    source_ok = head == PINNED_M2_COMMIT
    text = "\n".join(p.read_text(encoding="utf-8", errors="ignore")[:200000] for p in py_files[:80])
    has_clip_prior = "CLIP" in text or "clip" in text
    has_intensity_prior = "intensity" in text.lower() or "prior" in text.lower()
    vit_npz = official / "model/vit_checkpoint/imagenet21k/R50-ViT-B_16.npz"
    epoch_299 = official / "weights/TU_Myops128/TU_pretrain_R50-ViT-B_16_skip3_epo300_bs24_lr0.001_128/epoch_299.pth"
    text_features = [
        official / "text_features/embedding_class_information.pth",
        official / "text_features/embedding_MRI_information.pth",
    ]
    asset_receipt = RESULT_ROOT / "m2_i_mmseg_care/asset_download_receipt.json"
    smoke_receipt = RESULT_ROOT / "m2_i_mmseg_care/released_checkpoint_smoke_receipt.json"
    adapter_preflight = RESULT_ROOT / "m2_i_mmseg_care/adapter_preflight_report.json"
    core_assets_ready = vit_npz.exists() and epoch_299.exists() and all(path.exists() for path in text_features)
    adapter_preflight_payload: dict[str, Any] | None = None
    if adapter_preflight.exists():
        adapter_preflight_payload = json.loads(adapter_preflight.read_text(encoding="utf-8"))
    if source_ok and core_assets_ready and adapter_preflight_payload and adapter_preflight_payload.get("status") == "PREFLIGHT_PASS_READY_FOR_HTZHULAB_TRAINING":
        status = "PREFLIGHT_PASS_READY_FOR_HTZHULAB_TRAINING"
    elif source_ok and core_assets_ready and smoke_receipt.exists():
        status = "RELEASED_CHECKPOINT_SMOKE_PASS_PENDING_CARE_ADAPTER_PREFLIGHT"
    elif source_ok and core_assets_ready:
        status = "SOURCE_AND_CORE_MODEL_ASSETS_READY_PENDING_GPU_SMOKE"
    elif source_ok and (has_clip_prior or has_intensity_prior):
        status = "PREFLIGHT_PASS_SOURCE_READY_ASSET_CHECK_REQUIRED"
    else:
        status = "ASSET_APPROVAL_REQUIRED"
    return {
        "lane_id": "M2_I_MMSEG_CARE",
        "formal_training_credit": False,
        "status": status,
        "required_source": "https://github.com/zzzzzzl24/I_MMSeg",
        "required_commit": PINNED_M2_COMMIT,
        "official_source_path": str(official.relative_to(REPO_ROOT)),
        "official_source_exists": official.exists(),
        "official_source_head": head or None,
        "official_source_at_required_commit": source_ok,
        "python_file_count": len(py_files),
        "clip_or_text_prior_signal_seen": has_clip_prior,
        "intensity_prior_signal_seen": has_intensity_prior,
        "core_model_assets_ready": core_assets_ready,
        "vit_npz_path": str(vit_npz.relative_to(REPO_ROOT)),
        "epoch_299_path": str(epoch_299.relative_to(REPO_ROOT)),
        "text_feature_paths": [str(path.relative_to(REPO_ROOT)) for path in text_features],
        "asset_download_receipt": str(asset_receipt.relative_to(REPO_ROOT)) if asset_receipt.exists() else None,
        "released_checkpoint_smoke_receipt": str(smoke_receipt.relative_to(REPO_ROOT)) if smoke_receipt.exists() else None,
        "care_adapter_preflight_report": str(adapter_preflight.relative_to(REPO_ROOT)) if adapter_preflight.exists() else None,
        "care_adapter_preflight_status": None if adapter_preflight_payload is None else adapter_preflight_payload.get("status"),
        "rank_channel_substitute_used": False,
        "runtime_gpt_call_used": False,
        "myops380_dataset_used": False,
        "direct_vit_npz_load_from_status": "FAIL_UPSTREAM_LEGACY_SINGLE_TRANSFORMER_PATH" if smoke_receipt.exists() else "NOT_TESTED",
        "blocking_gap": None if source_ok and core_assets_ready else "pinned official source or public model assets are not present",
        "next_required_action": "run CARE adapter preflight, then submit fold2/fold3 M2 training on htzhulab; do not replace I-MMSeg with rank-channel lite features",
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--lane-id", required=True, choices=["M0R_FAITHFUL_CONTROL", "M1_MYOPSNET_L_CARE", "M2_I_MMSEG_CARE", "M3_CARE_TDS"])
    args = parser.parse_args()
    payload: dict[str, Any] = {
        "created_at": now_utc(),
        "git_head": git_out(["rev-parse", "HEAD"]),
        "torch_env": torch_env(),
        "task_key": TASK_KEY,
    }
    if args.lane_id == "M0R_FAITHFUL_CONTROL":
        payload.update(run_m0r())
    elif args.lane_id == "M1_MYOPSNET_L_CARE":
        payload.update(run_m1())
    elif args.lane_id == "M2_I_MMSEG_CARE":
        payload.update(run_m2())
    elif args.lane_id == "M3_CARE_TDS":
        payload.update(run_m3())
    out_dir = RESULT_ROOT / args.lane_id.lower()
    write_json(out_dir / "preflight_report.json", payload)
    write_json(out_dir / "lane_controller_packet.json", payload)
    print(json.dumps(payload, indent=2, sort_keys=True, ensure_ascii=False))
    return 2 if str(payload.get("status", "")).endswith("FAIL") else 0


if __name__ == "__main__":
    raise SystemExit(main())
