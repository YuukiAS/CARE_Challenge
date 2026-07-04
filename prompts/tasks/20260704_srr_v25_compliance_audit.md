---
task_key: "20260704_srr_v25_compliance_audit"
project: "CARE_Challenge"
status: "READY"
task_type: "execution"
controller_mode: false
planner: "ChatGPT/GPT thread"
strategic_controller: "user-supervised GPT thread"
execution_controller: "Codex executor session"
executor: "Codex executor session"
auditor: "separate read-only Codex auditor session or ChatGPT reviewer"
risk_level: "medium"
allow_code_change: true
allow_shell_command: true
allow_network: false
allow_external_upload: false
requires_human_approval: false
review_required: true
mechanism_class: "architecture compliance audit / SRR-v2.5 diagram-to-code gap / failure diagnosis"
target_metric: "myops_scar, myops_edema"
same_split_baseline: "same-split nnU-Net fold0 reference and SRR formal-training diagnostics; evidence not found if unavailable"
required_evidence: ["result.md", "MANIFEST.md", "diagram_contract_mapping.md", "code_path_inventory.md", "v25_gap_table.csv", "failure_root_cause.md", "nnunet_anchor_gap.md", "implementation_recommendation.md", "audit_notes.md"]
forbidden_substitutes: ["step/time adequacy discussion as main explanation", "generic undertraining-only conclusion", "claiming SRR-v2.5 implemented because names are similar", "new training run", "validation upload or package", "fold expansion", "major model edit"]
experiment_adequacy_gate: "This is an audit task, not training. It must determine whether the current implementation actually matches the SRR-v2/v2.5 diagram contract before any further training."
promotion_gate: "No route promotion is allowed. This task only produces a compliance and root-cause report."
failure_escalation_policy: "If current implementation does not match the diagram contract, write precise gaps and the minimum architecture changes needed before further training. Do not propose more step/time-only training as the primary fix."
allowed_next_states: ["EXECUTED_UNAUDITED", "NEEDS_EVIDENCE", "NEEDS_REVISION", "NEEDS_GPT_PLANNER", "STOP"]
auto_git_commit: false
auto_git_push: false
allow_git_commit: false
allow_git_push: false
---

# Task: SRR-v2/v2.5 Diagram Compliance Audit

## Goal

Produce a strict architecture-compliance and root-cause report explaining why the current SRR/PropRef implementation gives roughly 0.1 Dice instead of approaching the nnU-Net baseline. The goal is not to train more. The goal is to determine whether the code actually implements the SRR-v2/v2.5 idea shown in the architecture diagrams and to identify the exact missing pieces.

The user believes the SRR-v2/v2.5 idea is sound and should not collapse to 0.1 if implemented correctly. The suspected problem is that prior Codex runs implemented simplified modules with similar names, not the actual diagram mechanism. This task must verify or refute that suspicion with file/line evidence.

## Inputs to inspect

First search for diagram/image files under likely paths such as `images/`, `docs/images/`, `docs/figures/`, `assets/`, or any file containing `SRR-v2`, `SRR-v2.5`, `Selective Representation Retrieval`, or `Anatomy-guided Proposal`. If image files are not present in the repo, use the diagram contract embedded below. Do not block solely because the uploaded chat image is not in the repo.

Read at minimum:

- `src/care_myocardium/models/srr_propref.py`
- `src/care_myocardium/models/srr_v2_unet.py`
- `src/care_myocardium/models/srr_myops.py`
- `src/care_myocardium/models/pathology_heads.py`
- `src/care_myocardium/losses/srr_losses.py`
- `scripts/training/run_srr_propref_myops_fold0.py`
- `jobs/src/run_srr_propref_formal_myops_fold0.sh`
- `results/20260703_srr_formal_training/result.md`
- `results/20260703_srr_formal_training/review.md`
- `results/20260703_srr_formal_training/metrics_summary.md`
- `results/20260703_srr_formal_training/prediction_sanity.md`
- `results/20260703_srr_formal_training/subgroup_metrics.csv`
- `results/20260703_srr_formal_training/proposal_pr_sweep.csv`
- `results/20260703_nnunet_oof_component/review.md`
- `scripts/evaluation/run_nnunet_oof_component_20260703.py`
- relevant nnU-Net fold0 prediction/probability/cache paths if referenced by scripts/results.

You may add small read-only audit scripts under `scripts/evaluation/` only if needed to inspect modules, configs, outputs, or table summaries. Do not edit training/model code in this task.

## Embedded SRR-v2/v2.5 diagram contract

The diagram contract to audit against is:

1. Inputs and availability: LGE, C0/bSSFP, T2, plus explicit availability mask `m=(m_LGE,m_C0,m_T2)`. No zero-filling as evidence; use observed modalities only.
2. Multi-scale encoder and availability-aware router: modality-specific stems feeding a shared multi-scale encoder with channel scales approximately 32/64/128/256, plus pooled feature vector and availability embedding used by task-specific routers for anatomy, scar, and edema.
3. Representation retrieval bank at each scale: shared dictionary, LGE-specific dictionary, C0-specific dictionary, T2-specific dictionary, optional interaction dictionary, and pathology prototype groups including scar positive, scar negative, edema positive, and edema safe-negative. Retrieval should be segmentation-native and not just ordinary dense convolution.
4. Routed features: explicit routed anatomy features, routed scar features, and routed edema features produced from the retrieval bank.
5. Anatomy-guided lesion proposal: anatomy decoder should produce `P_union`, `P_LV`, and `P_RV`. These should form anatomy prior / distance map / soft anatomy gate. Scar proposal should be LGE-dominant with high-precision candidate selection. Edema proposal should be T2-conditioned and safe under missing T2.
6. Soft-ROI refinement: soft-ROI generator should use proposal, anatomy prior, distance/uncertainty. Scar refinement should be small-ROI high-resolution and should use original LGE crop. Edema refinement should be large-ROI/context-preserving and should use original T2 crop when T2 is present. Soft containment, not hard clipping.
7. Training objectives: anatomy Dice/CE, scar proposal loss with weak boundary/HD surrogate, edema proposal loss only when T2 is present, scar refinement loss, edema refinement loss only when T2 is present, negative-space/hard-negative discrimination, soft anatomy prior/ROI regularization, dictionary sparsity/coverage/load-balancing/prototype diversity, optional alignment on complete tri-modal subset.
8. Cine branch is separate: registration-aware anatomy-first temporal retrieval. It should not be confused with MyoPS SRR-v2.5.
9. Important expectation: the MyoPS path should not be a tiny from-scratch toy segmenter. If it is intended to improve over nnU-Net, it must either use a strong U-Net/nnU-Net-equivalent backbone or explicitly anchor on nnU-Net predictions/probabilities/components/teacher features and refine them.

## Required audit questions

Answer these directly and with code/file evidence:

1. Is the current formal route actually SRR-v2/v2.5, or only a simplified name-compatible approximation?
2. Does `SRRProposeRefineMyoPS` use nnU-Net logits, probabilities, compact predictions, components, or teacher features anywhere? If not, state that explicitly.
3. What is the actual backbone capacity: base channels, number of scales, encoder/decoder structure, patch size, and comparison to the diagram's 32/64/128/256 intent?
4. Is the retrieval bank a true multi-scale dictionary bank with shared/modality/interaction dictionaries and data-derived pathology prototypes, or just router/gated convolution plus randomly initialized trainable prototype parameters?
5. Is anatomy guidance a real `P_union/P_LV/P_RV + distance map + soft gate` mechanism, or only a `union_prior` bias from anatomy logits?
6. Are scar and edema proposals true LGE-dominant / T2-conditioned candidate-selection decoders, or just 1x1/prototype logits over decoder features?
7. Is soft-ROI refinement a true crop/local high-resolution refiner using original LGE/T2 crops, distance, uncertainty, and proposal maps, or a full-volume residual head?
8. Does inference enforce no-T2-safe edema output? Quantify or cite evidence for no-T2 edema voxels if available.
9. Why are metrics near 0.1? Separate causes into architecture mismatch, weak capacity, missing nnU-Net anchor, decode/no-T2 issues, proposal flooding, component FP burden, and training adequacy. Do not use training time as the main explanation unless evidence supports it.
10. What is the minimum viable architecture change that could plausibly move toward 0.4: nnU-Net-anchored residual/component refiner, stronger U-Net backbone, true data-derived prototype bank, no-T2 edema inference gate, or some combination?

## Required outputs

Write under `results/20260704_srr_v25_compliance_audit/`:

- `result.md`: concise executive result and decisions.
- `MANIFEST.md`: artifact index.
- `diagram_contract_mapping.md`: module-by-module mapping from diagram block to current code, with status `IMPLEMENTED`, `PARTIAL`, `NAME_ONLY`, or `MISSING`.
- `code_path_inventory.md`: exact model, runner, loss, job, and result files inspected.
- `v25_gap_table.csv`: machine-readable gap table with columns `diagram_block,current_code_path,status,evidence,impact_on_metric,required_fix,priority`.
- `failure_root_cause.md`: the main explanation for 0.1 Dice. Must explicitly say whether the current issue is undertraining, architecture mismatch, missing nnU-Net anchor, no-T2 decode, proposal flooding, or another cause.
- `nnunet_anchor_gap.md`: whether and where nnU-Net predictions/probs/components are consumed. If absent, explain why that matters.
- `implementation_recommendation.md`: a minimal next implementation plan, but do not create a new training task in this audit.
- `audit_notes.md`: caveats, missing evidence, and commands run.

If a separate auditor is used, write `results/20260704_srr_v25_compliance_audit/review.md` after the executor result exists.

## Decision fields to include in result.md

Use these fields:

```text
self_assessed_status: EXECUTED_UNAUDITED | NEEDS_EVIDENCE | NEEDS_REVISION
architecture_compliance_decision: COMPLIANT | PARTIAL | NOT_COMPLIANT | EVIDENCE_NOT_FOUND
root_cause_decision: ARCHITECTURE_MISMATCH | MISSING_NNUNET_ANCHOR | INFERENCE_DECODE_BUG | UNDERTRAINING_ONLY | MIXED
current_training_recommendation: DO_NOT_CONTINUE_CURRENT_PROPREF | CONTINUE_AFTER_FIX | NEEDS_EVIDENCE
next_required_action: ...
```

## Completion rule

This task is complete only when the report can answer, in plain terms, why the current code gets around 0.1 and whether that result is a fair test of the SRR-v2/v2.5 diagram. If the answer is that current code is not diagram-compliant, do not recommend more training of the same code as the main next step.

普通 executor 必须停在 `EXECUTED_UNAUDITED` and await review.
