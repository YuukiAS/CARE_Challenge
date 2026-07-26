# MoSAIC Hosted-Gap Forensics Controller Amendment

**Task:** `20260726_care_mosaic_validation_gap_forensics_and_final_blueprint`  
**Status:** `READY_FOR_CONTROLLER`  
**Precedence:** This amendment has higher precedence than conflicting wording in:

- `prompts/tasks/20260726_care_mosaic_validation_gap_forensics_and_final_blueprint_controller.md`
- `prompts/tasks/20260726_care_mosaic_validation_gap_forensics_and_final_blueprint_executor_plan.yaml`

Non-conflicting requirements in the original Controller Prompt and executor plan remain binding.

## 1. User-confirmed hosted lineage

The user explicitly confirms that no new validation submission was made after June 2026 and that the OrganAgent scar score `0.6965` belongs to the earlier MoSAIC submission. Freeze this fact as:

```text
model_family_lineage: USER_CONFIRMED_MOSAIC
hosted_scar_dice: 0.6965
model_family_attribution_reopen: false
```

The Controller must not spend the task deciding whether the model family was MoSAIC, and must not downgrade the model-family attribution to unresolved merely because the exact ZIP is absent.

Keep two evidence layers separate:

1. **Model-family attribution:** user-confirmed MoSAIC.
2. **Exact artifact and recipe attribution:** ZIP, prediction tree, checkpoint, coarse model, TTA, thresholds, containment, component cleanup, largest-component processing, command and timestamp still require machine evidence.

If exact artifact lineage remains unavailable, the correct claim is:

```text
user-confirmed MoSAIC hosted scar Dice 0.6965;
exact package, checkpoint and inference recipe unresolved
```

User attestation must never be used to claim that a particular local ZIP, checkpoint or reconstructed recipe is the exact hosted artifact.

Update hypothesis H5 to:

```text
H5: the 0.6965 model family is confirmed as MoSAIC, but the exact ZIP,
checkpoint, coarse model, TTA, threshold, post-processing or local
reconstruction may differ from the hosted submission.
```

## 2. Mandatory Controller repair loop

The Controller is the acceptance owner and must repair ordinary in-scope defects rather than stop at the first failure.

The following are repairable inside the current task:

```text
source/import/environment defects
cache and path defects
geometry, orientation and label-mapping defects
checkpoint-loading defects
inference-recipe defects
evaluator or metric-population defects
test and known-bad defects
aggregation, finalizer and validator defects
wiki/CURRENT inconsistencies
stale task-local locks whose holder no longer exists
```

For every repairable failure, perform this exact loop:

```text
detect gap
-> record root cause and failed attempt in repair_ledger.csv
-> return the gap to the same Executor
-> apply the smallest semantics-preserving repair
-> inspect the real diff and old/new hashes
-> rerun the failed command
-> rerun affected upstream and downstream aggregation/validators
-> inspect output contents, not only file existence
-> continue only after PASS
```

The Controller must preserve failed attempts, commands, exit codes, modified files and fingerprints. It must not silently change the frozen split, case population, model semantics, training budget, threshold grid, decode rule or metric definition.

The Controller must not ask the user to resolve ordinary repairable defects and must not treat a negative scientific result as an operational blocker. A failed hypothesis still requires completion of the remaining attribution, historical mechanism audit, candidate-v2 evaluation, blueprint adjudication and safe fallback decision.

Stopping is allowed only when one of these conditions is proved:

1. allocation `60657290` has terminated before remaining required GPU work can run;
2. a required raw asset or checkpoint is objectively absent and cannot be reconstructed from existing assets;
3. disk, permission or external cluster failure remains unrecoverable after direct verification;
4. repair would require a new Slurm allocation, external data, a new backbone or a change to the frozen scientific contract.

## 3. Existing allocation and workspace safety

All GPU work must use only:

```text
job_id: 60657290
partition: htzhulab
node: g1807htzh01
```

Forbidden:

```text
sbatch
salloc
new Slurm job
parallel GPU training or inference
validation upload
Docker upload
git push by runtime roles
```

At bootstrap:

- inspect `squeue --steps`, `scontrol show job`, `nvidia-smi` and live processes;
- create a task-local atomic GPU lock;
- do not overwrite an active lock; a lock is stale only when its PID and Slurm step no longer exist;
- release GPU memory and verify no orphan process after every GPU command;
- do not run `git reset --hard`, `git clean`, or delete unknown user files;
- classify pre-existing tracked/untracked changes and exclude task-external changes from the final commit;
- use atomic writes and isolated temporary directories so partial reruns do not overwrite existing OOF predictions, checkpoints or historical evidence.

Add these W0 outputs:

```text
results/20260726_care_mosaic_validation_gap_forensics_and_final_blueprint/user_attested_lineage_receipt.json
results/20260726_care_mosaic_validation_gap_forensics_and_final_blueprint/repair_ledger.csv
results/20260726_care_mosaic_validation_gap_forensics_and_final_blueprint/resource_budget_plan.json
results/20260726_care_mosaic_validation_gap_forensics_and_final_blueprint/existing_allocation_gpu_lock.json
```

## 4. Resource priority and optional matched training

The blocking scientific priority is:

```text
W0 bootstrap
-> W1 exact-artifact lineage
-> W2 canonical 220-case OOF
-> W3A-C recipe/domain/rank-reversal attribution
-> W4 historical CARE audit
-> W5 candidate dataset v2 and final-mask gate
-> W6 final blueprint adjudication
-> W7 validators, Mapper, CURRENT/wiki and local commit
```

W3D matched target-weighted training is optional and lower priority than W4-W7. It may run only when:

```text
remaining_seconds >= max(
    64800,
    2 * p90_reference_fine_scar_full_run_seconds + 28800
)
fold0 cache/coarse predictions/checkpoints are complete
writable disk >= 50 GiB
estimated completion still leaves >= 8 hours for W4-W7
```

If the guard fails, write `NOT_RUN_RESOURCE_OR_ASSET_GUARD`. Do not replace a full 300-epoch matched run with a short run. Failure to run W3D must not block the core attribution and final Docker decision.

## 5. Evaluation and attribution safeguards

Before the full 220-case evaluation, run an evaluator-parity sentinel on known fold0 outputs and at least two cases from different modality groups. Dice, HD95, exact HD, label mapping and orientation must match the existing canonical results within a preregistered tolerance. Repair parity before bulk evaluation.

Use these recipe labels:

```text
R0-R4: preregistered incremental factors
R5: current upstream native hosted-style reconstruction
R6: exact historical package recipe, only when exact artifact lineage is resolved
```

R5 must not be described as the exact historical hosted recipe.

Generate two additional diagnostics:

```text
full_data_vs_oof_inclusion_lift.csv
full_data_vs_oof_inclusion_lift_interpretation.md
validation_full_data_vs_fold_ensemble_disagreement.csv
validation_prediction_risk_summary.md
```

The full-data-versus-OOF training-set lift is contaminated and may only be reported as an optimistic upper bound on case-inclusion/memorization effects, not as generalization gain. On the 15 unlabeled validation images, compare the full-data MoSAIC model with the five clean fold models using probability, component, volume, confidence and fold-disagreement measures without validation GT.

## 6. Candidate-v2 and gate leakage controls

Candidate generation and deterministic merging must be GT-blind. GT may only define training-fold counterfactual utility and held-out evaluation.

For nested cross-validation:

- outer grouping follows original case/fold boundaries;
- standardization, missing-value handling, feature selection, calibration and prototypes are fit only on the outer training cases;
- no held-out case or component may enter preprocessing statistics or prototype banks;
- inner CV selects regularization and thresholds;
- reconstructed final-mask Dice, HD95, exact HD, precision, recall, remote FP, components, volume and help/harm are required;
- component classification F1 is diagnostic only.

Gate roles:

```text
G0 global all-220: primary scientific evidence
G1 complete-trimodal: primary target-matched evidence
G2 validation-domain weighted: transductive diagnostic only
```

G2 must not be the sole reason for promotion or final architecture selection.

## 7. Additional known-bad cases

The strict validator must reject at least:

```text
user attestation used to claim an exact ZIP/checkpoint/recipe
R5 current reconstruction described as exact historical package
full-data-vs-OOF contaminated lift described as generalization gain
standardization/prototype/feature selection fit before outer CV split
G2 alone used to promote a model
candidate generation or merge using GT
active GPU lock overwritten or concurrent GPU process started
first repairable error converted into Controller stop or user clarification
optional W3D failure used to block W4-W7
```

## 8. Terminal answer requirements

The final report must state:

1. `0.6965` is user-confirmed as MoSAIC;
2. whether the exact ZIP, checkpoint and recipe were machine-bound;
3. quantified contributions of target modality structure, validation-domain similarity, full-data inclusion/selection, inference recipe, 15-case sampling and metric/export semantics;
4. residual uncertainty caused by missing validation GT;
5. which Batch7, MMRD and Cascade mechanisms have independent incremental evidence;
6. why the old SafeScar Step3 gate is or is not scientifically sufficient;
7. the single selected final Docker architecture and exact fallback;
8. which actions remain unauthorized.

All required validators, Mapper updates, CURRENT/wiki updates, aggregation and the local lightweight commit must complete before `VERIFIED_COMPLETE`. Runtime roles must not push.