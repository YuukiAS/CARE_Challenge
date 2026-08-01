# Result 20260801_care_four_lane_evidence_reconciliation

status: completed

## 执行摘要

本任务完成了四模型证据纠偏，没有摘要化替代执行，也没有重新训练。重新计算后，M0R 在 fold2+fold3 outer 同病例 stock nnU-Net 对比中 scar 和 edema 都为负；M2 补做 outer 后 scar 明显为负，edema 没达到候选门槛且损害比例过高。当前科学结论为 `FOUR_LANE_EVIDENCE_CORRECTED_NO_CANDIDATE`。

## 读取文件

读取了任务指定的启动协议、route 规则、CURRENT、wiki、care-mapper skill、Slurm routing skill、冻结 result packets、checkpoint receipts、split receipt、训练入口和模型源码。

## 修改文件

新增或更新：

```text
scripts/evaluation/four_lane_reconciliation/evaluate_frozen_outer.py
scripts/validation/validate_four_lane_evidence_reconciliation.py
tests/four_lane_reconciliation/test_metric_contract.py
results/20260801_care_four_lane_evidence_reconciliation/**
prompts/routes/handoffs/CURRENT.md
wiki/README.md
```

## 运行命令

```bash
git fetch origin
git merge --ff-only origin/main
squeue -u "$USER" -p htzhulab -o '%i|%j|%P|%T|%M|%L|%R|%b|%D'
squeue -j 61220581 -o '%i|%j|%P|%T|%M|%L|%R|%b|%D'
scontrol show job 61220581
./envs/env_CARE/bin/python -m pytest -q tests/four_lane_reconciliation/test_metric_contract.py
./envs/env_CARE/bin/python -m py_compile scripts/evaluation/four_lane_reconciliation/evaluate_frozen_outer.py scripts/validation/validate_four_lane_evidence_reconciliation.py
srun --jobid=61220581 --overlap --ntasks=1 /users/a/e/aereinh/CARE/envs/env_CARE/bin/python /users/a/e/aereinh/CARE/scripts/evaluation/four_lane_reconciliation/evaluate_frozen_outer.py
```

## 测试结果

`tests/four_lane_reconciliation/test_metric_contract.py` 通过。最终 validator 报告见 `strict_validator_report.json`。

## 产物清单

见 `MANIFEST.md`。

## 失败信息

第一次 `srun` approval 审查超时，命令未执行；随后用更窄的直接 Python `srun` 命令成功运行。未发生 checkpoint/runtime 阻塞。

## git diff 摘要

本任务新增一个物理空间指标 evaluator、一个 strict validator、两个指标语义回归测试，并把 CURRENT/wiki 从旧 scar-only 候选状态更新为纠偏后无候选。

## 需要人工批准的事项

下一步路线选择、任何新训练、validation/Docker 上传、hosted metric claim 都仍需 Planner/用户另行授权。

## 下一步建议

返回 Planner，基于 same-case stock 对比和 M2 outer gate 失败结果决定是重新设计修复方向，还是停止当前 target-domain 四模型路线。
