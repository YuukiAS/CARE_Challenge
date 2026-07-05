---
task_key: "20260705_srr_v3_architecture_alignment_note"
project: "CARE_Challenge"
status: "READY_FOR_USER_REVIEW"
task_type: "architecture_note"
risk_level: "low"
allow_code_change: false
allow_shell_command: false
allow_network: false
allow_external_upload: false
review_required: true
mechanism_class: "SRR-v3 architecture alignment / nnU-Net role clarification"
expected_result_dir: "results/20260705_srr_v3_architecture_alignment_note/"
blocking: false
---

# SRR-v3 Architecture Alignment Note

## Purpose

This note clarifies the intended relationship between SRR and nnU-Net in the milestone plan. It prevents a wrong interpretation in which nnU-Net becomes the main scientific method and SRR becomes a minor post-processing add-on.

## Correct Interpretation

The scientific method remains SRR-ProposeRefine. nnU-Net is a protected baseline anchor and context provider, not the paper's central contribution.

SRR should provide better context and selective correction so that the final system can outperform the nnU-Net baseline on hard missing-modality and pathology cases. The goal is not to copy nnU-Net. The goal is to learn when and where to trust modality-specific SRR evidence, dictionary retrieval, prototypes, anatomy-guided proposal, and soft-ROI refinement enough to make bounded corrections to nnU-Net.

## Why Baseline Preservation Exists

The previous no-anchor ablation was strongly harmful. Therefore, SRR-v3 must preserve already-correct nnU-Net regions while learning useful corrections in uncertain or error-prone regions. Baseline preservation is a safety envelope, not a downgrade of SRR.

The intended relation is:

```text
final prediction = protected nnU-Net baseline + SRR-learned context-aware bounded correction
```

This means:

- nnU-Net supplies anchor probabilities/logits, hard predictions, components, uncertainty, and anatomy context;
- SRR supplies availability-aware modality encoding, semantic retrieval dictionary, real train/OOF prototypes, anatomy-guided scar/edema proposals, pathology-specific local refinement, and no-T2-safe edema logic;
- the gate decides where SRR correction is allowed to modify the baseline;
- the evaluation must measure both help and harm versus nnU-Net.

## Milestone Alignment With The SRR-v3 Diagram

- M0 locks this architecture story and makes every gate machine-checkable.
- M1 exports the missing runtime evidence needed to understand whether SRR correction is actually active.
- M2 repairs runtime architecture so SRR can open gates on meaningful error-prone regions and use non-empty T2-present edema prototypes.
- M3 tests whether this repaired SRR can learn useful bounded corrections under a minimum-effective pilot budget.
- M4 isolates which SRR mechanisms cause help, harm, or near-identity behavior.
- M5 keeps Cine as a secondary diagnostic line and prevents it from blocking MyoPS.

## Milestone Review Boundary

Each milestone is a two-step gate. The executor/controller writes required
outputs, `completion_check.md`, `review_request.md`, and `MANIFEST.md`, then
stops. It does not write `review.md`, does not approve itself, and does not
start the next milestone. A separate read-only reviewer must write `review.md`
with the exact audited-go state before continuation.

## Non-Goals

- Do not turn SRR into plain nnU-Net copy.
- Do not use nnU-Net only as the final answer.
- Do not let a closed gate plus near-identity metrics count as SRR success.
- Do not promote route candidates without meaningful help/harm evidence.
