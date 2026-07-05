# Execution Plan: 20260704 SRR-v2.5 Full Completion Goal

controller_task: `prompts/tasks/20260704_srr_v25_full_completion_goal.md`
controller_state: `EXECUTION_PLANNED`
human_approval: interpreted from the active user goal request on 2026-07-04
external_upload: forbidden
validation_packaging: forbidden
git_commit: disabled by task frontmatter
git_push: disabled by task frontmatter

## Scope Lock

This controller goal is not a rerun of the current anchored PropRef packet. The
current anchored packet is negative evidence and may be used only as a baseline
or failure source. Completion requires the requested SRR-v2/v2.5 mechanisms to
exist in callable code, be exercised by formal runners or tests, and be
reviewed by a separate read-only audit.

## Ordered Work

1. `20260704_srr_v25_visual_contract_lock`
   - Lock the visual SRR-v2/v2.5 contract from `images/SRR-v2.png` and
     `images/SRR-v2.5.png`.
   - Status target this turn: `PASS_WITH_RENDER_LIMITATION` if direct render
     remains blocked, with hash/OCR/image metadata evidence.
2. `20260704_srr_v25_anti_laziness_acceptance_tests`
   - Add validator code under `scripts/validation/`.
   - Add CPU tests that catch known shallow substitutes.
3. `20260704_srr_v25_gap_matrix_and_contract`
   - Build a current source-line gap matrix against committed code.
   - Link every high-impact gap to a downstream subtask and validator check.
4. MyoPS main implementation chain
   - Encoder/context interface.
   - Baseline-preserving nnU-Net residual/gated correction.
   - `P_union/P_LV/P_RV` anatomy distance ROI prior.
   - Semantic retrieval dictionary.
   - Real train/OOF prototype banks.
   - Pathology-specific proposal/refinement.
   - Active objective ablations.
   - Same-split nnU-Net help/harm metrics.
5. Cine secondary chain
   - Registration option matrix with CineMA/SyN/VoxelMorph evidence or concrete
     blockers.
   - Temporal dictionary integration only after registration input contract is
     known.
6. Read-only completion check and final read-only audit.

## Controller Boundaries

- Do not package or upload validation outputs.
- Do not expand folds before implementation, sanity, and audit gates pass.
- Do not use file presence as completion evidence.
- Do not mark `STOP_*` or scientific stop states from partial or undertrained
  evidence.
- Do not commit or push from this controller task.

## Subagent Use

A read-only explorer was launched to collect current SRR source-line gap
evidence. The controller remains responsible for integrating evidence and for
not treating explorer output as audited final review.
