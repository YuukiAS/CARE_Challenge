# SRR Recovery Root Cause

task: `prompts/tasks/20260625_srr_recovery.md`

## Findings

1. The strongest identified cause of the previous gate collapse is the retrieval regularizer direction in `src/care_myocardium/losses/srr_losses.py`: the prior implementation added positive entropy to the minimized loss, which encourages lower entropy and therefore one-hot routing. This is consistent with previous logged max row weights of `1.0000`.
2. Scar concentration on expert1 may be partly defensible because scar is LGE-dominant and LGE is always present, but `scar expert1 mean=0.9431` plus row-level max `1.0000` is too one-hot to treat as healthy specialization without additional evidence.
3. Edema usage was healthier than scar in the previous run (`expert0=0.4126`, `expert1=0.2996`, `expert2=0.2864`), suggesting the dictionary path can use multiple experts when the supervision signal is aligned with availability.
4. All-case edema was inflated by no-T2 empty-GT stability; the recovery gate must continue to emphasize GT-positive and T2-present/complete subsets.
5. Scar absolute Dice remains low; likely contributors are short effective training, class imbalance/loss balance, and weak routing regularization rather than a proven label mapping or evaluator failure.

## Repair Applied Before Jobs

- Replaced entropy minimization with an entropy-floor penalty, coverage penalty, and max-weight penalty.
- Added router temperature support.
- Added training-time expert dropout that only affects valid experts and never removes all valid experts for a sample.
- Added task-specific router temperature support for scar/edema/anatomy.
- Added fold0 runner variants: `srr_soft_entropy`, `srr_expert_dropout`, and `srr_task_tempered`.

## Guardrails

- Fold split, compact labels, raw export labels, evaluator, and T2-masked edema supervision remain unchanged.
- New outputs are isolated under `results/20260625_srr_recovery/`.
- No validation upload, network, external data, external weights, folds 1-4, or third-party baseline edits are used.
