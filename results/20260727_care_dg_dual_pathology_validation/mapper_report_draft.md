# CARE-DG Mapper Draft After Gate B-R2

created_at_utc: `2026-07-28T03:52:35Z`
base_git_head: `67dac96a22e6179e0a7fcc02815b36aab30a8bfc`
origin_main: `67dac96a22e6179e0a7fcc02815b36aab30a8bfc`
mapper_status: `DRAFT_NOT_FINAL`

## Plain Judgment

当前 CARE-DG 代码路径已经能证明“冻结 nnU-Net anchor + 紧凑共享编码器 + 独立 scar/edema 修正 decoder”这一实现存在，并且 Gate B-R2 的固定 train-side 搜索证明 fold0 没有安全扩展候选。这个 draft 不是终态 wiki 更新：五折 OOF、complete-80、all-data fit、validation package 和 final Mapper 均未完成，folds 1-4 也不得继续或聚合，除非 GPT/用户重新授权。

## Source And Config Mapping

| component | status | evidence |
|---|---|---|
| modality stems + compact shared encoder | implemented / Gate A verified | `src/care_myocardium/models/care_dg.py`; hash `ee38bd7d86ca37944ef4108fa4d5904d9ead1f7ae2dc4b7ec518d784acb71d55` |
| independent scar decoder | implemented / Gate A+B evidence | `self.scar_decoder`; FN/FP gate+magnitude outputs in `care_dg.py` |
| independent edema decoder | implemented / Gate A+B evidence | `self.edema_decoder`; no-T2 mask applied to edema delta/gates |
| scar-priority composition | implemented / Gate B hotfix evidence | `apply_scar_priority_composition`; outputs `after_edema_logits` and `final_logits_after_scar_priority` |
| soft myocardium support | implemented / Gate A-R1/R3 evidence | `support_maps()` uses labels `[1,4,5]`, excludes LV/RV `[2,3]`, shells 6mm/10mm |
| grouped Stage B optimizer | implemented / Gate A-R3 evidence | Stage B representation lr `2e-5`, pathology lr `1e-4`, weight decay `1e-4` |
| fixed inner selection | implemented / Gate A-R2/R3 evidence | checkpoint manifests use fixed train-side complete inner plan; outer val used `False` |
| full-volume Gaussian delta inference | implemented / Gate B-R1 evidence | R1 evaluator aggregates scar/edema deltas and composes once on full anchor |

## Runtime Evidence Boundary

- Fold0 repaired scar-priority runtime: 8000 optimizer steps, Gate B evaluated on 44 outer held-out and 16 complete-trimodal cases.
- Gate B original operational PASS was downgraded to diagnostic because complete16 scar/edema-zone/pure-edema and fragmentation metrics were worse than anchor.
- Gate B-R1 fixed patch-final-logit averaging but failed scientific expansion: no pathology improved by `>0.005`.
- Gate B-R2 evaluated `512` fixed train-side checkpoint/scale candidates and found `0` eligible candidates.
- Best R2 train-side candidate: scar delta `0.004258`, edema-zone delta `0.000630`, pure-edema delta `0.000607`; failure `no_pathology_improves_by_more_than_0.005`.

## Fold Expansion Status

`fold_expansion_status_audit.json` records physical receipts for folds 0-3 and missing fold4. Because Gate B-R2 found no eligible candidate and the later Gate B-R1/R2 instruction paused expansion, existing folds 1-3 receipts are provenance only and must not be aggregated into official W3 OOF without explicit GPT/user reauthorization.

## Wiki Staleness

Current `wiki/README.md`, `wiki/current_state.yaml`, and `prompts/routes/handoffs/CURRENT.md` still describe the 2026-07-26 MoSAIC hosted-gap / `NNUNET_ONLY_DOCKER` terminal state. That state is stale relative to current CARE-DG Gate B-R2 evidence, but this draft intentionally does not update root wiki because the task has not reached terminal Mapper final.

## Validator Status

- Gate B-R2 validator: `PASS` / `NO_INNER_ELIGIBLE_CANDIDATE`
- strict validator: `PASS`
- Gate B consistency validator: `PASS`
- architecture wiki strict check before draft: `PASS`
- architecture wiki generation check before draft: `PASS`
- toolkit healthcheck: `PASS`

## Missing For Final Mapper

- W3 220-case OOF and complete-80 aggregation are absent.
- A0/A1/A2/A3 full five-fold ablation is absent.
- W4 all-data deployment fit is absent and not authorized because no candidate passed.
- W5 validation inference/package/Docker-equivalent smoke are absent and not authorized.
- Root wiki/CURRENT final update, finalizer_state, MANIFEST, controller_report, completion_check and notification_brief remain absent.

## Files Inspected

- `START_HERE_FOR_GPT.md`
- `GPT_PLANNER_CARE_PROTOCOL.md`
- `AGENTS.md` via active repo instructions
- `prompts/AGENT_FLOW_V2_PROTOCOL.md`
- `.agents/skills/slurm-routing-partition/SKILL.md`
- `.agents/skills/care-mapper/SKILL.md`
- `prompts/routes/handoffs/CURRENT.md`
- `wiki/README.md`, `wiki/MODEL.md`, `wiki/COMPONENTS.csv`, `wiki/architecture.yaml`, `wiki/current_state.yaml`, `wiki/LINEAGE.md`, `wiki/EXECUTION.md`
- CARE-DG source/config/result files listed in this report and in `fold_expansion_status_audit.json`
