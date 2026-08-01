#!/usr/bin/env python3
from __future__ import annotations

import gzip
import hashlib
import json
import tarfile
from pathlib import Path

CARE_ROOT = Path(__file__).resolve().parents[2]
TASK_KEY = "20260801_care_test_docker_final_model_freeze_and_bundle"
RESULT_DIR = CARE_ROOT / "results" / TASK_KEY
RUNTIME = Path("/users/a/e/aereinh/.tmp/codex-CARE/20260801_care_test_docker_cross_machine")
READY_MARKER = RUNTIME / "transfer/SERVER_BUNDLE_READY.json"


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def load_json(path: Path):
    return json.loads(path.read_text())


def add(errors: list[str], condition: bool, message: str) -> None:
    if not condition:
        errors.append(message)


def main() -> int:
    errors: list[str] = []
    required = [
        "controller_context.json",
        "controller_ledger.csv",
        "final_submission_model_ledger.md",
        "final_submission_model_contract.json",
        "production_asset_manifest.json",
        "fresh_mosaic_cine_15case_manifest.json",
        "host_sentinel_manifest.json",
        "source_intervention_receipt.json",
        "transfer_bundle_receipt.json",
        "finalizer_state.json",
        "mapper_report_final.md",
        "completion_check.md",
        "controller_report.md",
        "MANIFEST.md",
        "organizer_email_draft_not_sent.md",
        "notification_brief.json",
    ]
    for name in required:
        add(errors, (RESULT_DIR / name).exists(), f"missing result file: {name}")

    if not errors:
        contract = load_json(RESULT_DIR / "final_submission_model_contract.json")
        assets = load_json(RESULT_DIR / "production_asset_manifest.json")
        cine = load_json(RESULT_DIR / "fresh_mosaic_cine_15case_manifest.json")
        sentinels = load_json(RESULT_DIR / "host_sentinel_manifest.json")
        intervention = load_json(RESULT_DIR / "source_intervention_receipt.json")
        transfer = load_json(RESULT_DIR / "transfer_bundle_receipt.json")
        finalizer = load_json(RESULT_DIR / "finalizer_state.json")

        add(errors, contract.get("frozen_by_planner") is True, "contract does not record Planner freeze")
        add(errors, contract.get("model_selection_closed") is True, "contract does not close model selection")
        add(errors, contract.get("historical_0_6691_lineage_status") == "UNRESOLVED_NOT_CLAIMED", "historical lineage status is not unresolved/not claimed")
        add(errors, contract.get("server_gpu_bitwise_repeat_required") is False, "server GPU bitwise repeat was reintroduced")
        add(errors, contract.get("known_gpu_float_parallel_delta", {}).get("changed_voxels") == 13, "13-voxel GPU delta not recorded")
        add(errors, contract.get("known_gpu_float_parallel_delta", {}).get("blocking") is False, "13-voxel GPU delta is marked blocking")

        add(errors, assets.get("all_required_assets_exist") is True, "required asset missing")
        add(errors, assets.get("myops_forbidden_mosaic_edema_included") is False, "MyoPS forbidden MoSAIC edema marked included")
        for item in assets.get("assets", []):
            p = Path(item["path"]) if item["path"].startswith("/") else CARE_ROOT / item["path"]
            add(errors, p.exists(), f"asset missing on disk: {item['path']}")
            if p.exists():
                add(errors, sha256(p) == item["sha256"], f"asset sha mismatch: {item['path']}")

        myops_ctx = CARE_ROOT / "docker/CARE2026_Myocardium/MyoPS"
        add(errors, not (myops_ctx / "vendor/myops/inference/edema_predict.py").exists(), "MyoPS context includes edema_predict.py")
        add(errors, not (myops_ctx / "vendor/myops/models/edema_net.py").exists(), "MyoPS context includes edema_net.py")
        add(errors, not (myops_ctx / "models/mosaic/myops/coarse_edema.pt").exists(), "MyoPS context contains coarse_edema.pt")
        add(errors, not (myops_ctx / "models/mosaic/myops/edema.pt").exists(), "MyoPS context contains edema.pt")

        add(errors, cine.get("case_count") == 15, f"MoSAIC Cine replay not 15/15: {cine.get('case_count')}")
        add(errors, cine.get("all_label_schema_ok") is True, "Cine label schema failed")
        add(errors, sentinels.get("host_smoke_status") == "PASS", "host sentinel smoke failed")
        add(errors, len([r for r in sentinels.get("records", []) if r.get("track") == "myops"]) == 3, "MyoPS sentinel count is not 3")
        add(errors, len([r for r in sentinels.get("records", []) if r.get("track") == "cinemyops"]) == 3, "Cine sentinel count is not 3")
        add(errors, intervention.get("all_pass") is True, "source intervention failed")
        for case in intervention.get("cases", []):
            add(errors, case.get("disable_mosaic_scar_changed_voxels", 0) > 0, f"{case.get('case_id')}: scar intervention did not change output")
            add(errors, case.get("disable_nnunet_edema_changed_voxels", 0) > 0, f"{case.get('case_id')}: nnU-Net edema intervention did not change output")
            add(errors, case.get("enable_mosaic_edema_changed_voxels", -1) == 0, f"{case.get('case_id')}: MoSAIC edema toggle changed output")

        add(errors, transfer.get("bundle_ready") is True, "transfer bundle not ready")
        add(errors, transfer.get("myops_forbidden_mosaic_edema_present") is False, "transfer bundle contains forbidden MyoPS edema asset")
        archive = Path(transfer.get("archive", {}).get("archive", ""))
        add(errors, archive.exists(), "transfer archive missing")
        if archive.exists():
            add(errors, sha256(archive) == transfer.get("archive", {}).get("sha256"), "transfer archive sha mismatch")
            with gzip.open(archive, "rb") as gz:
                with tarfile.open(fileobj=gz, mode="r:") as tar:
                    names = tar.getnames()
            add(errors, any(n.endswith("contexts/MyoPS/predict.py") for n in names), "MyoPS source missing from tar")
            add(errors, any(n.endswith("contexts/CineMyoPS/predict.py") for n in names), "Cine source missing from tar")
            add(errors, not any("contexts/MyoPS/models/mosaic/myops/edema.pt" in n for n in names), "forbidden MyoPS edema.pt in tar")
            add(errors, not any("contexts/MyoPS/models/mosaic/myops/coarse_edema.pt" in n for n in names), "forbidden MyoPS coarse_edema.pt in tar")

        add(errors, READY_MARKER.exists(), "SERVER_BUNDLE_READY.json missing")
        if READY_MARKER.exists():
            ready = load_json(READY_MARKER)
            add(errors, ready.get("status") == "SERVER_BUNDLE_READY", "ready marker status is not SERVER_BUNDLE_READY")
            add(errors, ready.get("final_status") == "complete", "ready marker final_status is not complete")
        add(errors, finalizer.get("terminal_state") == "SERVER_BUNDLE_READY", "finalizer terminal state is not SERVER_BUNDLE_READY")

    report = {
        "task_key": TASK_KEY,
        "status": "PASS" if not errors else "FAIL",
        "terminal_state": "SERVER_BUNDLE_READY" if not errors else "VALIDATOR_FAILED",
        "errors": errors,
    }
    RESULT_DIR.mkdir(parents=True, exist_ok=True)
    (RESULT_DIR / "strict_validator_report.json").write_text(json.dumps(report, indent=2, sort_keys=True) + "\n")
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0 if not errors else 1


if __name__ == "__main__":
    raise SystemExit(main())
