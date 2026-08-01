#!/usr/bin/env python3
"""Lane-level preflight for the CARE target-domain pathology race.

This is deliberately strict: it records what is ready and what is not ready for
formal training. It must not convert a preflight into formal training credit.
"""

from __future__ import annotations

import argparse
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

TASK_KEY = "20260801_care_target_domain_pathology_specialist_race"
RESULT_ROOT = REPO_ROOT / "results" / TASK_KEY


def now_utc() -> str:
    return datetime.now(timezone.utc).isoformat()


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True, ensure_ascii=False) + "\n", encoding="utf-8")


def git_out(args: list[str]) -> str:
    proc = subprocess.run(["git", *args], cwd=REPO_ROOT, text=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, check=False)
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
        # The shared adapter builds the reference network on CPU. Keep this
        # preflight moving by doing the parity check on CPU; this is slower but
        # preserves the exact FP32 comparison semantics.
        cpu_model = StockNNUNetFeatureAdapter(fold=fold, map_location="cpu")
        cpu_sample = sample.detach().cpu()
        return cpu_model.parity_report(cpu_sample)


def run_m0() -> dict[str, Any]:
    reports = {f"fold{fold}": stock_parity(fold) for fold in (2, 3)}
    status = "PREFLIGHT_PASS_READY_FOR_FORMAL_TRAINING_SCRIPT" if all(r["status"] == "PASS" for r in reports.values()) else "PREFLIGHT_FAIL"
    return {
        "lane_id": "M0_TD_NNUNET",
        "formal_training_credit": False,
        "status": status,
        "stock_parity": reports,
        "next_required_action": "run complete-case target-domain nnUNet fine-tune for 4000 optimizer steps per fold",
    }


def run_m1() -> dict[str, Any]:
    code_root = REPO_ROOT / "third_party/MyoPS-Net"
    code_files = sorted(p for p in code_root.rglob("*.py") if p.is_file()) if code_root.exists() else []
    text = "\n".join(p.read_text(encoding="utf-8", errors="ignore")[:200000] for p in code_files[:80])
    has_cmff = "CMFF" in text or "cmff" in text.lower() or "cross" in text.lower()
    has_mpc = "MPC" in text or "mpc" in text.lower() or "consistency" in text.lower()
    mentions_t1_t2star = any(token in text for token in ("T1", "T2*", "T2star", "t1", "t2star"))
    return {
        "lane_id": "M1_MYOPSNET_L_CARE",
        "formal_training_credit": False,
        "status": "PREFLIGHT_NEEDS_IMPLEMENTATION",
        "code_root_exists": code_root.exists(),
        "python_file_count": len(code_files),
        "cmff_or_cross_modal_signal_seen": has_cmff,
        "mpc_or_consistency_signal_seen": has_mpc,
        "t1_t2star_mentions_need_forward_audit": mentions_t1_t2star,
        "blocking_gap": "CARE-specific complete-trimodal MyoPS-Net-L full-volume training entrypoint is not yet implemented; old third_party code exists but cannot be used as formal race lane without wrapper repair.",
        "next_required_action": "implement C0/LGE/T2-only full-volume reconstruction and strict label4/label5 training wrapper before formal epochs",
    }


def run_m2() -> dict[str, Any]:
    official = REPO_ROOT / "third_party/I_MMSeg_PINNED"
    return {
        "lane_id": "M2_I_MMSEG_CARE",
        "formal_training_credit": False,
        "status": "LANE_BLOCKED_EXTERNAL_ASSET",
        "official_source_path": str(official.relative_to(REPO_ROOT)),
        "official_source_exists": official.exists(),
        "blocking_gap": "Pinned official I_MMSeg source/assets are not present in the repository. The contract forbids replacing this lane with hand-crafted rank channels.",
        "next_required_action": "download/pin official source, license, commit and public assets before faithful forward/training",
    }


def run_m3() -> dict[str, Any]:
    reports = {f"fold{fold}": stock_parity(fold) for fold in (2, 3)}
    status = "PREFLIGHT_NEEDS_IMPLEMENTATION"
    return {
        "lane_id": "M3_CARE_TDS",
        "formal_training_credit": False,
        "status": status,
        "stock_parity": reports,
        "blocking_gap": "Independent scar/pure-edema/injury/boundary heads and direct-gradient losses are not yet implemented as a formal lane.",
        "next_required_action": "implement CARE-TDS heads/losses and matched M0 batch descriptor before 4000-step formal training",
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--lane-id", required=True)
    args = parser.parse_args()
    payload: dict[str, Any] = {
        "created_at": now_utc(),
        "git_head": git_out(["rev-parse", "HEAD"]),
        "torch_env": torch_env(),
    }
    if args.lane_id == "M0_TD_NNUNET":
        payload.update(run_m0())
    elif args.lane_id == "M1_MYOPSNET_L_CARE":
        payload.update(run_m1())
    elif args.lane_id == "M2_I_MMSEG_CARE":
        payload.update(run_m2())
    elif args.lane_id == "M3_CARE_TDS":
        payload.update(run_m3())
    else:
        raise SystemExit(f"unknown lane id: {args.lane_id}")
    out_dir = RESULT_ROOT / args.lane_id.lower()
    write_json(out_dir / "preflight_report.json", payload)
    write_json(out_dir / "lane_controller_packet.json", payload)
    print(json.dumps(payload, indent=2, sort_keys=True))
    return 0 if not str(payload.get("status", "")).startswith("PREFLIGHT_FAIL") else 2


if __name__ == "__main__":
    raise SystemExit(main())
