# M9 Commands Run

This file records the final commands needed to audit the completed M9 packet. Earlier live scheduler polling was superseded by the terminal Slurm accounting and final post-job aggregation below.

## Environment Sanity

```text
pwd
true
git status --short --branch
```

Observed checkout: `/users/a/e/aereinh/CARE` on `main`.

## Slurm Terminal Accounting

```text
sacct -j 58297510,58297807,58297806,58348646,58297511 --format=JobID,JobName,Partition,State,ExitCode,Elapsed,Start,End,NodeList -P
```

Relevant terminal states:

```text
58297510|M9SRRDict|htzhulab|COMPLETED|0:0
58297807|M9SRRDict|htzhulab|COMPLETED|0:0|02:03:52
58297806|M9SRRDict|htzhulab|COMPLETED|0:0|02:04:07
58348646|M9SRRDict|htzhulab|COMPLETED|0:0|02:03:33|2026-07-08T21:11:33|2026-07-08T23:15:06|g180702
58297511|M9CineOut|htzhulab|COMPLETED|0:0
```

Routing-race mirrors `58297196` and `58297197` were cancelled after the corresponding `htzhulab` jobs started or completed.

## Terminal Runtime Files

```text
find results/20260708_srr_v3_m9_dictionary_fidelity_repair_training/runtime_htzhulab_true_br2_pattern_sip/variants/m9_srr_main_true_br2_pattern_sip -maxdepth 1 -type f -printf '%f|%s|%TY-%Tm-%Td %TH:%TM:%TS\n' | sort
```

Key terminal files:

```text
summary.json|35069|2026-07-08 23:14:59.1517640000
training_log.csv|898504|2026-07-08 23:14:58.3284800000
validation_events.csv|5932|2026-07-08 23:14:58.3334420000
```

## Final Aggregation

```text
python scripts/evaluation/aggregate_srr_v3_m9_dictionary_fidelity_packet.py \
  --runtime-root results/20260708_srr_v3_m9_dictionary_fidelity_repair_training/runtime_htzhulab_mirror \
  --runtime-root results/20260708_srr_v3_m9_dictionary_fidelity_repair_training/runtime_htzhulab_lesion_memory \
  --runtime-root results/20260708_srr_v3_m9_dictionary_fidelity_repair_training/runtime_htzhulab_t2_edema_focus \
  --runtime-root results/20260708_srr_v3_m9_dictionary_fidelity_repair_training/runtime_htzhulab_true_br2_pattern_sip \
  --out-dir results/20260708_srr_v3_m9_dictionary_fidelity_repair_training
```

Observed output:

```text
wrote results/20260708_srr_v3_m9_dictionary_fidelity_repair_training/m9_training_budget_ledger.csv
```

## Final Validator Checks

```text
python scripts/evaluation/validate_srr_v3_m9_dictionary_fidelity_packet.py --self-test
python scripts/evaluation/validate_srr_v3_m9_dictionary_fidelity_packet.py results/20260708_srr_v3_m9_dictionary_fidelity_repair_training
git diff --check
```

Expected final validator output after this packet update:

```text
error_count=0
```

`git diff --check` must exit `0` with no output.

## Final Interpretation

- `m9_training_budget_ledger.csv` has six runtime rows.
- Aggregate train-loop seconds: `26415.268`.
- Formal SRR-main candidates with `>=7200` train-loop seconds: `3`.
- The alternate M9 training adequacy gate is satisfied.
- All selected metric-facing candidates remain negative against the M8 nnU-Net anchor.
- Final executor route decision: `M9_NO_PROMOTION_DIAGNOSTIC_ONLY`.
- Explicit safety boundary: no validation upload, no hosted metric claim, no fold expansion, no M10.
