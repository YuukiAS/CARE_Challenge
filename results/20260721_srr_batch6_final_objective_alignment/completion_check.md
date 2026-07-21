# Batch6 Controller Completion Check

controller_verification_decision: VERIFIED_COMPLETE
executor_role: batch6_executor_only
scientific_signal_class: BELOW_USABLE
experiment_adequacy_decision: MECHANISM_REPAIRED_BUT_NOT_USEFUL_STOP_AT_300

## Wave Status

- B6-01 Batch5 reconciliation: COMPLETE, optimizer_steps: 0, parameter hash unchanged.
- B6-02 final objective and 13-channel production gate implementation: COMPLETE at code/test/runtime-audit level.
- B6-03 fixed Case2002+Case1002 60-step overfit: PASS in job `59743323`, formal training credit `0`.
- B6-04 formal 300-step fold0 calibration: COMPLETED in job `59744053`; 44-case eval at steps 100/200/300.
- B6-05 conditional 900-step extension: SKIPPED because the step-300 continuation gate failed.
- B6-06 final mechanism interventions: COMPLETED in job `59744941` on selected step300 checkpoint.
- B6-07 mapper/wiki/fingerprint and strict validation: prepared for controller verification.

## Fixed Overfit Gate

Latest passing attempt: `59743323`

- combined final pathology loss decrease: `0.22169648876881362` required `>= 0.20`
- scar final pathology loss decrease: `0.16623363430373905` required `>= 0.15`
- edema final pathology loss decrease: `0.26412012419374487` required `>= 0.15`
- gate repair/preserve loss decrease: `0.3865146147271092` required `>= 0.10`
- production gate repair gradient L2 max: `2010.4200978300662`
- final logits max abs change from step0: `7.999979496002197`
- Case1002 no-T2 edema exact zero: `True`
- save/reload final logits max abs delta: `0.0`

## Formal 300 Gate

Decision: FAIL, stop at 300.

- mean scar/edema positive Dice delta: `0.001699358420302757` required `>= 0.003`
- edema positive Dice: anchor `0.3944358976789887` -> SRR `0.3971606463518259`, delta `0.0027247486728372468`
- scar positive Dice: anchor `0.573196419478004` -> SRR `0.5738703876457723`, delta `0.0006739681677682672`
- help/harm: `25` / `18`
- HD95 relative worsening max: `0.0007215141609442357`
- remote-FP relative worsening max: `0.03255813953488372`
- no-T2 edema exact zero: `True`
- finite losses and gradient gate: `True`

Because the mean-delta check failed, no 900-step extension was submitted.

## Forbidden Actions

No validation upload, hosted claim, fold expansion, Cine work, backbone swap, prototype rebuild, push, route promotion, M11, reviewer, or Batch7 start was performed.
