# V1 gap audit for V2 completion

当前结论：V1 不是可进入 Deep Research 的终态证据包。它已经解决了 PDF 可搜索和部分清单问题，但核心本地证据仍未完成，尤其是统一指标、历史模型逐轮恢复、MoSAIC recipe decomposition、feature probe、selector/oracle、Cine temporal probe 和真实 nnU-Net decoder-reset D1-D3。

## Validator state

- V1 strict validator: `FAIL` / `NEEDS_REPAIR`.
- Hard fail count: `1`.
- Missing diagnostics: `D1_DECODER_RESET_ENCODER_FROZEN; D2_DECODER_RESET_TOP_ENCODER_TRAINABLE; D3_FULL_MODEL_SHORT_FINETUNE; FEATURE_PROBE_HELDOUT; MOSAIC_RECIPE_DECOMPOSITION; CINE_TEMPORAL_PROBE`.

## Critical correction

上一轮遗留的 `runtime/decoder_reset_diagnostics` 是 PRISM wrapper 诊断残留，不满足 V2 合同中“真实 nnU-Net plans、decoder、patch sampling、augmentation 和六类 loss”的 D1-D3 要求。它只能作为非合同残留记录，不得算入 decoder-reset 完成。

## Gap tokens

- `PARTIAL`: 551
- `UNRESOLVED`: 460
- `UNBOUND_CHECKPOINT`: 157
- `UNBOUND_RECIPE`: 153
- `STALE`: 92
- `REQUIRES_`: 86
- `PLACEHOLDER`: 46
- `MISSING`: 43
- `NOT_RUN`: 31
- `NEEDS_REPAIR`: 19
- `VISUAL_HUMAN_CONFIRMATION_PENDING`: 7
- `NEEDS_FEATURE_BINDING`: 5
- `NEEDS_RECIPE_BINDING`: 5
- `NEEDS_CINE_BINDING`: 5

## Required GPU tasks

| GPU task | V1 status | Notes |
| --- | --- | --- |
| `G1_NNUNET_IDENTITY_REPRODUCTION` | `PARTIAL_COMPLETED_D0_ONLY` | D0 replay exists, but V2 requires G1 consistency/hash comparison against baseline. |
| `G2_PRISM_13_CHECKPOINT_REPLAY` | `REQUIRED_NOT_TERMINAL` | No terminal V2 GPU evidence found. |
| `G3_DECODER_RESET_D0_D3_REAL_NNUNET` | `NOT_COMPLETE` | D1-D3 are missing from finalizer. Prior PRISM wrapper artifacts are explicitly non-contract because V2 requires real nnU-Net decoder/plans/loss. |
| `G4_MOSAIC_RECIPE_DECOMPOSITION` | `REQUIRED_NOT_TERMINAL` | Text hits only, not terminal V2 GPU evidence: mosaic_recipe_decomposition. |
| `G5_FROZEN_FEATURE_PROBES` | `REQUIRED_NOT_TERMINAL` | Text hits only, not terminal V2 GPU evidence: feature_probe_summary.csv;feature_probe_full_results.csv. |
| `G6_MODEL_COMPLEMENTARITY` | `REQUIRED_NOT_TERMINAL` | Text hits only, not terminal V2 GPU evidence: case_oracle_summary.csv;voxel_error_overlap_matrix.csv. |
| `G7_SELECTOR_FEASIBILITY` | `REQUIRED_NOT_TERMINAL` | Text hits only, not terminal V2 GPU evidence: selector_nested_cv_results.csv. |
| `G8_ALIGNMENT_DIAGNOSTICS` | `REQUIRED_NOT_TERMINAL` | Text hits only, not terminal V2 GPU evidence: alignment_error_correlation.csv. |
| `G9_CINE_ED_ONLY_VS_TEMPORAL` | `REQUIRED_NOT_TERMINAL` | Text hits only, not terminal V2 GPU evidence: cine_temporal_signal_probe.csv. |
| `G10_OLD_MODEL_REPLAY` | `REQUIRED_NOT_TERMINAL` | Text hits only, not terminal V2 GPU evidence: Batch7;MMRD;Cascade;ARC;DG/DR/DPR. |

## Immediate next action

先完成真实 nnU-Net G1/G3 preflight 和执行入口，再串行运行合同要求的 GPU 诊断。V1 PDF 不得覆盖；V2 PDF 必须另存为 `CARE_Failure_Forensics_Deep_Research_Evidence_Packet_20260730_v2.pdf`。

Generated files:

- `v1_gap_audit.json`
- `v1_pdf_section_completeness.csv`
- `v1_required_task_status.csv`
- `v2_task_status.csv`
- `v2_gpu_job_manifest.csv`
- `v2_source_manifest.csv`
