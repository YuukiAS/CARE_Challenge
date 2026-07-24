/goal 你是 CARE Batch10 的新 Controller/Coordinator 和最终操作验收人，接手自旧 session `Controller batch10 rescue`。必须在 `/users/a/e/aereinh/CARE` 的 `main` 上继续同一个 task_key，不得另起 Batch，不得启动 Batch11，不得恢复旧 Batch9 Wave6 到 epoch100，不得把 nnU-Net 作为模型、ensemble、anchor 或 fallback。

## Controller 强制职责和防错边界

你不是普通 Executor，也不是只记录状态的 observer。你必须作为 Batch10 Controller/Coordinator 和最终操作验收人持续监督 executor、Slurm job、runtime 输出、git diff、selection provenance、validator 和 final packet；发现 Batch10 原始合同或 amendment 明确要避免的问题时，必须在同一 Batch10 任务内退回同一 Executor 修复、重新运行受影响 runtime、复验后再继续。不得把“已提交”“运行中”“部分输出”“文件存在”“自报 PASS”“截图”“旧 checkpoint selection”“旧 runtime receipt”当作完成。

你必须持续监控并主动防止这些问题复发：
- 不得恢复旧 Batch9 Wave6 到 epoch100；Batch9 runtime/checkpoint 只能作为冻结输入和 provenance，不是完成证据。
- 不得启动 Batch11、Batch7、BR2、SIP、旧 SRR、prototype、memory、proposal、refiner、外部权重、fold expansion、Cine training、validation upload 或 hosted claim。
- nnU-Net 只能作为同划分 evaluation-only baseline；不得加载其 checkpoint/logits/probabilities 进入 CARE-MMRD，不得作为 model、ensemble source、anchor 或 fallback。
- direct/teacher checkpoint 不得继承 Batch9 旧 selected 结果；必须由 Batch10 calibration-only screening 重新筛选，每个 seed+variant 最多 top2 晋级，然后才允许 44 例正式评价。
- checkpoint/epoch、TTA 候选、best-two source、anatomy source、scar source、edema source、temperature/margin calibration、postprocess 参数都只能读取 calibration case IDs；audit case IDs 只能在所有规则冻结后用于一次性验收。
- `selection_provenance.json` 必须记录每项选择实际读取的 case IDs，并证明 audit case IDs 没有参与选择。
- TTA、ensemble、compositor、后处理、near-baseline gate 和最终 ranking 必须按 audit 上 scar/edema 相对同划分 nnU-Net 的较小增益、两病种平均增益、harm count、HD95、remote FP、简单稳定性排序；不得牺牲一个病种换另一个病种，也不得用跨 seed 平均掩盖 seed/pathology 失败。
- anatomy source 必须按 anatomy classes 1-3 的最小 Dice、三类平均 Dice、myocardium HD95、简单/更早候选排序；不得用 scar/edema 结果主观选择 anatomy source。
- 禁止拼接不同模型未校准 softmax 概率作为 pathology compositor；compositor 必须使用 anatomy source logits/prob base 加 scar/edema pathology margin/residual，并在 calibration 固定小网格选择单一 temperature 后统一 softmax/argmax。普通概率平均只作为对照。
- 后处理必须两阶段 calibration-only，低增益、增加 harm 或增加 empty prediction 时必须回退 no-postprocess；audit 不得重新选参数。
- 同 plans fingerprint 的模型必须优先在共同 preprocessed space 融合 logits/calibrated margins，再做一次 official inverse export；不得先把每个模型独立 inverse/interpolate 到原空间再无条件平均。
- baseline 自检必须区分 positive-GT、all-case empty-safe、complete-trimodal、calibration、audit、full44；不得把 all-case edema/scar Dice 与 positive-GT nnU-Net Dice 交叉比较。
- Wave4 之前必须有真实 coordinate/fiducial 的 student/natural/teacher spatial augmentation 一致性证据 `paired_spatial_fiducial_checks.csv`；seed/hash 相同不够。
- 最终复杂 TTA 或多模型 ensemble 晋级前必须有 Docker feasibility one-case probe；不能只凭本地 Dice 晋级不可执行候选。
- `gap_register.csv` 中每个 amendment issue 必须经历 OPEN -> EXECUTOR_FIXING -> CONTROLLER_CODE_REVIEWED -> TESTED -> RUNTIME_REVALIDATED -> CLOSED；每次选择、修复、重跑、提交、终态 accounting 和验收都必须追加 `controller_ledger.csv`。


迁移备份目录：
`/users/a/e/aereinh/CARE/results/20260724_care_myops_batch10_deadline_rescue/migration_backups/20260723_224553__to_Longleaf_Backup_Codex`

首先读取并核对这些备份文件：
- `/users/a/e/aereinh/CARE/results/20260724_care_myops_batch10_deadline_rescue/migration_backups/20260723_224553__to_Longleaf_Backup_Codex/backup_summary.json`
- `/users/a/e/aereinh/CARE/results/20260724_care_myops_batch10_deadline_rescue/migration_backups/20260723_224553__to_Longleaf_Backup_Codex/git_status.txt`
- `/users/a/e/aereinh/CARE/results/20260724_care_myops_batch10_deadline_rescue/migration_backups/20260723_224553__to_Longleaf_Backup_Codex/git_diff.patch`
- `/users/a/e/aereinh/CARE/results/20260724_care_myops_batch10_deadline_rescue/migration_backups/20260723_224553__to_Longleaf_Backup_Codex/untracked_code_files.txt`
- `/users/a/e/aereinh/CARE/results/20260724_care_myops_batch10_deadline_rescue/migration_backups/20260723_224553__to_Longleaf_Backup_Codex/untracked_code_files.tar.gz`
- `/users/a/e/aereinh/CARE/results/20260724_care_myops_batch10_deadline_rescue/migration_backups/20260723_224553__to_Longleaf_Backup_Codex/slurm_squeue_60342779.txt`
- `/users/a/e/aereinh/CARE/results/20260724_care_myops_batch10_deadline_rescue/migration_backups/20260723_224553__to_Longleaf_Backup_Codex/slurm_sacct_60342779.txt`
- `/users/a/e/aereinh/CARE/results/20260724_care_myops_batch10_deadline_rescue/migration_backups/20260723_224553__to_Longleaf_Backup_Codex/result_files/controller_ledger.csv`
- `/users/a/e/aereinh/CARE/results/20260724_care_myops_batch10_deadline_rescue/migration_backups/20260723_224553__to_Longleaf_Backup_Codex/result_files/gap_register.csv`
- `/users/a/e/aereinh/CARE/results/20260724_care_myops_batch10_deadline_rescue/migration_backups/20260723_224553__to_Longleaf_Backup_Codex/result_files/selection_provenance.json`
- `/users/a/e/aereinh/CARE/results/20260724_care_myops_batch10_deadline_rescue/migration_backups/20260723_224553__to_Longleaf_Backup_Codex/result_files/baseline_reference_consistency.json`
- `/users/a/e/aereinh/CARE/results/20260724_care_myops_batch10_deadline_rescue/migration_backups/20260723_224553__to_Longleaf_Backup_Codex/result_files/strict_entrypoint_audit.json`
- `/users/a/e/aereinh/CARE/results/20260724_care_myops_batch10_deadline_rescue/migration_backups/20260723_224553__to_Longleaf_Backup_Codex/logs/B10CkptScreen_60342779_latest_snapshot.log`

然后在真实工作树中重新检查当前状态，不要只信备份快照：
```bash
cd /users/a/e/aereinh/CARE
source /users/a/e/aereinh/CARE/.care-codex-env.sh || true
source /users/a/e/aereinh/CARE/env_nnunet.sh
export PATH=/users/a/e/aereinh/codex-runtime/bin:/users/a/e/aereinh/CARE/envs/env_CARE/bin:$PATH
git status --short --branch
squeue -j 60342779 -o '%i|%P|%j|%u|%t|%M|%D|%R'
sacct -j 60342779 --format=JobIDRaw,JobID,JobName,Partition,State,ExitCode,Elapsed,NodeList%40 -P -n
find results/20260724_care_myops_batch10_deadline_rescue/runtime/checkpoint_screening -type f -name '*.nii.gz' | wc -l
ls results/20260724_care_myops_batch10_deadline_rescue/screen_*_casewise_metrics.csv 2>/dev/null | wc -l
```

当前必须接手的 live executor：
- Slurm job `60342779`，name `B10CkptScreen`，partition `htzhulab`，node `g1807htzh01`。
- 目的：补充修订 A02，发现的 78 个 direct/teacher periodic checkpoint 使用 Batch10 正确 sliding-window + official inverse export，在 22 个 calibration cases 上 no-TTA screening。
- 不要取消它；继续监控到 terminal accounting。submitted/running/partial output 不能算完成。
- 旧 session 备份时进度大约是 `1232` 个 NIfTI、`56` 个完整 checkpoint CSV；你接手时必须刷新真实数字。目标是 78 个完整 `screen_*_casewise_metrics.csv` 和 1716 个 calibration NIfTI。

已经完成并可复验的事实：
- Wave0 完成：Batch9 runtime freeze、clean-checkout import、preprocessing fingerprint、checkpoint inventory、Batch9 Slurm accounting；旧 Batch9 Wave6 jobs 已被取消，不得恢复。
- Wave1 完成：`scripts/inference/run_care_mm_batch10_fair_inference.py` 实现 nnU-Net v2 sliding window、Gaussian、mirror TTA、official inverse export；单测 `tests/care_mm/test_batch10_fair_inference.py` 和 Batch9 loss tests 通过；Case1002 CPU smoke 通过，no-T2 edema voxels 为 0。
- 原 Wave2 完成过一次 8 checkpoint full44/TTA，但补充修订要求 Batch9 direct/teacher selected checkpoints 不能直接继承，且 TTA selection 必须 calibration-only；因此原 Wave2 的 direct/teacher ranking/TTA/后续 Wave3 选择均不能进入最终候选，必须在 screening 终态后按修复后的 `scripts/evaluation/batch10_wave2_fair_reevaluation.py` 重跑受影响 full44 正式评价和 calibration-only TTA selection。
- A07 strict entrypoint audit 已 PASS：`configs/srr_production/entrypoints.yaml` 已切为 Batch10 authority，`parallel_executor=false`，独立 Slurm jobs 可并行。
- A10 baseline reference consistency 已 PASS：nnU-Net full44 Dice 与 `results/srr_production/evaluation/nnunet_fold0_reproduction.json` 一致，且 baseline summary 现在区分 full44 / positive-GT / calibration / audit / complete-trimodal。

必须继续执行的补充修订：
1. 等 `60342779` 终态后查 `sacct`，运行 `./envs/env_CARE/bin/python scripts/evaluation/batch10_checkpoint_screening.py --phase aggregate`，检查 `checkpoint_screening_manifest.csv`：所有发现/缺失/淘汰/晋级 checkpoint 必须有 hash；每个 seed+variant 最多 top2 晋级；selection provenance 证明 audit case IDs 未参与选择。
2. 修/复验 `gap_register.csv` 生命周期：每个 issue 必须走 OPEN -> EXECUTOR_FIXING -> CONTROLLER_CODE_REVIEWED -> TESTED -> RUNTIME_REVALIDATED -> CLOSED。不要用自报 PASS 或文件存在替代验收。每次修复、重新提交 job、选择 checkpoint/TTA/ensemble/postprocess 都追加 `controller_ledger.csv`。
3. checkpoint screening 结束后重跑修复后的 Wave2：使用 screening promoted direct/teacher checkpoint + frozen epoch25 control/distill，44 例正式评价，calibration-only 选择 TTA。不得让旧 Batch9 selected direct/teacher 或 full44 selection 混入。
4. 修 Wave3 后再运行：固定 6 个 ensemble 候选；anatomy source 按 classes 1-3 的 min Dice、mean Dice、myocardium HD95、简单/更早候选排序；禁止拼接未校准 softmax。compositor 用 anatomy source logits/prob base + scar/edema pathology margin/residual + fixed temperature grid，并保留普通概率平均对照。后处理改两阶段，低增益或增加 harm/empty 时回退 no-postprocess。audit 只在冻结选择后运行一次。
5. 修 ensemble/export 顺序：同 plans fingerprint 的模型优先 common preprocessed-space 融合 logits/calibrated margins，然后 single official inverse export；original-space ensemble 只能作为 fingerprint mismatch 降级并显式记录。
6. 在允许 Wave4 前，加入真实 coordinate/fiducial 的 paired spatial augmentation 检查，输出 `paired_spatial_fiducial_checks.csv`；任何不一致不得提交短续训。
7. 在最终复杂 TTA/multi-model 候选前做 Docker feasibility one-case probe，记录推理时间、GPU/CPU peak、checkpoint size、estimated image size、no-network、repeat hash、missing modality、input naming/error handling。
8. 只有 `near_baseline_gate.json` 在 audit 上通过，才允许 Wave4 四个固定 25 epoch matched jobs。训练依赖用 afterok，accounting/finalizer 用 afterany。任何 seed 或 pathology 失败不能跨 seed 平均掩盖。
9. 最终完成 strict validator/known-bad、Mapper/wiki/CURRENT 一致性和本地轻量结果 commit；不得 push runtime，不得上传 validation/Docker，不得作 hosted 成绩主张。最终只能给出 `PAPER_AND_DOCKER_CANDIDATE`、`DOCKER_ONLY_CANDIDATE` 或 `STOP_CARE_MMRD_COMPETITION_ROUTE`。

接手后第一条回复只需说明：已读取备份、当前 cwd/branch/head、job 60342779 最新状态、screening 输出最新计数、下一步监控/修复动作。
