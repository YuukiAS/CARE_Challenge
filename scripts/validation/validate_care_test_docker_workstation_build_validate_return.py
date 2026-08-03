#!/usr/bin/env python3
from __future__ import annotations

import csv
import hashlib
import json
import subprocess
from pathlib import Path

TASK = "20260803_care_test_docker_workstation_build_validate_return"
CARE_ROOT = Path(__file__).resolve().parents[2]
RESULTS = CARE_ROOT / "results" / TASK
RUNTIME = CARE_ROOT / ".local_runtime" / TASK
DOWNLOADS = RUNTIME / "downloads"
DIST = CARE_ROOT / "dist" / "20260803_care_test_docker_final"

CINE_SHA = "c02db56bd52d14d3b5bbda9d204a20b7e4c061fd5e6012ffa1cebc67fb92c136"
MYOPS_SHA = "638c1d54d1c75f3514f325695025c03bd8f43625c9f2877d72841db6ee2ac73b"
MYOPS_IMAGE = "sha256:52f8d872a51c482d488e3d2a14893958a6b1d6c8c91fffed9985ee330fcec911"
CINE_IMAGE = "sha256:5b10e6272f555c5ac54a23cca5d3819518bdb7d8d74d9e6a5496fea4991318ae"

KNOWN_BAD_COVERAGE = [
    "MyoPS image internal checkpoint check missing",
    "MyoPS image has fewer than five checkpoint_best.pth files",
    "Docker daemon unavailable or non-linux server",
    "image is not linux/amd64",
    "MyoPS only ran once",
    "Cine only ran once",
    "array equal but geometry differs",
    "MyoPS host equivalence above threshold without approved stale-expected override",
    "Cine archive SHA changed",
    "Cine archive was docker-saved or recompressed",
    "clean-load run was not rerun",
    "archive SHA checked without actual output checks",
    "final server dist missing an archive",
    "local and remote MyoPS SHA differ",
    "heavy artifacts staged to Git",
    "challenge/validation/netdisk upload attempted",
    "organizer email sent",
]


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def add(failures: list[str], condition: bool, message: str) -> None:
    if not condition:
        failures.append(message)


def check_required_files(failures: list[str]) -> None:
    required = [
        "controller_context.json",
        "bundle_verification.json",
        "docker_installation_receipt.json",
        "build_receipt.json",
        "image_asset_receipt.json",
        "myops_cpu_smoke_casewise.csv",
        "myops_cpu_determinism_casewise.csv",
        "myops_host_equivalence_casewise.csv",
        "myops_validation_summary.json",
        "cine_cpu_smoke_casewise.csv",
        "cine_cpu_determinism_casewise.csv",
        "cine_validation_summary.json",
        "clean_save_load_run_receipt.json",
        "docker_export_manifest.json",
        "remote_return_receipt.json",
        "controller_report.md",
        "completion_check.md",
        "MANIFEST.md",
    ]
    for name in required:
        add(failures, (RESULTS / name).is_file(), f"missing results file: {name}")
    for path in [
        DIST / "MyoPS-OrganAgent.tar.gz",
        DIST / "CineMyoPS-OrganAgent.tar.gz",
        DIST / "SHA256SUMS",
        RUNTIME / "WORKSTATION_VALIDATION_PACKET.tar.gz",
    ]:
        add(failures, path.is_file(), f"missing artifact: {path}")


def check_receipts(failures: list[str]) -> None:
    bundle = load_json(RESULTS / "bundle_verification.json")
    add(failures, bundle.get("status") == "PASS", "bundle verification did not PASS")
    check_names = {c["name"]: c["status"] for c in bundle.get("checks", [])}
    for key in [
        "dockerfile_copies_models",
        "five_checkpoint_best_match_manifest",
        "plans.json_matches_manifest",
        "dataset.json_matches_manifest",
        "no_mosaic_or_forbidden_myops_weights_source_or_config_in_context",
        "nnunet_source_dependency_evidence_present",
        "sentinel_inputs_complete",
        "expected_outputs_complete",
        "no_symlinks",
        "no_server_absolute_runtime_dependencies",
        "label_map_correct",
    ]:
        add(failures, check_names.get(key) == "PASS", f"bundle check failed: {key}")

    docker_install = load_json(RESULTS / "docker_installation_receipt.json")
    add(failures, docker_install.get("status") == "PASS", "Docker installation receipt did not PASS")
    add(failures, docker_install["checks"]["hello_world"]["returncode"] == 0, "hello-world did not pass")
    add(failures, "linux" in docker_install["checks"]["docker_info"]["output"], "Docker server is not linux")
    add(failures, "x86_64" in docker_install["checks"]["machine"]["output"], "machine is not x86_64")

    build = load_json(RESULTS / "build_receipt.json")
    add(failures, build.get("status") == "PASS", "MyoPS build did not PASS")
    add(failures, build.get("image_os_arch") == "linux/amd64", "MyoPS image is not linux/amd64")
    add(failures, build.get("image_id") == MYOPS_IMAGE, "MyoPS image ID mismatch")
    add(failures, build.get("checkpoint_internal_check") == "PASS", "MyoPS five-checkpoint image check missing")

    assets = load_json(RESULTS / "image_asset_receipt.json")
    add(failures, assets.get("status") == "PASS", "image asset receipt did not PASS")
    add(failures, assets["myops"]["os_arch"] == "linux/amd64", "MyoPS asset is not linux/amd64")
    add(failures, assets["myops"]["five_checkpoint_best_in_image"], "MyoPS image lacks five checkpoints")
    add(failures, assets["cinemyops"]["os_arch"] == "linux/amd64", "Cine asset is not linux/amd64")
    add(failures, bool(assets["cinemyops"]["entrypoint_json"]), "Cine ENTRYPOINT empty")
    add(failures, assets["cinemyops"]["archive_sha256"] == CINE_SHA, "Cine archive SHA changed")


def check_casewise(failures: list[str]) -> None:
    myops_smoke = read_csv(RESULTS / "myops_cpu_smoke_casewise.csv")
    myops_det = read_csv(RESULTS / "myops_cpu_determinism_casewise.csv")
    myops_eq = read_csv(RESULTS / "myops_host_equivalence_casewise.csv")
    cine_smoke = read_csv(RESULTS / "cine_cpu_smoke_casewise.csv")
    cine_det = read_csv(RESULTS / "cine_cpu_determinism_casewise.csv")

    for name, rows in [
        ("MyoPS smoke", myops_smoke),
        ("MyoPS determinism", myops_det),
        ("MyoPS host equivalence", myops_eq),
        ("Cine smoke", cine_smoke),
        ("Cine determinism", cine_det),
    ]:
        add(failures, len(rows) == 3, f"{name} did not cover 3 cases")

    for row in myops_smoke + cine_smoke:
        add(failures, row.get("status") == "PASS", f"smoke failed for {row.get('case_id')}")
        add(failures, row.get("label_subset_ok") in {"True", "true"}, f"labels outside allowed set: {row.get('case_id')}")
    for row in cine_smoke:
        add(failures, row.get("input_geometry_equal") in {"True", "true"}, f"Cine geometry failed: {row.get('case_id')}")
    for row in myops_det + cine_det:
        add(failures, row.get("array_equal") in {"True", "true"}, f"array determinism failed: {row.get('case_id')}")
        add(failures, row.get("geometry_equal") in {"True", "true"}, f"geometry determinism failed: {row.get('case_id')}")

    myops_summary = load_json(RESULTS / "myops_validation_summary.json")
    add(failures, myops_summary.get("status") == "PASS", "MyoPS summary did not PASS")
    add(failures, myops_summary.get("smoke_pass") is True, "MyoPS smoke summary false")
    add(failures, myops_summary.get("determinism_pass") is True, "MyoPS determinism summary false")
    raw_eq = myops_summary.get("raw_host_equivalence_pass")
    override = myops_summary.get("approved_stale_expected_microdifference_override")
    add(failures, myops_summary.get("host_equivalence_pass") is True, "MyoPS host equivalence summary false")
    if raw_eq is False:
        # This task has a user-approved continuation for a stale server expected-output
        # microdifference: Case1012 differs by exactly two voxels, while geometry and
        # Docker repeatability are exact. Do not silently generalize this exception.
        c1012 = next(row for row in myops_eq if row["case_id"] == "Case1012")
        add(failures, override is True, "raw MyoPS host equivalence failed without approved override")
        add(failures, c1012["geometry_equal"] in {"True", "true"}, "override geometry is not exact")
        add(failures, float(c1012["changed_voxel_fraction"]) <= 2 / 101120, "override changed fraction exceeds 2 voxels")
        add(failures, float(c1012["min_label_dice"]) >= 0.9994, "override Dice below recorded 2-voxel bound")
    else:
        for row in myops_eq:
            add(failures, row["geometry_equal"] in {"True", "true"}, f"MyoPS host geometry failed: {row['case_id']}")
            add(failures, float(row["changed_voxel_fraction"]) <= 1e-5, f"MyoPS changed fraction high: {row['case_id']}")
            add(failures, float(row["min_label_dice"]) >= 0.9999, f"MyoPS Dice low: {row['case_id']}")

    cine_summary = load_json(RESULTS / "cine_validation_summary.json")
    add(failures, cine_summary.get("status") == "PASS", "Cine summary did not PASS")
    add(failures, cine_summary.get("smoke_pass") is True, "Cine smoke summary false")
    add(failures, cine_summary.get("determinism_pass") is True, "Cine determinism summary false")
    add(failures, cine_summary.get("host_equivalence_claimed") is False, "Cine host equivalence was improperly claimed")


def check_archives_clean_remote(failures: list[str]) -> None:
    export = load_json(RESULTS / "docker_export_manifest.json")
    add(failures, export.get("status") == "PASS", "docker export manifest did not PASS")
    archives = export.get("archives", {})
    add(failures, archives["MyoPS-OrganAgent.tar.gz"]["sha256"] == MYOPS_SHA, "local MyoPS archive SHA mismatch")
    add(failures, archives["CineMyoPS-OrganAgent.tar.gz"]["sha256"] == CINE_SHA, "local Cine archive SHA mismatch")
    add(failures, sha256_file(DIST / "MyoPS-OrganAgent.tar.gz") == MYOPS_SHA, "MyoPS archive bytes mismatch")
    add(failures, sha256_file(DIST / "CineMyoPS-OrganAgent.tar.gz") == CINE_SHA, "Cine archive bytes mismatch")
    add(failures, sha256_file(DIST / "CineMyoPS-OrganAgent.tar.gz") == sha256_file(DOWNLOADS / "CineMyoPS-OrganAgent.tar.gz"), "Cine was not byte-preserved")

    clean = load_json(RESULTS / "clean_save_load_run_receipt.json")
    add(failures, clean.get("status") == "PASS", "clean save/load/run did not PASS")
    add(failures, clean.get("only_task_tags_removed") is True, "clean stage removed non-task tags or did not record tag-only removal")
    add(failures, clean.get("docker_prune_performed") is False, "docker prune was performed")
    add(failures, clean["myops_clean_output_match"]["array_equal"], "MyoPS clean output array mismatch")
    add(failures, clean["myops_clean_output_match"]["geometry_equal"], "MyoPS clean output geometry mismatch")
    add(failures, clean["cinemyops_clean_output_match"]["array_equal"], "Cine clean output array mismatch")
    add(failures, clean["cinemyops_clean_output_match"]["geometry_equal"], "Cine clean output geometry mismatch")

    remote = load_json(RESULTS / "remote_return_receipt.json")
    add(failures, remote.get("status") == "PASS", "remote return did not PASS")
    add(failures, remote.get("remote_myops_sha256") == MYOPS_SHA, "remote MyoPS SHA mismatch")
    add(failures, remote.get("remote_cine_sha256") == CINE_SHA, "remote Cine SHA mismatch")
    add(failures, remote.get("local_myops_sha256") == remote.get("remote_myops_sha256"), "local/remote MyoPS SHA differ")
    for item in [
        "MyoPS-OrganAgent.tar.gz",
        "CineMyoPS-OrganAgent.tar.gz",
        "SHA256SUMS",
        "receipts/WORKSTATION_VALIDATION_PACKET.tar.gz",
    ]:
        add(failures, item in remote.get("final_server_dist_files", []), f"remote final dist missing {item}")

    packet_manifest = load_json(RESULTS / "packet_manifest.json")
    add(failures, packet_manifest.get("status") == "PASS", "packet manifest did not PASS")
    add(failures, packet_manifest.get("contains_heavy_artifacts") is False, "validation packet contains heavy artifacts")


def check_forbidden_actions_and_git(failures: list[str]) -> None:
    for path in RESULTS.glob("*.json"):
        text = path.read_text(encoding="utf-8", errors="ignore").lower()
        add(failures, "challenge_upload_performed\": true" not in text, f"challenge upload recorded in {path.name}")
        add(failures, "validation_upload_performed\": true" not in text, f"validation upload recorded in {path.name}")
        add(failures, "netdisk_upload_performed\": true" not in text, f"netdisk upload recorded in {path.name}")
        add(failures, "organizer_email_sent\": true" not in text, f"organizer email recorded in {path.name}")

    staged = subprocess.run(
        ["git", "diff", "--cached", "--name-only"],
        cwd=CARE_ROOT,
        text=True,
        capture_output=True,
        check=True,
    ).stdout.splitlines()
    forbidden_suffixes = (".pt", ".pth", ".nii", ".nii.gz", ".tar", ".tar.gz")
    for name in staged:
        add(failures, not name.startswith(".local_runtime/"), f"runtime file staged: {name}")
        add(failures, not name.startswith("dist/"), f"dist file staged: {name}")
        add(failures, not name.endswith(forbidden_suffixes), f"heavy artifact staged: {name}")


def main() -> int:
    failures: list[str] = []
    report = {
        "task": TASK,
        "known_bad_coverage": KNOWN_BAD_COVERAGE,
        "status": "FAIL",
        "failures": failures,
    }
    try:
        check_required_files(failures)
        if not failures:
            check_receipts(failures)
            check_casewise(failures)
            check_archives_clean_remote(failures)
            check_forbidden_actions_and_git(failures)
    except Exception as exc:  # fail closed
        failures.append(f"validator exception: {type(exc).__name__}: {exc}")

    report["status"] = "PASS" if not failures else "FAIL"
    (RESULTS / "strict_validator_report.json").write_text(
        json.dumps(report, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0 if report["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
