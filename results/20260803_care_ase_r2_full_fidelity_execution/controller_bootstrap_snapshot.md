# CARE-ASE R2 Controller Bootstrap Snapshot

当前 Goal 已同步到 main/origin `6be72cc6b55b28765e737b5ede7fa144845a02ca`。R2 基础合同、continuous independent Reviewer amendment、controller task 和 reviewer addendum 均已纳入 effective contract。

W0 没有读取 fold1/fold4 outer 图像或标签；outer case id 仅来自 `splits_final.json`。训练前实现流程现在固定为 `G1 -> R1 -> G2 -> R2 -> G2.5 -> R3 -> W3`。Reviewer 持续存在但不设置人工继续门；Reviewer 失败只能返回 `REVISE_CONTINUE_CURRENT_GOAL`，由 Controller 交回同一 Executor 修复并重审，不能终止 Goal、返回 Planner 或等待用户。
