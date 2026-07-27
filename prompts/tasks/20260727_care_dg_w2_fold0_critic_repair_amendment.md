# CARE-DG W2 Fold0 Critic Repair Amendment

**Task:** `20260727_care_dg_dual_pathology_validation`  
**Priority:** highest; overrides conflicting continuation wording in the original CARE-DG Controller/Executor plan.  
**Decision:** pause new formal folds, repair semantics, invalidate pre-repair fold0 for scientific credit, rerun fold0, then continue folds 1–4 only after the repair gate passes.

## 1. Immediate operational action

Do not terminate allocation `60657290`. Do not submit a new job.

If fold1 or any later fold is currently running, save the nearest safe checkpoint and stop that CARE-DG training process. Mark all pre-repair formal checkpoints and curves as:

```text
PRE_REPAIR_INVALID_SEMANTICS_DIAGNOSTIC_ONLY
scientific_credit: 0
```

Preserve them for provenance; do not overwrite or delete them. Folds 1–4 must not continue until repaired fold0 passes the gates below.

## 2. Why pre-repair fold0 is not scientifically valid

### A. Edema-zone contract is not implemented

The blueprint requires the edema decoder to predict injured-tissue zone `scar ∪ edema`, followed by scar-priority composition:

```text
zone target = label in {scar, edema}
pure edema = corrected zone - corrected scar
```

Current code builds edema targets only from compact class `4` and returns both `edema_zone_mask` and `pure_edema_mask` from the exclusive class-4 argmax. This silently changes the scientific task and must be repaired.

### B. FP margin loss has the wrong direction

Current margin code requires `final_margin - anchor_margin >= m` for both FN and FP voxels. This correctly raises FN margins but incorrectly raises pathology margins on FP voxels.

Required:

```text
FN: final_margin - anchor_margin >= m
FP: anchor_margin - final_margin >= m
```

Scar and edema/zone losses must use separate FN and FP masks.

### C. Gate/magnitude factorisation has collapsed

Fold0 Stage B reports mean gates around `0.004–0.007` while correction delta standard deviation remains around `1.3–1.45` and thousands of voxels change. This means unbounded `softplus(magnitude)` can compensate for near-zero gates, so `q_FN/q_FP` no longer functions as an interpretable error probability.

Replace unbounded magnitude with a bounded parameterisation, for example:

```text
m_k = M_k * sigmoid(raw_m_k)
delta_k = q_FN * m_FN - q_FP * m_FP
```

`M_k` must come from the outer-training anchor-error margin distribution specified by the blueprint, clipped to `[2,8]`; it must not be a fixed unverified `4.0` unless the train-side quantile audit yields exactly that value.

Log gate and magnitude statistics separately on true FN, true FP and anchor-correct voxels, plus correction clipping/saturation fraction.

### D. Scar competitor semantics are inconsistent

Current correction subtracts only the highest anatomy channel `0–3`, while scar loss compares scar against all channels `0–4`. The model therefore cannot reliably convert a voxel currently classified as edema into scar.

Required:

- scar correction competitor = highest channel among all classes except scar, including edema;
- edema-zone correction is a binary injured-zone-versus-anatomy decision, not an exclusive class-4 correction;
- use the same margin definition in correction, training loss and evaluation.

### E. Reliable-label loss is not correctly expressed

Current global six-class CE is applied to all cases even though anatomy/edema annotation sets vary by centre. The model only owns pathology correction and should not learn from silent classes as negatives.

Required:

- scar binary segmentation/error losses only on scar-reliable cases;
- edema-zone binary segmentation/error losses only on T2-present reliable cases;
- no-T2 cases contribute exactly zero edema loss and zero edema gradient, including in mixed batches;
- do not multiply an all-batch edema loss by `t2.mean()`; apply per-case/per-voxel supervision masks before reduction;
- global six-class CE may be used only on explicitly fully supervised complete cases and only if a matched ablation justifies it; default repair is pathology-specific masked binary objectives.

### F. Remote penalty currently observes post-support delta

The model returns `scar_delta/edema_delta` after multiplying by support. The trainer then multiplies by `(1-support)`, which makes the remote term zero or nearly vacuous. Expose both raw pre-support delta and applied delta. Compute the remote penalty from raw correction outside soft support.

### G. Formal source and validator provenance is incomplete

`implementation_contract.json` lists hashes for `scripts/training/run_care_dg.py`, inference/evaluation scripts and validator, but these files are absent from remote main in the W0/W1/fold0 commit. A strict validator report cannot be accepted when its source is not committed and inspectable.

Before resuming formal training, commit locally in the runtime worktree all exact source/config/test files used for fold0, including:

```text
scripts/training/run_care_dg.py
scripts/inference/run_care_dg_inference.py
scripts/evaluation/evaluate_care_dg.py
scripts/evaluation/select_care_dg_candidate.py
scripts/evaluation/validate_care_dg_packet.py
```

The runtime role still must not push. Record source hashes in the repaired fold receipt.

### H. Formal input contract must be audited

The anchor asset is stored as nnU-Net probabilities. Formal mode must prove whether the network receives genuine logits or `log(clamp(probability))`; raw probabilities must not be silently treated as logits.

Formal mode must also reject absent `uncertainty`, soft support and distance maps instead of silently replacing them with zeros/ones. Defaults are permitted only in unit tests.

### I. Error-centric sampling is not reviewable

The committed dataset file contains tensor validation and an in-memory test dataset, but not the formal loader/sampler. Commit and audit the exact formal case loader and sampler. Receipts must demonstrate the frozen batch quotas:

```text
50% FN/FP error-centred, balanced FN and FP
25% pathology/boundary-centred
25% hard-negative/random anatomy
```

### J. Validation package asset is incomplete

W0 records zero Cine validation cases, while the final official package requires the frozen 15-case Cine tree. Bind the exact existing Cine prediction source, case list and hashes before W5. CARE-DG does not retrain Cine, but the package cannot be audited with `cine_validation_cases: 0`.

## 3. Required repair tests

Add and pass tests/receipts for all of the following:

1. FN margin gradient raises pathology/zone margin.
2. FP margin gradient lowers pathology/zone margin.
3. Scar correction can convert an anchor edema voxel into scar.
4. Edema target is `scar ∪ edema`; final pure edema is corrected zone minus corrected scar.
5. Mixed batch containing T2-present and no-T2 cases gives exactly zero edema gradient for no-T2 samples before reduction.
6. Bounded magnitude cannot compensate for a zero gate; `q=0` implies zero correction.
7. Magnitude is within the fold-specific bound and clipping/saturation is reported.
8. Remote penalty is non-zero for a synthetic raw correction outside support.
9. Formal mode rejects missing support/uncertainty/distance and raw-probability-as-logit ambiguity.
10. Formal sampler quota audit passes on at least 1,000 sampled patches.
11. Strict validator known-bad fixtures fail when any of the above semantics is violated.
12. Exact formal runner/evaluator/validator source hashes match the local committed files.

## 4. Repaired W1/W2 gate

Rerun the 300-step real-case overfit after repair. In addition to loss reduction, require:

```text
median q_FN on true FN >= median q_FN on non-FN + 0.10
median q_FP on true FP >= median q_FP on non-FP + 0.10
correct-direction correction on >=10% anchor error voxels
scar and edema-zone each change non-zero voxels
correction saturation fraction <=30%
no-T2 edema changed voxels and gradient = 0
```

Then rerun formal fold0 from the original seed and full `5000 + 3000` schedule. The old fold0 is not resumed because its loss semantics changed.

After repaired fold0 completes, generate a non-selection health packet containing:

- full source/config/checkpoint hashes;
- train-side bound quantiles;
- sampler quotas;
- gate/magnitude/error-voxel calibration;
- held-out mechanism activation;
- scar, edema-zone and pure-edema diagnostic metrics;
- help/harm, exact-HD and remote-FP diagnostics.

Outer fold0 metrics must not be used to tune architecture or thresholds. They are used only to verify that the repaired implementation is not catastrophically inverted.

## 5. Continue/stop rule

Continue folds 1–4 automatically only when all semantic tests, repaired overfit gate and repaired fold0 health packet pass.

Do not stop merely because fold0 does not beat nnU-Net. Do stop and return `NEEDS_REPAIR` if any of the following remains:

- edema-zone/pure-edema semantics wrong;
- FP correction direction wrong;
- gate bypass through magnitude;
- raw probabilities used as logits;
- partial-label leakage;
- remote penalty vacuous;
- formal source/validator not committed locally;
- no-T2 edema leakage;
- mechanism output is effectively identity or correction saturation is uncontrolled.

Once repaired fold0 passes, continue the original W2–W6 contract in allocation `60657290`, with no new Slurm job, no validation upload and no runtime push.