# Leaderboard Lineage Timeline

当前证据说明，2026-05-21 的 OrganAgent edema 行更可信地对应历史 5-fold nnU-Net MyoPS 分支，而 2026-06-10 的 edema 行只能按既有日期规则归入 MoSAIC 相关候选，不能在本地确证为 exact hosted zip。

| time | row | local evidence | conclusion |
|---|---|---|---|
| 2026-05-19 08:40 local | `20260519_084057` package | `CARE-Myocardium-OrganAgent.zip` exists; manifest says MyoPS nnU-Net 5-fold; package SHA `d594a763577d235bdc1ccbb41479de22c647bcbecc1ef6e9a3125fc66d543e24` | historical nnU-Net MyoPS branch present |
| 2026-05-20 11:34 local | `20260520_113408` package | manifest says MyoPS copied from previous package and Cine changed to topology LCC | MyoPS unchanged; Cine branch changed |
| 2026-05-21 00:23:31 | OrganAgent hosted row | edema Dice 0.6691, HD 21.0898, PRE 0.6698, SEN 0.7351 | `NNUNET_EDEMA_PROVENANCE_UNRESOLVED` |
| 2026-06-10 04:46:23 | MoSAIC-attributed row | edema Dice 0.6255, HD 30.2965, PRE 0.7557, SEN 0.5760; exact local hosted zip unresolved | lower edema than 2026-05-21; attribution is not direct zip proof |

Direct upload receipt found: `False`.
