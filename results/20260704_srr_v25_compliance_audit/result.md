# Result 20260704 SRR-v2.5 Compliance Audit

self_assessed_status: EXECUTED_UNAUDITED
architecture_compliance_decision: NOT_COMPLIANT
root_cause_decision: MIXED
current_training_recommendation: DO_NOT_CONTINUE_CURRENT_PROPREF
next_required_action: GPT planner should choose an architecture repair route before any further PropRef training; do not continue step/time-only training of the current implementation as the primary fix.

## Executive Summary

The current formal route is not a faithful SRR-v2/v2.5 implementation. It is a simplified, name-compatible approximation: a small 3-scale from-scratch model with router-gated convolutional experts, randomly initialized trainable prototype parameters, a `union_prior_logits` bias, and full-volume residual refinement. It does not consume nnU-Net logits, probabilities, predictions, components, or teacher features.

The roughly 0.1 Dice outcome is therefore not a fair test of the SRR-v2/v2.5 diagram contract. The dominant causes are architecture mismatch and missing nnU-Net anchor, with additional no-T2 inference leakage and proposal/ROI false-positive flooding. The formal run also failed the task's time adequacy gate, but training time is not the main explanation to carry forward.

## Direct Answers

1. Current formal route: not SRR-v2/v2.5. It is `NAME_ONLY/PARTIAL`, not diagram-compliant.
2. nnU-Net anchor use: absent in `SRRProposeRefineMyoPS` and its formal runner. `rg` over the model/runner/loss files found no nnU-Net probability, prediction, component, logit, or teacher-feature input path.
3. Backbone capacity: formal job uses `base_channels=10`, patch `12,96,96`, batch `2`; code builds 3 scales of 10/20/40 channels. The diagram expects approximately 32/64/128/256 with a stronger segmentation backbone.
4. Retrieval bank: not a true segmentation-native multi-scale dictionary bank. `ScaleRetrieval` is shared/private/interaction ConvBlock experts plus softmax routers; pathology prototypes are randomly initialized `nn.Parameter`s, not data-derived scar/edema prototype groups.
5. Anatomy guidance: only `union_prior_logits` from anatomy logits and local average pooling. No explicit `P_union/P_LV/P_RV`, distance map, or uncertainty-aware soft anatomy gate exists.
6. Proposals: scar/edema proposals are 1x1 conv plus prototype similarity plus evidence/prior bias. They are not true LGE-dominant or T2-conditioned candidate-selection decoders.
7. Soft-ROI refinement: it is full-volume residual refinement over decoder features plus logits/proposal/ROI. It does not crop original LGE/T2 high-resolution image regions.
8. No-T2 edema inference: not enforced. Existing prediction sanity reports large no-T2 edema voxel counts, for example `886192` no-T2 edema voxels for no-proto pathology-aware and `445011` for shared-dual pathology-aware.
9. Why near 0.1 Dice: architecture mismatch, missing nnU-Net anchor, weak capacity, false-positive proposal flooding, no-T2 edema leakage, and undertrained formal evidence. The first four are primary; undertraining is a gate failure but not an adequate main repair explanation.
10. Minimum viable architecture change: use an nnU-Net-anchored residual/component refiner or a strong nnU-Net-equivalent backbone, add true data-derived retrieval/prototype banks if SRR-v2.5 is still desired, enforce no-T2-safe edema inference, and replace full-volume residual refinement with real proposal-conditioned ROI/crop refinement.

## Key Evidence

- Formal model constructs 3 modality encoders and 3 retrieval scales only: `src/care_myocardium/models/srr_propref.py:148-156`.
- Formal capacity defaults to `base_channels=10`: `src/care_myocardium/models/srr_propref.py:132-148`, `scripts/training/run_srr_propref_myops_fold0.py:984-987`, `jobs/src/run_srr_propref_formal_myops_fold0.sh:63-65`.
- `ScaleRetrieval` is ConvBlock experts plus router weights, not dictionary lookup: `src/care_myocardium/models/srr_v2_unet.py:58-120`.
- Prototype proposal parameters are random trainable tensors: `src/care_myocardium/models/srr_propref.py:34-47`, `src/care_myocardium/models/srr_myops.py:147-152`.
- Anatomy prior is a logsumexp union bias over anatomy logits: `src/care_myocardium/models/pathology_heads.py:15-30`.
- Refinement is full-volume convolutional residual using features/logits/proposal/ROI, not crop refinement: `src/care_myocardium/models/srr_propref.py:82-120`.
- Pathology-aware decode ignores modality availability and can emit edema when T2 is absent: `scripts/training/run_srr_propref_myops_fold0.py:259-275`.
- Formal metrics remain far below nnU-Net: best scar Dice at most `0.1665`, best edema GT-positive Dice at most `0.0868`, versus nnU-Net scar `0.5602` and edema `0.3944`: `results/20260703_srr_formal_training/metrics_summary.md`.
- Proposal threshold 0.5 summaries show high outside-myocardium FP ratios around `0.74-0.88`, very low precision around `0.018-0.098`, and large remote FP/component counts.

## Decision

The current code should not be trained longer as the primary fix. The next useful action is an architecture repair decision by GPT planner, not another time/step-only formal run.

## Files Written

- `results/20260704_srr_v25_compliance_audit/result.md`
- `results/20260704_srr_v25_compliance_audit/MANIFEST.md`
- `results/20260704_srr_v25_compliance_audit/diagram_contract_mapping.md`
- `results/20260704_srr_v25_compliance_audit/code_path_inventory.md`
- `results/20260704_srr_v25_compliance_audit/v25_gap_table.csv`
- `results/20260704_srr_v25_compliance_audit/failure_root_cause.md`
- `results/20260704_srr_v25_compliance_audit/nnunet_anchor_gap.md`
- `results/20260704_srr_v25_compliance_audit/implementation_recommendation.md`
- `results/20260704_srr_v25_compliance_audit/audit_notes.md`

No training, validation packaging, upload, fold expansion, model edit, or git commit/push was performed.
