
# SRR-v2.5 Evidence Supplement Audit

status: `COMPLETE`
domain_evidence_label: `PARTIAL_MECHANISM_INCOMPLETE`
route_decision: `DIAGNOSTIC_ONLY_NEEDS_EVIDENCE`
audit_basis_commit: `3f30e0ee4b8c951f700fe50de8810bac8e196c23`

## 1. HEAD And Commit Range

Current HEAD: `3f30e0ee4b8c951f700fe50de8810bac8e196c23`.

Recent commits:

```text
3f30e0e (HEAD -> main, origin/main) Add SRR v3 task diagram
51d4ef6 Complete SRR v2.5 diagnostic review packet
fa8cdf3 Include gap matrix in SRR v2.5 push summary
b13a09c Update gap matrix task with baseline preservation gap
3798482 Update SRR v2.5 pushed subtask summary
7212649 Update SRR v2.5 rebuild start prompt
de20eef Strengthen SRR completion check task
c7a9557 Make failure overlay a pre-training gate
ce6692a Update SRR training ablation matrix with residual variants
7f735c9 Strengthen SRR training objectives ablation task
```

Diff from `51d4ef683012d876431b839692beadfa69e34961..HEAD`:

```text
A	images/SRR-v3.png
```

Current pre-audit git status:

```text
## main...origin/main
```

## 2. 17-Task Completion Check

See `task_completion_table.csv`.

Finding: the local result directories for `20260704_srr_v25_completion_check` and `20260704_cine_temporal_dictionary_integration` do not exist. They are required by both the subtask index and controller task. The controller report lists 15 executor/auditor rows, not all 17 tasks. Several other task directories exist but lack prompt-required detailed outputs beyond `result.md`/`MANIFEST.md`.

## 3. Full Fold0 Checkpoint Provenance

See `checkpoint_provenance.csv` and `checkpoint_provenance.md`.

Finding: full-fold0 evaluation used existing bounded 6-step CPU checkpoints (`actual_optimizer_steps=6`, `encoder_profile=tiny_3scale`, `train_cases=12`, `val_cases=4`) and expanded evaluation to 44 fold0 cases. This is eval-only evidence over bounded checkpoints, not adequate formal training.

## 4. Gate / Residual Near-Identity

See `gate_residual_stats.csv` and `gate_residual_diagnosis.md`.

Finding: bounded training logs record small gate means around `0.017986` for anchor-enabled rows, but full-fold0 eval does not export gate open-rate or bounded-delta distributions. Near-identity is consistent with the closed-biased residual gate and small residuals, but exact attribution remains `EVIDENCE_NOT_FOUND` for full eval gate/delta distributions.

## 5. Prototype Bank Audit

See `prototype_bank_audit.csv` and `prototype_bank_audit.md`.

Finding: full-fold0 source summaries show scar prototypes but `edema_positive=0` and `edema_negative=0` for primary prototype rows, and no-prototype row skips the bank. Therefore full eval did not actually test an edema prototype bank.

## 6. Baseline Preservation

See `baseline_preservation_audit.md`.

Finding: code path exists and no-anchor ablation proves anchor/gate necessity. It does not prove SRR beats nnU-Net.

## 7. Metrics

See `metric_summary.csv` and `metric_summary.md`.

Finding: all anchor-enabled rows are near identity / not meaningful under the `abs(mean Dice delta) < 0.005` threshold. No-anchor is strongly harmful.

## 8. Cine Branch

See `cine_status_audit.md`.

Finding: Cine remains `PASS_DIAGNOSTIC_WITH_REGISTRATION_GAP`. SyN smoke and untrained VoxelMorph adapter probe exist, but temporal dictionary integration is absent and full same-safe-subset temporal evidence is missing.

## 9. Conclusion

- `code path exists`: baseline-preserving residual gate, loss logging, prototype-bank plumbing, anatomy ROI/gates, proposal/refiner paths, and Cine registration probes have source or diagnostic evidence.
- `runtime smoke verified`: bounded short-run tests, full-fold0 eval-only metrics, SyN one-case smoke, and untrained VoxelMorph adapter smoke are present.
- `formal adequate training verified`: no. Existing full-fold0 rows use bounded 6-step checkpoints.
- `metric improvement verified`: no. Anchor-enabled SRR rows do not meaningfully beat nnU-Net; no-anchor is harmful.
- `SRR-v3 / full SRR-v2.5 completion`: not supported. Current packet remains diagnostic-only / needs evidence.
