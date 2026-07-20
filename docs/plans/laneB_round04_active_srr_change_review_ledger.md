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


---

## Change 002: Batch 1 MyoPS single-mainline non-training repair

- 日期/时间: 2026-07-20
- 执行线程: CARE SRR main integrator, main-only
- 只读审计线程: Model-forward auditor, Anchor/prototype auditor, Loss/gradient auditor, Checkpoint/red-team auditor
- Base commit: `bfced937d0d864e2f591664d71b27b545fe792fb`
- Head commit: final Batch 1 commit SHA is reported in the final integrator response; exact self SHA cannot be embedded before commit without changing that SHA.
- 对应 TODO: Batch 1 MyoPS mainline repair
- 状态: complete pending commit/push

### 1. 本次目标

只修 MyoPS 单一主干，不修 Cine、不恢复 B3-B8、不训练、不 Slurm、不做 44 例性能比较。目标是把现有 `SRRProposeRefineMyoPS` 和 fold0 runner 收束为非训练 production authority smoke: 真实 OOF anchor、真实 prototype/memory、显式 anchor-bounded final output、单次 forward/backward、known-bad 拒绝和 checkpoint roundtrip。

### 2. 修改文件

| 文件 | 函数/区域 | 修改前行为 | 修改后行为 |
| --- | --- | --- | --- |
| `src/care_myocardium/models/srr_propref.py` | `ProposalDictionary.load_prototype_bank` | 只复制 bank；允许 deterministic/repeat fallback 结果被当作普通 source | 增加 `strict` 与 provenance；production strict 拒绝 deterministic/random、空向量、repeat-last、source vector count 不足 |
| `src/care_myocardium/models/srr_propref.py` | `ProposalDictionary.forward` | proposal 只用本地 positive/negative prototype buffers 和内置 negative memories | 接收 `memory_query`，将 cross-fitted positive/negative similarity 合入 proposal formula，影响 proposal logits |
| `src/care_myocardium/models/srr_propref.py` | `SRRProposeRefineMyoPS.__init__` | final-output 语义由 variant 隐式决定；无 production correction gate；未实例化 cross-fitted memory | 增加 `final_output_mode`，支持 `anchor_bounded_srr_correction` 和 `srr_no_anchor_control`；增加 `production_correction_gate` 和 `M10CrossFittedPrototypeMemory` |
| `src/care_myocardium/models/srr_propref.py` | `SRRProposeRefineMyoPS.forward` | M9/M10 可直接输出 `srr_logits`；memory 未接 proposal；production 无 `case_ids` fail gate | production mode 要求 `case_ids`，query cross-fitted memory，计算 `final_logits = frozen anchor + bounded scar correction + bounded edema correction`；`anchor_identity_control` 使 correction exact zero；`srr_no_anchor_control_logits` 仅诊断输出 |
| `src/care_myocardium/models/srr_dictionary_memory.py` | `SafePrototypeMemoryBank.update/summary` | 记录 ledger 但无 provenance summary | 记录 accepted provenance；保留 no-T2 edema-negative rejection |
| `src/care_myocardium/models/srr_dictionary_memory.py` | `M10CrossFittedPrototypeMemory.update/query/summary` | query 排除当前 shard，但可在未 ready 时返回零初始化 memory；summary 使用错误 `row.status` | 增加 source provenance、positive/negative source count、`require_ready` fail-closed；summary 使用 `row.reason == ACCEPTED` |
| `src/care_myocardium/models/srr_spatial_dictionary.py` | `M10TwoPassSpatialDictionary.forward` | 返回 gates/status，但 receipt 缺 query 输入与 slot mask policy 字段 | 增加 `spatial_query_inputs` 和 `slot_mask_policy` 审计字段 |
| `scripts/training/run_srr_propref_myops_fold0.py` | `M10_PRODUCTION_VARIANTS`, CLI choices | M10 只能从 wrapper 间接触达，runner CLI 不接受 | runner CLI 接受 M10 variants，但仍不授权正式训练 |
| `scripts/training/run_srr_propref_myops_fold0.py` | `model_kwargs_from_args`, `main` | 无显式 final-output mode 参数 | 增加 `--final-output-mode` 并传入现有模型 |
| `scripts/training/run_srr_propref_myops_fold0.py` | `propref_loss` | expanded loss 只覆盖 M6/M7/M8/M9 | M10 也走 expanded SRR loss，包含 live Pattern-SIP/dictionary/proposal/refiner/control terms |
| `scripts/training/run_srr_propref_myops_fold0.py` | `predict_case`, `validate_patch_loss`, `run_one_batch_overfit`, `train_variant` model calls | production memory 无 `case_ids`，正常 path 不能 query cross-fitted bank | 按真实 case id/keys 传 `case_ids`，使 production mode 的 memory leakage control 与 proposal影响可执行 |
| `configs/srr_production/myops_batch1.yaml` | new | 无 Batch 1 MyoPS production smoke config | 固定 M10 D3、四尺度、spatial retrieval、Pattern-SIP、cross-fitted memory、`anchor_bounded_srr_correction`；formal authority 仍 false |
| `scripts/srr_production/validate_myops_mainline.py` | new | 无 Batch 1 strict validator | 生成 220-case OOF manifest、prototype/memory provenance、forward/gradient/intervention/checkpoint/known-bad receipts；不训练不 step |
| `tests/srr_production/test_myops_mainline_batch1.py` | new | 无 Batch 1 unit/integration known-bad coverage | 检查 authority 仍 blocked for Batch2、OOF manifest/receipts、12 个 known-bad fixture 全拒绝 |
| `scripts/srr_production/audit_formal_entrypoints.py` | `audit_config` | strict 只允许 `BLOCKED_PENDING_BATCH1_REPAIR` 下空 formal entrypoints | 允许 Batch 2 blocked 状态下继续空 formal entrypoints |
| `tests/srr_production/test_formal_entrypoint_authority.py` | default status test | 期待 Batch 1 blocked status | 期待 `BLOCKED_PENDING_BATCH2_INFERENCE_AND_FAIR_EVALUATION` |
| `configs/srr_production/entrypoints.yaml` | authority status/candidates | `BLOCKED_PENDING_BATCH1_REPAIR` | `BLOCKED_PENDING_BATCH2_INFERENCE_AND_FAIR_EVALUATION`；新增 Batch 1 validator candidate，formal training 仍空 |

### 3. 真实数据流变化

Production MyoPS smoke 现在的真实链路为：

```text
Dataset501 real patch + availability
-> four-scale modality encoders
-> shared/private/interaction retrieval gates with invalid-slot zeroing
-> M10 spatial dictionary gates and live Pattern-SIP statistics
-> real fold0-train prototype vectors and cross-fitted memory query excluding query shard
-> positive/negative similarity
-> scar/edema proposal logits
-> scar/edema soft-ROI refiner logits
-> bounded scar/edema correction
-> frozen same-case OOF nnU-Net anchor logits
-> final logits
```

`anchor_identity_control` 的实测 `anchor_identity_max_abs_delta = 0.0`。`srr_no_anchor_control_logits` 保留为诊断输出，不进入 production final path。

### 4. 删除或关闭的绕过

- production pure-SRR 绕过: `final_output_mode=anchor_bounded_srr_correction` 时 final logits 不再由 M9/M10 variant 隐式切到 `srr_logits`。
- memory-disconnected 绕过: validator 记录 `memory_intervention_proposal_delta_mean=0.0655626654624939` 和 `memory_intervention_final_delta_mean=0.0031393414828926325`；memory 改变会影响 proposal 和 final。
- prototype fallback 绕过: strict `load_prototype_bank` 拒绝 deterministic/random/empty/repeat-last/source-count 不足。
- current-case leakage: production forward 必须传 `case_ids`，`M10CrossFittedPrototypeMemory.query(require_ready=True)` 排除当前 deterministic shard。
- missing modality slot: strict smoke 记录 `invalid_missing_slot_gate_max=0.0`。
- no-T2 edema: strict smoke 记录 `no_t2_edema_correction_abs_max=0.0`，`edema_owned` gradient `0.0`。
- old B3-B8: Batch 0 禁止保持不变，Batch 1 known-bad 包含 `legacy_b6_chain` 拒绝。

### 5. 运行命令与结果

| 命令 | Exit | 真实输入 | 真实输出 | 验证的事实 |
| --- | ---: | --- | --- | --- |
| `git status --short` | 0 | `/users/a/e/aereinh/CARE` | 启动为空 | 无需保全未提交工作 |
| `git fetch --all --prune` | 0 | origin | `origin/main` updated `4144277..bfced93` | 远端同步 |
| `git merge --ff-only origin/main` | 0 | local main | fast-forward 到 `bfced937d0d864e2f591664d71b27b545fe792fb` | 当前 main 满足 expected minimum |
| `python scripts/srr_production/audit_formal_entrypoints.py --strict` | 0 | `configs/srr_production/entrypoints.yaml` | failure_count 0; formal_entrypoint_count 0 | formal training 仍未授权，Batch2 blocked 状态合法 |
| `PATH=/users/a/e/aereinh/CARE/envs/env_CARE/bin:$PATH python scripts/srr_production/validate_myops_mainline.py --strict` | 1 then fixed | real Dataset501, cached nnU-Net anchors, current model | first failed on `M10MemoryUpdate.status`; fixed summary to use `reason` | 审计发现的 memory summary bug 被真实 smoke 触发并修复 |
| same strict validator | 1 then fixed | same | failed `BATCH_1_BLOCKED_PROTOTYPE_MEMORY_NOT_CONNECTED` because query shard lacked edema source memory | source selection changed to include T2-present edema-positive cases across all four shards |
| same strict validator | 1 then fixed | same | failed checkpoint roundtrip exact because validator compared post-intervention checkpoint against pre-intervention outputs | roundtrip reference changed to current post-intervention state |
| same strict validator | 0 | `configs/srr_production/myops_batch1.yaml`; 220 cached OOF anchor rows | 8 Batch 1 receipts under `results/srr_production/code_maturity/` | OOF manifest, production final output, memory influence, no-T2 exact-zero, Pattern-SIP grad, checkpoint roundtrip all passed |
| `PATH=/users/a/e/aereinh/CARE/envs/env_CARE/bin:$PATH python -m pytest -q tests/srr_production/test_formal_entrypoint_authority.py` | 0 | formal authority tests | `5 passed` | B3/B8 formal-entrypoint rejection remains active |
| `PATH=/users/a/e/aereinh/CARE/envs/env_CARE/bin:$PATH python -m pytest -q tests/srr_production/test_myops_mainline_batch1.py` | 0 | Batch 1 receipts and known-bad fixtures | `4 passed` with 12 known-bad fixtures rejected | Batch 1 authority and known-bad coverage pass |
| `git diff --check` | 0 | current diff | no whitespace errors | diff clean |

### 6. 关键数值/形状/哈希

- Base commit: `bfced937d0d864e2f591664d71b27b545fe792fb`
- OOF anchor manifest: `case_count=220`, `unique_cases=220`, `fold_counts={0:44,1:44,2:44,3:44,4:44}`
- First manifest row: `Case1001`, source fold `1`, tensor shape `[6, 9, 256, 256]`, `is_oof=true`
- Smoke selected cases: LGE-only `Case1001`; LGE+C0 `Case5001`; LGE+C0+T2 `Case2001`; T2-present edema-positive `Case2001`; no-T2 scar-positive `Case1001`
- Prototype/memory source cases: `Case2009`, `Case2001`, `Case2005`, `Case2006`, `Case1001`, `Case5001`
- Prototype vector counts: scar positive `288`, scar negative `1024`, edema positive `384`, edema negative `768`; required scar positive `6`, scar negative `12`, edema positive `8`, edema negative `6`
- Gradient receipt: edema encoder `313.71407964185346`, router `2110.2480482227734`, dictionary `0.448317086789757`, proposal `0.448317086789757`, refiner `117.02662850171328`, correction gate `8.817614934741869e-05`, Pattern-SIP router `9.56051271986784`, no-T2 edema-owned `0.0`
- Intervention: identity max delta `0.0`; invalid missing slot gate max `0.0`; memory proposal delta mean `0.0655626654624939`; memory final delta mean `0.0031393414828926325`; optimizer/slurm/formal training counts all `0`
- Checkpoint roundtrip: max tensor delta `0.0`; global step `0`; epoch `0`; optimizer state present; scheduler/scaler explicit null; checkpoint SHA `388a06d15f4b1026aa1eea137a5eec6c1ead962ac77401d7afe47372d6954bb9`
- File hashes: `configs/srr_production/myops_batch1.yaml=5c1448f509e672adb11e1dff84c889403d4485441f652c02364c8bccb9983ccf`; `validate_myops_mainline.py=f3cc94800dbb970ce5d0db115cad11c96a3ba72b0b03b2a4031b39f33ae16219`; `batch1_anchor_oof_manifest.json=ecde977a1d1d72014b9abff18cfd56320720ec6cfbac649dece30801fc5f2465`; `batch1_gradient_receipt.csv=2661b45f4fe37dd232986438fda269686cc6e4b5025093410056998b0d6593a6`

### 7. 人类解释

这次修的是 MyoPS SRR 主干的代码真实性，不是模型性能。现在 production smoke 的 final logits 有唯一语义：冻结 OOF nnU-Net anchor 作为 base，只允许由真实图像、retrieval、prototype/memory proposal 和 refiner 产生 bounded scar/edema correction。旧的 pure SRR、M6 arbitration、B3-B8 synthetic/proxy 都不能被默认为 production authority。

### 8. 未解决项

| 文件 | 函数/区域 | 未解决项 |
| --- | --- | --- |
| `scripts/training/run_srr_propref_myops_fold0.py` | `train_variant` | 虽然 production mode runner plumbing 已接通，但本批没有执行正式训练；formal training 仍未授权 |
| `scripts/training/run_srr_propref_myops_fold0.py` | checkpoint save/resume | validator 证明了 one-shot model/optimizer/null scheduler/null scaler/RNG metadata roundtrip；完整 long-run resume CLI 仍属于 Batch 2/训练授权前工作 |
| `scripts/evaluation/evaluate_predictions.py` | all | 本批禁止修改 evaluator；fair inference/evaluation 属于 Batch 2 |
| Cine files | all | 本批禁止 Cine；B7/B8 仍 historical forbidden，不代表 Cine production repaired |
| performance | all | 没有 44 例评价、没有 Dice 结论、没有 hosted metric 结论 |

### 9. 下一批允许范围

Batch 2 应只做 inference and fair evaluation authority:

1. 在不训练或按新授权训练的前提下，建立 production inference entrypoint，读取 Batch 1 anchor/prototype/memory manifests。
2. 绑定 `scripts/evaluation/evaluate_predictions.py` 的 empty-GT、fold parity、component/remote-FP/subgroup 输出，不改写 metric 含义。
3. 对 fold0 validation 做公平 SRR-vs-nnU-Net 本地重算；仍不得把结果包装成 hosted leaderboard 结论。
4. 若需要正式训练，必须有新的明确授权和资源计划；Batch 1 commit 本身不授权训练。

### 10. 审计意见

- Model-forward auditor: 指出 M9/M10 pure-SRR final-output、缺 `srr_no_anchor_control`、M10 memory 未接 proposal、M10 CLI 未暴露；Integrator 已用 `final_output_mode`、diagnostic logits、memory query、M10 CLI choices 修复。
- Anchor/prototype auditor: 确认 5 fold x 44 = 220 OOF anchors 完整，protocol split 与 nnU-Net split 匹配；指出 memory summary `row.status` bug 和 memory readiness 问题；Integrator 已修复并生成 220-case manifest。
- Loss/gradient auditor: 指出 M10 未走 expanded loss、Pattern-SIP 需要 live gate gradient、no-T2 exact-zero 需独立 receipt；Integrator 已让 M10 走 expanded loss并生成 gradient/no-T2 receipt。
- Checkpoint/red-team auditor: 指出 runner 默认非 production、normal path 未传 `case_ids`、checkpoint 不等于 resume authority；Integrator 已传 `case_ids`、做 checkpoint roundtrip receipt，但保留 formal training blocked 到 Batch 2。
- Integrator 处理结果: Batch 1 MyoPS mainline non-training authority complete for Batch 2; no training, no Slurm, no performance conclusion.


---

## Change 003: Batch 2A shared production-component closure

- 日期/时间: 2026-07-20
- 执行线程: CARE SRR main integrator, main-only Codex goal
- 只读审计线程: none; integrator self-validated only, no runtime reviewer
- Base commit: `72e4bd0`
- Head commit: final Batch 2A commit SHA is reported in the final integrator response; exact self SHA cannot be embedded before commit without changing that SHA.
- 对应 TODO: Batch 2A / Batch 1 closure before Batch 2B
- 状态: complete pending commit/push

### 1. 本次目标

只执行 Batch 2A：把 Batch 1 中散落在 validator 的 manifest、prototype/memory、checkpoint、known-bad 和 no-T2 safety 逻辑抽成共享生产薄层，让 validator 和 training runner 复用同一套 raw OOF anchor、casewise cross-fit memory、checkpoint schema 和 no-T2 safety 语义。没有训练、没有 Slurm、没有 44 例性能比较、没有 validation upload。

### 2. 修改文件

| 文件 | 动作 | 修改前行为 | 修改后行为 |
| --- | --- | --- | --- |
| `src/care_myocardium/srr_production/anchor_manifest.py` | add | anchor manifest 只在 validator 内部生成；`read_anchored_case` 会静默修改 no-T2 raw anchor | 共享 raw OOF anchor manifest builder、path/hash/geometry 检查和 raw-anchor-preserved safety context helper |
| `src/care_myocardium/srr_production/prototype_memory.py` | add | validator 把合并向量重复写入多个病例；runner 走旧全局 prototype builder | 共享逐病例 `CasePrototypeVectors`、case/shard exclusion 检查、casewise dictionary/memory loader 和 zero-count slot policy |
| `src/care_myocardium/srr_production/checkpoint.py` | add | checkpoint receipt 主要检查字段存在和 tensor roundtrip | 共享 schema v2 save/load，真实恢复新 model、新 optimizer、RNG、best state、prototype/memory provenance |
| `src/care_myocardium/models/srr_dictionary_memory.py` | modify | query 排除当前 shard，但 zero-count slots 仍进入 similarity | query 只使用 `counts > 0` active slots；production ready 缺正/负来源 fail closed |
| `src/care_myocardium/models/srr_propref.py` | modify | production proposal 仍可能混入全局 prototype；no-T2 residual/ROI/probability receipt 不完整 | crossfit-exclusive memory query 不再混入全局 prototype；no-T2 candidate probability、soft ROI、refinement residual、bounded correction exact-zero 可直接检查 |
| `scripts/training/run_srr_propref_myops_fold0.py` | modify | 读取病例时修改 raw anchor；runtime prototype fit 使用旧全局 builder | 保留 raw anchor，采样时派生 safety context；runner prototype/memory fit 调用共享 casewise helper |
| `scripts/srr_production/validate_myops_mainline.py` | modify | Batch 1 逻辑在脚本内重复实现；known-bad 是按名字固定拒绝；checkpoint resume 不完整 | 调用共享 builder/helper；生成 `batch2a_*` receipts；known-bad 构造实际错误对象；checkpoint schema v2 真恢复 |
| `tests/srr_production/test_myops_mainline_batch1.py` | modify | 只检查 Batch 1 receipt 和旧 manifest status | 检查 raw anchor semantics、Batch 2A required receipts、no-T2 exact-zero、checkpoint resume |
| `configs/srr_production/entrypoints.yaml` | modify | 仍描述 Batch 1 后的旧 blocked 状态和分叉缺口 | 记录 Batch 2A shared-component closure，formal training 仍 blocked pending Batch 2B |
| `prompts/routes/handoffs/CURRENT.md` | modify | 机器真值仍要求先做 Batch 2A | 标记 `batch2a_status: BATCH_2A_BATCH1_CLOSURE_COMPLETE`，下一步为 Batch 2B |

### 3. 真实数据流变化

Batch 2A 后的共享路径为：

```text
raw OOF nnU-Net fold validation probability/prediction
-> shared anchor manifest with hashes/geometry/class order
-> raw anchor preserved on case object
-> derived safety context only at patch/inference context stage
-> casewise real feature extraction per source case
-> four-shard M10 memory update with per-case provenance
-> counts>0, non-query-shard memory query
-> proposal/refiner/final bounded correction
-> checkpoint schema v2 save/load with model/optimizer/RNG/provenance state
```

### 4. 删除或关闭的绕过

- raw anchor mutation: no-T2 raw OOF edema channel is no longer changed by `read_anchored_case`.
- prototype self-leakage: production memory query uses non-query shards and crossfit-exclusive proposal similarity instead of global dictionary buffers.
- fake provenance: memory updates now consume each case's own extracted vectors.
- zero-count memory slots: excluded from similarity via `counts > 0` active slot masks.
- no-T2 partial safety: receipt covers candidate probability, soft ROI, residual, correction, loss and gradient.
- fixed-string known-bad: fixtures now inject bad objects and are rejected by validator logic.
- checkpoint field-only receipt: schema v2 restore loads a new optimizer and restores RNG state.

### 5. 运行命令与结果

| 命令 | Exit | 真实输入 | 真实输出 | 验证的事实 |
| --- | ---: | --- | --- | --- |
| `git status --short --branch` | 0 | `/users/a/e/aereinh/CARE` | `## main...origin/main` | 启动时无本地未提交变更 |
| `git fetch origin` | 0 | origin | fetched | 远端可达 |
| `git pull --ff-only` | 0 | origin/main | `Already up to date.` | main 与 origin/main 同步且未丢弃本地变更 |
| `./envs/env_CARE/bin/python -m py_compile ...` | 0 | modified Python files | no syntax errors | 共享模块、runner、validator、model 编译通过 |
| `./envs/env_CARE/bin/python scripts/srr_production/validate_myops_mainline.py --strict` | 0 | real Dataset501, 220 OOF nnU-Net anchors, Batch 1 config | `BATCH_2A_BATCH1_CLOSURE_COMPLETE` and `batch2a_*` receipts | Batch 2A 允许完成状态成立 |
| `./envs/env_CARE/bin/python -m pytest -q tests/srr_production/test_myops_mainline_batch1.py` | 1 then fixed | refreshed raw manifest | failed old manifest status expectation | 测试更新为 raw anchor schema |
| same pytest | 0 | Batch 2A receipts and known-bad fixtures | `5 passed` after test update | Batch 1/2A receipt gates pass |

### 6. 关键数值/形状/哈希

- Raw OOF anchor manifest: `case_count=220`, `unique_cases=220`, `fold_counts={0:44,1:44,2:44,3:44,4:44}`
- Batch 2A validator status: `BATCH_2A_BATCH1_CLOSURE_COMPLETE`
- Smoke source cases: `Case2009`, `Case2001`, `Case2005`, `Case2006`, `Case1001`, `Case5001`
- no-T2 exact-zero receipt: candidate probability `0.0`, soft ROI `0.0`, refinement residual `0.0`, bounded correction `0.0`, loss `0.0`, edema-owned gradient `0.0`
- Checkpoint resume receipt: schema version `2`, optimizer param groups match `true`, RNG next sampling match `true`, global step not reset `true`, epoch not reset `true`

### 7. 人类解释

这次改动解决的是 Batch 1 “validator 能跑但生产 runner 不一定走同一条路”的问题。现在 raw OOF anchor、原型/记忆、case exclusion、no-T2 safety 和 checkpoint schema 都有共享代码路径和轻量证据。它仍不是训练完成，也不是性能结论。

### 8. 未解决项

| 文件/区域 | 未解决项 |
| --- | --- |
| `scripts/srr_production/infer_myops.py` | 尚未创建；Batch 2B 必须建立 full-volume NIfTI inference 并复用 Batch 2A 共享模块 |
| `scripts/srr_production/evaluate_myops_fair.py` | 尚未创建；Batch 2B 必须统一 fold0 baseline reproduction、anchor identity、casewise/subgroup/component/remote-FP 输出 |
| production SRR checkpoint | 当前只有非训练 smoke/resume checkpoint；没有受信任训练后 checkpoint |
| formal training | 仍未授权 |
| performance/leaderboard | 无性能结论、无 hosted metric claim |
| Cine | 本批未修改，旧 B7/B8 仍 forbidden/historical |

### 9. 下一批允许范围

Batch 2B 只允许新增/修复 MyoPS full-volume inference 与 fair evaluation authority：`configs/srr_production/myops_batch2.yaml`、`scripts/srr_production/infer_myops.py`、`scripts/srr_production/evaluate_myops_fair.py`、`tests/srr_production/test_myops_batch2_inference_evaluation.py` 和计划列出的 inference/evaluation receipts。零步 SRR 只能标记为 `UNTRAINED_PIPELINE_DIAGNOSTIC`。

### 10. 审计意见

- 模型审计 GPT：未执行独立线程。
- 数据/评价审计 GPT：未执行独立线程。
- Cine 审计 GPT：未执行；本批不改 Cine。
- 红队 GPT：未执行独立线程；known-bad fixture 已从固定字符串升级为实际错误注入。
- Integrator 处理结果：Batch 2A complete pending commit/push；允许进入 Batch 2B，但仍禁止训练、Slurm、upload 和性能主张。
