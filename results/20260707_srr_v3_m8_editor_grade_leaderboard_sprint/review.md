# M8 Independent Review

review_status: `M8_AUDITED_NO_PROMOTION_SCIENTIFIC_UNRESOLVED`

reviewed_packet: `results/20260707_srr_v3_m8_editor_grade_leaderboard_sprint`
reviewed_at_utc: `2026-07-08`
reviewer_role: `read_only_milestone_reviewer`

## Decision

M8 is accepted as a completed executor evidence packet, but it is not accepted as
a route-promotion, fold-expansion, validation-packaging, hosted-metric,
leaderboard-readiness, scientific-stop, or M9 authorization.

The executor cleared the main M8 adequacy gates: completed aggregate MyoPS
training budget, real long-run validation events, broad same-split MyoPS
candidate-control evidence, per-case SRR contribution export, mature Cine
registration/temporal-dictionary evidence, label/export QC, and fail-closed
validator self-tests. The scientific outcome remains unresolved because no local
candidate is selected for promotion and the same-split evidence does not show a
leaderboard-relevant improvement over the nnU-Net anchor control.

## Evidence Checked

- `m8_training_budget_ledger.csv` records four included MyoPS training runs with
  `28800.190` aggregate train-loop seconds. Independent `sacct` accounting
  confirmed jobs `58081023`, `58081024`, `58081007`, and `58105084` completed
  with exit `0:0`, each at about two hours wall time.
- `m8_validation_events.csv` contains `110` validation events; each formal
  training run has at least 20 validation events and far exceeds the 900-second
  probe threshold.
- `m8_architecture_gap_closure_table.csv` has 13 rows, all
  `CLOSED_WITH_RUNTIME_EVIDENCE`; no bare `CLOSED` status was found.
- `m8_variant_config_contract.json` defines the required three M8 variants with
  distinct loss weights, sampler quotas, dictionary slots, encoder profiles,
  decode thresholds, and safety rules. The training code contains
  `apply_variant_config_contract(...)`, and the validator checks the config
  contract for the three-variant/non-renamed condition.
- `m8_batch_composition.csv` has 215371 per-step rows across 56913 steps,
  including CenterB/CenterC, T2-present and no-T2 safety cases:
  `153353` T2-present rows, `153353` edema-positive rows, `62018` no-T2 safety
  rows, and `91447` remote-FP rows.
- `m8_srr_contribution_by_case.csv` has 144 rows over 24 cases, three variants,
  and both `myops_scar`/`myops_edema`. It includes non-placeholder anchor/final
  delta, gate-opening, weight, Dice/HD95/component/remote-FP fields and populated
  `source_prediction_path` values. Caveat: the legacy `source_path` column is
  empty for 72 rows, so future packets should avoid this ambiguity even though
  the prediction source path is present.
- `m8_formal_case_manifest.csv` covers 24 cases across CenterA/CenterB/CenterC,
  with both LGE-only and C0+LGE+T2 cases; it is not an easy-only formal subset.
- `m8_candidate_assembly_matrix.csv` compares all local candidates against the
  same-split nnU-Net anchor control, with label export status passing and
  no-T2 edema voxels equal to zero for candidate rows.
- `m8_best_variant_decision_table.csv` selects no candidate. Edema Dice is lower
  than the nnU-Net anchor for all candidates, and scar gains are small local
  same-split deltas only. This blocks route promotion and fold expansion.
- Cine evidence is no longer a smoke-only check: `m8_cine_case_manifest.csv`
  covers 12 usable cases, `m8_registration_same_subset_matrix.csv` has 24 pairs
  each for identity, SimpleITK Demons, and ANTsPy SyNOnly, and
  `m8_temporal_dictionary_evidence.csv` records 24
  `TEMPORAL_DICTIONARY_EXECUTED` rows. The Cine files correctly keep hosted
  `myocardium_cinemyops` readiness unclaimed.
- `m8_official_label_mapping_qc.csv`, `m8_export_dry_run_qc.md`, and
  `m8_label_export_dry_run_qc.md` record compact-to-official label checks and
  explicitly state that no validation package or upload was created.
- `m8_strict_validator_report.md` reports real-packet validation pass with
  `error_count=0`. `m8_validator_unit_test_report.md` has 17 self-test rows:
  one good fixture passes and 16 known-bad mutations fail closed, including
  under-budget, monitor-marked-ready, config-not-read, renamed-only variants,
  missing per-case contribution, easy-only eval, no-T2 violation, missing
  candidate assembly, Cine smoke/proxy-only, missing best selection, usable Cine
  registration without temporal dictionary, missing export QC, placeholder proof,
  and unauthorized upload claim.

## Scientific Interpretation

M8 is a real step up from the earlier short/monitor-only runs: it accumulated
the required eight hours of MyoPS train-loop budget and added broad MyoPS plus
Cine evidence. However, the measured candidate-control outcome is negative for
promotion:

- nnU-Net anchor control: `myops_edema` Dice `0.7114`, `myops_scar` Dice
  `0.5876`.
- Best local edema candidate: `0.7041`, below the anchor.
- Best local scar candidate: `0.5930`, only about `+0.0054` Dice and not paired
  with edema improvement.
- T2/CenterC-focused candidate improves some scar/HD95 fields locally but
  worsens edema and remote-FP/component behavior in several decode modes.
- Cine temporal dictionary evidence is executed and useful for closing the
  prior evidence gap, but it remains a local proxy evidence packet with explicit
  hosted-metric caveats.

Therefore this review does not authorize validation packaging, validation
upload, leaderboard claims, route promotion, fold expansion, or M9.

## Required Next State

Use this review as `M8_AUDITED_NO_PROMOTION_SCIENTIFIC_UNRESOLVED`.

Any next executor work should be GPT-planned as a new repair/decision milestone
or continued task. It should not proceed as automatic fold expansion from M8.
