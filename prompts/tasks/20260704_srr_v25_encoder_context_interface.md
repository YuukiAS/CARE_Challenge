---
task_key: "20260704_srr_v25_encoder_context_interface"
project: "CARE_Challenge"
status: "READY_FOR_USER_REVIEW"
task_type: "execution"
risk_level: "high"
allow_code_change: true
allow_shell_command: true
allow_network: false
allow_external_upload: false
review_required: true
mechanism_class: "modality encoder / nnU-Net context interface / anatomy context"
required_evidence: ["code_diff", "context_contract", "shape_sanity", "same_case_anchor_alignment", "unit_tests", "ablation_plan"]
forbidden_substitutes: ["using nnU-Net as final answer without SRR context learning", "using nnU-Net only as a scalar summary", "unverified spatial alignment", "zero-filled missing modality treated as observed image"]
---

# Task: SRR Encoder And nnU-Net Context Interface

## Goal

Clarify and implement the intended relationship between SRR and nnU-Net. nnU-Net should supply anatomy, uncertainty, component, and probability context. SRR must still learn modality-specific and cross-modal representations from LGE/T2/C0 through its own encoder and retrieval path. The task is not to collapse back to plain nnU-Net or to ignore nnU-Net context.

## Required Work

Implement or verify a context interface that provides:

- nnU-Net anatomy probability maps, scar/edema probability maps, compact hard prediction, connected components, uncertainty/confidence, and anatomy union/distance context;
- strict same-case and same-shape alignment checks;
- no-T2 edema context blocking;
- explicit separation between image encoder features and nnU-Net context features;
- source-line documentation showing where context enters dictionary routing, proposal scoring, and crop refinement.

## Encoder Requirements

Evaluate whether the current three-scale encoder is sufficient. If not, implement a stronger four-scale or nnU-Net-equivalent SRR encoder option. Do not call the current encoder sufficient only because it runs. Report parameter count, feature shapes, memory, and one-batch overfit.

## Required Outputs

Write `results/20260704_srr_v25_encoder_context_interface/` with `result.md`, `context_contract.md`, `shape_alignment_sanity.md`, `encoder_capacity_report.md`, `unit_test_report.md`, `ablation_plan.md`, and `MANIFEST.md`.

## Completion Gate

A pass requires source-line evidence that nnU-Net context is neither ignored nor used as a lazy final output. It must be spatially aligned, availability-aware, and consumed by SRR encoder/retrieval/proposal/refinement at documented sites.
