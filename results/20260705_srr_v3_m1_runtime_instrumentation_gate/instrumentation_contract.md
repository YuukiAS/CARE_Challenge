# SRR-v3 M1 Runtime Instrumentation Contract

## Scope

This packet is the continued M1 evidence revision for `srr_propref_shared_dual_dict`. It is eval-only instrumentation: no model training, no full-fold training, no validation packaging/upload, no route promotion, and no M2 execution.

## Runtime Source

- Helper: `scripts/evaluation/export_srr_v3_m1_runtime_instrumentation.py`
- Variant: `srr_propref_shared_dual_dict`
- Checkpoint used for forward instrumentation: `/users/a/e/aereinh/CARE/results/20260704_srr_v25_training_ablation_matrix/bounded_matrix/variants/srr_propref_shared_dual_dict/checkpoints/fold_0/propref_config/checkpoint_final.pt`
- Device: `cpu`
- Cases: `Case1002, Case2002, Case3004, Case3011`
- Sample scope: one deterministic validation patch per case, patch shape `12x96x96`.

## Prototype Coverage Source

The selected review source is `/users/a/e/aereinh/CARE/results/20260704_srr_v25_prototype_bank_cache/prototype_bank_summary.json`. It is an existing train/OOF runtime prototype summary and is not produced by new training in this M1 revision. It reports `edema_positive=8`, `edema_negative=30`, and `t2_present_edema_positive=2897` with `coverage_status=PRESENT`.

The previous 6-step bounded checkpoint source remains listed as `previous_blocking_checkpoint_source`; it still reports `edema_positive=0` and `edema_negative=0`. It is retained to preserve the prior blocker rather than hide it.

## Exported Evidence

- `gate_residual_export.csv`: per-case and aggregate baseline residual gate, bounded delta, applied correction, decode delta versus nnU-Net, and anchor confidence/entropy fields.
- `prototype_coverage_export.csv`: selected non-empty T2-present prototype coverage plus the previous blocking checkpoint source.
- `anchor_context_alignment_export.csv`: tensor shapes, availability, anchor/component presence, source path, fold, and shape alignment status.
- `no_t2_safety_export.csv`: no-T2 edema logit/decode/loss-path runtime evidence.

## Status Categories

- `code_path_exists`: source lines define the contract but do not prove runtime behavior.
- `runtime_instrumented`: this packet ran the existing checkpoint through the helper and exported CSV evidence.
- `formal_training_evidence`: not established here; the forward checkpoint still reports only `6` optimizer steps.

## Strict Gate

The strict anti-laziness validator rejects claim-only CSVs. It now passes this continued M1 packet because a selected non-empty T2-present edema prototype source is exported and all required runtime CSVs contain data rows.
