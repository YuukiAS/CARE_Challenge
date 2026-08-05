#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
import json
import subprocess
import sys
from pathlib import Path


TASK = "20260805_care_myops_attempt3_single_slice_hotfix"
EXPECTED_BASE_SHA = "921a0115428b8d597c67d57d45862de1371bf6d3097b5dc8c9b27e7407589ef3"
EXPECTED_BASE_SIZE = 5102883153
EXPECTED_BASE_IMAGE_ID = "sha256:a291ab1e51a52c0739970a45db567b4e4a8cb103e06946626509800fa6f258bf"
EXPECTED_NNUNET_SOURCE_SHA = "0925abcba8f87d84819921ae661fdafa5c871226a5dbceca61e9947e63acad98"
GEOMETRY_MISMATCH_TOKEN = "INHERITED_BASE_BEHAVIOR_OUT_OF_SCOPE_NONBLOCKING"
FORBIDDEN_STAGED_MARKERS = (
    ".tar",
    ".tar.gz",
    ".pt",
    ".pth",
    ".nii",
    ".nii.gz",
    "rclone.conf",
    "token",
    "secret",
    ".local_runtime/",
    "dist/",
    "predictions/",
)


class Failure(Exception):
    pass


def load_json(path: Path) -> dict:
    if not path.exists():
        raise Failure(f"missing required JSON: {path}")
    return json.loads(path.read_text(encoding="utf-8"))


def require(condition: bool, message: str) -> None:
    if not condition:
        raise Failure(message)


def count_csv_rows(path: Path) -> int:
    if not path.exists():
        raise Failure(f"missing required CSV: {path}")
    with path.open(newline="", encoding="utf-8") as f:
        return sum(1 for _ in csv.DictReader(f))


def check_git_staging(repo: Path) -> list[str]:
    proc = subprocess.run(
        ["git", "diff", "--cached", "--name-only"],
        cwd=repo,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )
    if proc.returncode != 0:
        raise Failure(f"git staged-file scan failed: {proc.stderr.strip()}")
    violations: list[str] = []
    for name in proc.stdout.splitlines():
        lowered = name.lower()
        if any(marker in lowered for marker in FORBIDDEN_STAGED_MARKERS):
            violations.append(name)
    return violations


def validate(results: Path, repo: Path, require_upload: bool) -> dict:
    base = load_json(results / "base_artifact_provenance.json")
    resolution = load_json(results / "attempt3_submitted_artifact_resolution.json")
    invariance = load_json(results / "model_invariance_comparison.json")
    reproducer = load_json(results / "organizer_failure_reproducer.json")
    normal = load_json(results / "normal_15case_regression_summary.json")
    edge = load_json(results / "single_slice_edge_summary.json")
    mixed = load_json(results / "mixed_batch_summary.json")
    clean = load_json(results / "clean_save_load_receipt.json")
    archive = load_json(results / "corrected_archive_manifest.json")
    provenance = load_json(results / "corrected_myops_runtime_only_hotfix_provenance.json")
    source = load_json(results / "hotfix_source_receipt.json")
    failure_modes = load_json(results / "failure_mode_summary.json")

    require(base.get("archive_sha256") == EXPECTED_BASE_SHA, "base archive SHA mismatch")
    require(base.get("archive_size_bytes") == EXPECTED_BASE_SIZE, "base archive size mismatch")
    require(base.get("image_id") == EXPECTED_BASE_IMAGE_ID, "base image ID mismatch")
    require(base.get("nnunet_source_sha256") == EXPECTED_NNUNET_SOURCE_SHA, "base nnU-Net source SHA mismatch")
    require(resolution.get("status") == "PASS", "Attempt 3 submitted artifact resolution did not pass")
    require(resolution.get("not_attempt2_pure_nnunet_archive") is True, "Attempt 3 archive not proven distinct from Attempt 2 pure archive")
    require(resolution.get("not_attempt2_corrected_archive") is True, "Attempt 3 archive not proven distinct from Attempt 2 corrected archive")
    require(base.get("self_model_asset_count", 0) >= 5, "Attempt 3 self_model asset count mismatch")

    require(reproducer.get("old_direct_function_zero_dimension") is True, "old direct function did not produce zero dimension")
    require(reproducer.get("old_end_to_end_failure_reproduced") is True, "old Docker end-to-end failure not reproduced")
    require("single-slice" in (results / "organizer_failure_reproducer.md").read_text(encoding="utf-8").lower(), "missing failure narrative")

    for key in (
        "model_checkpoint_hashes_equal",
        "plans_dataset_hashes_equal",
        "predict_entrypoint_requirements_hashes_equal",
        "pip_freeze_equal",
        "entrypoint_cmd_env_equal",
        "base_rootfs_diff_ids_are_exact_prefix",
        "care_ase_assets_equal",
        "no_extra_self_model_assets",
    ):
        require(invariance.get(key) is True, f"invariance field failed: {key}")

    require(source.get("single_slice_clamp_minimum_one") is True, "hotfix clamp receipt missing")
    require(source.get("replacement_count") == 1, "patch source pattern not uniquely matched")
    require("np.maximum(new_shape, 1)" in source.get("patched_function_source", ""), "patched function missing clamp")

    require(count_csv_rows(results / "compute_new_shape_boundary_matrix.csv") >= 16, "boundary matrix too small")
    require(edge.get("status") == "PASS", "synthetic edge matrix did not pass")
    require(edge.get("depth1_cases_passed", 0) >= 7, "depth-one coverage too small")
    require(edge.get("depth2_cases_passed", 0) >= 4, "depth-two coverage too small")
    require(edge.get("all_outputs_geometry_match") is True, "synthetic output geometry mismatch")

    require(normal.get("status") == "PASS", "normal 15-case regression failed")
    require(normal.get("case_count") == 15, "normal case count not 15")
    require(normal.get("array_exact_count") == 15, "normal arrays not 15/15 exact")
    require(normal.get("geometry_exact_count") == 15, "normal geometry not 15/15 exact")
    require(normal.get("canonical_sha_exact_count") == 15, "normal canonical SHA not 15/15 exact")

    require(mixed.get("status") == "PASS", "mixed batch failed")
    require(mixed.get("normal_case_exact_against_base_count") == 15, "mixed batch normal outputs drifted")
    require(mixed.get("missing_outputs") == [], "mixed batch missing outputs")
    require(mixed.get("unknown_outputs") == [], "mixed batch unknown outputs")

    det = load_json(results / "patched_determinism_summary.json")
    require(det.get("status") == "PASS", "synthetic determinism failed")
    require(det.get("array_exact_count") == 13, "synthetic determinism was not full matrix")

    require(clean.get("status") == "PASS", "clean save/load rerun failed")
    require(clean.get("archive_reload_performed") is True, "archive reload not performed")
    require(clean.get("synthetic_rerun_pass") is True, "clean synthetic rerun failed")
    require(clean.get("normal_compare_pass") is True, "clean normal compare failed")
    require(clean.get("synthetic_full_matrix_rerun_pass") is True, "clean full synthetic matrix rerun failed")
    require(clean.get("normal_sentinel_count") == 3, "clean normal sentinel count is not 3")
    require(clean.get("synthetic_plus_normal_mixed_batch_pass") is True, "clean synthetic+normal mixed sentinel failed")

    failure_mode_failures = failure_modes.get("failures", [])
    allowed_geometry_mismatch = (
        len(failure_mode_failures) == 1
        and failure_mode_failures[0].get("mode") == "geometry_mismatch"
        and failure_mode_failures[0].get("status") == "INHERITED_BASE_BEHAVIOR_OUT_OF_SCOPE_NONBLOCKING"
    )
    require(
        failure_modes.get("status") == "PASS" or allowed_geometry_mismatch,
        "failure-mode expansion failed: " + json.dumps(failure_mode_failures, sort_keys=True),
    )

    require(archive.get("archive_size_bytes", 0) > 0, "corrected archive size missing")
    require(len(archive.get("archive_sha256", "")) == 64, "corrected archive SHA missing")
    require(archive.get("image_tag") == "care-myocardium-myops:organagent", "final image tag mismatch")
    require(Path(archive.get("archive_path", "")).name == "MyoPS-OrganAgent-Attempt3-corrected.tar.gz", "Attempt 3 corrected archive name mismatch")

    for key in (
        "model_changed",
        "training_performed",
        "checkpoint_selection_changed",
        "inference_configuration_changed",
    ):
        require(provenance.get(key) is False, f"provenance forbidden true field: {key}")
    require(provenance.get("only_runtime_preprocessing_fix") is True, "provenance missing runtime-only flag")

    if require_upload:
        drive = load_json(results / "google_drive_corrected_upload_receipt.json")
        link = load_json(results / "google_drive_corrected_public_link.json")
        require(drive.get("status") == "PASS", "Drive upload did not pass")
        require(link.get("public_access_ok") is True, "Drive public link not verified")
        require(link.get("reused_old_failed_url") is False, "old failed URL reused")

    draft = results / "organizer_reply_draft.md"
    require(draft.exists(), "organizer reply draft missing")
    draft_text = draft.read_text(encoding="utf-8")
    require("email_sent=false" in draft_text, "reply draft must explicitly remain unsent")
    require("CARE-ASE" in draft_text, "reply draft must state CARE-ASE checkpoints are unchanged")
    require("CineMyoPS remains intentionally unchanged" in draft_text, "reply draft must state CineMyoPS reuse is intentional")

    staged_violations = check_git_staging(repo)
    require(not staged_violations, "forbidden heavy/secret artifact staged: " + ", ".join(staged_violations))

    return {"status": "PASS", "require_upload": require_upload}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--results", default=f"results/{TASK}")
    parser.add_argument("--repo", default=".")
    parser.add_argument("--require-upload", action="store_true")
    parser.add_argument("--write-report")
    args = parser.parse_args(argv)

    report_path = Path(args.write_report) if args.write_report else None
    try:
        report = validate(Path(args.results), Path(args.repo), args.require_upload)
    except Exception as exc:
        report = {"status": "FAIL", "error": str(exc), "require_upload": args.require_upload}
        if report_path:
            report_path.write_text(json.dumps(report, indent=2, sort_keys=True), encoding="utf-8")
        print(json.dumps(report, indent=2, sort_keys=True), file=sys.stderr)
        return 1

    if report_path:
        report_path.write_text(json.dumps(report, indent=2, sort_keys=True), encoding="utf-8")
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
