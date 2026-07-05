# SRR-v3 M1 Runtime Instrumentation Contract

## Scope

This packet is eval-only instrumentation for `srr_propref_shared_dual_dict` using the existing bounded checkpoint. It does not train, does not run full fold training, does not package validation data, and does not promote a route.

## Runtime Source

- Helper: `scripts/evaluation/export_srr_v3_m1_runtime_instrumentation.py`
- Variant: `srr_propref_shared_dual_dict`
- Checkpoint: `/users/a/e/aereinh/CARE/results/20260704_srr_v25_training_ablation_matrix/bounded_matrix/variants/srr_propref_shared_dual_dict/checkpoints/fold_0/propref_config/checkpoint_final.pt`
- Device: `cpu`
- Cases: `Case1002, Case2002, Case3004, Case3011`
- Sample scope: one deterministic validation patch per case, patch shape `12x96x96`.

## Exported Evidence

- `gate_residual_export.csv`: per-case and aggregate baseline residual gate, bounded delta, applied correction, decode delta versus nnU-Net, and anchor confidence/entropy fields.
- `prototype_coverage_export.csv`: source-summary-derived prototype bank counts and T2-present edema coverage fields.
- `anchor_context_alignment_export.csv`: tensor shapes, availability, anchor/component presence, source path, fold, and shape alignment status.
- `no_t2_safety_export.csv`: no-T2 edema logit/decode/loss-path runtime evidence.

## Status Categories

- `code_path_exists`: source lines define the contract but do not prove runtime behavior.
- `runtime_instrumented`: this packet ran the existing checkpoint through the helper and exported CSV evidence.
- `formal_training_evidence`: not established here; source checkpoint reports only `6` optimizer steps.

## Strict Gate

The strict anti-laziness validator rejects claim-only CSVs and rejects this current packet as M1-ready because prototype coverage reports `EDEMA_PROTOTYPES_EMPTY`. That is an evidence blocker, not a tooling failure.
