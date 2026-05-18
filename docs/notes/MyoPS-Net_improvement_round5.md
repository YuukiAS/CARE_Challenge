# MyoPS-Net improvement round5

日期：2026-05-17

## 目标

本轮只验证一个主要假设：官方 validation 的 MyoPS cases 是完整 C0+LGE+T2，因此训练一个 full-modality expert，并通过 modality-aware routing 保留缺模态病例的 round4 scar/edema-safe 结果。

## 代码改动

| 文件 | 改动 |
| --- | --- |
| `code/MyoPS-Net/prepare_myops_net_layout.py` | 增加 `--train-require-all-modalities` / `--val-require-all-modalities`，用于只 staging C0+LGE+T2 完整病例 |
| `third_party/MyoPS-Net/utils/config.py` | 增加 `--init_checkpoint`、`--best_metric`、`--best_weight_scar`、`--best_weight_edema` |
| `third_party/MyoPS-Net/train.py` | 支持从 round3 checkpoint 初始化；支持 `weighted_pathology` best checkpoint 选择；`train_stop_summary.json` 记录初始化状态、best metric、best scar/edema/avg |
| `code/MyoPS-Net/run_train.sh` | 透传 checkpoint init 和 best metric 参数 |
| `jobs/MyoPS-Net/sbatch.sh` | 透传 prepare full-modality filters，并打印 round5 关键 env |

## Full-modality staging

Command:

```bash
./env_CARE/bin/python code/MyoPS-Net/prepare_myops_net_layout.py \
  --splits-file data/benchmarks/protocol/splits_MyoPS.json \
  --fold 0 \
  --output data/benchmarks/MyoPS-Net/fold_0_fullmod_round5 \
  --train-require-all-modalities \
  --val-require-all-modalities
```

Result:

| split | before filter | after filter | slice lines | modality composition |
| --- | ---: | ---: | ---: | --- |
| train | 176 cases | 64 cases | 287 | 64 C0+LGE+T2 |
| val | 44 cases | 16 cases | 72 | 16 C0+LGE+T2 |

Metadata: `data/benchmarks/MyoPS-Net/fold_0_fullmod_round5/modalities_present.json`.

## Round5 training job

Submitted Slurm job: `51270455`

```bash
sbatch --export=ALL,FOLD=0,PREPARE=1,MYOPS_NET_DATA=/overflow/htzhu/CARE/data/benchmarks/MyoPS-Net/fold_0_fullmod_round5,MYOPS_NET_WORKDIR=/overflow/htzhu/CARE/results/checkpoints/MyoPS-Net/fold_0_fullmod_round5,MYOPS_NET_VARIANT=challenge3,MYOPS_NET_INIT_CHECKPOINT=/overflow/htzhu/CARE/results/checkpoints/MyoPS-Net/fold_0_maskgated_round3/checkpoints/best.pth,MYOPS_NET_END_EPOCH=80,MYOPS_NET_MAX_RUNTIME_HOURS=7.75,MYOPS_NET_EARLY_STOP_PATIENCE=15,MYOPS_NET_LR=5e-5,MYOPS_NET_MASK_GATED_LOSS=1,MYOPS_NET_MODALITY_DROPOUT=0,MYOPS_NET_PATHOLOGY_SAMPLER=1,MYOPS_NET_SAMPLE_WEIGHT_SCAR=2.0,MYOPS_NET_SAMPLE_WEIGHT_EDEMA=12.0,MYOPS_NET_SAMPLE_WEIGHT_BOTH=4.0,MYOPS_NET_BEST_METRIC=weighted_pathology,MYOPS_NET_BEST_WEIGHT_EDEMA=2.0,MYOPS_NET_BEST_WEIGHT_SCAR=1.0,MYOPS_NET_PREP_TRAIN_REQUIRE_ALL_MODALITIES=1,MYOPS_NET_PREP_VAL_REQUIRE_ALL_MODALITIES=1,MYOPS_NET_EXPORT_EVAL=1,MYOPS_NET_PRED_DIR=/overflow/htzhu/CARE/results/predictions/MyoPS-Net_fullmod_round5/fold_0,MYOPS_NET_EVAL_OUTPUT_DIR=/overflow/htzhu/CARE/results/metrics/unified/MyoPS-Net_fullmod_round5/fold_0 jobs/MyoPS-Net/sbatch.sh
```

Budget:

| item | value |
| --- | --- |
| Fold | 0 only |
| Slurm walltime | 08:00:00 |
| Train runtime guard | 7.75 hours |
| Max epochs | 80 |
| Early stop patience | 15 validation epochs |
| Init checkpoint | `results/checkpoints/MyoPS-Net/fold_0_maskgated_round3/checkpoints/best.pth` |
| Best metric | `weighted_pathology`, edema weight 2.0, scar weight 1.0 |

Queue status: pending on `htzhulab` at creation time. `a100-gpu` had a heavier pending queue and `volta-gpu` was fully busy, so no fallback job was launched.

## Completed result

Round5 full-modality expert produced:

| eval scope | n | myops_edema | myops_scar | conclusion |
| --- | ---: | ---: | ---: | --- |
| complete C0+LGE+T2 fold0 val | 16 | 0.3746 | 0.6163 | scar exceeds nnU-Net reference; edema still below |
| nnU-Net Dataset501 5-fold | 5 folds | 0.4197 | 0.5592 | direct local reference |

The result supports the official-validation-specific idea that complete modalities help scar, but it does not solve edema and it was only evaluated on the 16 complete cases.

## Round6 prepared

Added an export-only all-case/hybrid step:

- `code/MyoPS-Net/build_round6_hybrid.py`
- `jobs/MyoPS-Net/sbatch_round6_hybrid_export.sh`

It exports the round5 full-modality checkpoint on all 44 fold0 validation cases, evaluates that directly, then routes complete C0+LGE+T2 cases to round5 and T2-missing cases to round4 `combined_safe`.

Expected outputs:

- `results/metrics/unified/MyoPS-Net_round6_fullmod_on_allval/fold_0/evaluation_summary.json`
- `results/metrics/unified/MyoPS-Net_round6_hybrid_fullmod_plus_round4/fold_0/evaluation_summary.json`
- `results/metrics/unified/MyoPS-Net_round6_hybrid_fullmod_plus_round4/fold_0/routing_summary.json`

Do not expand to folds 1-4 until the hybrid all-case metric is checked against nnU-Net edema 0.4197 and scar 0.5592.
