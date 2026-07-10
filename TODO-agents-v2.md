# TODO-agents-v2：CARE 执行控制与架构可观测性重构

status: `AUTHORITATIVE_REFACTOR_PROPOSAL`

本文件用于替代根目录现有 `TODO-agents.md` 作为下一次 Codex 协议维护任务的唯一规划源。旧文件保留为历史讨论记录，但其中关于角色命名、Mermaid 必需渲染、documentation audit、Graphify 和外部绘图工具的零散条目不再作为实现规范。

本次重构同时解决两个问题：

1. 长 Slurm milestone 不能因为 executor 提前退出或错误写成 `blocked` 而浪费整晚时间。
2. 用户、GPT planner 和 Codex 必须能快速看清“当前版本实际实现了什么、代码在哪里、哪些模块只是 scaffold、目标还差什么”，而不需要反复通读大量代码和旧 result packet。

---

## 1. 最终角色命名

新协议只使用下面这些短名称。

| 名称 | 类型 | 职责 | 明确禁止 |
| --- | --- | --- | --- |
| `planner` | GPT/ChatGPT | 制定路线、milestone、证据门槛、执行模式、controller/executor prompt 和 reviewer prompt | 不执行代码，不监控 Slurm，不替代最终 review |
| `controller` | 顶层 Codex goal | 负责一个长任务的执行连续性、subagent 调度、live-state grounding、Slurm 监控和最终收尾 | 不发明新路线，不写 `review.md`，不启动下一 milestone |
| `executor` | controller 内部 subagent，或短任务独立 thread/goal | 修改代码、运行授权命令、提交 Slurm、写初始 evidence | 不拥有 overnight 连续性，不自审，不决定路线晋级 |
| `mapper` | controller 内部只读代码审计与文档 subagent | 把当前代码、配置、运行入口和证据映射成架构说明、组件表和图片 | 不改模型代码，不做科学晋级决定，不写 `review.md` |
| `finalizer` | controller 自身的确定性阶段/脚本，不是 LLM subagent | 等待 terminal job，聚合、验证、更新最终文档、`git diff --check`、commit | 不依赖自然语言判断，不作为 reviewer |
| `validator` | 一方脚本 | 机器检查 packet、状态、文件、wiki/diagram 一致性和 known-bad fixtures | 不由 LLM 手写结论替代 |
| `reviewer` | 独立 Codex thread 或短 reviewer goal | 只读审阅最终 committed packet，写 `review.md`，可按授权 commit，不 push | 不监控、不 resume、不训练、不补 artifact、不改代码 |

### 1.1 不再使用内部 `auditor`

新任务不再让 controller 启动一个名为 `auditor` 的内部 agent。这个词和最终 `reviewer` 的职责重叠，容易再次把执行恢复、文档检查和独立审阅混在一起。

兼容规则：

- 现有 frontmatter 中的 `auditor` 仅作为历史 alias，语义等同于独立 `reviewer`。
- 新 task/frontmatter 统一写 `reviewer`。
- controller 内部需要的代码到架构核对由 `mapper` 完成。
- 机器正确性由 `validator` 完成。

### 1.2 documentation audit 和 finalizer 的正式名称

- 原先讨论的 `documentation audit` 正式命名为 `mapper`。
- 原先讨论的 controller 收尾逻辑正式命名为 `finalizer`。

这两个名称都与 `reviewer` 明确区分：`mapper` 描述和映射当前实现，`finalizer` 完成运行态收尾，`reviewer` 才做独立审阅。

---

## 2. 两种执行模式

### 2.1 短任务

适用条件：无长 Slurm、预计可以在一次交互中完成、没有明显 resume 风险。

```text
planner -> executor -> reviewer
```

- `executor` 可以是独立 thread 或 goal。
- 只有 `architecture_impact != none` 时才必须调用 `mapper`。
- reviewer 默认是普通独立 thread；只有需要自动 commit review 时才使用短 reviewer goal。

### 2.2 长 Slurm / overnight / 多 job 任务

适用条件：任一 required job 可能跨越用户离线时间，或任务需要多次 monitor/resume/final aggregation。

```text
planner -> controller
                 |-> executor
                 |-> mapper (draft)
                 |-> monitor Slurm
                 |-> finalizer
                 |-> mapper (final)
                 |-> commit
            -> separate reviewer
```

用户只启动一个顶层 `controller` goal，不再同时启动一个独立 overnight executor goal。

---

## 3. controller 的完整生命周期

### 3.1 Bootstrap

controller 在每个 major phase 前必须重新从磁盘和 live state grounding，不能依赖上下文压缩或旧摘要。

必读：

- `AGENTS.md`
- `START_HERE_FOR_GPT.md`
- `GPT_PLANNER_CARE_PROTOCOL.md`
- `prompts/HANDOFF_ROLES.md`
- 当前 GPT-authored milestone/task prompt
- `.agents/skills/slurm-routing-partition/SKILL.md`，只要任务涉及 Slurm
- `wiki/README.md`
- `wiki/MODEL.md`
- `wiki/COMPONENTS.csv`
- 当前 result directory 中已有的 `MANIFEST.md`、状态文件和 runtime ledger

必须刷新：

```bash
git status --porcelain=v1 -b
git log --oneline --decorate -5
squeue / sacct for required job ids
required runtime output existence
required tracked evidence existence
```

写入：

```text
results/<task_key>/controller_bootstrap_snapshot.md
```

### 3.2 Executor launch

GPT planner 必须显式写：

```yaml
executor_slots: 1
```

默认只能启动 1 个 executor subagent。只有 GPT task graph 已经把工作拆成互不写同一文件的独立 scope，才允许 `executor_slots > 1`。

controller 不得自行因为“可能更快”增加 subagent 数量。

### 3.3 Implementation freeze

executor 完成代码修改和 job submission 后，必须写出：

```text
results/<task_key>/implementation_snapshot.md
```

至少记录：

- 当前 commit / dirty state；
- 改动文件；
- 关键 class/function；
- Slurm job IDs；
- runtime output paths；
- 尚未完成的运行证据。

此后 mapper 才开始 draft mapping。executor 若继续改模型代码，必须更新 snapshot，mapper draft 作废后重跑。

### 3.4 Mapper draft

Slurm job pending/running 时，mapper 可以利用等待时间完成第一次代码审计，但只写 milestone-local draft：

```text
results/<task_key>/mapper_report_draft.md
results/<task_key>/architecture_delta_draft.md
```

这一阶段不得提前把未验证模块写成 `implemented`。

### 3.5 Monitor

只要 required job 处于以下任一状态，controller 必须继续监控：

```text
PENDING
RUNNING
CONFIGURING
COMPLETING
AWAITING_SACCT
```

对应 milestone 状态只能是 `NEEDS_MONITOR`。这些状态不能被写成 `blocked`、`resource blocked`、`external condition unresolved` 或同义替代。

scheduler block 只允许在 Slurm skill 规定的条件下出现：所有已提交 routing partitions 连续 12 次、每次间隔 2 小时、总计 24 小时都 pending，并且没有任何 job start。

### 3.6 Finalizer stage A

required jobs terminal 后，controller 自己进入 `finalizer`，不得把收尾继续交给已退出的 executor。

顺序：

1. 读取 live `sacct`、exit code、elapsed、node、log path；
2. 检查 runtime outputs；
3. 跑 aggregator/evidence collector；
4. 跑 milestone validator 和 self-tests；
5. 若 outputs 缺失或 aggregation 失败，写 `NEEDS_EVIDENCE`；
6. job failure 写运行失败证据，不得误写 scheduler block。

### 3.7 Mapper final

final runtime evidence 存在后，mapper 再运行一次：

- 核对代码实际路径；
- 核对配置/CLI 是否真正接入；
- 核对模块是否影响最终 logits/labels；
- 更新 current architecture；
- 更新 component statuses；
- 生成 SVG 和 PNG；
- 写 final mapper report。

### 3.8 Finalizer stage B

mapper final 后，controller 再执行：

```bash
validator for result packet
validator for wiki/component/diagram consistency
git diff --check
git add -f <authorized lightweight files>
git commit
```

然后停止，不 push，不写 `review.md`，不启动下一 milestone。

---

## 4. mapper 的固定职责

`mapper` 是代码到架构的映射器，不是泛泛的文档写手。

它必须回答：

1. 当前整体模型是什么；
2. 每个 component 的输入、输出和数据流是什么；
3. 每个 component 由哪个文件、class/function、entrypoint 实现；
4. 配置项和 loss 是否真正接入运行链；
5. 当前状态是 implemented、partial、scaffold、legacy、disabled 还是 unknown；
6. 目标状态是什么；
7. 哪个 runtime evidence 支持这个判断；
8. 本 milestone 相比上一版本改了什么。

### 4.1 Component 状态枚举

```text
implemented
partial
scaffold
legacy
disabled
unknown
```

证据状态另列：

```text
verified
unverified
stale
missing
```

不要把“文件存在”自动等同于 `implemented`。

### 4.2 mapper 必须使用的技能

从 `YuukiAS/AI_Skills_Collection` 精确安装或复制以下 skills 到 CARE repo-local `.agents/skills/`，不要安装整个大 domain：

```text
skills/core/codex-system/codex-workflow-protocol
skills/tools/visualization/markdown-mermaid-writing
skills/science/communication/scientific-visualization
skills/writing/core/chinese-prose
skills/domains/medical-imaging/medical-imaging-deep-learning
```

可选：

```text
skills/science/communication/scientific-schematics
skills/writing/core/scientific-prose
```

用途：

- `codex-workflow-protocol`：source-of-truth、live-state、subagent 验证和报告边界；
- `markdown-mermaid-writing`：文本图、README、状态报告和架构文档标准；
- `scientific-visualization`：状态图、颜色、布局和 publication-friendly 输出；
- `chinese-prose`：中文 wiki/报告终审；
- `medical-imaging-deep-learning`：判断 segmentation、registration、temporal、missing-modality、proposal/refiner 是否是真实实现；
- `scientific-schematics`：只在已配置 API、用户允许且需要 paper-style PNG 时使用；不得作为代码事实源。

### 4.3 新增 project-local mapper skill

维护任务必须创建：

```text
.agents/skills/care-mapper/SKILL.md
```

该 skill 必须固定指向：

- CARE root `wiki/` schema；
- `AI_Research_Toolkit` 的资源索引和本地安装报告；
- 上述 AI Skills Collection skills；
- component status 和证据标准；
- D2/Graphviz/Mermaid 的选择顺序；
- mapper draft/final 输出路径；
- 禁止扫描 raw data、NIfTI、checkpoints、logs、secrets、upload packages。

---

## 5. 画图资源：现有仓库已经足够

不需要再为基本架构图安装新的外部系统。

`YuukiAS/AI_Research_Toolkit` 已经提供并检查：

- D2；
- Graphviz；
- Mermaid CLI；
- PlantUML；
- Typst；
- diagrams.py；
- figures4papers 风格参考；
- Paper2Any 等可选科研图工具索引。

当前本地安装报告显示：D2、Graphviz、PlantUML、Typst 和 diagrams.py 可工作；Mermaid CLI 已安装，但当前节点因 Chromium 权限问题不能稳定渲染。因此不能把 PNG/SVG 生成硬绑在 `mmdc` 上。

### 5.1 资源发现路径

mapper 每次开始前必须读取：

```text
${AI_RESEARCH_TOOLKIT_ROOT}/RESOURCE_INDEX.md
${AI_RESEARCH_TOOLKIT_ROOT}/inventory/resources.yaml
${AI_RESEARCH_TOOLKIT_ROOT}/docs/local_install_report.md
```

推荐环境变量：

```text
AI_RESEARCH_TOOLKIT_ROOT=/overflow/htzhu/mingcheng_new/AI_Research_Toolkit
AI_SKILLS_COLLECTION_ROOT=/overflow/htzhu/mingcheng_new/AI_Skills_Collection
```

这些外部仓库默认只读。所有输出必须写入 CARE repo，不得写回 Toolkit 或 Skills Collection。

### 5.2 渲染顺序

模型架构和状态图：

1. `architecture.yaml` / `COMPONENTS.csv` 是结构化事实源；
2. D2 是首选 render source；
3. D2 输出 SVG 和 PNG；
4. Graphviz 是 fallback；
5. Mermaid 用于 Markdown 内嵌和 execution/state flow 文本表达，但当前节点的 `mmdc` 失败不能阻塞 D2 输出。

论文级精修：

- `figures4papers` 只作为风格参考；
- `scientific-schematics` 可生成补充 PNG，但只能读取脱敏 architecture brief；
- Paper2Any、AutoFigure、LiveFigure 等只能在用户明确批准的独立 figure task 中使用；
- Graphify 只用于 code/docs relationship discovery，不是正式架构图工具，也不是必需依赖。

---

## 6. 根目录 wiki 设计

需要 repo 内知识层，但不使用 GitHub Wiki 作为 canonical source。

现有 `docs/wiki/` 结构较泛，且基本为空。它不应继续扩展成 papers/concepts/entities/comparisons/gaps/synthesis 等多层目录。维护任务应将其迁移并压缩为根目录：

```text
wiki/
  README.md
  MODEL.md
  EXECUTION.md
  COMPONENTS.csv
  LINEAGE.md
  architecture.yaml
  RESEARCH.md              # 可选：合并旧 hypotheses/questions；无实质内容可省略
  figures/
    model-current.d2
    model-current.svg
    model-current.png
    component-status.d2
    component-status.svg
    component-status.png
    execution-flow.d2
    execution-flow.svg
    execution-flow.png
```

不再新增 `docs/architecture/`、`docs/methods/`、`docs/evidence/`、`docs/decisions/` 等目录。现有 `docs/plans/`、`docs/presentation/`、`literature/` 保持原职责。

### 6.1 `wiki/README.md`

这是用户和 GPT 的第一入口，第一屏必须包含：

- 当前 architecture version；
- 对应 git commit；
- 最近 milestone/review 状态；
- 三张直接可看的图片；
- 一张不超过 12 行的 component status 表；
- 链接到详细文件。

嵌入图片：

1. `model-current.png`：当前真实模型数据流；
2. `component-status.png`：当前状态与目标差距；
3. `execution-flow.png`：planner/controller/executor/mapper/finalizer/reviewer + Slurm 流程。

### 6.2 `wiki/MODEL.md`

按 MyoPS、Cine、shared/runtime 三部分写详细说明：

- 输入/输出；
- tensor/data flow；
- component 作用；
- loss/metric/export contract；
- current status；
- target status；
- 主要 evidence path；
- 已知限制。

不要复制整段代码，不要写成论文综述。

### 6.3 `wiki/COMPONENTS.csv`

必需字段：

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
config_keys
inputs
outputs
losses
final_output_effect
runtime_evidence
last_verified_commit
last_verified_milestone
notes
```

函数定位使用 `source_file + symbol + entrypoint + grep key`，不要依赖容易漂移的固定行号。

### 6.4 `wiki/architecture.yaml`

作为 diagram generator 的机器事实源，至少包含：

```yaml
architecture_version:
verified_commit:
verified_milestone:
nodes:
  - id:
    label:
    branch:
    status:
    source_file:
    symbol:
edges:
  - from:
    to:
    kind: data | control | loss | evidence | fallback
    condition:
```

### 6.5 `wiki/LINEAGE.md`

只记录架构级变化，不复制每次训练日志：

- milestone；
- commit；
- architecture delta；
- component status delta；
- review token；
- evidence link。

### 6.6 Wiki 更新门槛

GPT task 必须写：

```yaml
architecture_impact: none | component | system
mapper_required: true | false
wiki_update_required: true | false
diagram_update_required: true | false
```

规则：

- `architecture_impact: none`：mapper 只验证，写 `NO_ARCHITECTURE_CHANGE`，不重绘全部图片；
- `component`：更新 COMPONENTS、MODEL、相关图；
- `system`：更新全部 canonical wiki 文件和 3 张图；
- 纯 metric run 不得无意义重写架构图；
- wiki 中的 `verified_commit` 与当前代码不一致时，GPT/Codex 必须标记 stale，不能把 wiki 当最新事实。

---

## 7. GPT planner 新契约

GPT 在写 milestone 前必须明确这些字段：

```yaml
execution_mode: direct_executor | controller_supervised
requires_execution_controller: true | false
executor_slots: 1
mapper_required: true | false
architecture_impact: none | component | system
wiki_update_required: true | false
diagram_update_required: true | false
slurm_runtime_continuity_required: true | false
review_mode: independent_thread | short_goal
reviewer: separate_readonly
```

判定规则：

- overnight、长 Slurm、多 job、高 resume 风险：必须 `controller_supervised`；
- 模型结构、loss wiring、dataflow、export、registration/temporal 路径变化：必须 `mapper_required: true`；
- GPT 必须同时写 controller/executor contract、mapper contract 和独立 reviewer prompt；
- GPT 不得把 reviewer 写成 controller 的 subagent；
- GPT 不得让 controller 自己选择 executor 数量；
- GPT planning startup 必须先读 root `wiki/README.md`、`MODEL.md`、`COMPONENTS.csv`，再按 touched components 回查代码。

---

## 8. Reviewer 边界

reviewer 只在 controller/executor 已经产生最终 committed packet 后启动。

reviewer 检查：

- result packet；
- validator reports；
- mapper report；
- architecture delta；
- wiki 是否与 commit 对齐；
- 当前主张是否有 runtime evidence。

reviewer 不得：

- resume executor；
- 等待 Slurm；
- 跑训练；
- 更新 wiki；
- 生成缺失图片；
- 修代码；
- 代替 finalizer。

---

## 9. Slurm 与上下文 known-bad fixtures

维护任务必须新增 fail-closed checks：

1. required job 是 `RUNNING`，packet 写 `blocked`；
2. required job 是 `PENDING`，没有 24 小时证据却写 scheduler blocked；
3. job 仍运行、outputs 尚未生成，却因 outputs missing 退出 goal；
4. controller 没有 fresh bootstrap snapshot 就 resume；
5. GPT 写 overnight milestone 但 `execution_mode != controller_supervised`；
6. controller 启动超过 `executor_slots` 的 executor；
7. controller 将 reviewer 当内部恢复 agent；
8. mapper 把 scaffold 标记为 implemented；
9. wiki `verified_commit` 与代码不一致却未标 stale；
10. architecture-changing milestone 缺 COMPONENTS/MODEL/PNG 更新；
11. D2 可用但 mapper 仅因 `mmdc` 失败而不生成图片；
12. mapper 扫描 raw data、NIfTI、checkpoint、logs、secret 或 upload package；
13. controller 写 `review.md` 或 audited-go；
14. finalizer 只提交 monitor packet，未等 terminal/aggregation。

---

## 10. 需要修改或新增的文件

维护任务至少处理：

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
wiki/*                                               # migrate/new
README.md                                             # add current architecture entry link
```

必要时修改 shared executor/reviewer prompts 中仍把 auditor 当 controller child、或允许 standalone overnight executor 的全局段落。不要重写历史 result packets。

---

## 11. 迁移顺序

1. 以本文件作为唯一任务源；
2. 修改角色和执行模式；
3. 创建 `care-mapper` skill；
4. 精确安装/复制 mapper 所需 skills，不安装整个 visualization/research-writing domain；
5. 建立 root `wiki/`；
6. 将 `docs/wiki/` 中有实质内容的 hypotheses/questions 合并到 `wiki/RESEARCH.md`；
7. 删除或保留一个 redirect README 后停止使用 `docs/wiki/`；
8. 从当前 M9/M10 代码和最新 committed evidence 生成第一版 current architecture；
9. 用 D2 生成 SVG 和 PNG；
10. 增加 validators/known-bad fixtures；
11. 更新 GPT startup/read order；
12. `git diff --check`；
13. commit，不 push。

---

## 12. 完成标准

只有全部满足，维护任务才算完成：

- 长 Slurm milestone 必须由 controller goal 承担连续性；
- 默认 1 个 executor subagent，数量由 GPT task 指定；
- controller 内部角色为 executor + mapper，不再使用 auditor；
- finalizer 是 controller 自身阶段/脚本；
- reviewer 独立只读；
- `RUNNING/PENDING` 不能进入 blocked；
- mapper 能从 AI Research Toolkit 找到可用 renderer；
- mapper 明确使用 AI Skills Collection 的 diagram/report/domain skills；
- root `wiki/README.md` 能直接看到 3 张 PNG；
- `wiki/COMPONENTS.csv` 能定位 component 到 source file 和 symbol；
- `wiki/architecture.yaml`、MODEL、COMPONENTS、图片和 git commit 一致；
- GPT planner 启动时必须读 wiki current state；
- Codex 修改架构后必须通过 mapper 更新 wiki；
- reviewer 能审 architecture delta，但不负责生成文档；
- validators 覆盖上述 known-bad cases；
- 只提交轻量代码/协议/wiki/图片，不提交 raw data、NIfTI、checkpoint、大日志或 upload package。

---

## 13. 可直接交给 Codex 的统一 prompt

```text
你是 CARE agent-flow 与 architecture observability 的 Codex maintenance controller。只执行本次协议重构，不训练模型、不提交 Slurm、不打包 validation、不上传、不启动 M10。

唯一规划源是根目录 `TODO-agents-v2.md`。旧 `TODO-agents.md` 仅供历史参考；若两者冲突，以 v2 为准。

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
- current root README and latest 10 commits

同时读取外部只读资源：

- `${AI_RESEARCH_TOOLKIT_ROOT}/README.md`
- `${AI_RESEARCH_TOOLKIT_ROOT}/RESOURCE_INDEX.md`
- `${AI_RESEARCH_TOOLKIT_ROOT}/inventory/resources.yaml`
- `${AI_RESEARCH_TOOLKIT_ROOT}/docs/local_install_report.md`
- `${AI_SKILLS_COLLECTION_ROOT}/README.md`
- 精确 skills：codex-workflow-protocol、markdown-mermaid-writing、scientific-visualization、chinese-prose、medical-imaging-deep-learning；scientific-schematics/scientific-prose 为可选。

按 v2 完成：

1. 重构 planner/controller/executor/mapper/finalizer/validator/reviewer 角色边界；
2. 新任务不再使用内部 auditor；历史 auditor 只作为 reviewer alias；
3. 强制 GPT 选择 direct_executor 或 controller_supervised；
4. 强制 overnight Slurm 使用 controller-supervised；
5. 默认 executor_slots=1，controller 不得自行增加；
6. 实现 fresh disk/live-state bootstrap contract；
7. 实现 Slurm monitor/finalizer contract，RUNNING/PENDING 不得 blocked；
8. 创建 `.agents/skills/care-mapper/SKILL.md`；
9. 精确安装或复制 mapper 所需 skills，遵守当前 /users workspace 的 real-directory/no-overflow-write 规则；
10. 将 `docs/wiki/` 迁移并压缩为根目录 `wiki/`，不要创建繁杂子目录；
11. 创建 README、MODEL、EXECUTION、COMPONENTS.csv、LINEAGE、architecture.yaml 和 figures/；
12. 从当前一方代码和最新 committed evidence 生成真实 current architecture；
13. 用 D2 作为首选 renderer，生成三套 `.d2 + .svg + .png`；Graphviz fallback；不要让 mmdc/Chromium 问题阻塞图片；
14. 更新 root README，链接 `wiki/README.md`；
15. 增加 validator/known-bad fixtures；
16. 搜索并修复 active prompts 中 reviewer-supervised execution、standalone overnight executor、controller child auditor 等冲突措辞；
17. 不修改历史 result packets；
18. 运行所有轻量验证和 `git diff --check`；
19. commit，不 push。

mapper 生成的模型图必须区分 MyoPS 与 Cine，并标记 implemented/partial/scaffold/legacy/disabled/unknown。COMPONENTS.csv 必须包含 source_file、symbol、entrypoint、config_keys、inputs、outputs、losses、final_output_effect、runtime_evidence、last_verified_commit 和 last_verified_milestone。

最终回复只需要说明：修改了哪些 active protocol、创建了哪些 wiki/skill/diagram、验证结果、commit SHA、未 push。
```
