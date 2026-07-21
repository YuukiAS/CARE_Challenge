# Batch6 Controller Report

controller_verification_decision: VERIFIED_COMPLETE
review_token: NOT_REVIEWED_CONTROLLER_VERIFIED
scientific_signal_class: BELOW_USABLE
next_required_action: RETURN_TO_PLANNER

## What Actually Happened

Batch6 fixed the same-scope loss/gate problem enough for the required two-case fixed-overfit to pass. That means the model can now learn the direction of a bounded scar/edema correction on `Case2002` and `Case1002` when only the production gate and scar/edema refiners are trainable.

The formal 300-step fold0 calibration also ran to completion on the authorized 176/44 split. It did not meet the continuation gate: edema improved by `+0.002724749` Dice on positive cases, scar improved by `+0.000673968`, and their mean was `+0.001699358`, below the required `+0.003`. Therefore Batch6 correctly stopped at 300 and did not submit the 900-step extension.

## Primary Metric Paths

- formal 300 summary: `training_adequacy.json`
- checkpoint selection: `checkpoint_selection.csv`
- subgroup metrics: `subgroup_metrics.csv`
- case help/harm: `help_harm.csv`
- final interventions: `final_mechanism_interventions.csv`
- Slurm ledger: `slurm_attempts.csv`

## Safety / Accounting

- no-T2 edema exact zero: `True`
- help/harm: `25` / `18`
- HD95 relative worsening max: `0.0007215141609442357`
- remote-FP relative worsening max: `0.03255813953488372`
- failed attempts are terminal and recorded with zero formal credit.
- no push, upload, Cine, fold expansion, reviewer, hosted claim, route promotion, M11, or Batch7 was performed.
