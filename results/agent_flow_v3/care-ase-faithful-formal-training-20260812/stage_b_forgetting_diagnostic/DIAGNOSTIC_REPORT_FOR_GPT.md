# CARE-ASE Stage-B Forgetting Diagnostic

第一轮只读诊断已经把现有 formal-inner 35-case 证据、训练 sampler 日志、checkpoint 参数漂移和静态 runtime 语义审计分开汇总。当前证据说明这不是单纯的评估口径问题：fold3 no-T2/partial scar 在 Stage B 中确实从 step2000 的较高召回退化到 step6000 的近乎全空预测；同时没有发现足以停止当前 formal training 的新实现性硬错误。GPU-only 的 logit margin、extent/wall intervention、named evidence intervention 和 actual-train full-volume 对照仍在独立诊断支线中继续补齐，不能用于 checkpoint selection 或 early stop。

## Scope

- metric source: `FORMAL_35_CASE_INNER`, `ACTUAL_TRAIN_DIAGNOSTIC`, `CORE_6_CASE_INNER_TREND_PANEL` separated by name.
- no outer labels or predictions were read by this script.
- no model, loss, sampler, schedule, checkpoint, decode, threshold, or training runtime file was modified.
- current frozen formal training should continue to 14000 unless a later GPU runtime audit finds a hard implementation blocker.

## Formal Inner Subgroup Trend

| fold | step | complete scar Dice | no-T2 scar Dice | complete edema Dice | no-T2 empty scar cases |
|---:|---:|---:|---:|---:|---:|
| 2 | 2000 | 0.9612666359 | 0.8725440016 | 0.9050795677 | 0/22 |
| 2 | 4000 | 0.9290378121 | 0.7628540223 | 0.8438352973 | 0/22 |
| 2 | 6000 | 0.9301653101 | 0.6676542406 | 0.8406347986 | 0/22 |
| 3 | 2000 | 0.9540311476 | 0.8619067384 | 0.9085376841 | 1/22 |
| 3 | 4000 | 0.9197636795 | 0.5301955064 | 0.8567744349 | 1/22 |
| 3 | 6000 | 0.919633265 | 0.04545454545 | 0.8516145271 | 22/22 |

## Sampler Effective Supervision First Pass

| fold | steps | partial scar events | bad fallback rate | unexpected random rate | candidate coord mean | supervision gap flag |
|---:|---:|---:|---:|---:|---:|---|
| 2 | (2000,4000] | 1000 | 0 | 0 | 1325.518 | False |
| 2 | (4000,6000] | 1000 | 0 | 0 | 1312.638 | False |
| 2 | (6000,7000] | 500 | 0 | 0 | 1254.352 | False |
| 3 | (2000,4000] | 1000 | 0 | 0 | 1270.706 | False |
| 3 | (4000,6000] | 1000 | 0 | 0 | 1252.818 | False |
| 3 | (6000,7000] | 122 | 0 | 0 | 1235.098361 | False |

## Runtime Semantic First Pass

- no-T2 decode class set `[0,1,2,3,5]` static pass: `True`
- `disable_extent_wall` forward argument present: `True`
- named evidence disabling API present: `True`
- status: `NO_PARTIAL_RUNTIME_SEMANTIC_BUG_FOUND_IN_STATIC_METADATA_FIRST_PASS_GPU_FORWARD_PENDING`

## Causal Diagnosis Status

- PRIMARY_CAUSE: `UNRESOLVED_GPU_LOGIT_AND_ACTUAL_TRAIN_DIAGNOSTICS_PENDING`
- STRONG_SIGNAL: `REAL_STAGE_B_PARTIAL_NO_T2_SCAR_FORGETTING_IN_FORMAL_INNER`, especially fold3.
- RULED_OUT_OR_WEAK_CAUSES: sampler omission is weak in this first pass because Stage B logs show substantial partial-scar events with low/no fallback in the inspected windows.
- UNRESOLVED: final myocardium competition vs scar-logit collapse, extent/wall negative bias, named evidence contribution loss, actual-train collapse vs held-out overfit.

## Required Files

- `subgroup_checkpoint_trend.csv`
- `actual_train_vs_inner_partial.csv`
- `sampler_effective_supervision.csv`
- `parameter_drift.csv`
- `runtime_semantic_audit.json`
- GPU-only placeholders: `logit_margin_trend.csv`, `extent_wall_intervention.csv`, `evidence_intervention.csv`
