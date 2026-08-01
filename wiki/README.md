# CARE 架构 Wiki

architecture_version: `care-test-docker-provenance-reconcile-deployable-nondeterministic-20260801`
latest_verified_runtime: `package A labelwise audit completed; used nnU-Net channels 1/2/3/4 matched 4/15; three frozen replay variants did not exact reproduce package A; second checkpoint_best default-TTA deployment replay matched geometry 15/15 but array only 7/15`
latest_scientific_status: `SERVER_BUNDLE_BLOCKED: current nnU-Net deployment source is not two-run voxel deterministic, so workstation Docker bundle must not start`
latest_controller_task: `20260801_care_test_docker_provenance_reconcile_and_bundle`
route_status: `MAIN_ONLY_TEST_DOCKER_RECONCILE_BLOCKED_RETURN_TO_PLANNER`

当前机器真值是 `prompts/routes/handoffs/CURRENT.md`。这次已经按新合同纠正了上一轮过窄的阻塞口径：没有直接把完整六类数组 mismatch 当成终点，而是先按语义标签审计 production 会使用的 nnU-Net anatomy `1/2/3` 和 pure-edema `4`。审计结果是 package A 与上一轮 fresh replay 几何 15/15 一致，但 full array 4/15、一致的 used channels 也只有 4/15；11 个不一致病例合计 120 个体素差异，横跨 anatomy、pure edema、scar 和背景。三个冻结 variant 均没有 exact 复现 package A，因此历史 `0.6691` lineage 保持 `UNRESOLVED`，不得作 hosted claim。

随后本任务按合同把历史 lineage 和当前部署源分开：对 `checkpoint_best.pth + folds 0-4 + default TTA` 做第二次独立 15/15 fresh replay。两次当前部署源 replay 的 geometry 是 15/15，但 array 只有 7/15 一致，合计 13 个体素变化。这个状态触发合同允许的硬阻塞 `NNUNET_DEPLOYABLE_SOURCE_NONDETERMINISTIC`；因此没有生成 `SERVER_BUNDLE_READY.json`，没有让工位开始 Docker 构建，也没有上传网盘、validation、Docker 或给组织方发邮件。

关键证据：

```text
results/20260801_care_test_docker_provenance_reconcile_and_bundle/nnunet_used_channel_equivalence_summary.json
results/20260801_care_test_docker_provenance_reconcile_and_bundle/nnunet_replay_variant_decision.json
results/20260801_care_test_docker_provenance_reconcile_and_bundle/nnunet_deployable_source_receipt.json
results/20260801_care_test_docker_provenance_reconcile_and_bundle/nnunet_lineage_vs_deployment_decision.json
results/20260801_care_test_docker_provenance_reconcile_and_bundle/controller_report.md
```

## 2026-08-01 Docker provenance 纠偏后阻塞

```text
result_root:
results/20260801_care_test_docker_provenance_reconcile_and_bundle

terminal_state:
SERVER_BUNDLE_BLOCKED

blocking_token:
NNUNET_DEPLOYABLE_SOURCE_NONDETERMINISTIC

package A audit:
geometry equality 15/15
full array equality 4/15
used channels 1/2/3/4 equality 4/15
changed semantic voxels vs package A 120

variant replay:
v1 checkpoint_final default TTA NOT_EXACT
v2 checkpoint_best no TTA NOT_EXACT
v3 checkpoint_final no TTA NOT_EXACT

deployable repeat:
checkpoint_best folds0-4 default TTA
geometry equality 15/15
array equality 7/15
changed voxels 13
```

不得把 `NNUNET_DEPLOYABLE_SOURCE_NONDETERMINISTIC` 解释成历史 `0.6691` 已复现。下一步需要 GPT Planner 决定是否授权一个确定性部署模式或修订 bundle source 合同。

architecture_version: `care-test-docker-server-bundle-nnunet-mismatch-20260801`
latest_verified_runtime: `server-side fresh nnU-Net 5-fold replay completed 15 outputs; geometry matched package A 15/15, array matched 4/15; MoSAIC MyoPS diagnostic replay completed 15/15; Cine diagnostic stopped at 4/15 after upstream gate failure`
latest_scientific_status: `SERVER_BUNDLE_BLOCKED: workstation Docker bundle must not start because nnU-Net edema provenance was not reproduced`
latest_controller_task: `20260801_care_test_docker_server_bundle`
route_status: `MAIN_ONLY_TEST_DOCKER_SERVER_BUNDLE_RETURN_TO_PLANNER`

当前机器真值是 `prompts/routes/handoffs/CURRENT.md`。服务器端跨机器 Docker bundle 任务已经绕开本机 Docker/rootless 限制，直接复用现有 GPU allocation 做 fresh inference 证据；但关键 nnU-Net hosted provenance gate 未通过：15 例 fresh 输出全部存在，几何全一致，数组只有 4/15 与历史 package A 一致。因此不能生成 `SERVER_BUNDLE_READY.json`，不能让工位开始构建/验证 Docker，也不能把历史 hosted edema 分数绑定到当前冻结权重。

关键证据：

```text
results/20260801_care_test_docker_server_bundle/fresh_nnunet_provenance_receipt.json
results/20260801_care_test_docker_server_bundle/fresh_nnunet_vs_historical_casewise.csv
results/20260801_care_test_docker_server_bundle/fresh_mosaic_replay_receipt.json
results/20260801_care_test_docker_server_bundle/controller_report.md
```

## 2026-08-01 服务器端跨机器 bundle 阻塞

```text
result_root:
results/20260801_care_test_docker_server_bundle

terminal_state:
SERVER_BUNDLE_BLOCKED

blocking_token:
NNUNET_PROVENANCE_REPLAY_MISMATCH

nnU-Net fresh replay:
15 outputs generated
15/15 geometry equality vs historical package A
4/15 array equality vs historical package A

MoSAIC diagnostic:
MyoPS 15/15 complete
CineMyoPS 4/15 partial, stopped after upstream nnU-Net hard gate failure
```

不得把该状态解释成 Docker submission readiness。不得生成或上传 Docker archive，不得给组织方发邮件；后续需要 GPT Planner 决定是否追溯历史 package A 生成环境或修订合同。

architecture_version: `care-test-docker-rootless-prerequisite-blocked-20260801`
latest_verified_runtime: `rootless Docker prerequisite audit completed; official rootless installer downloaded but not executed because /etc/subuid and /etc/subgid have no current-user range for aereinh`
latest_scientific_status: `ROOTLESS_DOCKER_PREREQUISITE_BLOCKED: Docker packaging did not reach inference, image build, export, upload, or hosted metric stages`
latest_controller_task: `20260801_care_test_docker_rootless_unblock`
route_status: `MAIN_ONLY_TEST_DOCKER_RUNTIME_BLOCKED_RETURN_TO_PLANNER`

当前机器真值是 `prompts/routes/handoffs/CURRENT.md`。这次测试 Docker unblock 已经把旧的“docker command not found”粗粒度阻塞细化为 rootless Docker 主机前提阻塞：user namespace、uidmap 二进制和本地 `/tmp` data root 可用，但 `/etc/subuid` 与 `/etc/subgid` 没有给 `aereinh` 配置至少 65536 的 subordinate ID 范围。由于任务禁止 sudo 和系统级安装，Docker build/load/run/save、CPU smoke、host/Docker 等价验证、tar.gz 导出和邮件草稿都没有启动。

关键证据：

```text
results/20260801_care_test_docker_rootless_unblock/rootless_prerequisite_audit.json
results/20260801_care_test_docker_rootless_unblock/rootless_storage_receipt.json
results/20260801_care_test_docker_rootless_unblock/rootless_install_receipt.json
results/20260801_care_test_docker_rootless_unblock/controller_report.md
results/20260801_care_test_docker_rootless_unblock/strict_validator_report.json
```

## 2026-08-01 测试 Docker rootless 前提阻塞

```text
result_root:
results/20260801_care_test_docker_rootless_unblock

terminal_state:
ROOTLESS_DOCKER_PREREQUISITE_BLOCKED

hard requirement failure:
subuid_total 0
subgid_total 0

passed host checks:
unshare -Ur true passed
newuidmap exists
newgidmap exists
/tmp/aereinh/care-rootless-docker-data selected on xfs

official installer:
downloaded and SHA256 recorded
not executed after hard prerequisite failure
```

不得把该状态解释成 Docker submission readiness，也不得上传 Docker、给组织方发邮件或作 hosted metric claim。管理员补齐 `/etc/subuid` 和 `/etc/subgid` 后，才能从该 controller 合同 W1 重新跑。

architecture_version: `care-four-lane-evidence-reconciled-no-candidate-20260801`
latest_verified_runtime: `M0R/M1/M2/M3 frozen fold2+fold3 evidence reconciled; same-case stock comparison complete; M2 outer replay complete; physical-space metric correction complete`
latest_scientific_status: `FOUR_LANE_EVIDENCE_CORRECTED_NO_CANDIDATE: M0R did not beat same-case stock on outer scar or edema, and M2 did not pass scar/edema packaging gates`
latest_controller_task: `20260801_care_four_lane_evidence_reconciliation`
route_status: `MAIN_ONLY_FOUR_LANE_RECONCILIATION_RETURN_TO_PLANNER`

当前机器真值是 `prompts/routes/handoffs/CURRENT.md`。最新四模型证据纠偏已经完成：M0R 与同病例 stock nnU-Net 的 outer 对比为负，M2 补做 outer 后也没有达到候选门槛；M1/M3 的失败被归类为实现不忠实导致的负结果，而不是对应论文路线的科学失败。旧的 scar-only 候选说法已撤销；不得解释为 hosted validation claim，也不得自动上传 validation 或 Docker。

## 2026-08-01 四模型证据纠偏终态

```text
result_root:
results/20260801_care_four_lane_evidence_reconciliation

scientific_decision:
FOUR_LANE_EVIDENCE_CORRECTED_NO_CANDIDATE

M0R same-case stock comparison:
scar Dice delta -0.0020118904817150174
pure-edema Dice delta -0.030114178203399733

M2 outer gate:
scar gate false, Dice delta -0.05011471399535905
pure-edema gate false, Dice delta 0.018926404811234976, harm fraction 0.46875

metric correction:
HD95 and exact HD are reported in mm from nnU-Net preprocessing properties; small lesion uses physical volume <1000 mm3.
```

关键证据：

```text
results/20260801_care_four_lane_evidence_reconciliation/controller_report.md
results/20260801_care_four_lane_evidence_reconciliation/four_lane_scientific_interpretation.md
results/20260801_care_four_lane_evidence_reconciliation/m0r_vs_stock_outer_summary.csv
results/20260801_care_four_lane_evidence_reconciliation/m2_vs_stock_outer_summary.csv
results/20260801_care_four_lane_evidence_reconciliation/strict_validator_report.json
```

## 2026-08-01 已撤销历史证据：目标域四模型缺口闭合曾标记候选

```text
result_root:
results/20260801_care_target_domain_race_gap_closure

scientific_decision:
superseded_scar_only_candidate_label

global scar source:
m0r_faithful_control checkpoint_step03500

global edema source:
m0r_faithful_control checkpoint_step04000

outer replay:
results/20260801_care_target_domain_race_gap_closure/outer_replay/outer_replay_receipt.json

outer summary:
scar Dice mean 0.6500, sensitivity mean 0.7264
edema Dice mean 0.4340, sensitivity mean 0.4124

sentinel atlas:
results/20260801_care_target_domain_race_gap_closure/outer_replay/sentinel_case_atlas.md
```

## 2026-08-01 目标域四模型缺口闭合历史继续执行证据

```text
result_root:
results/20260801_care_target_domain_race_gap_closure

controller report:
results/20260801_care_target_domain_race_gap_closure/controller_report.md

old M0 fidelity audit:
results/20260801_care_target_domain_race_gap_closure/m0_protocol_fidelity_audit.json
old_m0_classification: HIGH_LR_SHORT_FINETUNE_NEGATIVE

interactive allocation receipt:
results/20260801_care_target_domain_race_gap_closure/existing_interactive_receipt.json
usable_existing_interactive_allocation: true
job_id: 61220581
partition: htzhulab
node: g1807htzh01
gpu: NVIDIA H100 NVL

scientific decision:
results/20260801_care_target_domain_race_gap_closure/scientific_decision.json
scientific_decision: CONTROLLER_ACTIVE_CONTINUATION
previous_decision_superseded: OPERATIONALLY_BLOCKED_EXISTING_INTERACTIVE_LOST

scheduler receipt:
results/20260801_care_target_domain_race_gap_closure/scheduler_receipt.json
M3: fold2/fold3 complete 4000 steps
M0R: old fold2 job 61565286 and fold3 takeover PID 4039804 superseded; faithful fold2/fold3 rerun completed in interactive allocation 61220581; log logs/M0RGapLane_61220581_20260801_014519.log
M1: old fold jobs 61565288/61565289 cancelled; lane job 61576324 COMPLETED with 12 CPU/96G/12h
takeover monitor: PID 4185840 exited as M1_QUEUE_COMPLETED_NO_TAKEOVER_NEEDED, state results/20260801_care_target_domain_race_gap_closure/interactive_takeover_monitor_state.json
M2: source pinned; R50-ViT-B_16.npz and epoch_299.pth downloaded; released checkpoint GPU smoke PASS; Dataset501 adapter preflight PASS; lane job 61627615 COMPLETED_0_0; MyoPS380 dataset not downloaded

checkpoint asset manifest:
results/20260801_care_target_domain_race_gap_closure/checkpoint_reload_audit.json
status: PASS
M0R/M1/M2/M3: 500-step checkpoint grid complete; final/max-step checkpoint torch.load and SHA256 audit PASS

planner handoff:
results/20260801_care_target_domain_race_gap_closure/planner_gap_resolution_handoff.md
records remaining gaps, implementation plan, external asset locations, download commands, and hard boundaries

strict validator:
results/20260801_care_target_domain_race_gap_closure/strict_validator_report.json
bootstrap status: PASS after active-continuation update
```

不得把旧 W0 阻塞解释为四模型科学失败。继续该目标时必须复用 `61220581`，M3 先跑 interactive，M0R/M1/M2 在 preflight 后提交 `htzhulab` 队列；若 interactive 跑完而某条 lane 仍 pending，则取消一个 pending 作业并在 interactive 中串行接力。禁止私自 `salloc`、提交 a100/volta、访问 official validation、上传 validation/Docker 或作 hosted metric claim。

## 2026-07-31 MyoWall-IF 终态证据

CARE-MyoWall-IF 机制试验已完成 metric dependency、fold1 stock nnU-Net 资产冻结、fold1 train-derived pilot split、stock parity、实现/known-bad/final validator 和完整 `pilot_inner` predicted geometry gate。geometry gate 未通过：case geometry valid rate `0.84375` 低于 `>=0.95`，5th-percentile wall roundtrip Dice `0.7068920140479127` 低于 `>=0.90`；因此合同终态为 `STOP_GEOMETRY_NOT_RELIABLE`。C0/W1/W2/W3 8000-step formal training 未启动，fold1 outer 未读取，validation/Docker upload 未启动。

```text
result_root:
results/20260731_care_myowall_if_mechanism_pilot

terminal packet:
results/20260731_care_myowall_if_mechanism_pilot/controller_terminal_packet.json

strict validator:
results/20260731_care_myowall_if_mechanism_pilot/strict_validator_report.json
status: PASS
terminal_stop_validated: true

geometry gate:
results/20260731_care_myowall_if_mechanism_pilot/geometry_gate_report.json
formal_geometry_gate: FAIL
case_count: 32
case_geometry_valid_rate: 0.84375
median_wall_roundtrip_dice: 0.9998856896450612
fifth_percentile_wall_roundtrip_dice: 0.7068920140479127
median_roundtrip_hd95_mm: 0.0

stock parity:
results/20260731_care_myowall_if_mechanism_pilot/stock_parity_report.json
status: PASS
fp32_stock_logit_parity_max_abs_error: 0.0
argmax_changed_voxels: 0
```

## 2026-07-29 PRISM W3 终态证据

## 2026-07-29 W3 终态证据

```text
result_root:
results/20260729_care_prism_v2_backbone_repair_and_resume

W1/W2 validator:
results/20260729_care_prism_v2_backbone_repair_and_resume/w1_w2_strict_validator_report.json

W3 training:
results/20260729_care_prism_v2_backbone_repair_and_resume/w3_training_summary.json
optimizer_steps: 6500
synthetic_credit_used: false

W3 checkpoint audit:
results/20260729_care_prism_v2_backbone_repair_and_resume/w3_checkpoint_audit_report.json
audited_steps: 500,1000,1500,2000,2500,3000,3500,4000,4500,5000,5500,6000,6500

Inner selection:
results/20260729_care_prism_v2_backbone_repair_and_resume/evaluation/fold0_w3_inner_select_formal_v2/summary.json
checkpoint_count: 13
case_count: 35
selected_checkpoint: checkpoint_step03000.pt

Outer once:
results/20260729_care_prism_v2_backbone_repair_and_resume/evaluation/fold0_w3_outer_once_formal_v2/summary.json
case_count: 44
outer_accessed: true

Strict validator:
results/20260729_care_prism_v2_backbone_repair_and_resume/w3_strict_validator_report.json
status: FAIL
failure_classification: CALIBRATION
```

## 当前权威

```text
prompts/tasks/20260729_care_prism_v2_backbone_and_w1_repair_amendment.md
prompts/tasks/20260729_care_prism_v2_backbone_repair_executor_plan.yaml
prompts/tasks/20260729_care_prism_v2_backbone_repair_controller.md
prompts/tasks/20260729_care_prism_execution_hardening_amendment_v2.md
prompts/blueprints/CARE_PRISM_pathology_retrieval_soft_cascade_20260729.md
```

```text
549dc4aed1a74682f8d35932f3d4fc7b7d61f564  repair amendment
1f1f39264cf248fb11d0322f41d4fe4c2aae021d  repair executor plan
acbc44cea3c3d86882cd56e5faab5b1d72b642c6  repair controller
5269f9b909c3a123e5e39db12532e61a2d633f74  CURRENT repair state
```

## 冻结主干资产

```text
fold0:
data/nnUNet/nnUNet_results/Dataset501_CAREMyoPS/nnUNetTrainer_500epochs__nnUNetPlans__3d_fullres/fold_0/checkpoint_final.pth
sha256 8bceb20cae8920e87d43b14665a0db9dfd4f1204533d25a3cd6e40ad9de74111

fold1:
data/nnUNet/nnUNet_results/Dataset501_CAREMyoPS/nnUNetTrainer_500epochs__nnUNetPlans__3d_fullres/fold_1/checkpoint_final.pth
sha256 5310569ff62f2f9a6ff2bc7dd3754404140071427a2025caf5e25d2916cfe400

plans:
data/nnUNet/nnUNet_preprocessed/Dataset501_CAREMyoPS/nnUNetPlans.json
```

来源：

```text
results/20260727_care_dg_dual_pathology_validation/nnunet_oof_anchor_manifest.json
results/20260722_care_myops_batch9_reliable_label_distillation/standard_nnunet_baseline_contract.json
```

Controller 必须重新验证当前文件的 stat/hash；历史 manifest 不是文件存在替代品。禁止只按目录名搜索 `resenc`，禁止用 MMRD/Batch9 checkpoint 或新训练 ResEnc 代替。

## PRISM v2 目标结构

```text
[LGE,T2,C0] exact stock nnU-Net shared encoder
→ lightweight modality-private pyramids
→ scar/edema multi-scale soft retrieval
→ real top-down internal anatomy decoder
→ stop-gradient anatomy→pathology exchange
→ learned positive proposal + four-category safe-negative logits
→ full-volume continuous proposal/anatomy attention
→ independent multi-scale scar and edema refiners
→ direct edema-zone → scar priority → pure edema
```

Prototype 与 slice correspondence 都不是核心强依赖：prototype 默认关闭；slice correspondence 当前冻结 identity，除非以后真实实现并通过独立门。

## 当前部分实现的已知漏洞

1. `CAREPRISM.forward` 只把 level0 routed/anatomy features送入 refiner；深层共享主干和 level1–3 router/exchange没有进入最终 mask。
2. anatomy decoder只是逐尺度1×1 projection并从level0输出，不是真实 top-down decoder。
3. slice correspondence flag当前是no-op。
4. `care_prism_dataset.py`仍是synthetic-only，不能产生W2 real-case credit。
5. 正式训练、评价和packet validator脚本缺失。
6. surface与lesion/MIL仍是placeholder。
7. 四通道negative logits的target被写成全零，没有病种安全负空间类别监督。
8. burden heads仍是auxiliary-only，没有调制proposal或refiner。
9. prototype cross-case排除与完整状态尚未实现，因此保持关闭。

W1必须先修复这些问题，再进入W2。

## 执行门

```text
R0 actual stock checkpoint locate/stat/hash
→ R1 plan-driven stock network restore + W1 implementation closure
→ W2 400-step real-case zero-credit preflight
→ W3 fold0 6500-step all-checkpoint inner selection + one-time outer
→ W4 only after W3 pass: fold1 8000-step clean one-time outer
→ W5 terminal accounting / aggregation / validator / Mapper / local commit
```

共享主干验收：

```text
parameter-byte coverage >=0.99
FP32 per-scale max_abs_error <=1e-6
all declared deep scales causally affect final logits
```

实现、数据、OOM、cache、sampler、loss、resume、evaluation和validator缺陷必须在同一Controller目标内修复，不能再次包装为科学失败。

## 冻结历史结果

CARE-ARC W3仍保留为诊断负结果：scar/edema-zone相对nnU-Net Dice delta为 `-0.1805/-0.1554`，HD95与remote FP显著恶化；但它不能作为忠实ARC机制负结果，因为router、anatomy、coarse proposal和同折初始化均未真实闭环。

前一 blocked packet保留在：

```text
results/20260729_care_prism_fold0_fold1_v2
```

其训练credit为0，fold1 outer未访问。

## 资源与权限

只允许复用既有 allocation `61220581 / htzhulab / g1807htzh01`；若仍运行，GPU命令必须串行。禁止新Slurm job、写`/overflow/htzhu/CARE`、runtime push、validation/Docker upload、fold1 outer调参或二次评价。

## 2026-08-01 nnU-Net / MoSAIC complementarity closure

这次补上的不是新模型，而是一套冻结证据表：把 220 例 fair OOF、80 例 M10 机制诊断和 15 例 fresh validation no-GT disagreement 放在同一个可审计结果包里。可读结论是：nnU-Net 仍是更稳的底线；MoSAIC clean OOF 只在 scar 少数病例上显示有限互补，pure edema 没有显示可用互补；M10 只能解释机制，不能证明泛化。

```text
result_root:
results/20260801_care_nnunet_mosaic_complementarity_closure

strict_validator:
results/20260801_care_nnunet_mosaic_complementarity_closure/strict_validator_report.json

controller_report:
results/20260801_care_nnunet_mosaic_complementarity_closure/controller_report.md
```

Evidence files:

- `oof_complementarity_casewise.csv`: 220-case scar and 80-case pure-edema fair OOF comparison, with buckets and component fields.
- `oof_case_oracle_bounds.csv`: case-oracle upper bound only; not a selector.
- `m10_diagnostic_casewise.csv`: 80-case full-data M10 diagnostic, marked as not valid for generalization claims.
- `validation_disagreement_casewise.csv`: 15-case fresh validation pairwise disagreement only; no GT and no performance claim.
- `hard_case_bucket_index.csv`: hard-case index grouped by frozen OOF buckets.

Key numbers:

- scar all-case: nnU-Net mean Dice `0.561047`, MoSAIC clean OOF mean Dice `0.378168`, case-oracle gain `0.021954`, MoSAIC rescue fraction `18/220 = 0.081818`.
- pure edema T2-present 80-case: nnU-Net mean Dice `0.430812`, MoSAIC clean OOF mean Dice `0.052756`, case-oracle gain `0.002293`, MoSAIC rescue fraction `0/80`.

This closure does not authorize training, threshold tuning, case-level selector construction, validation upload, Docker upload, or hosted metric claims.
