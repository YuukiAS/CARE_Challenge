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
