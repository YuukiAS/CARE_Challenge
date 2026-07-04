---
task_key: "20260704_anchor_srr_forensic_repro_audit"
project: "CARE_Challenge"
status: "READY"
task_type: "execution"
controller_mode: false
planner: "ChatGPT/GPT thread"
strategic_controller: "user-supervised GPT thread"
executor: "Codex forensic audit session"
auditor: "ChatGPT/GPT reviewer after commit"
risk_level: "high"
allow_code_change: true
allow_shell_command: true
allow_network: false
allow_external_upload: false
requires_human_approval: false
review_required: true
mechanism_class: "forensic reproducibility audit / implementation compliance audit / evidence-chain repair"
target_metric: "myops_scar, myops_edema, myocardium_cinemyops diagnostic packet integrity"
required_evidence: ["exact_code_used_by_slurm_57782211", "repo_vs_runtime_diff", "implementation_claim_truth_table", "missing_commits_or_files", "source_line_evidence", "run_config_and_logs", "result_artifact_manifest", "audit_downgrade_if_needed"]
forbidden_substitutes: ["new training", "changing code and re-running to make old claims true", "summarizing without source-line evidence", "claiming nnU-Net anchor consumption without committed source path", "claiming multi-slot dictionary from old ScaleRetrieval", "claiming data-derived prototypes from random nn.Parameter prototypes", "claiming crop refiner from full-volume residual head", "hiding uncommitted runtime files", "validation packaging/upload"]
promotion_gate: "No route promotion from this task. It can only certify, downgrade, or request missing evidence for the existing diagnostic packet."
route_negative_gate: "If the committed code cannot reproduce the claimed implementation, do not support STOP as a scientific conclusion. Mark the packet implementation-audit-failed or evidence-incomplete."
allowed_next_states: ["EXECUTED_UNAUDITED", "NEEDS_EVIDENCE", "NEEDS_REVISION", "IMPLEMENTATION_AUDIT_FAILED", "STOP"]
auto_git_commit: false
auto_git_push: false
allow_git_commit: true
allow_git_push: true
---

# Task: Forensic Reproducibility Audit Of Anchored SRR Diagnostic Packet

## Purpose

The latest diagnostic packet claims that the anchored SRR fold0 run consumed nnU-Net anchors/components and passed adequacy, but the committed source code currently appears inconsistent with that claim. This task must determine whether the diagnostic packet is reproducible from committed code, whether required runtime code/configs/logs are missing from GitHub, and whether the implementation truly satisfies the locked SRR-v2.5 contract.

Do not train a new model. Do not change code and rerun to make the old result true. This is a forensic audit and evidence-chain repair task.

## Required Starting Point

Work from current `main` after commit `f37f1b8f81efb6af6277d9e8983ec932b138a8ce` or the current HEAD if newer. Record `git rev-parse HEAD`, `git status --short`, and any untracked or modified files. If uncommitted files are needed to explain Slurm array `57782211`, list them and commit them as diagnostic evidence or source-code evidence as appropriate.

## Central Questions

Answer these questions with source-line evidence and artifact paths:

1. Which exact source files, job scripts, configs, and environment were used for Slurm array `57782211`?
2. Are those exact files committed to GitHub? If not, commit the minimal necessary source/job/config/audit files and explain why they were missing.
3. Does the committed `SRRProposeRefineMyoPS.forward` accept and use `anchor_features` and `component_features`, or does it only accept `(x, availability)`?
4. Do training, validation, one-batch overfit, prediction export, and evaluation actually pass nnU-Net anchors/components into `model(...)`?
5. Is the dictionary implementation a true multi-slot shared/private/interaction bank, or still the old one-shared-block plus one-private-block-per-modality `ScaleRetrieval`?
6. Are prototypes truly loaded from train/OOF feature caches before training, or are positive/negative prototype parameters still random trainable `nn.Parameter`s with only hard-negative replay as partial evidence?
7. Is refinement a true original-LGE/T2 crop refiner, or a full-volume residual head over decoder features/logits/proposal/ROI?
8. Does no-T2 edema safety exist in inference/decode/export, not just in loss?
9. Is the STOP decision scientifically supported by a committed, reproducible implementation, or only by a diagnostic packet whose source-code evidence is incomplete?

## Required Implementation-Claim Truth Table

Create `results/20260704_anchor_srr_forensic_repro_audit/implementation_claim_truth_table.md` with one row per claim:

- nnU-Net anchor probability consumption;
- nnU-Net component consumption;
- true multi-slot dictionary bank;
- task-specific gates with missing-modality slot masking;
- data-derived scar-positive prototypes;
- data-derived scar-safe-negative prototypes;
- data-derived edema-positive prototypes;
- edema-safe-negative policy excluding no-T2 myocardium;
- hard-negative memory use;
- original LGE crop scar refinement;
- original T2 crop edema refinement;
- soft anatomy/ROI prior;
- no-T2 inference/decode/export guardrail;
- SRR-v2/v2.5 diagram-consistent loss stack;
- convergence/plateau training evidence;
- same-split nnU-Net comparison;
- CineMA attempt or blocker;
- registration option matrix.

Each row must include `claim`, `status` as `SUPPORTED | PARTIAL | UNSUPPORTED | EVIDENCE_MISSING`, `committed_source_evidence`, `runtime_artifact_evidence`, `risk_to_conclusion`, and `required_fix_or_next_action`.

## Required Files To Inspect

At minimum inspect and cite line ranges from:

- `src/care_myocardium/models/srr_propref.py`
- `src/care_myocardium/models/srr_v2_unet.py`
- `src/care_myocardium/losses/srr_losses.py`
- `scripts/training/run_srr_propref_myops_fold0.py`
- every job script used for `MyoPSAnchorSRRF0` or Slurm array `57782211`
- `results/20260704_myops_anchor_srr_fold0_formal/review.md`
- `results/20260704_myops_anchor_srr_fold0_formal/result.md`
- `results/20260704_myops_anchor_srr_fold0_formal/variants/*/configs/run_config.env`
- `results/20260704_myops_anchor_srr_fold0_formal/variants/*/summary.json`
- available logs for `57782211`, `57782213`, `57782214`
- `results/20260704_anchor_srr_v25_goal/audit_summary.md`
- `results/20260704_anchor_srr_v25_goal/controller_report.md`

If a referenced file exists on disk but is not committed, either commit it if it is diagnostic-scope and safe, or list it under `uncommitted_required_evidence.md` with exact path and reason it was not committed.

## Required Outputs

Write and commit the following under `results/20260704_anchor_srr_forensic_repro_audit/`:

- `result.md` with `forensic_decision: REPRODUCIBLE_AND_SUPPORTED | PARTIAL_REPRODUCIBLE | IMPLEMENTATION_AUDIT_FAILED | NEEDS_EVIDENCE | NEEDS_REVISION`
- `implementation_claim_truth_table.md`
- `repo_vs_runtime_diff.md`
- `exact_code_used_by_slurm_57782211.md`
- `source_line_evidence.md`
- `uncommitted_required_evidence.md`
- `diagnostic_packet_risk_assessment.md`
- `recommended_next_action.md`
- `MANIFEST.md`

If safe and necessary, also commit missing source/job/config files used by the run, but do not commit checkpoints, prediction NIfTI outputs, heavy logs, private credentials, or validation upload packages.

## Required Final Decision Logic

If committed code and runtime artifacts genuinely support the claims, mark `REPRODUCIBLE_AND_SUPPORTED` or `PARTIAL_REPRODUCIBLE` and explain remaining gaps.

If the audit packet claims anchor/component consumption or full SRR-v2.5 mechanisms but committed code does not support those claims, mark `IMPLEMENTATION_AUDIT_FAILED` or `NEEDS_EVIDENCE`. In that case, do not treat the current STOP as a scientific stop for the architecture; treat it as a stop for a non-reproducible or partial packet until missing code/evidence is supplied.

## Boundary

No validation packaging. No upload. No new model training. No fold expansion. No new route. This task only checks and repairs the evidence chain so the GPT planner can decide whether the current packet is trustworthy.
