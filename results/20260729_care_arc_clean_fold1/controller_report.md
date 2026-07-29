# CARE-ARC Controller Report

CARE-ARC 本轮已经完成可执行实现和 fold0 开发验证，但没有达到进入 clean fold1 的科学安全门槛。具体说，模型能在完整病例上训练，W2 的 300-step preflight、梯度、no-T2、resume 和 strict validator 都通过；然而 W3 fold0 outer 显示 raw direct scar 与 edema-zone 的 Dice 明显低于 nnU-Net，说明当前单 encoder 结构的轮廓/定位能力不足。下一步应返回 Planner 修订机制，不得继续消耗 fold1、不得上传、不得把 nnU-Net-only 包装成本研究终态。

```text
controller_verification_decision: OPERATIONALLY_BLOCKED_BY_W3_MECHANISM_GATE
failure_classification: CONTOUR_LIMITED
w0: PASS
w1_implementation_validator: PASS
w2_preflight_strict_validator: PASS
w3_gate: FAIL
w4_w5_w6: SKIPPED_FORBIDDEN_BY_W3_GATE
```

## Key Evidence

| item | result | evidence |
| --- | --- | --- |
| Required commits/main sync | PASS | `adoption_receipt.json` |
| W0 split/crop/depth | PASS | `split_freeze_receipt.json`, `crop_freeze_receipt.json`, `full_volume_shape_audit.json` |
| W1 single encoder implementation | PASS | `implementation_validator_report.json`, `model_parameter_report.json` |
| W2 300-step zero-credit preflight | PASS | `preflight_strict_validator_report.json` |
| W3 3000-step fold0 development | terminal PASS | `runtime/fold0_development/training_receipt.json` |
| W3 mechanism gate | FAIL | `fold0_development_adequacy_gate.json` |

## W3 Mechanism Result

| metric | value | gate |
| --- | ---: | --- |
| scar raw direct Dice delta vs nnU-Net | -0.180502 | must be >= -0.05 |
| edema-zone raw direct Dice delta vs nnU-Net | -0.155363 | must be >= -0.05 |
| scar median volume ratio | 0.798182 | [0.25, 4.0] |
| edema-zone median volume ratio | 0.896345 | [0.25, 4.0] |
| frozen alignment mode | identity | fixed by amendment rule |

Coarse/presence AUPRC, volume ratio, changed-mask fraction, component safety, no-T2 exact-zero, and anchor-context invariance passed. The failing boundary is direct mask quality/geometry, so the terminal classification is `CONTOUR_LIMITED`.

## Operational Boundary

All W2/W3 GPU child processes reached terminal state under existing allocation `61220581` on `htzhulab/g1807htzh01`; final GPU check showed 0 MiB used and no CARE training/eval process except the check command itself. No new Slurm job, upload, push, or `/overflow/htzhu/CARE` write was performed.

Mapper updates are in `wiki/README.md`, `wiki/current_state.yaml`, `wiki/architecture.yaml`, `wiki/COMPONENTS.csv`, and `wiki/figures/care-arc-w3-stop.svg`.
