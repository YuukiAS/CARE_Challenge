# CARE-ASE outer diagnostic comparison: step5000/4000 vs step12000/11000

本报告比较两次用户授权 outer diagnostic：旧结果是 fold2 step5000 + fold3 step4000，新结果是 fold2 step12000 + fold3 step11000。它是 held-out outer 诊断证据，不用于 checkpoint selection、threshold tuning、early stop 或训练参数修改。

## Main Dice changes

| group | split | cases | old CARE | new CARE | CARE change | old nnU-Net | new nnU-Net | nnU-Net change | old delta | new delta | delta change |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| all_outer_scar | fold2 | 44 | 0.529509 | 0.567347 | 0.037837 | 0.590782 | 0.590806 | 0.000024 | -0.061272 | -0.023459 | 0.037813 |
| all_outer_scar | fold3 | 44 | 0.372246 | 0.217733 | -0.154514 | 0.521763 | 0.521776 | 0.000013 | -0.149516 | -0.304043 | -0.154527 |
| all_outer_scar | combined | 88 | 0.450878 | 0.392540 | -0.058338 | 0.556272 | 0.556291 | 0.000019 | -0.105394 | -0.163751 | -0.058357 |
| complete_tri_modal_scar | fold2 | 16 | 0.704129 | 0.694271 | -0.009858 | 0.697969 | 0.698013 | 0.000044 | 0.006160 | -0.003742 | -0.009902 |
| complete_tri_modal_scar | fold3 | 16 | 0.654441 | 0.598765 | -0.055676 | 0.647050 | 0.647076 | 0.000026 | 0.007391 | -0.048311 | -0.055701 |
| complete_tri_modal_scar | combined | 32 | 0.679285 | 0.646518 | -0.032767 | 0.672510 | 0.672544 | 0.000035 | 0.006775 | -0.026026 | -0.032802 |
| partial_modality_scar | fold2 | 28 | 0.429727 | 0.494819 | 0.065092 | 0.529531 | 0.529544 | 0.000013 | -0.099805 | -0.034725 | 0.065079 |
| partial_modality_scar | fold3 | 28 | 0.210992 | 0.000000 | -0.210992 | 0.450170 | 0.450176 | 0.000006 | -0.239177 | -0.450176 | -0.210998 |
| partial_modality_scar | combined | 56 | 0.320360 | 0.247409 | -0.072950 | 0.489851 | 0.489860 | 0.000009 | -0.169491 | -0.242451 | -0.072960 |
| pure_edema_t2_present | fold2 | 16 | 0.507419 | 0.512826 | 0.005407 | 0.506598 | 0.506578 | -0.000020 | 0.000822 | 0.006249 | 0.005427 |
| pure_edema_t2_present | fold3 | 16 | 0.393242 | 0.448863 | 0.055621 | 0.443793 | 0.443799 | 0.000006 | -0.050551 | 0.005065 | 0.055616 |
| pure_edema_t2_present | combined | 32 | 0.450331 | 0.480845 | 0.030514 | 0.475196 | 0.475188 | -0.000007 | -0.024865 | 0.005657 | 0.030521 |

## CARE shape/recall diagnostics

| group | split | CARE sensitivity old->new | CARE precision old->new | CARE HD95 old->new | CARE volume ratio old->new | CARE empty pred old->new | help/harm/tie old->new |
|---|---:|---:|---:|---:|---:|---:|---:|
| complete_tri_modal_scar | fold2 | 0.737107->0.718927 (-0.018180) | 0.705321->0.707285 (0.001964) | 29.270756->28.118815 (-1.151941) | 1.176592->1.147635 (-0.028957) | 0.000000->0.000000 (0.000000) | 11/5/0->10/6/0 |
| complete_tri_modal_scar | fold3 | 0.663391->0.686016 (0.022624) | 0.738881->0.650981 (-0.087901) | 62508.375167->62509.723826 (1.348658) | 1.177537->1.252230 (0.074692) | 2.000000->0.000000 (-2.000000) | 8/8/0->6/9/1 |
| complete_tri_modal_scar | combined | 0.701438->0.703002 (0.001564) | 0.720983->0.679133 (-0.041850) | 31268.822962->31268.921320 (0.098359) | 1.177049->1.198245 (0.021196) | 2.000000->0.000000 (-2.000000) | 19/13/0->16/15/1 |
| partial_modality_scar | fold2 | 0.381458->0.483258 (0.101800) | 0.642905->0.597548 (-0.045357) | 71451.328652->71448.090834 (-3.237818) | 0.712842->0.924511 (0.211668) | 1.000000->1.000000 (0.000000) | 5/20/3->8/17/3 |
| partial_modality_scar | fold3 | 0.154877->0.000000 (-0.154877) | 0.713931-> () | 285736.829046->1000000.000000 (714263.170954) | 0.224688->0.000000 (-0.224688) | 8.000000->28.000000 (20.000000) | 2/24/2->0/26/2 |
| partial_modality_scar | combined | 0.261755->0.227952 (-0.033803) | 0.673129->0.597548 (-0.075581) | 178594.078849->535724.045417 (357129.966568) | 0.454950->0.436090 (-0.018860) | 9.000000->29.000000 (20.000000) | 7/44/5->8/43/5 |
| pure_edema_t2_present | fold2 | 0.482059->0.508124 (0.026064) | 0.634697->0.584648 (-0.050049) | 25.207658->33.880728 (8.673069) | 0.815729->0.877447 (0.061718) | 0.000000->0.000000 (0.000000) | 6/10/0->11/5/0 |
| pure_edema_t2_present | fold3 | 0.342850->0.419480 (0.076629) | 0.634391->0.577925 (-0.056467) | 62528.738438->28.339817 (-62500.398621) | 0.585583->0.794856 (0.209273) | 1.000000->0.000000 (-1.000000) | 6/10/0->9/7/0 |
| pure_edema_t2_present | combined | 0.412455->0.463802 (0.051347) | 0.634549->0.581286 (-0.053263) | 31276.973048->31.110272 (-31245.862776) | 0.700656->0.836152 (0.135495) | 1.000000->0.000000 (-1.000000) | 12/20/0->20/12/0 |

## Center complete tri-modal Dice changes

| group | split | cases | old CARE | new CARE | CARE change | old nnU-Net | new nnU-Net | nnU-Net change | old delta | new delta | delta change |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| centerB_complete_scar | fold2 | 7 | 0.719907 | 0.701409 | -0.018498 | 0.702761 | 0.702832 | 0.000071 | 0.017146 | -0.001423 | -0.018569 |
| centerB_complete_scar | fold3 | 7 | 0.617510 | 0.629544 | 0.012034 | 0.715274 | 0.715480 | 0.000206 | -0.097764 | -0.085936 | 0.011828 |
| centerB_complete_scar | combined | 14 | 0.668708 | 0.665477 | -0.003232 | 0.709017 | 0.709156 | 0.000139 | -0.040309 | -0.043679 | -0.003371 |
| centerC_complete_scar | fold2 | 9 | 0.691857 | 0.688719 | -0.003138 | 0.694243 | 0.694265 | 0.000023 | -0.002385 | -0.005546 | -0.003161 |
| centerC_complete_scar | fold3 | 9 | 0.683165 | 0.574826 | -0.108339 | 0.593987 | 0.593872 | -0.000115 | 0.089178 | -0.019047 | -0.108224 |
| centerC_complete_scar | combined | 18 | 0.687511 | 0.631772 | -0.055739 | 0.644115 | 0.644069 | -0.000046 | 0.043396 | -0.012296 | -0.055693 |
| centerB_complete_edema | fold2 | 7 | 0.608713 | 0.607091 | -0.001622 | 0.617819 | 0.617815 | -0.000003 | -0.009105 | -0.010724 | -0.001619 |
| centerB_complete_edema | fold3 | 7 | 0.438806 | 0.513604 | 0.074798 | 0.524348 | 0.524436 | 0.000088 | -0.085542 | -0.010832 | 0.074710 |
| centerB_complete_edema | combined | 14 | 0.523760 | 0.560348 | 0.036588 | 0.571083 | 0.571126 | 0.000042 | -0.047324 | -0.010778 | 0.036545 |
| centerC_complete_edema | fold2 | 9 | 0.428635 | 0.439509 | 0.010874 | 0.420093 | 0.420059 | -0.000033 | 0.008543 | 0.019450 | 0.010907 |
| centerC_complete_edema | fold3 | 9 | 0.357803 | 0.398509 | 0.040706 | 0.381140 | 0.381081 | -0.000059 | -0.023336 | 0.017428 | 0.040765 |
| centerC_complete_edema | combined | 18 | 0.393219 | 0.419009 | 0.025790 | 0.400616 | 0.400570 | -0.000046 | -0.007397 | 0.018439 | 0.025836 |

## Diagnostic no-T2 matched class-set comparison

This preserves the audit row where nnU-Net no-T2 cases are decoded with a class set matched to CARE-ASE no-T2 decode. It is diagnostic-only and does not replace the original direct-six-class nnU-Net headline.

| group | split | cases | old CARE | new CARE | CARE change | old matched nnU-Net | new matched nnU-Net | matched nnU-Net change | old delta | new delta | delta change |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| partial_modality_scar | fold2 | 28 | 0.429727 | 0.494819 | 0.065092 | 0.529547 | 0.529544 | -0.000003 | -0.099820 | -0.034725 | 0.065095 |
| partial_modality_scar | fold3 | 28 | 0.210992 | 0.000000 | -0.210992 | 0.450179 | 0.450176 | -0.000003 | -0.239187 | -0.450176 | -0.210989 |
| partial_modality_scar | combined | 56 | 0.320360 | 0.247409 | -0.072950 | 0.489863 | 0.489860 | -0.000003 | -0.169503 | -0.242451 | -0.072947 |

## Interpretation

- 上次 outer diagnostic 到 fold2 step5000 / fold3 step4000；这次是 fold2 step12000 / fold3 step11000。
- mixed scar headline 变差：combined CARE scar 0.450878 -> 0.392540，delta 从 -0.105394 变为 -0.163751。
- complete tri-modal scar 从轻微领先变为落后：combined delta +0.006775 -> -0.026026；主要由 fold3 complete scar 0.654441 -> 0.598765 拉低。
- partial/no-T2 scar 是最严重变化：combined CARE 0.320360 -> 0.247409；fold3 partial 0.210993 -> 0.000000，28/28 CARE empty prediction。
- edema 方向相反：combined CARE pure edema 0.450331 -> 0.480845，delta 从 -0.024865 变为 +0.005657；但 precision 仍下降，不能把这解释成整体胜出。
- 当前没有因为这次 outer 诊断发现新的实现性硬错误；它强化的是 Stage B/C 后 partial/no-T2 scar forgetting 与 fold3 泛化/competition 问题。formal training 应继续到 frozen 14000，不应据此中断或调参。

## Evidence

- `results/agent_flow_v3/care-ase-faithful-formal-training-20260812/outer_diagnostic_user_authorized/outer_diagnostic_step12000_11000_vs_step5000_4000_comparison.csv`
- `results/agent_flow_v3/care-ase-faithful-formal-training-20260812/outer_diagnostic_user_authorized/outer_diagnostic_step12000_11000_vs_step5000_4000_verification_receipt.json`
- `results/agent_flow_v3/care-ase-faithful-formal-training-20260812/outer_diagnostic_user_authorized/outer_diagnostic_step12000_11000_combined_summary.json`
- `results/agent_flow_v3/care-ase-faithful-formal-training-20260812/outer_diagnostic_user_authorized/outer_diagnostic_step12000_11000_subgroup_table.csv`
- `results/agent_flow_v3/care-ase-faithful-formal-training-20260812/outer_diagnostic_user_authorized/outer_diagnostic_step12000_11000_subgroup_summary.json`
