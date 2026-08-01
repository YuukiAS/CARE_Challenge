# MoSAIC Leaderboard Live Snapshot

This packet records a live CARE2026 myocardium leaderboard check for MoSAIC-related `OrganAgent` rows and the best non-abnormal second-place rows requested by the user.

## Source

- Fetch command: `env SSL_CERT_FILE=/users/a/e/aereinh/CARE/envs/env_CARE/lib/python3.12/site-packages/certifi/cacert.pem ./envs/env_CARE/bin/python scripts/leaderboard/fetch_care2026_scores.py`
- Fetch time from JSON: `20260801T013319Z`
- Source files:
  - `results/leaderboard/care2026_myocardium_latest.json`
  - `results/leaderboard/care2026_myocardium_myops_scar_latest.csv`
  - `results/leaderboard/care2026_myocardium_myops_edema_latest.csv`
  - `results/leaderboard/care2026_myocardium_myocardium_cinemyops_latest.csv`

## Interpretation Boundary

The `OrganAgent` row at `2026-07-28 16:08:05` for `myops_edema` scored `0.6607`, but the user identified this row as a local submission, not MoSAIC. It is therefore excluded from the MoSAIC-attributed result below.

For MoSAIC attribution, this snapshot uses the prior paper/workspace rule that `OrganAgent` submissions on or after `2026-06-01` may be treated as MoSAIC-related unless the user identifies a specific row as not MoSAIC. Older May `OrganAgent` rows are reported separately as all-OrganAgent evidence, not MoSAIC-attributed evidence.

## MoSAIC-Attributed Best Rows

These rows are `OrganAgent`, strictly before `2026-07-28 00:00:00`, and on or after `2026-06-01`.

| Task | Rank | Time | Dice/score | HD | PRE | SEN |
|---|---:|---|---:|---:|---:|---:|
| `myops_scar` | 16 | 2026-07-06 09:13:49 | 0.6965 | 13.7827 | 0.7000 | 0.7478 |
| `myops_edema` | 93 | 2026-06-10 04:46:23 | 0.6255 | 30.2965 | 0.7557 | 0.5760 |
| `myocardium_cinemyops` | 27 | 2026-06-27 22:35:12 | 0.2069 | 48.7463 | n/a | n/a |

## All OrganAgent Best Rows Before 2026-07-28

These rows answer the literal `OrganAgent before 2026-07-28` query without applying the MoSAIC date attribution boundary.

| Task | Rank | Time | Dice/score | HD | PRE | SEN |
|---|---:|---|---:|---:|---:|---:|
| `myops_scar` | 16 | 2026-07-06 09:13:49 | 0.6965 | 13.7827 | 0.7000 | 0.7478 |
| `myops_edema` | 66 | 2026-05-21 00:23:31 | 0.6691 | 21.0898 | 0.6698 | 0.7351 |
| `myocardium_cinemyops` | 27 | 2026-06-27 22:35:12 | 0.2069 | 48.7463 | n/a | n/a |

## Leaderboard Rank-2 Rows After Suspicious Rank-1

The public CSVs do not prove whether a rank-1 row is internal testing. The table below only reports the visible rank-2 row, plus the first row from a different user when rank 2 is the same user as rank 1.

| Task | Visible rank 1 | Visible rank 2 | First different-user row after rank 1 |
|---|---|---|---|
| `myops_scar` | ZQH, 0.8390 | Monster, 0.7323 | Monster, 0.7323 |
| `myops_edema` | ZQH, 0.8536 | ZQH, 0.7324 | MaJin, 0.7258 |
| `myocardium_cinemyops` | NCC1H, 0.2645 | NCC1H, 0.2645 | ZQH, 0.2336 |

## Conclusion

After excluding the user-identified local `2026-07-28` edema row, the current MoSAIC-attributed `myops_edema` best visible leaderboard score is `0.6255` from `2026-06-10 04:46:23`. The older `0.6691` row is the best literal all-OrganAgent-before-2026-07-28 edema row, but it predates the MoSAIC attribution boundary and should not be used as the MoSAIC paper number without separate provenance approval.
