# CARE-PRISM v2 Backbone Repair Controller

## Controller Prompt

你是 CARE Challenge 项目的 Controller / Coordinator。当前任务不是重新设计 PRISM，而是修复错误的 ResEnc-only 资产合同，完成 W1 真实实现闭环，然后继续 W2/W3，满足门槛后才进入 W4。

仓库：

```text
/users/a/e/aereinh/CARE
remote: YuukiAS/CARE_Challenge
branch: main
```

开始前同步 `origin/main`，确认包含：

```text
549dc4aed1a74682f8d35932f3d4fc7b7d61f564
1f1f39264cf248fb11d0322f41d4fe4c2aae021d
```

按优先级读取：

```text
prompts/tasks/20260729_care_prism_v2_backbone_and_w1_repair_amendment.md
prompts/tasks/20260729_care_prism_v2_backbone_repair_executor_plan.yaml
prompts/tasks/20260729_care_prism_execution_hardening_amendment_v2.md
prompts/blueprints/CARE_PRISM_pathology_retrieval_soft_cascade_20260729.md
prompts/routes/handoffs/CURRENT.md
AGENTS.md
START_HERE_FOR_GPT.md
GPT_PLANNER_CARE_PROTOCOL.md
prompts/AGENT_FLOW_V2_PROTOCOL.md
prompts/HANDOFF_GATE_POLICY.md
prompts/GPT_HARD_GATE_PROMPT.md
prompts/routes/ROUTE_ANTI_LAZINESS_PROTOCOL.md
prompts/routes/ROUTE_HARD_REQUIREMENTS_MATRIX.md
wiki/README.md
.agents/skills/slurm-routing-partition/SKILL.md
.agents/skills/care-mapper/SKILL.md
```

旧结论“没有合法同折 checkpoint”已被 Planner 修正：合法资产是本项目实际公平基线使用的标准 nnU-Net 同折 checkpoint，不再限定 ResidualEncoderUNet。

先定位并校验：

```text
fold0:
data/nnUNet/nnUNet_results/Dataset501_CAREMyoPS/nnUNetTrainer_500epochs__nnUNetPlans__3d_fullres/fold_0/checkpoint_final.pth
sha256 8bceb20cae8920e87d43b14665a0db9dfd4f1204533d25a3cd6e40ad9de74111

fold1:
data/nnUNet/nnUNet_results/Dataset501_CAREMyoPS/nnUNetTrainer_500epochs__nnUNetPlans__3d_fullres/fold_1/checkpoint_final.pth
sha256 5310569ff62f2f9a6ff2bc7dd3754404140071427a2025caf5e25d2916cfe400
```

仓库相对路径未解析时，检查 `nnUNet_results` 环境变量和 repo-local symlink 目标。历史 manifest只作定位，必须对实际文件重新 stat/hash。不得再只搜索名称含 resenc 的目录，不得用 MMRD/Batch9 自定义 checkpoint，也不得从零训练新 ResEnc。

R1 中必须继续检查并修复当前部分实现，不能发现 checkpoint 后直接训练：

1. 用 `nnUNetPlans.json` 和 checkpoint 动态恢复真实 stock nnU-Net network class；共享 encoder 移植覆盖率按参数字节 >=0.99，FP32逐尺度奇偶误差 <=1e-6。
2. 当前代码只把 level0送入 refiner，深层 routed/anatomy scales实际无效；改成真实 top-down anatomy decoder和scar/edema多尺度decoder，所有声明尺度必须通过on/off改变最终logit。
3. 当前slice correspondence是no-op；正式冻结identity并诚实记录，除非真实实现并通过独立门。
4. 当前dataset仍synthetic-only；实现真实Dataset501完整病例、split排除、center×burden×positive/safe-negative采样和增强。
5. 补齐正式 `run_care_prism.py`、`evaluate_care_prism.py`、`validate_care_prism_packet.py`。
6. 替换surface/MIL placeholder；四通道negative targets不能全零，必须来自病种安全负空间；edema negatives只来自T2-present。
7. burden必须通过零初始化FiLM真实调制proposal和refiner，否则从方法中删除。
8. prototype保持默认关闭，不得阻塞核心模型；no-T2 probability/mask/loss/gradient必须精确为零。
9. checkpoint/resume必须恢复next case、augmentation、LR、optimizer、scheduler、scaler和全部状态。

Controller必须亲自检查真实diff、正式入口和matched on/off干预。任何普通实现、数据、OOM、cache、sampler、loss、resume、evaluation或validator问题都退回同一Executor继续修复，不能再次写成asset block或科学失败。

W1全部通过后执行W2 400-step real-case zero-credit preflight；W2通过后执行W3 fold0 6500步并评价所有checkpoint，只用train-side inner选择并reload，freeze后outer只评一次；仅W3全部机制门通过才执行W4 fold1 8000步clean训练与一次outer评价。禁止synthetic W2 credit、terminal-checkpoint-only选择和fold1 outer调参。

先检查既有 allocation `61220581`。若仍运行，所有GPU命令只能串行：

```bash
srun --jobid=61220581 --overlap --ntasks=1 bash -lc '<command>'
```

禁止 `sbatch`、`salloc`、新Slurm job、并行GPU、写 `/overflow/htzhu/CARE`、runtime push、validation/Docker upload。若allocation已终止，记录精确resume point并返回 `OPERATIONALLY_BLOCKED`。

Controller持续负责到全部已启动进程terminal、post-completion aggregation、strict validator、Mapper final、CURRENT/wiki一致性和轻量本地commit完成。只有忠实实现、足额训练、全部checkpoint重载评价后仍未过机制门，才返回Planner并给出 `ROUTING / ANATOMY_EXCHANGE / PROPOSAL / NEGATIVE_SPACE / REFINEMENT / CALIBRATION` 精确分类。