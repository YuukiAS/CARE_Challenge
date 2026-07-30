# V4 audit of V3 scientific design-readiness gaps

V3 is useful operational evidence, but it is not a final design-readiness packet. V4 reopens every gap that can change the next model design.

| id | severity | status | observed gap | required output |
| --- | --- | --- | --- | --- |
| G01_BATCH0_7 | critical | OPEN | Batch lineage remains grouped; V4 requires individual BATCH0 through BATCH7 recovery. | v4_batch_history_recovery.csv |
| G02_BATCH7 | critical | PARTIAL | Batch7 has usable historical traces, but final design conclusion still needs explicit component survival synthesis. | v4_batch7_* |
| G03_MMRD | critical | PARTIAL | Batch9 MMRD has matched-seed casewise evidence; V4 must bind decoder inheritance and direct/distill comparisons. | v4_mmrd_* |
| G04_CASCADE | high | PARTIAL | Cascade evidence supports bounded tiny correction; prototype/control isolation remains a semantic risk. | v4_cascade_* |
| G05_ARC | high | PARTIAL | ARC has implementation/runtime evidence but must keep blueprint, code and runtime separate. | v4_arc_* |
| G06_MOSAIC | critical | OPEN | V3 M2-M10 fields remain underpopulated for full-data mechanism claims. | v4_mosaic_* |
| G07_FEATURE_PROBE | critical | OPEN | V3 edema probes contain single-class folds; V4 requires patient-level refolding and leakage controls. | v4_feature_probe_* |
| G08_SCAR_EDEMA_BRIEFS | high | OPEN | Disease briefs need independent text and similarity validation. | v4_scar_scientific_brief.md; v4_pure_edema_scientific_brief.md |
| G09_LARGE_GAIN | critical | OPEN | V3 has oracle summaries but not pool-level 0.1 Dice recovery accounting. | v4_large_gain_* |
| G10_ALIGNMENT | high | CLOSED | V4 binds complete-trimodal alignment rows and recomputes bootstrap/center-adjusted statistics. | v4_alignment_* |
| G11_ATLAS | critical | CLOSED | V4 rebuilds the atlas as A3 landscape and validates positive page margins. | v4_atlas_* |
| G12_STATE_SEMANTICS | critical | CLOSED | V4 separates execution, evidence, model-failure and design-readiness state. | v4_state_semantics_contract.json; v4_final_state.json |
