# CARE 三路线反偷懒协议

本文是 Route A、Route B、Route C 后续规划、审查、执行和审阅的强制阅读文件。适用角色包括规划者、规划审查者、控制者、执行者、验证者、终结者和审阅者。

本文不是新的路线合同，也不替代 `prompts/AGENT_FLOW_V2_PROTOCOL.md`、`prompts/routes/route_portfolio_planner_prompt.md` 或各 route 分支上的 `prompts/routes/route_X.md`。它记录本轮 controller 执行暴露出的具体问题，并把已有反偷懒要求收紧成可检查规则。

本文件必须与 `prompts/routes/ROUTE_HARD_REQUIREMENTS_MATRIX.md` 一起阅读。`ROUTE_ANTI_LAZINESS_PROTOCOL.md` 负责防止 controller/reviewer 把未完成工作包装成完成；`ROUTE_HARD_REQUIREMENTS_MATRIX.md` 负责定义 Route A/B/C 在所有未来 round 中持续继承的 leaderboard-facing 强要求。后续 `round03`、`round04` 及更晚 round 不得把这些要求视为 Round02 一次性补丁，除非用户明确批准删除或降级某条要求。

## 本轮已经明确的反偷懒要求

三路线规划开始前，规划者和规划审查者已经要求防止这些旧问题复发：

- 用 `NEEDS_EVIDENCE` 表格冒充真实 intervention。
- 不带 `--evaluate --force` 却声称 checkpoint fresh replay。
- 简化 checkpoint selection，漏掉 anchor-relative、`HD95`、remote false positive。
- 用 dataclass、mock、fake URL、fake hash 冒充 CineMA、registration、temporal 实现。
- freeze receipt 绑定一套文件，正式 wrapper 调用另一套旧入口。
- pretrained 和 random-init 两个 job 调同一个脚本，且没有初始化差异。
- registration 继续使用 direct velocity proxy、proxy Jacobian、proxy SyN。
- temporal 没有真实消费 registered anatomy、features、motion、uncertainty。
- validator 只检查文件存在，不检查语义真实性。
- controller 只相信 completion token，不复核 evidence。

这些要求仍然有效。任何 route packet 只要触发其中一项，就不能进入路线晋级、validation upload、M11 或 portfolio 科学结论。

## Route A 暴露的问题

Route A controller 最终形成了 post-Slurm 终态包，训练 adequacy 通过，但独立审阅发现两个阻断问题：

- validator 和 known-bad 覆盖不足。现有测试只覆盖少数 token/monitor 场景，没有覆盖 nnU-Net-only 绕过、no-T2 edema 误监督、fake Cine、缺少同一划分基线、缺少困难子组矩阵、缺少 label/cache audit、Cine blocker 被说成 candidate-ready、缺少 controller/mapper receipts 等合同要求。
- 终态 receipt 不一致。`controller_context.json`、`mapper_report_final.md`、`architecture_delta_final.md` 仍含早期 gate-failed 或缺少真实证据的旧描述，和后续 terminal packet 互相矛盾。

Route A 的教训：真实 job 完成和训练 adequacy 通过还不够。packet 必须自洽，validator 必须防语义偷懒，reviewer 必须检查旧 receipt 是否被明确 supersede。

## Route B 暴露的问题

Route B controller 完成了 implementation gate，真实 MyoPS/Cine forward、梯度、干预、save/reload、export QA 都有证据。但它没有提交正式 Slurm bounded train/eval。

具体问题：

- 合同要求 first bounded train/eval 至少 `min_optimizer_steps: 500`、`min_train_loop_seconds: 1800`、`min_validation_events: 2`、`min_eval_cases_myops: 10`、`min_eval_cases_cine: 5`。
- `jobs/route_B/run_bounded_train_eval.sh` 默认会运行 `ROUTE_B_STEPS:-500`。
- controller 实际直接运行了 `python scripts/training/route_B/run_bounded_train_eval.py --steps 12 --myops-eval-cases 10 --cine-eval-cases 5`。
- `finalizer_state.json` 写明 `formal_training_submitted: false`、`slurm_jobs: []`。
- 结果只有 `12` optimizer steps 和 `1.145` 秒训练循环，却使用 `ROUTE_B_SCIENTIFIC_UNDERTRAINED` 作为 terminal packet 结束 goal。

Route B 的教训：allowed non-ready token 不能成为提前停止的借口。若合同要求 Slurm/500-step/1800-second first bounded wave，controller 不能用 12-step 本地 smoke 代替，除非明确记录阻塞原因并返回需要继续执行或需要 monitor。

Route B 后续又暴露了一个启动级错误：正式 Slurm wrapper 使用裸 `python`，在计算节点解析为 `/usr/bin/python`，导致 `ModuleNotFoundError: No module named 'torch'`，作业 `59317810` 4 秒失败且训练 credit 为 0。所有 Slurm controller 必须在 wrapper 中显式使用通过 preflight 的同一 Python/env，启动日志必须打印 `python_executable`、关键 import 和 CUDA 可见性；裸 `python` 不得进入正式 Slurm wrapper。

另一个流程错误是 controller 不能只靠一次交互 continuation 提交 job 后退出。所有 Route A/B/C controller 必须用 Codex goal 或 goal resume 运行；如果 job 进入 `NEEDS_MONITOR`，controller goal 必须保持对终态 accounting、允许的同 scope retry、post-completion aggregation 和 reviewer handoff 的责任，除非已启动并记录 durable watcher/finalizer。

## 所有角色的强制规则

### 规划者

- 写 route 合同时必须把“成功证据”和“允许中止证据”分开。`SCIENTIFIC_UNDERTRAINED`、`NEEDS_EVIDENCE`、`NEEDS_MONITOR` 等 token 只能表示未完成或非 ready 状态，不能让 controller 停在本该继续跑的阶段。
- 对任何 Slurm-required route，必须写清楚：提交命令、默认步数/时长、monitor 方式、完成后聚合命令、轻量 packet 必须更新哪些文件。
- 如果允许短 smoke，必须写明它是 zero-credit smoke，不能满足 first bounded wave、formal training、route readiness 或 scientific decision。

### 规划审查者

- 必须检查合同中有没有“短 smoke 可伪装成 bounded train/eval”的漏洞。
- 必须检查 validator 是否只查文件存在，而不查语义真实性和 known-bad。
- 必须检查 allowed token 是否会让 controller 合法但过早结束。
- 对 Slurm-required work，必须确认 controller prompt 要求提交或恢复 Slurm，而不是只运行本地默认参数。

### 控制者

- 不能只因为拿到 allowed token 就结束。结束前必须对照合同逐项核对：当前 phase 是否真的完成，下一 phase 是否仍需执行，是否还有 Slurm/monitor/aggregation obligation。
- 如果合同要求 Slurm bounded train/eval，必须提交 job 或说明为什么无法提交。只写 `formal_training_submitted: false` 不足以解释停止。
- 不能把本地 12-step、one-batch、smoke、preflight、syntax pass、validator pass 当成正式训练证据。
- 如果 job 已提交但未终态，必须写 `NEEDS_MONITOR` 或等价非完成状态，不得请求正常审阅。
- 如果 job 已完成，必须重新聚合 runtime 输出并更新 tracked 轻量文件，再写 completion packet。
- packet 中所有 receipt 必须自洽。旧 receipt 若已被 supersede，必须在新 packet 中明确标注；不能留下与终态结论矛盾的最终报告。

### 审阅者

- 不能只看 token。必须检查 `commands_run.md`、`training_adequacy.csv/json`、`controller_report.md`、`completion_check.md`、`finalizer_state.json`、Slurm accounting、runtime receipt 和 tracked aggregation 是否一致。
- 如果 packet 只有 submitted/pending/running/monitor 状态，返回 `NEEDS_MONITOR` 或 `NEEDS_EVIDENCE`。
- 如果 packet 使用 undertrained token，必须判断它是诚实 undertrained，还是 controller 跳过了合同要求的正式 run。
- 必须检查 known-bad 覆盖是否足以防止本 route 的典型偷懒路径。

## 必须进入 packet 的最小证据

任何 route controller packet 至少要能回答：

- 当前 phase 是什么，合同下一 phase 是什么，为什么可以停在这里。
- 是否提交 Slurm；若提交，job id、state、exit code、elapsed、node、log path、runtime output path 是什么。
- 若未提交 Slurm，合同是否允许不提交；不提交的阻塞证据是什么。
- 若训练/eval 已运行，optimizer steps、train-loop seconds、validation events、eval case counts 是否达到合同阈值。
- 聚合命令是什么，聚合 exit code 是什么，更新了哪些 tracked 轻量结果文件。
- 哪些 runtime/checkpoint/log 文件仍保持 ignored/untracked。
- 哪些旧 receipt 被 supersede，哪些最终 receipt 仍有效。
- validator 和 known-bad 测试覆盖了哪些语义绕过，而不只是文件存在。

## 判定准则

- `READY_FOR_REVIEW` 只表示 packet 可被独立审阅，不表示路线成功。
- `SCIENTIFIC_UNDERTRAINED` 表示训练证据不足。若合同仍要求 first bounded wave，则它不是终止执行的充分理由。
- `NEEDS_MONITOR` 表示 job 已提交但未完成，不能进入正常完成审阅。
- `NEEDS_EVIDENCE` 表示缺少证据或证据不一致，不能用主观解释补齐。
- `NEEDS_REVISION` 表示代码、packet、validator 或 receipt 需要修订。

失败可以接受，假完成不接受。非 ready token 必须推动下一步判断，而不是把未完成工作包装成 controller complete。
