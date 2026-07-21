# CARE 架构沿革

| 里程碑 | 基线 | 架构版本 | fingerprint | 变化 | review token | evidence |
| --- | --- | --- | --- | --- | --- | --- |
| M8 implementation analysis | `TODO.md` historical source | `care-srr-v3-m08-history` | history snapshot | 迁移 M8 路线审阅分析，不作为 current runtime evidence。 | `M8_AUDITED_NO_PROMOTION_SCIENTIFIC_UNRESOLVED` | `wiki/history/M08/README.md` |
| M9 follow-up evidence reconciliation | current `main` | `care-srr-v3-m09-history` | history snapshot | 迁移 M9 follow-up 期间路线级审计；later status 更新为 no-promotion diagnostic-only。 | `M9_FOLLOWUP_AUDITED_READY_NO_PROMOTION_DIAGNOSTIC_ONLY` | `wiki/history/M09/README.md` |
| Agent-flow v2 continuity repair | `10878dc` and follow-up | `care-agent-flow-v2-complete` | `wiki+validator+skills+toolkit-healthcheck` | 增加 durable finalizer、并行 executor plan gate、中文 wiki 和 history generator。 | protocol-only | `wiki/writing_skill_receipt.json` |

后续 mapper-final 更新必须追加新行，记录 architecture version、code fingerprint、component status delta、review token 和 evidence path。历史版本默认不可静默改写；纠错使用 `ERRATA.md` 或 `later_status_update`。

| M10 follow-up candidate packet | M09 current state | `care-agent-flow-v2-m10-candidate-unreviewed` | `m10_candidate=78d6398` | Added unreviewed F1/F2/F3 evidence mapping; F3 temporal remains NEEDS_EVIDENCE after timeout. | `NOT_REVIEWED` | `results/20260714_srr_v3_m10_continuation_reconciliation/result.md` |
| Batch6 final objective alignment | Batch4 selected checkpoint | `care-srr-batch6-final-objective-alignment-stop300` | `srr_propref=8b98ac43;srr_losses=eaabe101;run_myops=e9f531b0;infer_myops=df3922d7;batch6_formal=8619856a;batch6_validator=635f0157;batch6_config=9922ba2c` | Direct final-logits scar/edema losses and production gate repair path; fixed-overfit PASS; formal300 gate FAIL so 900 skipped. | `NOT_REVIEWED_CONTROLLER_VERIFIED` | `results/20260721_srr_batch6_final_objective_alignment/MANIFEST.md` |
