---
document_type: route_planning_critic_request
route_id: route_B
portfolio_round: round04
date: 2026-07-19
status: AWAITING_INDEPENDENT_CRITIC
critic_role: separate_gpt_thread
critic_write_path: prompts/routes/route_B_round04_critic_review.md
allowed_tokens:
  - ROUTE_B_ROUND04_PLANNING_READY_FOR_CONTROLLER
  - ROUTE_B_ROUND04_PLANNING_NEEDS_REVISION
controller_start_authorized: false
---

# Route B Round04 Critic Request

你是CARE Route B独立规划期Critic。只审查planning，不执行代码、不训练、不提交Slurm、不写runtime `review.md`、不做validation upload、promotion、M11、cross-route merge、hosted metric或final scientific decision。

## Exact review target

Critic必须fetch最新`origin/main`，记录包含以下五个planning文件和本request的exact commit，并计算每个文件SHA256：

```text
prompts/routes/portfolio_round04_route_B_planner_plan_20260719.md
prompts/routes/route_B_round04_planner_prompt.md
prompts/routes/route_B_round04_controller_contract.md
prompts/routes/route_B_round04_executor_plan.yaml
prompts/routes/route_B_round04_critic_request.md
prompts/routes/route_B_round04_planner_audit.md
```

同时fetch`origin/route_B`，确认review commit `b9c7664da7cb1f1892fff37a4497722f31a0a96d`与reviewed packet head `8dfa40f8c4cedb2507f35a482bd46244a7a1c94c`存在，读取`results/route_B/review.md`中的`ROUTE_B_ROUND03_REVIEW_ADEQUATE_NEGATIVE`。任何commit/blob/hash变化使review失效。

## Mandatory review questions

1. 是否真正继承`ROUTE_HARD_REQUIREMENTS_MATRIX`中的完整Route B，而不是Route A压缩版、nnU-Net-only、postprocess-only、wrapper-only或validator-only。
2. B3 gate是否被科学地拆成实现正确性microfit与最终病灶有效性门；是否仍有旧`anatomy_union_overfit`隐藏地阻断B4–B10；是否存在无条件绕过。
3. B0–B2继承是否先做fingerprint audit；改过的target/loss/wrapper是否被错误继承旧runtime。
4. OOF bank、safe hard-negative、proposal、soft ROI、scar/edema refiner、bounded final correction是否形成memory-to-final-label causal chain。
5. 是否精确定义same-split nnU-Net、case-wise help/harm、scar-positive、T2-present edema-positive、no-T2 safety、CenterB/C、remote-FP、component count、HD95、volume ratio。
6. official CineMA与matched-random是否同结构、同下游初始化、同病例、同frames、同augmentation、同optimizer、同budget。
7. faithful registration是否包含symmetric velocity、seven-step integration、true Jacobian、inverse composition、real SyN、pair/case/aggregate denominators。
8. temporal是否真实消费全部registered fields并完成reference-only、unregistered、registered、temporal-off、motion-off、anatomy-off、pretrained/random消融。
9. Controller task graph是否能执行到terminal packet；MyoPS/Cine并行是否有write/runtime isolation；MyoPS内部是否仍顺序。
10. 所有Slurm wrapper是否固定`/users/a/e/aereinh/CARE/envs/env_CARE/bin/python`；preflight、race、V100兼容、zero-credit、afterok/afterany、24-hour block规则是否完整。
11. validator是否检查语义并运行known-bad，而不是只检查文件存在。
12. completion token是否区分monitor、implementation defect、stage adequate negative、full evidence；Controller是否可能用非ready token提前退出。
13. planner文件中是否存在设计空白授权、Cine/registration/temporal降格为非正式阶段、runtime push或越权。
14. Reviewer draft是否能区分evidence complete、adequate negative、needs revision、needs evidence、needs monitor。
15. deep research每项是否映射到具体模块、阶段、evidence与validator。

## Required executable checks

Critic必须在具备仓库shell的环境执行：

```text
/users/a/e/aereinh/CARE/envs/env_CARE/bin/python scripts/ops/validate_executor_plan.py prompts/routes/route_B_round04_executor_plan.yaml
git diff --check
FORBIDDEN_PATTERN='T''BD|op''tional|as appro''priate|if nee''ded|choose be''st|Codex dec''ide|controller dec''ide|按''需|视''情况|自行''决定'
rg -n "$FORBIDDEN_PATTERN" prompts/routes/portfolio_round04_route_B_planner_plan_20260719.md prompts/routes/route_B_round04_*.md prompts/routes/route_B_round04_executor_plan.yaml
rg -n '(^|[;&|[:space:]])python(3)?[[:space:]]' prompts/routes/route_B_round04_*.md prompts/routes/route_B_round04_executor_plan.yaml
rg -n -i 'CineMA|registration|temporal' prompts/routes/route_B_round04_*.md prompts/routes/route_B_round04_executor_plan.yaml
```

第一条和`git diff --check`必须exit 0；两条风险搜索必须无不合格命中。CineMA/registration/temporal搜索必须显示正式阶段、预算、outputs和validators，不得显示延后或降格语义。

## Critic output schema

`prompts/routes/route_B_round04_critic_review.md`必须记录：

```text
reviewed_main_commit
reviewed_route_B_commit
reviewed_round03_packet_head
six file SHA256 values
executor_plan_validator exit/output
git diff exit/output
forbidden-blank scan
bare-interpreter scan
CineMA/registration/temporal coverage judgment
B3 gate judgment
deep-research mapping judgment
task-graph terminality judgment
decision token
blocking findings
authority boundary
```

只有无blocking finding时写`ROUTE_B_ROUND04_PLANNING_READY_FOR_CONTROLLER`。该token只授权exact reviewed contract的Route B Controller启动。
