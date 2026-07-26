# CARE2026 validation leaderboard and local submission alignment - 2026-07-26

本记录把 2026-07-26 重新抓取的 CARE2026 myocardium leaderboard 三项结果，与当前 checkout 中可见的本地 validation package 记录对照。leaderboard 只暴露 `user/time/metric`，不暴露本地 package id；因此没有直接证据的映射保留为 unresolved。

## Fetch Evidence

- fetched_at_utc: `20260726T151647Z`
- latest json: `results/leaderboard/care2026_myocardium_latest.json`
- myops_scar: `results/leaderboard/care2026_myocardium_myops_scar_latest.csv` (85 rows)
- myops_edema: `results/leaderboard/care2026_myocardium_myops_edema_latest.csv` (85 rows)
- myocardium_cinemyops: `results/leaderboard/care2026_myocardium_myocardium_cinemyops_latest.csv` (62 rows)

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
