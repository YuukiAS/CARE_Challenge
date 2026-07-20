# CARE SRR 主线代码改动审阅账本

Plan metadata:
- Type: append-only implementation change ledger
- Lane: historical Route B merged into main; single active SRR mainline
- Round scope: Round04 recovery label only; no Round05
- Status: active
- Parent roadmap: `docs/plans/`
- Parent plan: `docs/plans/laneB_round04_active_srr_mainline_production_execution.md`
- Function: 让用户和后续 GPT/Codex 能逐次看到每批代码补全究竟改了什么、真实数据流是否改变、旧绕过是否被关闭、仍有哪些缺口
- Do not: 不得只记录 token、PASS、测试数量或自然语言“已实现”；不得覆盖旧记录；不得把性能结论写入代码补全记录
- Rule exception: 用户明确要求暂停旧 portfolio/route 流程，直接在 `main` 开发，并要求每次代码完成后解释具体变化。

## 账本规则

1. 本文件 append-only；旧记录只能追加 `Correction`，不能静默改写。
2. 每个写入 `main` 的 SRR production commit 必须新增一条记录。
3. 一条记录只能对应一个明确代码批次；混合多个无关改动必须拆开。
4. 记录必须绑定 base/head SHA。
5. “测试通过”不等于“实现完成”；必须说明测试验证了哪条真实数据流。
6. 任何未解决问题必须明写，不能留给下一个 GPT 猜。
7. 多个只读审计 GPT 的意见必须分别记录，并标明是否已由 integrator 修复。

## 当前基线

```text
historical Route B reviewed packet merged into main:
078c3548645b14224b997e41995520ec865d4b62

five-day production plan added:
8b801e80472dba54c1bcee008f5c2525e9636723

code completion TODO added:
bde402a85fd11beca3f908e3e41c93d369f529d7

change ledger bootstrap:
1db3c46a3e51915eb51402bc894c2529f1cfa498

CURRENT bound to production sprint:
339738d6790c71d6bee87d59678afeacce67f59a
```

当前已知事实：Round04 reviewer 只确认 operational packet reviewability；旧 B3-B6/B8 不能作为真实生产训练和公平评价证据。后续记录必须从这一事实出发。

---

## 记录模板

复制以下模板追加，不得删除字段。

```markdown
## Change <序号>：<中文短标题>

- 日期/时间：
- 执行线程：
- 审计线程：
- Base commit：
- Head commit：
- 对应 TODO：C<number>
- 状态：complete | partial_complete | qa_failed | blocked

### 1. 本次目标

用两三句话说明本次只解决什么，不要写空泛目标。

### 2. 修改文件

| 文件 | 动作 | 修改前行为 | 修改后行为 |
| --- | --- | --- | --- |
| path | add/modify/delete/deauthorize | ... | ... |

### 3. 真实数据流变化

按顺序写：

```text
输入文件/manifest
-> Dataset/DataLoader
-> tensor shape/availability
-> model component
-> checkpoint/prediction
-> evaluator/export
```

明确哪些节点实际读取真实病例，哪些节点仍未接通。

### 4. 删除或关闭的绕过

逐项列出：

- synthetic/random path；
- hard-coded metric；
- stale wrapper；
- token-only dependency；
- random/deterministic prototype；
- wrong split/label/empty-GT；
- 其他。

若本次没有关闭任何绕过，写 `none`，不能省略。

### 5. 运行命令与结果

| 命令 | Exit | 真实输入 | 真实输出 | 验证的事实 |
| --- | ---: | --- | --- | --- |
| exact command | 0/nonzero | path | path | ... |

不要只写 `pytest passed`；必须说明测试为什么与本次数据流相关。

### 6. 关键数值/形状/哈希

至少记录本次涉及的：

- tensor shapes；
- checkpoint/config/split/prototype/prediction hashes；
- no-T2 edema delta/gradient；
- baseline identity delta；
- evaluator reproduction delta；
- 其他能证明代码行为的数值。

### 7. 人类解释

用中文回答：这次改动对最终 SRR 模型意味着什么？它解决了哪个旧假进展？它尚未证明什么？

### 8. 未解决项

逐文件/函数列出。禁止写“后续完善”。

### 9. 下一批允许范围

列出下一批可以修改的文件和目标；不得泛化成新架构搜索。

### 10. 审计意见

- 模型审计 GPT：
- 数据/评价审计 GPT：
- Cine 审计 GPT：
- 红队 GPT：
- Integrator 处理结果：
```

---

## Change 000：建立五天主线计划与 TODO

- 日期/时间：2026-07-20
- 执行线程：GPT Planner / GitHub connector
- 审计线程：none
- Base commit：`078c3548645b14224b997e41995520ec865d4b62`
- Head commit：`339738d6790c71d6bee87d59678afeacce67f59a`
- 对应 TODO：plan bootstrap
- 状态：complete

### 1. 本次目标

停止 Route A/C 和旧 Round/Controller 周期，把历史 Route B 合并后的 `main` 定义为唯一 SRR 开发主线；建立今天不训练、先全面补完代码和公平评价的工作入口。

### 2. 修改文件

| 文件 | 动作 | 修改前行为 | 修改后行为 |
| --- | --- | --- | --- |
| `docs/plans/laneB_round04_active_srr_mainline_production_execution.md` | add | 无五天单主线计划 | 定义五天生产化、唯一入口、今日禁训、后续训练顺序 |
| `docs/plans/laneB_round04_active_srr_code_completion_todo.md` | add | 无逐批代码补全清单 | 定义 C0-C14 真实代码、评价、Cine、anti-bypass TODO |
| `docs/plans/laneB_round04_active_srr_change_review_ledger.md` | add | 代码改动难以逐次追踪 | 每个 commit 必须解释真实变化和未解决项 |
| `prompts/routes/handoffs/CURRENT.md` | modify | main-only 状态未绑定五天代码计划 | 绑定 production plan/TODO/ledger、今日禁训和唯一 integrator 规则 |

### 3. 真实数据流变化

本次只改变计划和当前入口，不修改模型运行数据流，不声称代码已修复。

### 4. 删除或关闭的绕过

本次没有修改代码；计划层明确取消 token/packet 作为代码成熟依据，并要求旧 synthetic entrypoints 去授权。

### 5. 运行命令与结果

GitHub contents API 已成功创建总计划、TODO、账本并更新 CURRENT；本次未运行服务器测试或训练。

### 6. 关键数值/形状/哈希

- historical reviewed merge: `078c3548645b14224b997e41995520ec865d4b62`
- production plan commit: `8b801e80472dba54c1bcee008f5c2525e9636723`
- TODO commit: `bde402a85fd11beca3f908e3e41c93d369f529d7`
- ledger bootstrap commit: `1db3c46a3e51915eb51402bc894c2529f1cfa498`
- CURRENT production-sprint commit: `339738d6790c71d6bee87d59678afeacce67f59a`

### 7. 人类解释

这次改动只解决“后面到底按什么顺序做、如何防止再次假完成、如何逐次向用户解释”的问题。它没有补模型代码，也没有证明 SRR 性能。

### 8. 未解决项

全部 C0-C14 仍未执行。当前旧 production 路径仍可能绕到 synthetic Round04 scripts。

### 9. 下一批允许范围

先执行 C0/C1：建立唯一 `entrypoints.yaml`、legacy inventory 和 production anti-synthetic scan。今天不得训练。

### 10. 审计意见

- 模型审计 GPT：未执行。
- 数据/评价审计 GPT：未执行。
- Cine 审计 GPT：未执行。
- 红队 GPT：未执行。
- Integrator 处理结果：等待首次代码批次。


---

## Change 001: Batch 0 SRR implementation truth and formal-entrypoint authority

- 日期/时间: 2026-07-20
- 执行线程: CARE SRR main integrator, main-only
- 只读审计线程: Model truth auditor, Data/evaluation auditor, Cine auditor, Red-team auditor
- Base commit: `3f36a4ec62278ae097267d9c0eea14dd5e68a9e7`
- Head commit: final Batch 0 commit SHA is reported in the final integrator response; the exact self SHA cannot be embedded into this tracked ledger entry before creating the commit without changing that SHA.
- 对应 TODO: Batch 0 / C0-C1 implementation truth, formal authority convergence, anti-synthetic scan
- 状态: complete pending commit/push

### 1. 本次目标

只执行 Batch 0: 梳理当前 SRR 实现真相，建立唯一 formal-entrypoint authority 配置，关闭旧 Round04 B3-B8 synthetic/proxy 脚本及其 job wrapper 成为正式入口的路径，并用静态审计和 known-bad 测试证明该约束生效。

本次明确没有训练、没有 Slurm、没有 validation packaging/upload、没有 optimizer loop、没有架构搜索、没有从零写第二套 SRR 模型。

### 2. 修改文件

| 文件 | 动作 | 修改前行为 | 修改后行为 |
| --- | --- | --- | --- |
| `configs/srr_production/entrypoints.yaml` | add | 无 Batch 0 formal-entrypoint authority；旧 `--formal` wrapper 可能被误读成生产入口 | 明确 `formal_training_status: BLOCKED_PENDING_BATCH1_REPAIR`，`formal_entrypoints: []`；只保留现有 SRR runner/evaluator 为 candidate；列出 B3-B8 Python 脚本和 job wrapper 为 `forbidden_formal_entrypoint` |
| `scripts/srr_production/audit_formal_entrypoints.py` | add | 无统一静态审计器阻止 synthetic/proxy 路径成为 formal | `audit_config`, `formal_entries`, `configured_forbidden`, `source_calls_forbidden`, `source_matches`, `source_metric_matches` 会拒绝 B3-B8、B3-B8 wrapper、科学数据中的 random tensor、硬编码 metric、deterministic/random prototype bootstrap |
| `tests/srr_production/test_formal_entrypoint_authority.py` | add | 无 known-bad 单测证明旧路径不能被恢复为 formal | 覆盖默认 blocked-strict pass、B6/B8 known-bad fail、B6 job wrapper fail、临时 random/hard-coded metric formal path fail |
| `results/srr_production/code_maturity/current_implementation_truth.md` | add | 当前实现状态散落在代码和历史计划中，容易把 synthetic/proxy 和真实路径混同 | 按 `already real and reusable`、`real but incomplete`、`declared but disconnected`、`synthetic/proxy`、`historical only`、`must repair in Batch 1` 分类记录 |
| `results/srr_production/code_maturity/canonical_call_graph.json` | add | 无机器可读 call graph | 记录 MyoPS candidate、B3-B8 legacy、Cine B7/B8 的数据源、模型、prototype/memory、loss、metric 和 authority 状态 |
| `results/srr_production/code_maturity/variant_final_output_matrix.csv` | add | variant 与 final logits 关系未集中记录 | 列出 legacy baseline residual、M6 arbitration、M9 pure SRR-main、M10 pure proposal-refinement、baseline-preserving gate 的 final-output truth |
| `results/srr_production/code_maturity/anchor_prototype_loss_checkpoint_matrix.csv` | add | anchor/prototype/loss/checkpoint/metric 真相未集中记录 | 区分真实 cached nnU-Net anchor、deterministic prototype fallback、real runtime prototype fitting、disconnected memory、real/zero/disconnected losses、token-only B3-B6 continuity、hard-coded metrics |
| `results/srr_production/code_maturity/cine_call_graph.md` | add | Cine B7/B8 容易被误解为真实 downstream CineMA/registration | 明确 B7 只是 isolated official CineMA probe + synthetic adapter，B8 是 synthetic fixed/moving pair，无真实 4D/ED-space export authority |
| `results/srr_production/code_maturity/legacy_path_inventory.csv` | add | 旧 wrapper/synthetic/proxy 入口未统一盘点 | 列出 B3-B8 Python、B3-B8 job wrapper、当前候选 runner/evaluator/model/memory 的 formal policy 和 evidence |
| `docs/plans/laneB_round04_active_srr_change_review_ledger.md` | modify | 只有 Change 000 计划层记录 | 追加本 Change 001 的实际行为、命令、哈希、未解决项、Batch 1 精确函数清单和四路审计意见 |

### 3. 真实数据流变化

本次没有改变模型 forward、loss 计算、训练循环、数据读取或 evaluator 的运行行为。真实数据流变化只发生在 authority 层:

- 正式训练入口从“未集中定义、旧 `--formal` wrapper 可能被误读”收束为 `formal_entrypoints: []`。
- 当前唯一可继续修复的训练候选是 `scripts/training/run_srr_propref_myops_fold0.py`，但它不是 formal training entrypoint。
- 当前唯一可复用的本地 metric 候选是 `scripts/evaluation/evaluate_predictions.py`，但它不是训练入口，也不代表 hosted leaderboard authority。
- `src/care_myocardium/models/srr_propref.py` 被选为现有模型源码候选，不是新模型实现。

### 4. 删除或关闭的绕过

- synthetic/random path: B3-B8 Python 脚本和 B3-B8 job wrapper 被列入 `forbidden_formal_entrypoints`；审计器会在它们进入 formal config 时非零退出。
- hard-coded metric: formal path 源码中若出现 Dice/AUC/HD/metric/proxy 固定数值赋值，审计器会非零退出；B4/B5/B6 被记录为 hard-coded/fixed proxy metric historical only。
- stale wrapper: `jobs/route_B_round04/run_B3_representation.sh` 到 `run_B8_registration.sh` 被作为 formal wrapper 禁止，而不只禁止 Python 脚本。
- token-only dependency: B3->B4->B5->B6 被记录为 token/file existence continuity，不是 parent model/optimizer/prototype/config continuity。
- random/deterministic prototype: formal path 源码若使用 `deterministic_axis_prototypes`、random prototype、bootstrap pending，会非零退出；当前 model 默认 deterministic prototype 只允许作为 unfit module initialization，不允许作为 formal evidence。
- Cine formal bypass: B7 的 isolated CineMA probe 和 B8 的 synthetic pair registration 被记录为不能提供 downstream Cine authority。

### 5. 运行命令与结果

| 命令 | Exit | 真实输入 | 真实输出 | 验证的事实 |
| --- | ---: | --- | --- | --- |
| `git status --short` | 0 | `/users/a/e/aereinh/CARE` | 初始为空；修改后只含本次 Batch 0 文件 | 启动时没有未提交本地内容需要保全 |
| `git fetch --all --prune` | 0 | origin remotes | `origin/main` 更新到 `3f36a4ec62278ae097267d9c0eea14dd5e68a9e7` | 同步远端，不 force push |
| `git branch --show-current` | 0 | worktree | `main` | 确认本次直接在 main 执行 |
| `git rev-parse HEAD` | 0 | worktree | `3f36a4ec62278ae097267d9c0eea14dd5e68a9e7` | fast-forward 后基线为指定 main |
| `python scripts/srr_production/audit_formal_entrypoints.py --strict` | 0 | `configs/srr_production/entrypoints.yaml` | failure_count 0, formal_entrypoint_count 0 | 默认 formal authority 为空且 blocked 状态合法 |
| `python scripts/srr_production/audit_formal_entrypoints.py --strict --known-bad legacy_b6` | 1 expected | in-memory config 将 B6 设为 formal | `forbidden_formal_entrypoint` for `run_B6_joint.py` | 旧 B6 不能成为 formal entrypoint |
| `python scripts/srr_production/audit_formal_entrypoints.py --strict --known-bad legacy_b8` | 1 expected | in-memory config 将 B8 设为 formal | `forbidden_formal_entrypoint` for `run_B8_registration.py` | 旧 B8 不能成为 formal entrypoint |
| `python -m pytest -q tests/srr_production/test_formal_entrypoint_authority.py` | 1 then fixed | first run with tmp config under repo-external pytest path | 3 passed, 2 failed due config path reporting using `relative_to(REPO_ROOT)` | 暴露审计器对 repo 外临时 YAML 不健壮；随后修复 `display_path` |
| `python -m pytest -q tests/srr_production/test_formal_entrypoint_authority.py` | 0 | final audit script and tests | `5 passed in 0.64s` | 默认 blocked、B6/B8 known-bad、B6 wrapper、random/hard-coded metric fixtures 均按预期 |
| `git diff --check` | 0 | current unstaged diff | no whitespace errors | 本次改动无 whitespace diff 问题 |

### 6. 关键数值/形状/哈希

- Base source SHA: `3f36a4ec62278ae097267d9c0eea14dd5e68a9e7`
- Initial local branch before fetch: `main` at `af630ef017b87fe86b01d5fd8aaa44203c1aa6d4`
- Fast-forward target: `origin/main` at `3f36a4ec62278ae097267d9c0eea14dd5e68a9e7`
- `configs/srr_production/entrypoints.yaml`: `e14699fe9a6df2cf338f33ec83c077f9853075e375bf48f7f6c29d354dc82533`
- `scripts/srr_production/audit_formal_entrypoints.py`: `658a28cde5ec78d7958e579994b797664ae91eef3673a4131055739ba007de8a`
- `tests/srr_production/test_formal_entrypoint_authority.py`: `d0286663a3cb2e2ff34d35505cd966e94aeaf605b8b82044f85b03d2326cb5ab`
- `results/srr_production/code_maturity/current_implementation_truth.md`: `fa861f847be00986c055ba7712baef35723710a34f176e9b94a5bf05ee421e0c`
- `results/srr_production/code_maturity/canonical_call_graph.json`: `6dfb9649ebd38d0f49dd2492c8b6b58acbbaff04177c2cb93909257966ef1b21`
- `results/srr_production/code_maturity/variant_final_output_matrix.csv`: `86d942b9b2591355453b690c6ab13d035ebe6c8e5ab76a956bd52bf756562d16`
- `results/srr_production/code_maturity/anchor_prototype_loss_checkpoint_matrix.csv`: `bc6b3e5821e9192394a83ee75968722d314bebcf5c97284f29dd4f93b94c8425`
- `results/srr_production/code_maturity/cine_call_graph.md`: `09bf1ec2add0cdffc3328cef4289fbb66b7f7f326d256d64a8eb9223f2cece1b`
- `results/srr_production/code_maturity/legacy_path_inventory.csv`: `a24d32420d76e10b3c274f0f31703aff96801c031e7939598e3221ec4d2f9f10`
- 本次没有训练 tensor shapes、no-T2 edema gradient、baseline identity delta、evaluator reproduction delta 或性能数值；这些必须等 Batch 1/后续非禁训批次用真实运行证据记录。

### 7. 人类解释

这次改动不是让 SRR 变强，也不是宣布训练就绪；它解决的是“哪些代码可以被称为 formal authority”这个更底层的问题。旧 Round04 B3-B8 中存在 synthetic tensor、hard-coded proxy metric、token-only continuity、isolated Cine probe 等假进展路径，现在这些路径即使带 `--formal` 或通过 job wrapper 调用，也不能被 authority 配置接受。当前真实可复用资产是现有 SRR model、真实 Dataset501/cached nnU-Net anchor runner、以及 prediction/GT evaluator；但它们还缺 formal provenance、checkpoint continuity、memory/prototype wiring 和 fair-eval gates。

### 8. 未解决项

| 文件 | 函数/区域 | 未解决项 |
| --- | --- | --- |
| `scripts/training/run_srr_propref_myops_fold0.py` | `main`, `train_variant` | 没有 production-mode formal gate；M10 变体未通过 CLI 暴露；anchor/prototype/checkpoint hash 还未形成正式 manifest |
| `scripts/training/run_srr_propref_myops_fold0.py` | `fit_and_load_runtime_prototype_bank` | 仍需严格拒绝 deterministic fallback，并记录真实 train/OOF prototype source counts/hash |
| `scripts/training/run_srr_propref_myops_fold0.py` | `propref_loss` | M10 loss expansion和 memory/prototype dependency 需要 formal autograd 检查 |
| `src/care_myocardium/models/srr_propref.py` | `SRRProposeRefineMyoPS.forward` | M10 `m10_final_probabilities` 目前是 diagnostic，`outputs["logits"]` 仍为 `srr_logits`; memory-enabled variants 未真正连接 memory query 到 proposal/final logits |
| `src/care_myocardium/models/srr_propref.py` | `ProposalDictionary.forward`, `load_prototype_bank` | 默认 deterministic prototypes 需要 formal 禁用或 provenance gate；real bank load 需要 source manifest |
| `src/care_myocardium/models/srr_dictionary_memory.py` | `SafePrototypeMemoryBank`, `M10CrossFittedPrototypeMemory` | 类存在但未进入当前 SRR proposal/logit/loss authority |
| `src/care_myocardium/losses/srr_losses.py` | `expanded_srr_loss` and helpers | memory loss 可能 placeholder-zero；dictionary/SIP 需要 formal nonzero/dependency gates |
| `scripts/evaluation/evaluate_predictions.py` | `main`, metric helpers | local recompute 真实，但 production fair-eval authority 需要 empty-GT、fold parity、component/remote-FP 和 subgroup 输出 |
| `scripts/training/route_B_round04/cine/B7/run_B7_cinema_control.py` | `main`, adapter/probe path | official CineMA 未进入 downstream；synthetic adapter 不能 formal |
| `scripts/training/route_B_round04/cine/B8/run_B8_registration.py` | `main`, `make_pair`, registration/export path | 缺真实 4D input、ED/reference/key frames、real fixed/moving、transform/warp、temporal aggregation、ED-space export |

### 9. 下一批允许范围

Batch 1 应只修改现有文件和函数，不做新架构搜索:

1. `configs/srr_production/entrypoints.yaml`: 将 Batch 1 选择的唯一 real runner/evaluator 绑定到 exact config、split、checkpoint/cache、prototype 和 output manifest；仍禁止 B3-B8。
2. `scripts/training/run_srr_propref_myops_fold0.py`: 在 `main`, `train_variant`, `fit_and_load_runtime_prototype_bank`, `propref_loss` 加 formal mode、M10 exposure、prototype fallback rejection、checkpoint/prototype/anchor hash manifest、autograd dependency gates。
3. `src/care_myocardium/models/srr_propref.py`: 在 `SRRProposeRefineMyoPS.forward`, `ProposalDictionary.forward`, `ProposalDictionary.load_prototype_bank` 明确 final-output mode，禁止 unfit deterministic prototype formal use，连接或显式阻断 memory variants。
4. `src/care_myocardium/models/srr_dictionary_memory.py`: 在 `SafePrototypeMemoryBank` 和 `M10CrossFittedPrototypeMemory` 的 update/query 路径补真实训练/OOF provenance，并将 query output 接入 proposal/loss 或保持非 formal。
5. `src/care_myocardium/losses/srr_losses.py`: 在 `expanded_srr_loss`、`prototype_memory_alignment_loss`、`semantic_retrieval_regularization`、`negative_space_consistency_loss` 增加 zero/disconnected known-bad gate。
6. `scripts/evaluation/evaluate_predictions.py`: 绑定 formal fair-eval config、empty-GT policy、fold parity、component/remote-FP 输出和 subgroup report。
7. Cine 若进入 Batch 1: 只能修 `scripts/training/route_B_round04/cine/B7/run_B7_cinema_control.py` 与 `B8/run_B8_registration.py` 的真实 4D/CineMA/downstream/export 数据流，不能以 synthetic probe 充当 formal。

### 10. 审计意见

- 模型审计 GPT: 13 个 `SRRProposeRefineMyoPS` variant 可实例化；legacy/M6/M9/M10 final-output 语义不同。M10 variant 在 model 内存在，但 current runner 未暴露；memory helper 未连到 proposal logits；B3-B6 是 synthetic/token-continuity，不是 checkpoint-continuity。
- 数据/评价审计 GPT: `evaluate_predictions.py` 是真实 prediction/GT NIfTI recompute；SRR runner 使用真实 Dataset501 和 cached nnU-Net `.npz`/`.nii.gz` anchor，不直接加载 checkpoint 推理；B4/B5/B6 proxy metric 是 hard-coded/fixed formula，必须 forbidden。
- Cine 审计 GPT: B7 official CineMA 只是 isolated probe，adapter 使用 synthetic frame/target；B8 使用 synthetic fixed/moving pair，没有真实 4D frame、registration warp、temporal aggregation 或 ED-space export。
- 红队 GPT: 必须同时禁止 B3-B8 Python 和 job wrappers；formal scanner 需要拦截 random scientific data、hard-coded metric、deterministic/random prototype bootstrap、legacy wrapper 调用。
- Integrator 处理结果: 已把 B3-B8 与 wrapper 收入 `forbidden_formal_entrypoints`，新增 strict audit 和 pytest known-bad；当前没有 production formal training entrypoint，状态保持 `BLOCKED_PENDING_BATCH1_REPAIR`。
