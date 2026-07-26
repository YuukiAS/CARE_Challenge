# CARE2026 validation leaderboard and local submission alignment - 2026-07-26

本记录把 2026-07-26 重新抓取的 CARE2026 myocardium leaderboard 三项结果，与当前 checkout 中可见的本地 validation package 记录对照。leaderboard 只暴露 `user/time/metric`，不暴露本地 package id；因此没有直接证据的映射保留为 unresolved。

## Fetch Evidence

- fetched_at_utc: `20260726T151647Z`
- latest json: `results/leaderboard/care2026_myocardium_latest.json`
- myops_scar: `results/leaderboard/care2026_myocardium_myops_scar_latest.csv` (85 rows)
- myops_edema: `results/leaderboard/care2026_myocardium_myops_edema_latest.csv` (85 rows)
- myocardium_cinemyops: `results/leaderboard/care2026_myocardium_myocardium_cinemyops_latest.csv` (62 rows)

## Current Leaderboard Top 5

### myops_scar

| rank | user | time | Dice | HD | PRE | SEN | score |
|---:|---|---|---:|---:|---:|---:|---:|
| 1 | ZQH | `2026-05-06 12:52:15` | 0.839 | 6.2775 | 0.8252 | 0.8563 | 0.839 |
| 2 | Monster | `2026-07-11 20:31:08` | 0.7323 | 14.7812 | 0.7148 | 0.7694 | 0.7323 |
| 3 | Monster | `2026-07-14 12:08:38` | 0.7322 | 14.7812 | 0.7147 | 0.7693 | 0.7322 |
| 4 | Monster | `2026-06-23 15:01:55` | 0.7239 | 15.3081 | 0.7195 | 0.7451 | 0.7239 |
| 5 | Monster | `2026-06-24 23:55:07` | 0.7237 | 15.3081 | 0.7192 | 0.7451 | 0.7237 |

### myops_edema

| rank | user | time | Dice | HD | PRE | SEN | score |
|---:|---|---|---:|---:|---:|---:|---:|
| 1 | ZQH | `2026-05-06 12:52:15` | 0.8536 | 8.6853 | 0.8575 | 0.8591 | 0.8536 |
| 2 | ZQH | `2026-06-09 16:51:25` | 0.7324 | 20.4347 | 0.7826 | 0.7229 | 0.7324 |
| 3 | ZQH | `2026-07-12 23:29:35` | 0.7322 | 19.7994 | 0.7887 | 0.7199 | 0.7322 |
| 4 | Monster | `2026-07-14 12:08:38` | 0.7217 | 21.5463 | 0.7174 | 0.7603 | 0.7217 |
| 5 | Sheffield_Heart | `2026-07-23 09:04:08` | 0.7215 | 22.5339 | 0.7687 | 0.7064 | 0.7215 |

### myocardium_cinemyops

| rank | user | time | Dice | HD | score |
|---:|---|---|---:|---:|---:|
| 1 | NCC1H | `2026-07-06 19:43:32` | 0.2634 | 40.1938 | 0.2634 |
| 2 | NCC1H | `2026-05-14 16:16:23` | 0.2594 | 38.1004 | 0.2594 |
| 3 | NCC1H | `2026-05-13 17:44:57` | 0.256 | 40.1528 | 0.256 |
| 4 | NCC1H | `2026-06-30 18:46:00` | 0.2533 | 40.0949 | 0.2533 |
| 5 | NCC1H | `2026-05-28 23:08:34` | 0.2533 | 40.1827 | 0.2533 |

## OrganAgent Hosted Rows

| leaderboard time | scar Dice/HD/rank | edema Dice/HD/rank | cine Dice/HD/rank | local assignment | confidence |
|---|---:|---:|---:|---|---|
| `2026-05-18 15:45:41` | 0.5969/16.2536/#74 | 0.6496/22.0125/#64 | 0.1748/75.213/#36 | nnUNet MyoPS + CineMyoPS pathology_direct | confirmed_by_local_readme |
| `2026-05-21 00:23:31` | 0.6258/14.9844/#63 | 0.6691/21.0898/#52 | 0.1816/52.9706/#35 | likely nnUNet 5-fold MyoPS + Cine topology_lcc calibration | likely_by_time_and_local_readme_not_direct_upload_receipt |
| `2026-06-03 23:04:15` | 0.6833/25.7857/#22 | 0.5897/32.6491/#77 | 0.1596/49.9538/#43 | unresolved; possible ensemble/SRR lineage, not provably MoSAIC from current local package records | unresolved |
| `2026-06-10 04:46:23` | 0.6841/25.8151/#20 | 0.6255/30.2965/#71 | 0.1996/49.3764/#25 | unresolved; cannot confirm MoSAIC from current local records | unresolved |
| `2026-06-23 12:20:22` | 0.6189/17.5332/#69 | 0.5532/23.5024/#83 | 0.2053/49.0281/#24 | unresolved; cannot confirm MoSAIC from current local records | unresolved |
| `2026-06-27 22:35:12` | 0.6475/15.5541/#50 | 0.5676/24.9973/#79 | 0.2069/48.7463/#22 | unresolved; cannot confirm MoSAIC from current local records | unresolved |
| `2026-07-06 09:13:49` | 0.6965/13.7827/#13 | 0.5983/26.7067/#74 | 0.1878/48.8241/#32 | unresolved; not locally confirmed as MoSAIC | unresolved |
| `2026-07-08 19:08:16` | 0.6965/13.7827/#14 | 0.5963/25.2403/#75 | 0.2058/46.6586/#23 | unresolved; not locally confirmed as MoSAIC | unresolved |

## Best Current OrganAgent Scores

| task | time | rank | Dice | HD | PRE | SEN | score |
|---|---|---:|---:|---:|---:|---:|---:|
| `myops_scar` | `2026-07-06 09:13:49` | 13 | 0.6965 | 13.7827 | 0.7 | 0.7478 | 0.6965 |
| `myops_edema` | `2026-05-21 00:23:31` | 52 | 0.6691 | 21.0898 | 0.6698 | 0.7351 | 0.6691 |
| `myocardium_cinemyops` | `2026-06-27 22:35:12` | 22 | 0.2069 | 48.7463 |  |  | 0.2069 |

## Local Upload-Ready Packages

| folder | MyoPS source | Cine source | zip sha256 |
|---|---|---|---|
| `20260517_reviewtest__nnUNet_reviewtest` | explicit | explicit | `054a3fdbf83709ba` |
| `20260518_030921__nnUNet_MyoPS+CineMyoPS_pathology_direct` | nnUNetv2_predict | CineMyoPS | `4907f1a39950f564` |
| `20260519_083839__nnUNet_MyoPS+CineMyoPS_pathology_direct_lcc_hd_repair` | explicit | explicit | `dc9eb7b503181f4f` |
| `20260519_084057__nnUNet_MyoPS+nnUNet_CineMyoPS_5fold_baseline_round8` | explicit | explicit | `d594a763577d235b` |
| `20260520_113408__nnUNet5fold_MyoPS+Cine_topology_lcc_round03_RECOMMENDED` | unchanged MyoPS branch from previous nnUNet_MyoPS+nnUNet_CineMyoPS_5fold_baseline_round8 package | topology_lcc | `5b0d4143e451bba9` |
| `20260726_nnunet5f_control__nnUNet5F-control` | explicit | explicit | `155b1997afc0ccde` |

## Interpretation

- 2026-05-18 row is locally confirmed as `20260518_030921`: nnUNet MyoPS fold0 plus CineMyoPS pathology_direct fold0.
- 2026-05-21 row is likely the `20260520_113408` nnUNet5fold MyoPS + Cine topology_lcc package, but this checkout lacks a direct hosted upload receipt.
- Later OrganAgent rows are real leaderboard rows, but current local upload manifests do not prove their package lineage. Do not claim they are MoSAIC without an external upload log or missing package record.
- This record performed no validation upload, no Docker upload, and no new Slurm allocation.

Machine-readable companion: `results/leaderboard/care2026_validation_submission_alignment_20260726.json`
