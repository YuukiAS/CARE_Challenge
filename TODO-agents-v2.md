# TODO-agents-v2：CARE 执行控制与架构可观测性重构

status: `AUTHORITATIVE_REFACTOR_PROPOSAL`

本文件替代根目录 `TODO-agents.md`，作为下一次 Codex 协议维护任务的唯一规划源。旧文件仅保留为历史讨论记录；若两者冲突，以本文件为准。

本次重构同时解决两类问题：

1. 长 Slurm milestone 不能因为 executor/controller 提前退出或把正常 `PENDING/RUNNING` 错写成 `blocked` 而浪费整晚时间。
2. 用户、GPT planner 和 Codex 必须能快速看清当前版本真实实现、目标差距、代码位置和证据状态，而不需要反复通读大量代码与旧 result packet。

---

## 0. 当前远端证据边界

截至本文件更新时，GitHub 远端可验证的 M9 状态是：

- M9 runtime jobs 已 terminal，三条 formal SRR-main candidate 均完成超过 7200 秒的训练；
- 三条 candidate 均低于 tracked M8 nnU-Net anchor，因此 executor 的科学方向是 `M9_NO_PROMOTION_DIAGNOSTIC_ONLY`；
- 远端 `review.md` 仍是 `M9_AUDITED_NEEDS_REVISION`，blocker 是 stale pending/runtime 状态与 validator 未扫描 required CSV/JSON，不是 scheduler 仍在运行；
- 远端存在 M9 follow-up reconciliation/re-audit prompt，但当前没有可验证的 `m9_followup_reconciliation_report.md`、follow-up commit 或新的 follow-up review token。

因此任何 planner/controller/mapper 都必须遵守：

```text
chat/user statement that a run finished != committed audited evidence
```

初次建立 wiki 时，必须重新读取最新 committed result/review；若 follow-up 文件届时已经提交，则使用其精确 token；否则明确标记 `M9_FOLLOWUP_REMOTE_EVIDENCE_NOT_FOUND`，不得从聊天推断 audited state。

---

## 1. 最终角色命名

只使用下面这些短名称。

| 名称 | 类型 | 核心职责 | 明确禁止 |
| --- | --- | --- | --- |
| `planner` | GPT/ChatGPT | 制定路线、milestone、证据门槛、执行模式、subagent 数量、controller/executor/mapper/reviewer prompt | 不执行代码，不监控 Slurm，不替代 reviewer |
| `controller` | 顶层 Codex goal | 承担一个长任务的运行连续性、subagent 调度、全局 grounding、Slurm continuity 和最终收尾 | 不发明新路线，不写 `review.md`，不启动下一 milestone |
| `executor` | controller 内部 subagent；短任务时可独立 thread/goal | 修改代码、运行授权命令、提交 jobs、写初始 evidence | 不拥有 overnight 连续性，不自审，不决定路线晋级 |
| `mapper` | controller 内部只读 subagent | 从代码、配置、入口与 runtime evidence 映射当前架构，更新组件表、说明和图片 | 不改模型代码，不写 `review.md`，不做科学晋级判断 |
| `finalizer` | controller 管理的确定性脚本/阶段，不是 LLM subagent | durable monitoring、terminal accounting、aggregation、validation、wiki finalization、commit | 不以自然语言自行解释状态，不替代 reviewer |
| `validator` | first-party 脚本 | 机器检查 packet、状态机、wiki、diagram、fingerprint 和 known-bad fixtures | 不接受 LLM 手写结论替代 |
| `reviewer` | 独立 Codex thread 或短 reviewer goal | 只读审阅最终 committed packet，写 `review.md`，按授权 commit，不 push | 不监控、不 resume、不训练、不补 artifact、不改代码 |

### 1.1 不再使用内部 `auditor`

`auditor` 和最终 `reviewer` 语义过近，容易混淆独立审阅与执行期检查。

新协议中：

- controller 内部只读核对角色统一叫 `mapper`；
- 机器核对由 `validator` 完成；
- 最终独立审阅统一叫 `reviewer`；
- 历史 frontmatter 中的 `auditor` 仅作为 `reviewer` 的 legacy alias，不再用于新 task。

### 1.2 名称解释

- `mapper`：把 code/config/runtime 映射成 architecture/component documentation，同时做只读一致性检查。
- `finalizer`：完成运行态收尾；它是脚本/阶段，不是另一个会遗忘规则的 agent。
- `reviewer`：最终独立审阅者，和执行链完全分离。

---

## 2. 两种执行模式

### 2.1 短任务

适用：无长 Slurm、预计一次交互完成、没有明显 resume 风险。

```text
planner -> executor -> reviewer
```

- `executor` 可用独立 thread 或 goal。
- `architecture_impact: none` 时不强制 mapper 更新，只需验证 wiki 未 stale。
- reviewer 默认普通独立 thread；需要自动 commit review 时才用短 reviewer goal。

### 2.2 长 Slurm / overnight / 多 job 任务

适用：任一 required job 可能跨越用户离线时间，或任务需要多次 monitor/resume/final aggregation。

```text
planner -> controller
                 |-> executor
                 |-> mapper (draft)
                 |-> durable watcher/finalizer
                 |-> mapper (final)
                 |-> validator + commit
            -> separate reviewer
```

用户只启动一个顶层 `controller` goal，不同时启动独立 overnight executor goal。

默认：

```yaml
executor_slots: 1
mapper_slots: 1
```

controller 不得自行增加 executor 或 mapper 数量。只有 GPT-authored task graph 已明确拆成互不写同一文件、互不共享 runtime output 的 scope，才允许 `executor_slots > 1`。

---

## 3. controller 的全局意识与生命周期

### 3.1 每个 major phase 都重新 grounding

controller 不得把上下文压缩、旧摘要或 executor 自述当事实源。以下 phase 开始前都要重新读取磁盘与 live state：

```text
BOOTSTRAP
PRE_SUBMISSION
MONITOR_RESUME
FINALIZE_A
MAPPER_FINAL
FINALIZE_B
```

必读：

- `AGENTS.md`
- `START_HERE_FOR_GPT.md`
- `GPT_PLANNER_CARE_PROTOCOL.md`
- `prompts/HANDOFF_ROLES.md`
- `prompts/HANDOFF_STATE_MACHINE.md`
- `prompts/CONTROLLER_TASK_PROTOCOL.md`
- 当前 GPT-authored task/milestone prompt
- `.agents/skills/slurm-routing-partition/SKILL.md`，只要涉及 Slurm
- `.agents/skills/care-mapper/SKILL.md`，只要 mapper 启用
- `wiki/README.md`
- `wiki/MODEL.md`
- `wiki/COMPONENTS.csv`
- 当前 result directory 的 `MANIFEST.md`、状态文件、job ledger 与已有 evidence

必须刷新：

```bash
git rev-parse --show-toplevel
git status --porcelain=v1 -b
git log --oneline --decorate -5
squeue/sacct for every required job id
required runtime-output existence
required tracked-evidence existence
```

必须写：

```text
results/<task_key>/controller_context.json
results/<task_key>/controller_ledger.csv
results/<task_key>/controller_bootstrap_snapshot.md
```

`controller_context.json` 至少包含：

```json
{
  "phase": "BOOTSTRAP",
  "git_head": "...",
  "git_status": "...",
  "task_prompt_path": "...",
  "task_prompt_sha256": "...",
  "agents_path": "AGENTS.md",
  "agents_sha256": "...",
  "slurm_skill_sha256": "...",
  "wiki_code_fingerprint": "...",
  "required_job_ids": [],
  "required_runtime_paths": [],
  "files_read": []
}
```

`controller_ledger.csv` append-only，至少包含：

```text
timestamp_utc,phase,git_head,agents_sha256,task_sha256,job_states,decision,next_action
```

validator 必须拒绝缺少 fresh context receipt 的 resume/finalize。

### 3.2 Implementation freeze

executor 完成代码修改与 job submission 后写：

```text
results/<task_key>/implementation_snapshot.md
```

至少记录：

- 当前 HEAD/dirty state；
- 改动文件；
- 关键 class/function/entrypoint；
- 配置和 CLI keys；
- job IDs；
- runtime output paths；
- 仍缺的 runtime evidence。

mapper draft 只能在 snapshot 后运行。executor 若继续修改模型代码，旧 mapper draft 自动 stale，必须重跑。

### 3.3 Mapper draft

job pending/running 时，mapper 利用等待时间做第一次只读映射：

```text
results/<task_key>/mapper_report_draft.md
results/<task_key>/architecture_delta_draft.md
```

未有 runtime proof 的模块不得提前写成 `implemented + verified`。

### 3.4 Monitor 与 durable continuity

仅让 LLM controller 在前台循环等待不够可靠。所有 overnight 任务必须设置 durable continuity backend：

```yaml
slurm_runtime_continuity_required: true
continuity_backend: slurm_dependency | tmux_watcher
finalizer_lock_path: results/<task_key>/.finalizer.lock
```

优先级：

1. Slurm `afterany` dependency finalizer；
2. namespace-local tmux watcher；
3. 仅短任务允许 foreground monitor。

controller 在提交训练 jobs 后，必须立即记录 watcher/finalizer job ID、命令、日志和锁路径。即使 Codex goal/session 意外终止，durable backend 也必须继续等待 terminal state 并生成可 resume 的 machine-readable state。

允许的正常 monitor states：

```text
PENDING
RUNNING
CONFIGURING
COMPLETING
AWAITING_SACCT
```

这些状态只能映射到 `NEEDS_MONITOR`，不得写成 `blocked`、`resource blocked`、`external condition unresolved` 或同义替代。

scheduler block 仅在 Slurm skill 的严格门槛成立时允许：所有已提交 routing partitions 连续 12 次、每次间隔 2 小时、总计 24 小时均 pending，且没有任何 job start。

### 3.5 Finalizer stage A

required jobs terminal 后，deterministic finalizer 依次执行：

1. 读取 live `sacct`、state、exit code、elapsed、node、log path；
2. 检查 runtime outputs；
3. 跑 aggregator/evidence collector；
4. 跑 milestone validator 与 self-tests；
5. terminal 但 outputs 缺失或 aggregation 失败：写 `NEEDS_EVIDENCE`；
6. job failure：写运行失败证据，不得误写 scheduler block；
7. 写 `finalizer_state.json`，供 controller resume。

finalizer 使用锁避免与人工 resume 并发写同一 packet。

### 3.6 Mapper final

final runtime evidence 可用后，mapper 再运行一次：

- 核对代码路径和 symbols；
- 核对 config/CLI/loss 是否真实接入；
- 核对 component 是否影响 final logits/labels/export；
- 更新 component current/target/evidence status；
- 更新 canonical wiki；
- 用 D2 生成 SVG/PNG；
- 写 final mapper report 与 architecture delta。

### 3.7 Finalizer stage B

mapper final 后：

```bash
result-packet validator
wiki/component/diagram consistency validator
git diff --check
git add -f <authorized lightweight files>
git commit
```

然后停止，不 push，不写 `review.md`，不启动下一 milestone。

---

## 4. mapper 的固定职责

mapper 必须回答：

1. 当前整体模型真实数据流是什么；
2. 每个 component 的输入、输出、条件和 final-output effect 是什么；
3. 由哪个 source file、symbol、entrypoint 实现；
4. config/CLI/loss 是否真实接入；
5. 当前状态和目标状态分别是什么；
6. 哪个 runtime evidence 支持该判断；
7. 相比上一 architecture version 改了什么；
8. 哪些内容只是 scaffold、legacy、disabled 或未知。

### 4.1 状态枚举

实现状态：

```text
implemented
partial
scaffold
legacy
disabled
unknown
```

证据状态：

```text
verified
unverified
stale
missing
```

“文件存在”不等于 `implemented`；“输出 tensor 存在”也不等于对 final label 有真实贡献。

### 4.2 mapper 使用 AI Skills Collection

当前 Skills Collection 已提供 `codex-scientific-diagrams` profile，包含 D2、Draw.io、PlantUML、Excalidraw、Mermaid writing、scientific visualization、scientific schematics 和 paper workflow。CARE 不需要安装整个大 domain，也不应盲目启用需要 API 的 skill。

本次维护应以 `--mode copy` 精确复制以下 repo-local real directories，遵守当前 `/users` workspace 的 no-symlink-to-overflow 规则：

必需：

```text
skills/core/codex-system/codex-workflow-protocol
skills/tools/visualization/d2-diagrams
skills/tools/visualization/drawio-diagrams
skills/tools/visualization/plantuml-diagrams
skills/tools/visualization/markdown-mermaid-writing
skills/science/communication/scientific-visualization
skills/writing/core/chinese-prose
skills/domains/medical-imaging/medical-imaging-deep-learning
```

可选：

```text
skills/writing/core/scientific-prose
skills/science/communication/scientific-schematics
```

`scientific-schematics` 需要 network/API key，只能在用户明确批准的独立 paper-figure task 中使用，不能作为 architecture truth source 或 milestone completion gate。

### 4.3 新增 CARE mapper skill

必须创建：

```text
.agents/skills/care-mapper/SKILL.md
```

该 skill 固定定义：

- root `wiki/` schema；
- component 状态与证据规则；
- source file/symbol/entrypoint 定位方法；
- AI Research Toolkit 发现与 health-check 命令；
- D2/Graphviz/PlantUML/Draw.io/Mermaid 的使用边界；
- mapper draft/final 输出路径；
- code fingerprint 规则；
- 禁止扫描 raw data、NIfTI、checkpoints、大日志、secrets、submission/upload packages。

---

## 5. 画图与报告资源

### 5.1 AI Research Toolkit 是工具事实源

当前 Toolkit 已明确：服务器无法稳定启动 Chromium headless，因此 Mermaid CLI 已从正式资源中移除。可靠 core renderer 是：

- D2：模型架构、method pipeline、系统关系图；
- Graphviz：依赖图、DAG、状态关系；
- PlantUML：sequence/state/component/UML；
- Typst：说明页、公式、图注与 PDF 排版；
- diagrams.py：可选 Python 组件图；
- Draw.io：可选 editable `.drawio`，当前 headless 支持需先验证；
- figures4papers：风格参考，不是执行工具；
- Paper2Any / academic-figure-generator / AutoFigure：独立用户批准的 paper-figure 工具，不进入默认 controller gate。

mapper 不得依赖已从 Toolkit HEAD 删除的 `docs/local_install_report.md`。每次必须从 current checkout 运行：

```bash
${AI_RESEARCH_TOOLKIT_ROOT}/bin/ai-research-toolkit validate
${AI_RESEARCH_TOOLKIT_ROOT}/bin/ai-research-toolkit doctor --json
${AI_RESEARCH_TOOLKIT_ROOT}/bin/ai-research-toolkit status
${AI_RESEARCH_TOOLKIT_ROOT}/bin/ai-research-toolkit smoke
```

并读取：

```text
${AI_RESEARCH_TOOLKIT_ROOT}/README.md
${AI_RESEARCH_TOOLKIT_ROOT}/RESOURCE_INDEX.md
${AI_RESEARCH_TOOLKIT_ROOT}/inventory/resources.yaml
```

外部 Toolkit/Skills repos 只读，输出全部写入 CARE repo。

推荐环境变量：

```text
AI_RESEARCH_TOOLKIT_ROOT=/overflow/htzhu/mingcheng_new/AI_Research_Toolkit
AI_SKILLS_COLLECTION_ROOT=/overflow/htzhu/mingcheng_new/AI_Skills_Collection
```

路径必须由 controller live-check，不得仅凭该默认值假设存在。

### 5.2 canonical 渲染顺序

```text
architecture.yaml + COMPONENTS.csv
        -> D2 source
        -> SVG + PNG
        -> Graphviz fallback
```

- D2 是默认 renderer，`.d2` 是图的可版本化源文件。
- 每张 canonical 图必须有 `.d2 + .svg + .png`。
- Graphviz 是 D2 不可用时的 fallback。
- PlantUML 主要用于 execution sequence/state 图。
- Mermaid 只用于 Markdown 内嵌文本表达；`mmdc`/Chromium 失败不得阻塞图片生成。
- Draw.io 只在需要人工编辑或论文精修时输出 `.drawio + SVG/PDF`，不是日常硬门槛。
- Graphify 仅用于 code/docs relationship discovery，不是正式架构图工具，也不是必需依赖。

### 5.3 图片视觉规范

三张 canonical 图必须丰富但不繁杂：

- 最大主层级不超过 7 个 stage；
- component 详细信息放在 `COMPONENTS.csv`/`MODEL.md`，不塞进节点；
- `implemented` 用实线，`partial/scaffold` 用虚线，`legacy/disabled` 用灰色；
- 图中必须有 legend、architecture version、verified milestone 和 code fingerprint short form；
- 颜色只编码 branch/status，不把美观当事实证据；
- PNG 供用户快速查看，SVG/D2 供 Codex 与后续编辑。

---

## 6. 根目录 wiki：最小、版本化、可验证

需要知识层，但不使用 GitHub Wiki 作为 canonical source。GitHub Wiki 与主 repo history/PR/validator 分离，容易过期。

将现有泛化且基本空的 `docs/wiki/` 迁移并压缩为：

```text
wiki/
  README.md
  MODEL.md
  EXECUTION.md
  COMPONENTS.csv
  LINEAGE.md
  architecture.yaml
  figures/
    model-current.d2
    model-current.svg
    model-current.png
    model-gap.d2
    model-gap.svg
    model-gap.png
    execution-flow.d2
    execution-flow.svg
    execution-flow.png
```

不新增 `docs/architecture/`、`docs/methods/`、`docs/evidence/`、`docs/decisions/` 或每个 component 一个 Markdown 的繁杂树。`docs/plans/`、`docs/presentation/`、`literature/` 保持原职责。

旧 `docs/wiki/` 若有实质研究问题/假设，可合并成单个可选 `wiki/RESEARCH.md`；否则仅保留 redirect README 或删除空模板。

### 6.1 `wiki/README.md`

用户和 GPT 的第一入口。第一屏必须包含：

- architecture version；
- latest verified milestone/review token；
- code fingerprint；
- 三张直接可看的 PNG；
- 不超过 12 行的 component summary；
- 链接到 MODEL、EXECUTION、COMPONENTS、LINEAGE。

三张图：

1. `model-current.png`：当前真实模型数据流；
2. `model-gap.png`：current 与 target 的状态差距；
3. `execution-flow.png`：planner/controller/executor/mapper/finalizer/reviewer + Slurm continuity。

### 6.2 `wiki/MODEL.md`

按 MyoPS、Cine、shared/runtime 三部分写：

- 输入/输出和 tensor/data flow；
- component 作用；
- loss/metric/export contract；
- current status；
- target status；
- final-output effect；
- evidence paths；
- 已知限制。

不复制大段代码，不写成论文综述。

### 6.3 `wiki/COMPONENTS.csv`

字段：

```text
component_id
branch
role
current_status
evidence_status
target_status
source_file
symbol
entrypoint
grep_key
config_keys
inputs
outputs
losses
final_output_effect
runtime_evidence
code_fingerprint_member
last_verified_milestone
review_token
notes
```

函数定位使用 `source_file + symbol + entrypoint + grep_key`，不依赖易漂移的固定行号。

### 6.4 `wiki/architecture.yaml`

作为 diagram generator 的机器事实源：

```yaml
architecture_version:
verified_at_utc:
verified_milestone:
review_token:
verification_base_commit:
code_fingerprint:
evidence_fingerprint:
nodes:
  - id:
    label:
    branch:
    current_status:
    target_status:
    source_file:
    symbol:
edges:
  - from:
    to:
    kind: data | control | loss | evidence | fallback
    condition:
```

不要要求 wiki 文件内部写“包含它自己的最终 commit SHA”，这会产生自引用。使用声明过的 source/config 路径生成稳定 `code_fingerprint`；最终 commit SHA 记录在 controller report 和 `LINEAGE.md` 的后续发布记录中。

### 6.5 `wiki/LINEAGE.md`

只记录架构级变化：

- milestone；
- published commit；
- architecture version；
- code fingerprint；
- architecture delta；
- component status delta；
- review token；
- evidence link。

### 6.6 wiki 更新门槛

GPT task 必须写：

```yaml
architecture_impact: none | component | system
mapper_required: true | false
wiki_update_required: true | false
diagram_update_required: true | false
```

规则：

- `none`：mapper 只验证 fingerprint，写 `NO_ARCHITECTURE_CHANGE`，不重绘；
- `component`：更新 COMPONENTS、MODEL 和相关图；
- `system`：更新全部 canonical wiki 和三张图；
- 纯 metric run 不得无意义重写图片；
- fingerprint 不匹配时 wiki 自动 `stale`，GPT/Codex 不得把它当最新事实。

---

## 7. GPT planner 新契约

每个 milestone 必须显式写：

```yaml
execution_mode: direct_executor | controller_supervised
requires_execution_controller: true | false
executor_slots: 1
mapper_slots: 1
mapper_required: true | false
architecture_impact: none | component | system
wiki_update_required: true | false
diagram_update_required: true | false
slurm_runtime_continuity_required: true | false
continuity_backend: none | slurm_dependency | tmux_watcher
review_mode: independent_thread | short_goal
reviewer: separate_readonly
```

判定：

- overnight、长 Slurm、多 job、高 resume 风险：必须 `controller_supervised`；
- overnight 时 `continuity_backend` 不得为 `none`；
- 模型结构、loss wiring、dataflow、export、registration/temporal 路径变化：必须启用 mapper；
- GPT 同时写 controller/executor contract、mapper contract 和独立 reviewer prompt；
- GPT 不得把 reviewer 写成 controller subagent；
- GPT 不得让 controller 自行选择 subagent 数量；
- GPT planning startup 先读 root wiki current state，再按 touched components 回查 code/evidence；
- 若 wiki stale，先标记 stale 并以代码/live evidence 为准。

---

## 8. reviewer 边界

reviewer 只在 controller/executor 产生最终 committed packet 后启动。

reviewer 检查：

- result packet；
- validator/self-test reports；
- mapper report 与 architecture delta；
- wiki fingerprint/figures 是否与 declared code scope 对齐；
- 当前主张是否有 runtime evidence。

reviewer 不得：

- resume executor/controller；
- 等待 Slurm；
- 跑训练；
- 更新 wiki；
- 生成缺失图片；
- 修代码；
- 代替 finalizer。

---

## 9. known-bad fixtures

维护任务必须新增 fail-closed checks：

1. required job `RUNNING`，packet 写 `blocked`；
2. required job `PENDING`，未满足 24 小时阈值却写 scheduler blocked；
3. job 仍运行、outputs 尚未生成，却因 outputs missing 退出 goal；
4. overnight task 没有 durable continuity backend；
5. controller 没有 fresh context receipt 就 resume/finalize；
6. GPT overnight milestone 使用 `direct_executor`；
7. controller 超过 GPT 指定的 executor/mapper slots；
8. controller 将 reviewer 当内部恢复 agent；
9. mapper 把 scaffold 标记为 implemented；
10. wiki fingerprint 不匹配却未标 stale；
11. architecture-changing milestone 缺 COMPONENTS/MODEL/PNG 更新；
12. D2 可用但仅因 Mermaid/Chromium 失败而不生成图片；
13. mapper 扫描 raw data、NIfTI、checkpoint、大日志、secret 或 upload package；
14. controller 写 `review.md` 或 audited-go；
15. finalizer 只提交 monitor packet，未等 terminal/aggregation；
16. planner/mapper 从聊天声称 follow-up 完成，却找不到 committed follow-up evidence/review；
17. wiki 依赖 Toolkit 中已删除或不存在的 install-report 文件；
18. component `final_output_effect` 无 evidence，却标记 verified。

---

## 10. 需要修改或新增的 active files

至少处理：

```text
AGENTS.md
START_HERE_FOR_GPT.md
GPT_PLANNER_CARE_PROTOCOL.md
prompts/CHATGPT_RULES.md
prompts/HANDOFF_ROLES.md
prompts/HANDOFF_STATE_MACHINE.md
prompts/CONTROLLER_TASK_PROTOCOL.md
prompts/GPT_HARD_GATE_PROMPT.md
prompts/templates/CONTROLLER_TASK_TEMPLATE.md
.agents/skills/agent-task-executor/SKILL.md
.agents/skills/slurm-routing-partition/SKILL.md
.agents/skills/care-mapper/SKILL.md                  # new
scripts/architecture/*                               # small first-party generator/validator helpers
wiki/*                                               # migrate/new
README.md                                             # link current architecture entry
```

必要时修改 active shared executor/reviewer prompts 中仍把 auditor 当 controller child、允许 standalone overnight executor、或让 reviewer 补执行缺口的全局段落。不要重写历史 result packets。

---

## 11. 迁移顺序

1. 以本文件为唯一任务源；
2. 重构角色和执行模式；
3. 增加 context receipt、durable watcher/finalizer contract；
4. 创建 `care-mapper` skill；
5. 精确复制 mapper 所需 skills；
6. 建立 root `wiki/`；
7. 迁移/压缩旧 `docs/wiki/`；
8. 从当前 committed code、result、review 生成第一版 current architecture；
9. 远端 follow-up evidence 不存在时明确标记，不推断；
10. 用 D2 生成三套 `.d2 + .svg + .png`；
11. 增加 architecture/wiki/fingerprint validators 与 known-bad fixtures；
12. 更新 GPT startup/read order；
13. 搜索 active prompts 的冲突措辞；
14. 跑轻量 tests 与 `git diff --check`；
15. commit，不 push。

---

## 12. 完成标准

全部满足才算完成：

- 长 Slurm milestone 由 controller goal 承担连续性；
- overnight task 有 durable watcher/finalizer，不依赖 LLM 持续在线；
- 默认 1 executor + 1 mapper，数量由 GPT task 指定；
- controller 内部不再使用 auditor；
- finalizer 是确定性阶段/脚本；
- reviewer 独立只读；
- `RUNNING/PENDING` 不能进入 blocked；
- controller 每个 major phase 有可验证 context receipt；
- mapper 能从 current Toolkit 发现并验证 renderer；
- mapper 使用 D2/Draw.io/report/domain skills；
- root `wiki/README.md` 直接显示三张 PNG；
- `COMPONENTS.csv` 能定位 component 到 source file 与 symbol；
- current/target/evidence 状态清楚；
- `architecture.yaml`、COMPONENTS、MODEL 和图片的 IDs/fingerprint 一致；
- GPT planner 启动时读取 wiki current state；
- architecture-changing task 结束前 mapper 更新 wiki；
- reviewer 审 architecture delta，但不生成文档；
- validator 覆盖全部 known-bad；
- 只提交轻量 code/protocol/wiki/figures，不提交 raw data、NIfTI、checkpoint、大日志或 upload package。

---

## 13. 可直接交给 Codex 的统一 prompt

```text
你是 CARE agent-flow 与 architecture observability 的 Codex maintenance controller。只执行协议重构，不训练模型、不提交新的训练 Slurm job、不打包 validation、不上传、不启动 M10。

唯一规划源是根目录 `TODO-agents-v2.md`。旧 `TODO-agents.md` 仅供历史参考；若冲突，以 v2 为准。

开始前读取：

- `AGENTS.md`
- `TODO-agents-v2.md`
- `START_HERE_FOR_GPT.md`
- `GPT_PLANNER_CARE_PROTOCOL.md`
- `prompts/CHATGPT_RULES.md`
- `prompts/HANDOFF_ROLES.md`
- `prompts/HANDOFF_STATE_MACHINE.md`
- `prompts/CONTROLLER_TASK_PROTOCOL.md`
- `prompts/GPT_HARD_GATE_PROMPT.md`
- `prompts/templates/CONTROLLER_TASK_TEMPLATE.md`
- `.agents/skills/agent-task-executor/SKILL.md`
- `.agents/skills/slurm-routing-partition/SKILL.md`
- current `docs/wiki/`
- root README and latest 10 commits
- latest committed M9 result/review and any committed M9 follow-up files

同时只读检查：

- `${AI_RESEARCH_TOOLKIT_ROOT}/README.md`
- `${AI_RESEARCH_TOOLKIT_ROOT}/RESOURCE_INDEX.md`
- `${AI_RESEARCH_TOOLKIT_ROOT}/inventory/resources.yaml`
- `${AI_SKILLS_COLLECTION_ROOT}/README.md`
- `${AI_SKILLS_COLLECTION_ROOT}/profiles/codex-scientific-diagrams.json`
- required source skills listed in v2

不要依赖已从 Toolkit HEAD 删除的 `docs/local_install_report.md`。运行 Toolkit `validate`、`doctor --json`、`status`、`smoke` 获取当前机器事实。

按 v2 完成：

1. 重构 planner/controller/executor/mapper/finalizer/validator/reviewer 边界；
2. 新任务不再使用内部 auditor；历史 auditor 仅作 reviewer alias；
3. 强制 GPT 选择 direct_executor 或 controller_supervised；
4. overnight Slurm 强制 controller-supervised + durable continuity backend；
5. 默认 executor_slots=1、mapper_slots=1，controller 不得自行增加；
6. 实现 phase-based disk/live-state context receipt；
7. 实现 Slurm monitor/finalizer contract，RUNNING/PENDING 不得 blocked；
8. 创建 `.agents/skills/care-mapper/SKILL.md`；
9. 以 `--mode copy` 精确复制 v2 指定 skills，遵守 /users real-directory/no-overflow-write 规则；
10. 将 `docs/wiki/` 迁移压缩为 root `wiki/`，不要创建繁杂目录；
11. 创建 README、MODEL、EXECUTION、COMPONENTS.csv、LINEAGE、architecture.yaml 和 figures/；
12. 从 current committed first-party code/evidence 生成真实 current architecture；
13. 如 GitHub 仍无 M9 follow-up final evidence/review，明确标记 remote evidence missing，不从聊天推断；
14. 用 D2 生成三套 `.d2 + .svg + .png`；Graphviz fallback；不要让 Mermaid/Chromium 问题阻塞图片；
15. 使用 code fingerprint，避免在 wiki 内写自引用 commit SHA；
16. 更新 root README，链接 `wiki/README.md`；
17. 增加 validators/known-bad fixtures；
18. 搜索并修复 active prompts 中 reviewer-supervised execution、standalone overnight executor、controller child auditor 等冲突措辞；
19. 不修改历史 result packets；
20. 运行轻量验证与 `git diff --check`；
21. commit，不 push。

mapper 的模型图必须区分 MyoPS 与 Cine，并用统一视觉语义标记 implemented/partial/scaffold/legacy/disabled/unknown。COMPONENTS.csv 必须包含 source_file、symbol、entrypoint、grep_key、config_keys、inputs、outputs、losses、final_output_effect、runtime_evidence、code_fingerprint_member、last_verified_milestone 和 review_token。

最终回复只说明：修改了哪些 active protocol、创建了哪些 wiki/skill/diagram、验证结果、commit SHA、未 push。
```
