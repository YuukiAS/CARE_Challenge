---
task_key: "20260704_srr_v25_gap_matrix_and_contract"
project: "CARE_Challenge"
status: "READY_FOR_USER_REVIEW"
task_type: "execution"
risk_level: "medium"
allow_code_change: false
allow_shell_command: true
allow_network: false
allow_external_upload: false
review_required: true
mechanism_class: "gap matrix / full SRR-v2.5 contract lock"
required_evidence: ["diagram_to_code_gap_matrix", "high_impact_gap_ranking", "no_lazy_completion_contract", "source_line_evidence"]
forbidden_substitutes: ["reusing previous audit without new source-line gap matrix", "treating partial implementation as complete", "minor-only recommendations"]
---

# Task: Full SRR-v2.5 Gap Matrix And Contract

## Goal

Create a binding gap matrix between the SRR-v2/v2.5 diagrams and current committed code. This task must rank gaps by likely effect on Dice, not by ease of implementation. It must identify which missing pieces are likely responsible for scar degradation, edema GT-positive weakness, CenterC failure, high component count, and remote false positives.

## Required Inputs

Read `images/SRR-v2.png`, `images/SRR-v2.5.png`, `results/20260704_anchor_srr_forensic_repro_audit/review.md`, `implementation_claim_truth_table.md`, `src/care_myocardium/models/srr_propref.py`, `src/care_myocardium/models/srr_v2_unet.py`, `src/care_myocardium/models/srr_blocks.py`, `src/care_myocardium/models/proposal_prototypes.py`, `src/care_myocardium/losses/srr_losses.py`, and `scripts/training/run_srr_propref_myops_fold0.py`.

## Required Output

Write `results/20260704_srr_v25_gap_matrix_and_contract/` with:

- `result.md`
- `diagram_to_code_gap_matrix.md`
- `high_impact_gap_ranking.md`
- `no_lazy_completion_contract.md`
- `source_line_evidence.md`
- `MANIFEST.md`

## Required Gap Categories

Cover at least these categories: encoder/backbone capacity, nnU-Net context interface, multi-slot retrieval semantics, dictionary supervision, data-derived prototype banks, proposal decoder quality, crop refiner behavior, SRR-v2/v2.5 loss stack, training/ablation adequacy, same-split nnU-Net context comparability, CineMA, registration, and temporal dictionary.

## Completion Gate

Do not mark `PASS` unless every high-impact gap has a downstream subtask and an anti-laziness acceptance test. If evidence is missing, use `NEEDS_EVIDENCE`, not `PASS_DIAGNOSTIC`.
