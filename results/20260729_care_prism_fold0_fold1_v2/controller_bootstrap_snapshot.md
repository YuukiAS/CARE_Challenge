本次控制器已经完成执行前同步、授权读取和唯一 GPU allocation 检查。远端主分支已经快进到用户要求的提交，现有 allocation 仍在 `htzhulab` 的 `g1807htzh01` 上运行，因此任务可以进入 W1 实现门；但训练前仍必须由 Controller 复核共享主干移植、信息流干预、梯度隔离、no-T2 精确为零和 checkpoint/resume 完整性。

```text
task_key: 20260729_care_prism_fold0_fold1_v2
phase: W0_AUTHORITY_ROOT_CAUSE_ASSETS
git_head: 7e659fd6f559cad464cfea31879970b273ce2993
allocation: 61220581 RUNNING htzhulab g1807htzh01
executor_count: 1
mapper_count: 1
parallel_execution_allowed: false
new_slurm_job_allowed: false
```

W0 required outputs written: `controller_context.json`, `adoption_receipt.json`, `arc_w3_root_cause_audit.json`, `split_freeze_receipt.json`, `nnunet_asset_receipt.json`, `allocation_snapshot.json`.
