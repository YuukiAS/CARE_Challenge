# Repaired Proposal Repeat Repair Contract

Task: `prompts/tasks/20260629_repaired_proposal_repeat.md`

## Implemented Before Formal Jobs

- Ignore-label masking: `src/care_myocardium/losses/srr_losses.py` masks `IGNORE_LABEL=-1` in anatomy CE, scar BCE/Dice, T2-masked edema BCE/Dice, and soft prior loss.
- T2/no-T2 contract: dense edema loss is enabled only for `availability[:, 1] == 1`; no-T2 myocardium/scar voxels are excluded from edema proposal hard negatives.
- Proposal final mixing: `PathologyProposalHead` now supports `proposal_final_mix_weight`; repaired jobs use calibrated values rather than fixed `0.40 evidence + 0.60 proposal`.
- Evidence/proposal/final logits: proposal routes export `scar_evidence_logits`, `edema_evidence_logits`, `scar_proposal_logits`, `edema_proposal_logits`, and final mixed logits for downstream decode audits.
- Hard-negative replay: `scripts/training/run_srr_myops_fold0.py` can read `results/20260629_proposal_memory_hardneg/mined_components.csv`, filter replay-safe components, and sample patches around mined FP component centers.
- Checkpoint candidates: the runner saves both `checkpoint_best.pt` and `checkpoint_final.pt`; downstream decode/checkpoint audit script can compare both.

## Formal Variants

- `repaired_uncertainty_hardneg`: edema/no-T2 stability route with uncertainty loss and edema-safe hard negatives.
- `repaired_posneg_scar_hardneg`: scar-focused positive/negative prototype route with scar safe hard negatives.
- `repaired_joint_calibrated_proposal`: joint scar/edema proposal route with calibrated final mixing and hard-negative replay.

## Remaining Audit After Jobs Finish

- Run decode/checkpoint comparison on the new checkpoints rather than relying on raw argmax.
- Aggregate component burden, remote FP, proposal recall/precision, and subgroup metrics.
- Compare against D4 dictionary, prior proposal variants, and nnU-Net fold0 reference.
