---
task_key: "20260705_srr_v3_m0_architecture_master_contract"
project: "CARE_Challenge"
status: "READY_FOR_USER_REVIEW"
task_type: "milestone"
milestone_id: "M0"
risk_level: "medium"
allow_code_change: false
allow_shell_command: true
allow_network: false
allow_external_upload: false
review_required: true
mechanism_class: "SRR-v3 architecture master contract / hard-gated interface spec"
expected_result_dir: "results/20260705_srr_v3_m0_architecture_master_contract/"
required_inputs:
  - "prompts/tasks/20260705_next_planning_start.md"
  - "prompts/tasks/20260705_next_planning_brief.md"
  - "results/20260705_handoff_hard_gate_repair/review.md"
  - "results/20260705_handoff_hard_gate_repair/current_bad_packet_regression.md"
  - "results/20260705_srr_v25_evidence_supplement_audit/result.md"
  - "results/20260705_srr_v25_evidence_supplement_audit/missing_evidence_and_next_questions.md"
  - "prompts/HANDOFF_GATE_POLICY.md"
  - "prompts/GPT_HARD_GATE_PROMPT.md"
required_outputs:
  - "result.md"
  - "architecture_contract.md"
  - "interface_contract.md"
  - "metric_contract.md"
  - "hard_gate_mapping.md"
  - "downstream_milestone_graph.md"
  - "completion_check.md"
  - "review_request.md"
  - "MANIFEST.md"
forbidden_substitutes:
  - "another mega-goal"
  - "natural-language-only warnings without machine-checkable gates"
  - "final audit without completion_check readiness"
  - "route promotion"
  - "validation packaging or upload"
---

# Milestone M0: SRR-v3 Architecture Master Contract

## Goal

Create the binding SRR-v3 / SRR-ProposeRefine master contract before any new implementation. This milestone must turn the lessons from the SRR-v2.5 diagnostic packet and hard-gate repair into a small, checkable milestone graph. It must not edit model code, run training, package validation, upload, expand folds, or claim route promotion.

## Required Reading

Read the required input files listed in frontmatter. If `results/20260705_handoff_hard_gate_repair/review.md` is not `AUDITED_GO`, stop with `NEEDS_REVISION`.

## Architecture Story To Lock

The next SRR-v3 story is:

1. nnU-Net is the protected baseline anchor and supplies probabilities/logits, hard prediction, components, uncertainty, and anatomy context.
2. SRR remains the scientific branch: availability-aware modality stems, strong encoder/context path, semantic retrieval dictionary, real train/OOF prototypes, pathology-specific proposal/refinement, and no-T2-safe edema behavior.
3. The final MyoPS output is a baseline-preserving bounded correction, not a from-scratch replacement: `final = nnU-Net anchor + gated SRR residual` or an explicitly equivalent probability mixture.
4. The first scientific question is not "can a 6-step smoke beat nnU-Net" but "can SRR learn where to open the gate and produce bounded helpful corrections on cases where nnU-Net is uncertain or wrong, while preserving already-correct regions".
5. Cine remains secondary and cannot block MyoPS. Cine work must stay diagnostic until a same-safe-subset registration/temporal evidence matrix exists.

## Required Work

Write a master contract that specifies:

- exact inputs and outputs for the SRR-v3 MyoPS model;
- how nnU-Net anchor/context is represented and aligned;
- how gate/residual statistics must be exported;
- how prototype banks must prove T2-present edema coverage;
- how dictionary/proposal/refinement modules are considered runtime-active rather than utility-only;
- minimum effective training fields for later pilot work;
- exact completion and review gates for each downstream milestone.

## Strict Validation

Run read-only validation only:

- strict anti-laziness validator on the known bad SRR-v2.5 full-completion packet must still fail;
- if a diagnostic-non-strict validator is used, it must be labeled diagnostic and not used as a completion pass;
- verify every downstream milestone path and expected result directory in `downstream_milestone_graph.md`.

## Required Outputs

Write the required output files under `results/20260705_srr_v3_m0_architecture_master_contract/`.

`completion_check.md` must contain one of:

- `M0_READY_FOR_REVIEW`
- `M0_NEEDS_REVISION`
- `M0_NEEDS_EVIDENCE`

A separate read-only reviewer should later write `review.md` with one of:

- `M0_AUDITED_GO`
- `M0_AUDITED_NEEDS_REVISION`
- `M0_AUDITED_NEEDS_EVIDENCE`

## Completion Gate

Do not mark ready unless the architecture contract and downstream graph are machine-checkable by exact file paths and result directories. Do not start M1 from this task.
