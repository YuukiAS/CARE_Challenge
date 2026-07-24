# SCR-R1 Controller Bootstrap Snapshot

本轮已经绑定最新 `origin/main`，并在实现前把 base config、executor plan 与 preexecution amendment 合并为唯一 resolved contract。W0 资产审计确认两个冻结 CARE-MMRD source checkpoint SHA256 与合同一致，Dataset501 OOF anchor manifest 覆盖 220 例、五折各 44 例、概率和预测文件均存在，Batch10 calibration/audit split 为 22/22，Dataset501 `3d_fullres` plans 可解析。

当前还没有启动 W1 实现、正式训练、Slurm、package 或上传。Source cache parity、anchor canonical probability tensor roundtrip、模型 identity、loss backward、fixed overfit 和 known-bad 仍是 W1/W2 的阻断门，不能由 W0 文件替代。

- repo: `/users/a/e/aereinh/CARE`
- branch/head: `6b9834c6f20416392a540535056c7196a4c429f3`
- origin/main: `6b9834c6f20416392a540535056c7196a4c429f3`
- method: `CARE-SRR-Cascade`
- execution: `SCR-R1`
- resolved contract: `results/20260724_care_myops_srr_cascade_submission_rescue/resolved_execution_contract.json`
- W0 decision: `PASS_READY_FOR_CONTROLLER_VERIFICATION`
