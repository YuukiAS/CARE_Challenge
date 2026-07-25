# MoSAIC fair reproduction

MoSAIC 权重已经下载到 `/users/a/e/aereinh/MoSAIC`，public source 已 vendored 到 `third_party/MoSAIC/source`（IndeedLiu/MoSAIC commit `d334bd1fb2a99dbbc230510590cd8e3ee08cc377`）。当前允许做的是公平复现协议、runtime preflight、native inference 启动检查、通道/label/几何审计和同口径评价；仍然不能训练、不能上传 validation、不能把 MoSAIC 接进生产路径。clone、import、model-load 或 dry-run 只能算 `PREFLIGHT_SMOKE_ONLY`，44 例 fold0 预测和同一 evaluator 完成后才可写 `VERIFIED_EVALUATION_COMPLETE`。

## GPT entrypoints

- `MOSAIC_ROOT=/users/a/e/aereinh/MoSAIC`
- Weights manifest: `third_party/MoSAIC/weights_manifest.json`
- Vendored source: `third_party/MoSAIC/source`
- Native entrypoint: `third_party/MoSAIC/source/scripts/infer_and_submit.py`
- Runtime preparation: `scripts/inference/prepare_mosaic_inference_runtime.py`
- Fair protocol config: `configs/baselines/mosaic_fold0_fair.yaml`
- Protocol helpers: `code/MoSAIC/mosaic_fair_protocol.py`
- Inference wrapper: `scripts/inference/run_mosaic_fold0_fair_inference.py`
- Evaluation wrapper: `scripts/evaluation/evaluate_mosaic_fold0_fair_comparison.py`
- Slurm job: `jobs/evaluation/mosaic_fold0_fair.sh`
- Result packet: `results/20260725_care_m0_mosaic_fold0_fair_repro/`

## Fixed protocol

- Dataset: `data/benchmarks/protocol/splits_MyoPS.json`, fold0, expected `44` validation cases.
- CARE historical input order: `[LGE, T2, C0]`.
- MoSAIC native input order: `[LGE, C0, T2]`.
- Compact-to-official pathology labels: `4 -> 1220`, `5 -> 2221`.
- `pure_edema` and `edema_zone` are separate metrics; `edema_zone` must not replace `pure_edema`.
- Geometry audit must cover size, spacing, origin, direction, and ZHW/HWZ-style transpose detection.
- Evaluation uses the same positive-GT population and the same Dice/exact-HD implementation for every model.

## Boundaries

- `evaluation-only`
- `no training`
- `no validation upload`
- `no hosted metric claim`
- `no fold expansion`
- `no production-path dependency`
- `no checkpoint or prediction artifacts in git`

旧 Batch10 配置里禁止 MoSAIC 代码/权重的约束仍然是旧生产路径约束。本文件只授权一个独立的 baseline comparison / mechanism-screening task，不改变 Batch10 结论。
