# CineMyoPS round7 prompt: pathology_direct validation packaging and hosted-metric check

你是 CARE-Myocardium 项目的代码实现与实验 agent。请在 `/overflow/htzhu/CARE` 中继续 CineMyoPS。本轮目标不是继续训练，而是把 round6 已经超过 nnU-Net local reference 的 `pathology_direct` fixed-inference 策略推进到 official validation submission-ready 状态，并验证 submission pipeline 是否真正使用该策略。

## 必须先读

- `docs/notes/CineMyoPS_improvement_round6.md`
- `results/experiments/CineMyoPS_iteration_log.md`
- `prompts/CineMyoPS/prompt6_fixed_inference_class1_repair.md`
- `logs/CineMyoPS_r6_modes_51367766_20260518_024719.log`
- `results/metrics/unified/CineMyoPS_R6_pathology_direct/fold_0/evaluation_summary.json`
- `scripts/submission/prepare_care_myocardium_validation.py`
- `jobs/submission/prepare_care_myocardium_validation.sh`
- `README.md`
- `AGENTS.md`

## 当前事实

Local protocol fold0:

| model/variant | class_1 myocardium | class_2 LV | class_3 scar | foreground_mean |
| --- | ---: | ---: | ---: | ---: |
| nnU-Net Dataset502 5-fold reference | 0.6808 | 0.8874 | 0.2586 | - |
| nnU-Net Dataset502 fold0 reference | 0.6864 | 0.9036 | 0.2446 | 0.6115 |
| CineMyoPS round6 `pathology_direct` | 0.6933 | 0.9316 | 0.4378 | 0.6876 |
| CineMyoPS round6 `class1_primary_overlay` | 0.6934 | 0.9316 | 0.4374 | 0.6875 |
| CineMyoPS round6 `cardiac_only` | 0.7611 | 0.9316 | 0.0000 | 0.5642 |

Round6 conclusion:

- `pathology_direct` is the best paper-aligned candidate: it keeps the pathology branch active and exceeds nnU-Net local class_1 and class_3 references.
- `cardiac_only` is only an anatomy upper bound; do not use it as final because it drops the pathology branch.
- Next step is hosted validation, not more local fold0 tuning.

## Round7 目标

1. Make the validation submission pipeline explicitly support and record `CINE_COMBINE_MODE=pathology_direct`.
2. Prepare a submission package using:
   - MyoPS side: conservative nnU-Net default.
   - CineMyoPS side: `Task026_Cine_4D`, `CARECineMyoPSTrainerBNCalib`, `model_final_checkpoint`, `CINE_COMBINE_MODE=pathology_direct`, `CINE_NUM_FRAMES=4`.
3. Ensure the workspace/prediction cache is isolated and the manifest records the Cine combine mode, trainer, checkpoint, task, and folds used.
4. Do not upload automatically unless the user explicitly asks; write upload-ready zip and report the exact path.

## 必须实现或检查

### 1. Submission script combine-mode support

Update `scripts/submission/prepare_care_myocardium_validation.py` if needed:

- Add an argument such as `--cine-combine-mode`, defaulting to `os.environ.get("CINE_COMBINE_MODE", "current")`.
- Pass it into the environment used by `run_cinemyops_predict`.
- Record it in the returned metadata/manifest for the CineMyoPS branch.
- Keep output workspace timestamped and isolated; do not reuse old `_tmp/CineMyoPS_*` protocol prediction dirs.

### 2. Slurm entrypoint

Update or add a short validation packaging wrapper, for example:

- `jobs/submission/prepare_care_myocardium_validation_cinemyops_pathology_direct.sh`

It should use an explicit header from `AGENTS.md` and run something equivalent to:

```bash
./env_CARE/bin/python scripts/submission/prepare_care_myocardium_validation.py \
  --team-name OrganAgent \
  --myops-model nnUNet \
  --cine-model CineMyoPS \
  --folds 0 \
  --checkpoint checkpoint_best.pth \
  --cine-task Task026_Cine_4D \
  --cine-trainer CARECineMyoPSTrainerBNCalib \
  --cine-checkpoint model_final_checkpoint \
  --cine-num-frames 4 \
  --cine-combine-mode pathology_direct
```

Use fold0 only unless folds 1-4 of `CARECineMyoPSTrainerBNCalib` already exist and are proven compatible. Hard-label majority vote across unavailable or mismatched folds is not allowed.

### 3. Package QA

After packaging:

- inspect manifest;
- verify the zip layout contains both `MyoPS/Anonymous Center/...` and `CineMyoPS/Anonymous Center/...`;
- verify Cine predictions are not all background and contain expected compact/raw labels after conversion;
- record any one-voxel fallback cases separately.

## 结果判定

- Success: upload-ready package exists and manifest proves CineMyoPS used `pathology_direct`.
- Strong success: no CineMyoPS validation case required pathology fallback and prediction label counts are plausible.
- If packaging fails because submission script cannot pass combine mode, fix that pipeline bug first.
- If official validation submission is later run and beats nnU-Net on `myocardium_cinemyops`, prepare fold expansion or official final packaging next.
- If hosted metric disagrees with local class_1 proxy, inspect the official metric semantics before training more.

## 禁止事项

- 不要训练新 CineMyoPS 模型。
- 不要使用 `cardiac_only` as final validation candidate.
- 不要 silently fall back to default `CINE_COMBINE_MODE=current`.
- 不要 package stale predictions from `CineMyoPS_R5_fixed_inference` or round4 all-background dirs.
- 不要 upload unless user explicitly asks.

## 交付物

- Code/script changes.
- New report: `docs/notes/CineMyoPS_improvement_round7.md`.
- Append: `results/experiments/CineMyoPS_iteration_log.md`.
- Upload-ready package path and manifest path under `results/submissions/care_myocardium_validation/upload_ready/...`.

最终报告必须明确回答：validation package 是否真实使用了 paper-aligned `pathology_direct` CineMyoPS；是否已经可以交给用户上传；如果不能，阻塞点是什么。
