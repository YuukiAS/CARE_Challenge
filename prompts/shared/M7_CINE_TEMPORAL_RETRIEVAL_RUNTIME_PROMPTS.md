# M7: Cine Temporal Retrieval Runtime Pilot Prompts

Use this file for the next Cine-side milestone after `results/20260705_srr_v3_m5_cine_secondary_contract/review.md:M5_AUDITED_DIAGNOSTIC_GO`.

M7 is intentionally not another registration audit. M5 already established that registration evidence is incomplete, but it also showed that frame-quality/motion-saliency router inputs, frame0/CineMA anatomy evidence, optical-flow proxy rows, and SimpleITK/Demons fallback rows exist. M7 must therefore build and evaluate a runtime temporal retrieval / anatomy-first aggregation path with explicit registration-risk labels. Do not keep blocking merely because full registration is not proven.

## M7 executor

```text
只执行 M7：Cine temporal retrieval runtime pilot。开始前必须确认 `results/20260705_srr_v3_m5_cine_secondary_contract/review.md` 存在且包含 `M5_AUDITED_DIAGNOSTIC_GO`，否则停止并写 `M7_BLOCKED_BY_M5`。M7 是 Cine 副线的 runtime execution milestone，不阻塞 MyoPS M6，也不允许 validation packaging/upload、hosted metric claim、route promotion 或 full-fold expansion。

M7 的目标不是继续审计 registration 是否完美，而是把 M5 已经整理出的 Cine evidence 推进成一个可运行的 temporal retrieval / anatomy-first aggregation pilot。M5 已经说明：frame0/CineMA anatomy prior 可用，optical-flow proxy 和 descriptor router rows 可用，SimpleITK/Demons fallback 有 8 个安全 case，SyN 只有 one-case smoke，VoxelMorph 是 untrained near-identity。M7 必须承认 registration 风险，但不能因此停在 registration 配置阶段；必须构建 runtime temporal dictionary、运行 frame-quality/motion-saliency router、输出 temporal aggregation，并和 frame0/ED control 做 same-split 对比。

核心路线：以 frame0/ED anatomy prior 作为安全参考；从 cine 序列中选择 ED/reference frame、high-motion / high-quality non-reference frames、late/ES-like control frame；用 registration-light descriptor temporal dictionary 作为主路径，允许使用 optical-flow/Demons warping 作为带风险标签的辅助特征，但不能把 optical-flow/Demons/SyN/VoxelMorph 冒充 validated registration。输出必须明确区分：`registration_free_descriptor_dictionary`、`proxy_warp_assisted_feature`、`fallback_demons_feature`、`frame0_control`。

M7 必须满足最低 runtime 范围，不允许 one-case smoke：

1. dictionary/eval cases：优先使用 M5 中 strict-safe frame0-label cases 的最大可用子集；如果资源不足，至少 `24` 个 case；如果实际可用不足 24，必须写 `M7_RESOURCE_BLOCKED` 或 `M7_NEEDS_EVIDENCE`，不能写 ready。
2. frames per case：每个 case 至少纳入 `3` 个 frames：reference/ED frame、router 选出的 high-motion frame、一个 late/ES-like 或 low-quality control frame；如果某 case 帧数不足，必须逐 case 记录 reason。
3. temporal dictionary：必须实际生成 runtime temporal dictionary artifact 或 index，不允许只有自然语言 claim。可以把大型数组留在 ignored runtime path，但必须提交小型 `temporal_dictionary_index.json`，记录 case ids、frame ids、feature source、router weights、artifact paths、hash/shape/summary stats。
4. temporal aggregation：必须实际生成 temporal aggregation outputs 或 compact prediction/evidence summaries，并与 frame0/ED control 比较。至少报告 local class-1 myocardium proxy；如果 class-3/scar sanity 可从现有 label/evaluator得到，也要报告。不能只报告 image NCC。
5. safety/provenance：必须记录 registration risk，不得宣称 full registration、trained VoxelMorph、hosted improvement 或 challenge readiness。

允许代码修改：可以新增或修改小型 first-party helper/source/config 来构建 temporal dictionary、router weights、aggregation evaluation 和 strict validator。禁止大训练、full fold training、validation packaging/upload、hosted metric claim、route promotion。

必须写入 `results/20260705_srr_v3_m7_cine_temporal_retrieval_runtime/`，并至少提交以下轻量文件：

`result.md`
`cine_temporal_runtime_contract.md`
`code_diff_summary.md`
`temporal_dictionary_index.json`
`temporal_dictionary_case_summary.csv`
`frame_router_weights.csv`
`temporal_aggregation_metrics.csv`
`frame0_vs_temporal_help_harm.csv`
`registration_risk_matrix.csv`
`cine_prediction_sanity.csv`
`source_evidence_index.csv`
`unit_test_report.md`
`strict_validator_report.md`
`completion_check.md`
`review_request.md`
`MANIFEST.md`

`completion_check.md` 只能写 `M7_READY_FOR_REVIEW`、`M7_NEEDS_REVISION`、`M7_NEEDS_EVIDENCE` 或 `M7_RESOURCE_BLOCKED`。不能 mark ready 的情况包括：少于 24 个 dictionary/eval cases 且没有资源/数据阻塞说明；没有 runtime temporal dictionary artifact/index；每 case 少于 3 个 frame 且没有 reason；没有 frame0/control vs temporal aggregation comparison；只用一例 SyN 或 untrained VoxelMorph 作为 temporal retrieval 证据；没有 registration risk matrix；没有 strict validator；或者 strict validator 不能 fail closed 于 claim-only / one-case-smoke / no-runtime-dictionary / no-frame0-comparison / untracked-heavy-artifact packet。

必须运行并记录至少以下 validator/QA：

- required files exist and are non-empty;
- temporal dictionary index has at least 24 cases and at least 3 frames per valid case, unless blocked state is used;
- temporal aggregation metrics include frame0/control baseline and temporal output rows;
- router weights are finite and sum/normalize by case, or explicitly record a deterministic fallback rule;
- registration risk labels are present for every non-reference feature source;
- no validation package, hosted metric claim, NIfTI prediction package, checkpoint, raw image, or heavy dictionary array is committed.

完成后用 `git add -f` 提交 M7 packet 供 reviewer 审阅所需的全部轻量文件和必要 helper/source/config；不要提交 checkpoints、NIfTI predictions、upload packages、大日志、raw data、敏感信息、environment dumps、full runtime result tree 或大型 temporal dictionary arrays；不要 push，由用户手动 push。不要写 `review.md`，不要批准自己，不要启动 M8。M7 是否给 `M7_AUDITED_DIAGNOSTIC_GO` 或 `M7_AUDITED_GO` 由独立 reviewer 决定。
```

## M7 reviewer

```text
只读审阅 `results/20260705_srr_v3_m7_cine_temporal_retrieval_runtime/`。请读取本文件的 M7 executor、`prompts/MILESTONE_REVIEW_PROTOCOL.md`、`prompts/HANDOFF_GATE_POLICY.md`、`prompts/GPT_HARD_GATE_PROMPT.md`、M5 review，以及 M7 result directory。不要补 executor 缺失文件，不要改模型代码，不要训练，不要 validation packaging/upload，不要 route promotion，不要启动 M8。

重点检查 M7 是否真的从 M5 的配置/诊断推进到 runtime temporal retrieval，而不是又停在 registration audit。必须审阅：

1. `cine_temporal_runtime_contract.md` 是否明确说明 M7 使用 registration-light descriptor temporal dictionary 作为主路径，并把 optical-flow/Demons/SyN/VoxelMorph 等路径标成对应风险级别。
2. `temporal_dictionary_index.json` 和 `temporal_dictionary_case_summary.csv` 是否证明实际生成了 runtime temporal dictionary/index；是否至少覆盖 24 个 case 和每 case 至少 3 个 frames，除非 completion state 是 blocked。
3. `frame_router_weights.csv` 是否有 frame-quality/motion-saliency router weights，并且每个 case 的权重有限、可解释、可复现。
4. `temporal_aggregation_metrics.csv` 与 `frame0_vs_temporal_help_harm.csv` 是否包含 frame0/ED control 和 temporal aggregation output 的 same-split comparison；不能只报告 image NCC 或 router statistics。
5. `registration_risk_matrix.csv` 是否给每个非参考 feature source 标注 registration risk；是否避免把 optical-flow/Demons/SyN/VoxelMorph 冒充 validated registration。
6. `cine_prediction_sanity.csv` 是否覆盖输出合法性、label presence、component sanity、frame coverage 和 missing-case reason。
7. `source_evidence_index.csv`、`MANIFEST.md` 和 helper/source/config 是否足以让 reviewer 从 git 恢复轻量 evidence；是否没有提交 checkpoints、NIfTI predictions、validation packages、大日志、raw data 或大型 dictionary arrays。
8. `strict_validator_report.md` 和 `unit_test_report.md` 是否 fail closed 于 claim-only、one-case-smoke、no-runtime-dictionary、no-frame0-comparison、untrained-VoxelMorph-as-success、missing-registration-risk、committed-heavy-artifact 等 known-bad packets。

如果 M7 仍然只说 `TEMPORAL_DICTIONARY_NOT_READY` 而没有实际 runtime dictionary/index，或者只新增 registration 审计表而没有 temporal aggregation comparison，或者只用一例 SyN/VoxelMorph smoke 冒充方法，decision 必须是 `M7_AUDITED_NEEDS_REVISION` 或 `M7_AUDITED_NEEDS_EVIDENCE`。

最后只写 `results/20260705_srr_v3_m7_cine_temporal_retrieval_runtime/review.md`，decision 只能是 `M7_AUDITED_GO`、`M7_AUDITED_DIAGNOSTIC_GO`、`M7_AUDITED_NEEDS_REVISION` 或 `M7_AUDITED_NEEDS_EVIDENCE`。完成后 `git add -f review.md` 并 commit；不要 push，由用户手动 push。
```
