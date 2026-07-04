---
task_key: "20260704_external_assets_cinema_registration"
project: "CARE_Challenge"
status: "READY"
task_type: "execution"
controller_mode: false
planner: "ChatGPT/GPT thread"
strategic_controller: "user-supervised GPT thread"
execution_controller: "20260704_anchor_srr_v25_goal controller"
executor: "Codex executor session"
auditor: "separate read-only Codex auditor session or ChatGPT reviewer"
risk_level: "medium"
allow_code_change: true
allow_shell_command: true
allow_network: true
allow_external_upload: false
requires_human_approval: false
review_required: true
mechanism_class: "external asset acquisition / license audit / cine anatomy and registration options"
target_metric: "myocardium_cinemyops diagnostic proxy; MyoPS anatomy/registration support if useful"
required_evidence: ["asset_registry.md", "license_compliance.md", "environment_probe.md", "download_or_clone_log.md", "usable_asset_matrix.md", "MANIFEST.md"]
forbidden_substitutes: ["skipping CineMA without trying or documenting blocker evidence", "skipping registration assets without environment/license evidence", "using external code without license/source record", "uploading data or predictions externally", "treating an unavailable asset as evaluated"]
promotion_gate: "No route promotion from this subtask alone."
network_policy: "Network is allowed only to fetch public code/model assets needed for this goal. Record URL, commit/version, license, local path, and whether code/weights are actually usable. Do not upload CARE data, predictions, credentials, or private files."
allowed_next_states: ["EXECUTED_UNAUDITED", "NEEDS_EVIDENCE", "NEEDS_REVISION", "STOP"]
auto_git_commit: false
auto_git_push: false
allow_git_commit: false
allow_git_push: false
---

# Task: Acquire And Audit External Assets For CineMA And Registration Options

## Goal

Make a serious attempt to prepare common external assets that can materially help the Cine and registration parts of the goal. This task exists so later executors cannot avoid CineMA or registration work by saying network was disabled or by silently using only a reference-frame baseline.

## Required Attempts

Attempt or explicitly document blockers for these asset classes:

1. Cine anatomy prior: CineMA first. CorSeg-CineSAX or another open cine anatomy model may be second choice.
2. Classical registration: check whether ANTs/SyN is installed or installable in the existing environment without breaking the repo.
3. Learning-based registration: VoxelMorph or an equivalent public learning-based registration implementation, including available weights if license and environment allow.
4. Existing repo-local TPS paths: U-MyoPS/CineMyoPS TPS or feature-warp code already present under `third_party/` or `code/`.
5. Lightweight optical-flow/feature-warp proxy already used in `results/20260703_cine_motion/`, as a fallback but not a validated registration substitute.

## Rules

Do not upload CARE data or predictions anywhere. Do not use unclear-license assets as if they are production-ready. If a repository or weight cannot be fetched, record the command, URL, error, and whether retry is reasonable. If license is unclear, mark it `license_needs_review` rather than blocking the whole goal unless that asset is required for the current run.

## Required Outputs

Write under `results/20260704_external_assets_cinema_registration/`: `result.md` with `external_asset_decision: USABLE_ASSETS_FOUND | PARTIAL_ASSETS_FOUND | NEEDS_EVIDENCE | NEEDS_REVISION`, `asset_registry.md`, `license_compliance.md`, `environment_probe.md`, `download_or_clone_log.md`, `usable_asset_matrix.md`, and `MANIFEST.md`.

## Completion Definition

Completion means later Cine and registration tasks know which assets are usable and which are blocked. It does not authorize validation packaging, upload, hosted metric claims, or route promotion.
