# Mapper Report Draft

本次代码变化改变的是 Batch7 机制验证和训练控制面，不是扩大模型应用范围。核心架构变化是：proposal discovery 路径不再读取 nnU-Net pathology anchor，上下文 anchor 只进入 confirmation/safety 路径；semantic memory 资产加载改成 fail-closed；生产 crossfit 字段恢复为真实 query policy 语义。

Draft mapping:

- `src/care_myocardium/models/srr_dictionary_memory.py`: `production_crossfit_exclusive` now reflects `query_policy == training_crossfit_exclude_query_shard`; formal real-memory exclusivity is carried separately by `formal_real_memory_exclusive`.
- `src/care_myocardium/models/srr_propref.py`: discovery and confirmation features are separated; intervention modes `prototype_maps_off`, `semantic_negative_memory_off`, and production open-gate control have distinct model semantics.
- `scripts/srr_production/infer_myops.py`: semantic memory asset loading is fail-closed for required memory state and records load receipts.
- `scripts/training/run_srr_propref_myops_fold0.py`: training asset loading and one-batch preflight use the same fail-closed memory receipt path.
- `scripts/evaluation/validate_srr_batch7_repair_packet.py`: validator rejects missing outputs, copied placeholders, invalid memory assets, anchor-dependent discovery, missing T2-present edema gradient authority, and unexpected duplicate prediction hash sets.

No Cine path, validation packaging path, hosted metric path, or fold expansion path was modified.
