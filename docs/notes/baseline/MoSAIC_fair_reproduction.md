# MoSAIC fair reproduction

MoSAIC 权重已经下载到 `/users/a/e/aereinh/MoSAIC`，但当前只看到 checkpoint 和下载 manifest，没有 native MoSAIC 源码；因此现在允许做的是公平复现协议、权重登记、通道/label/几何审计和已有预测的同口径评价，不能训练、不能上传 validation、不能把 MoSAIC 接进生产路径。若没有 native 源码或经过验证的 native entrypoint，native MoSAIC 结果必须标记为 `NEEDS_MOSAIC_SOURCE`。

## GPT entrypoints

- `MOSAIC_ROOT=/users/a/e/aereinh/MoSAIC`
- Weights manifest: `third_party/MoSAIC/weights_manifest.json`
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
