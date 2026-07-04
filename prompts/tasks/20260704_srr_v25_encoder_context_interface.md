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
mechanism_class: "modality stems / strong shared encoder / nnU-Net context interface / anatomy context"
required_evidence: ["code_diff", "context_contract", "shape_sanity", "same_case_anchor_alignment", "parameter_count", "unit_tests", "ablation_plan"]
forbidden_substitutes: ["using nnU-Net as final answer without SRR context learning", "using nnU-Net only as a scalar summary", "unverified spatial alignment", "zero-filled missing modality treated as observed image", "keeping the tiny 3-scale encoder without capacity justification", "claiming context use without downstream consumption"]
---

# Task: SRR Encoder And nnU-Net Context Interface

## Goal

Clarify and implement the intended relationship between SRR and nnU-Net. nnU-Net should supply anatomy, uncertainty, probability, component, and teacher context. SRR must still learn modality-specific and cross-modal representations from LGE/T2/C0 through its own encoder and retrieval path. The task is not to collapse back to plain nnU-Net or to ignore nnU-Net context.

## Required Context Interface

Implement or verify a context interface that provides:

- nnU-Net anatomy probability maps, scar/edema probability maps, compact hard prediction, connected components, uncertainty/confidence, anatomy union/distance context;
- strict same-case, same-fold or OOF, same-shape, same-spacing, and same-orientation checks;
- no-T2 edema context blocking;
- explicit separation between image encoder features and nnU-Net context features;
- source-line documentation showing where context enters dictionary routing, proposal scoring, residual/gated correction, and crop refinement.

## Encoder Requirements

The visual contract expects modality-specific stems followed by a strong shared multi-scale encoder or nnU-Net-equivalent context path with intended channel scales around 32/64/128/256. The current three-scale 10/20/40 route is not sufficient by default.

Required actions:

1. Report the current encoder parameter count, scale shapes, patch shape, and memory footprint.
2. Implement one stronger option: four-scale SRR encoder, nnU-Net-like residual U-Net encoder, MONAI/MedNeXt-style encoder, or explicit nnU-Net feature/context bridge.
3. Preserve availability-aware modality stems and missing-modality closure.
4. Show one-batch overfit for the stronger option and compare against the current tiny route.
5. If the stronger encoder cannot fit memory, implement a documented fallback that still preserves nnU-Net baseline through the residual/gated correction task.

## Anti-Laziness Checks

Do not pass by saying the current encoder "runs." Do not pass by adding a larger class that is never called. The formal runner must be able to select the stronger encoder by config, and `summary.json` must record which encoder was used.

## Required Outputs

Write `results/20260704_srr_v25_encoder_context_interface/` with:

- `result.md`
- `context_contract.md`
- `shape_alignment_sanity.md`
- `encoder_capacity_report.md`
- `unit_test_report.md`
- `ablation_plan.md`
- `MANIFEST.md`

## Completion Gate

A pass requires source-line evidence that nnU-Net context is neither ignored nor used as a lazy final output. It must be spatially aligned, availability-aware, and consumed by SRR encoder/retrieval/proposal/residual/refinement at documented sites. A stronger encoder option must exist and be callable, or the task must mark `NEEDS_EVIDENCE` with a resource blocker.
