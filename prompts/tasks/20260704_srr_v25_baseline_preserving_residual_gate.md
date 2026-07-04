---
task_key: "20260704_srr_v25_baseline_preserving_residual_gate"
project: "CARE_Challenge"
status: "READY_FOR_USER_REVIEW"
task_type: "execution"
risk_level: "high"
allow_code_change: true
allow_shell_command: true
allow_network: false
allow_external_upload: false
review_required: true
mechanism_class: "nnU-Net anchored residual/gated SRR correction / baseline preservation"
required_evidence: ["code_diff", "identity_fallback_test", "same_case_alignment", "bounded_residual_stats", "harm_vs_help_case_table", "same_split_metrics", "ablation"]
forbidden_substitutes: ["plain nnU-Net copy as SRR", "from-scratch weak SRR replacing nnU-Net", "unbounded residual that destroys anchor", "using nnU-Net only as global scalar summary", "threshold-only correction", "claiming improvement without harm analysis"]
---

# Task: Baseline-Preserving nnU-Net Anchored SRR Residual Gate

## Goal

Implement a strong SRR component that can improve nnU-Net without freely destroying it. The current anchored SRR packet consumes nnU-Net context but still underperforms. The next architecture must treat nnU-Net as an anatomy/probability/component teacher and reference, while SRR learns availability-aware, pathology-specific corrections.

## Required Architecture

Implement a residual or gated-correction path with an explicit formula equivalent to one of:

```text
final_logits = nnunet_logits + gate(x, m, context) * bounded_delta_srr(x, m, context)
```

or

```text
final_prob = (1 - gate(x, m, context)) * nnunet_prob + gate(x, m, context) * srr_prob
```

Required context inputs:

- nnU-Net class probabilities/logits for all compact classes;
- nnU-Net hard prediction and connected components for scar/edema;
- nnU-Net uncertainty/confidence;
- anatomy union/LV/RV context and distance maps where available;
- modality availability mask and original LGE/T2/C0 image features.

The SRR branch must still use the visual SRR contract: modality-specific evidence, retrieval/dictionary context, scar/edema-specific proposal/refinement, and T2-masked edema logic. nnU-Net is an anchor/teacher, not the paper story by itself.

## Mandatory Safety Tests

1. Closed gate or zero residual must reproduce the nnU-Net prediction exactly, voxel-for-voxel, on toy and real validation cases.
2. Same-case and same-shape alignment must be checked before context use; shifted or mismatched anchor tensors must fail.
3. Residual magnitude must be bounded and logged per class and subgroup.
4. No-T2 edema must remain blocked through loss, logits, decode, and export.
5. Gate maps must not be constant all-zero or all-one. If they are, mark `NEEDS_REVISION`.
6. SRR correction must be measured as help/harm relative to nnU-Net per case and component.

## Required Ablations

At minimum compare:

- nnU-Net only;
- current anchored PropRef packet;
- residual gate without dictionary/prototypes;
- residual gate with semantic dictionary but no data-derived prototypes;
- full residual gate with semantic dictionary and real prototypes;
- SRR branch without nnU-Net anchor, to quantify baseline destruction.

## Required Metrics

Report scar Dice/HD95/component count/remote FP, edema GT-positive/T2-present Dice, CenterC edema, no-T2 safety, component-level help/harm, residual magnitude, gate open-rate, and number of cases where SRR improves versus harms nnU-Net.

## Required Outputs

Write `results/20260704_srr_v25_baseline_preserving_residual_gate/` with:

- `result.md`
- `residual_gate_contract.md`
- `identity_fallback_test.md`
- `same_case_alignment_sanity.md`
- `bounded_residual_stats.csv`
- `help_harm_by_case.csv`
- `ablation_summary.csv`
- `unit_test_report.md`
- `MANIFEST.md`

## Completion Gate

Do not mark `PASS` if the model is a plain nnU-Net copy, a weak from-scratch SRR replacement, or an unbounded residual that harms nnU-Net on most cases. A scientifically acceptable result may be `PASS_DIAGNOSTIC` if it proves SRR corrections help only certain subgroups and identifies where the gate should open.
