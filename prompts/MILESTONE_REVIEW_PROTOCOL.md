# Milestone Review Protocol

本协议只适用于显式设置：

```yaml
review_required: true
```

的 CARE milestone 或特殊发布审查。默认新 Batch 使用 Controller/Coordinator 执行验收并返回 Planner，不需要 independent reviewer，也不需要 `review.md`。

## 一、默认流程不使用本协议

默认 Sprint Flow：

```text
Planner
-> Controller/Coordinator
   -> Executor
   -> optional Mapper
   -> deterministic Finalizer/Validator
   -> Controller verification and same-scope repair loop
   -> local lightweight result commit
-> Planner
```

默认字段：

```yaml
review_required: false
review_mode: none
reviewer: none
```

此时：

- Executor 不能宣布整个任务完成；
- Controller 必须检查实际 diff、tests、Slurm、aggregation、required outputs 和 contract compliance；
- Controller 以 `VERIFIED_COMPLETE | NEEDS_REPAIR | OPERATIONALLY_BLOCKED` 结束；
- 缺少 `review.md` 不阻塞 Planner 读取结果或制定下一任务；
- Controller 不得自授下一 Batch、route promotion、validation upload、hosted claim、fold expansion 或 final scientific decision。

## 二、何时显式启用 Reviewer

只有用户或 Planner 明确认为以下场景需要额外独立只读审查时，才设置 `review_required: true`：

- validation packaging/upload 前；
- Docker/最终 submission release 前；
- hosted metric 或 leaderboard claim 前；
- route promotion 或 scientific stop 前；
- 论文最终结果表、正式消融结论或外部发布前；
- 用户明确要求独立 reviewer；
- 需要保留历史 milestone chain 的受控 review token。

高风险、Slurm、system-impact 或 scientific milestone 本身不自动触发 reviewer。

## 三、显式 Reviewer 合同

启用时必须声明：

```yaml
review_required: true
review_mode: independent_thread | short_goal
reviewer: separate_readonly
review_path: results/<task_key>/review.md
review_token: <controlled token>
```

任务正文才需要：

```text
## Reviewer Prompt
```

Reviewer 必须在 Controller 已完成本地轻量 packet commit 后启动，并固定到被审查 commit/checkpoint/case/decode/metric hashes。

## 四、角色边界

### Controller/Coordinator

即使启用 reviewer，Controller 仍是执行验收者。它必须：

- 监督 Executor；
- 检查真实 diff 和命令；
- 完成 terminal job accounting；
- 运行 aggregation 和 validators；
- 修复同范围执行问题；
- 写 controller report 和 completion check；
- 本地提交轻量 packet；
- 在 explicit reviewer handoff 边界停止。

Controller 不写 `review.md`，不写 reviewer token。

### Reviewer

Reviewer 是独立只读会话，只能：

- 读取 task、controller packet、代码和必要 lightweight evidence；
- 运行显式允许的只读 validators；
- 核对 required outputs、hashes、training adequacy、metric semantics、Slurm accounting 和 claims；
- 写 `results/<task_key>/review.md`。

Reviewer 不得：

- 修代码；
- 生成缺失文件；
- 补训练或推理；
- 修改 wiki；
- package/upload；
- 启动下一 Batch；
- 把 missing evidence 解释成 pass。

## 五、Monitor Packet 仍不是完成

无论是否启用 reviewer，以下状态都不是完成：

```text
SUBMITTED
PENDING
RUNNING
CONFIGURING
COMPLETING
NEEDS_MONITOR
AWAITING_SACCT
```

Job-derived packet 必须记录：

```text
job id
partition
state
exit code
elapsed
node
log path
runtime output path
aggregation command/exit
updated tracked evidence
```

Runtime 输出缺失或 aggregation 失败时必须是 `NEEDS_EVIDENCE`/`NEEDS_REPAIR`，不能进入 reviewer pass 或 Controller `VERIFIED_COMPLETE`。

## 六、显式 Review 文件

只有 `review_required: true` 时才要求：

```text
results/<task_key>/review.md
```

此时 review token 可以作为明确声明的 continuation/publication gate。没有显式 reviewer 的默认任务不得要求该文件。

## 七、历史兼容

历史 task 若已明确 reviewer path/token，继续按原 task 合同执行；不得删除历史 `review.md` 或改写已完成 review token。

未来 task 不得因为历史模板中出现 reviewer wording 就自动继承 reviewer 门。以 task frontmatter 的 `review_required` 为唯一开关。

## 八、显式 Reviewer Prompt 必须包含

```text
This task explicitly sets review_required: true. This is a separate read-only reviewer session. Do not fix code, generate missing artifacts, train, run missing inference, package validation, upload, update wiki, or start the next Batch. Inspect only the committed controller packet and write the declared review.md decision. Missing or contradictory evidence cannot be converted into a pass.
```

## 九、默认无 Reviewer Task 必须包含

```text
review_required: false. Do not start an independent reviewer and do not require review.md. The Controller/Coordinator owns execution acceptance and must return VERIFIED_COMPLETE, NEEDS_REPAIR, or OPERATIONALLY_BLOCKED to the Planner after checking real diffs, outputs, terminal jobs, aggregation, validators, and contract compliance.
```