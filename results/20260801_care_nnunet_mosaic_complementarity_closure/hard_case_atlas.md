# Hard-case bucket atlas index

这份索引只绑定已有 V4 atlas 路径和 OOF 分桶，不生成新的模型证据，也不把 no-GT validation 当成成功或失败病例。

| case_id | center | pathology | bucket | rank_within_bucket | nnunet_dice | mosaic_dice | dice_delta_mosaic_minus_nnunet | gt_positive | gt_voxels | gt_components | nnunet_pred_components | mosaic_pred_components | modality_pattern | existing_v4_atlas_path | visual_source_status |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Case3005 | CenterC | pure_edema | BOTH_FAIL | 1 | 0 | 0 | 0 | True | 3214 | 1 | 3 | 0 | LGE+T2+C0 |  | NO_EXISTING_V4_ATLAS |
| Case3043 | CenterC | pure_edema | BOTH_FAIL | 2 | 0 | 0 | 0 | True | 1056 | 9 | 2 | 0 | LGE+T2+C0 |  | NO_EXISTING_V4_ATLAS |
| Case3001 | CenterC | pure_edema | BOTH_FAIL | 3 | 0.0132943 | 0 | -0.0132943 | True | 3422 | 3 | 9 | 0 | LGE+T2+C0 |  | NO_EXISTING_V4_ATLAS |
| Case3027 | CenterC | pure_edema | BOTH_FAIL | 4 | 0.0241595 | 0 | -0.0241595 | True | 4900 | 1 | 2 | 0 | LGE+T2+C0 |  | NO_EXISTING_V4_ATLAS |
| Case3002 | CenterC | pure_edema | BOTH_FAIL | 5 | 0.120841 | 0 | -0.120841 | True | 5402 | 16 | 5 | 0 | LGE+T2+C0 |  | NO_EXISTING_V4_ATLAS |
| Case3045 | CenterC | pure_edema | BOTH_FAIL | 6 | 0.161046 | 0 | -0.161046 | True | 1278 | 13 | 8 | 0 | LGE+T2+C0 |  | NO_EXISTING_V4_ATLAS |
| Case3033 | CenterC | pure_edema | BOTH_FAIL | 7 | 0.165908 | 0 | -0.165908 | True | 1775 | 12 | 12 | 0 | LGE+T2+C0 |  | NO_EXISTING_V4_ATLAS |
| Case3044 | CenterC | pure_edema | BOTH_FAIL | 8 | 0.166125 | 0.1053 | -0.0608249 | True | 263 | 20 | 19 | 3 | LGE+T2+C0 |  | NO_EXISTING_V4_ATLAS |
| Case3038 | CenterC | pure_edema | BOTH_FAIL | 9 | 0.167788 | 0.0264569 | -0.141331 | True | 1585 | 33 | 12 | 2 | LGE+T2+C0 |  | NO_EXISTING_V4_ATLAS |
| Case2013 | CenterB | pure_edema | BOTH_FAIL | 10 | 0.175522 | 0 | -0.175522 | True | 639 | 15 | 5 | 0 | LGE+T2+C0 |  | NO_EXISTING_V4_ATLAS |
| Case2014 | CenterB | pure_edema | NNUNET_PROTECTS | 1 | 0.727273 | 0 | -0.727273 | True | 1890 | 5 | 5 | 0 | LGE+T2+C0 | results/20260730_care_failure_forensics_deep_research_packet/case_montages_v3/Case2014_v3_atlas.png | BOUND_EXISTING_V4_ATLAS |
| Case2010 | CenterB | pure_edema | NNUNET_PROTECTS | 2 | 0.721331 | 0 | -0.721331 | True | 1560 | 14 | 6 | 0 | LGE+T2+C0 | results/20260730_care_failure_forensics_deep_research_packet/case_montages_v3/Case2010_v3_atlas.png | BOUND_EXISTING_V4_ATLAS |
| Case2009 | CenterB | pure_edema | NNUNET_PROTECTS | 3 | 0.719324 | 0 | -0.719324 | True | 1955 | 6 | 8 | 0 | LGE+T2+C0 | results/20260730_care_failure_forensics_deep_research_packet/case_montages_v3/Case2009_v3_atlas.png | BOUND_EXISTING_V4_ATLAS |
| Case2001 | CenterB | pure_edema | NNUNET_PROTECTS | 4 | 0.693299 | 0 | -0.693299 | True | 2410 | 12 | 11 | 0 | LGE+T2+C0 | results/20260730_care_failure_forensics_deep_research_packet/case_montages_v3/Case2001_v3_atlas.png | BOUND_EXISTING_V4_ATLAS |
| Case2019 | CenterB | pure_edema | NNUNET_PROTECTS | 5 | 0.692992 | 0 | -0.692992 | True | 978 | 5 | 8 | 0 | LGE+T2+C0 | results/20260730_care_failure_forensics_deep_research_packet/case_montages_v3/Case2019_v3_atlas.png | BOUND_EXISTING_V4_ATLAS |
| Case2026 | CenterB | pure_edema | NNUNET_PROTECTS | 6 | 0.682453 | 0 | -0.682453 | True | 761 | 9 | 9 | 0 | LGE+T2+C0 | results/20260730_care_failure_forensics_deep_research_packet/case_montages_v3/Case2026_v3_atlas.png | BOUND_EXISTING_V4_ATLAS |
| Case2003 | CenterB | pure_edema | NNUNET_PROTECTS | 7 | 0.667165 | 0 | -0.667165 | True | 2280 | 8 | 4 | 0 | LGE+T2+C0 |  | NO_EXISTING_V4_ATLAS |
| Case2025 | CenterB | pure_edema | NNUNET_PROTECTS | 8 | 0.661555 | 0 | -0.661555 | True | 2007 | 3 | 8 | 0 | LGE+T2+C0 | results/20260730_care_failure_forensics_deep_research_packet/case_montages_v3/Case2025_v3_atlas.png | BOUND_EXISTING_V4_ATLAS |
| Case2015 | CenterB | pure_edema | NNUNET_PROTECTS | 9 | 0.659777 | 0 | -0.659777 | True | 2266 | 4 | 13 | 0 | LGE+T2+C0 | results/20260730_care_failure_forensics_deep_research_packet/case_montages_v3/Case2015_v3_atlas.png | BOUND_EXISTING_V4_ATLAS |
| Case2005 | CenterB | pure_edema | NNUNET_PROTECTS | 10 | 0.655874 | 0 | -0.655874 | True | 2521 | 26 | 6 | 0 | LGE+T2+C0 |  | NO_EXISTING_V4_ATLAS |
| Case3032 | CenterC | scar | BOTH_FAIL | 1 | 0 | 0 | 0 | False | 0 | 0 | 3 | 1 | LGE+T2+C0 |  | NO_EXISTING_V4_ATLAS |
| Case6008 | CenterF | scar | BOTH_FAIL | 2 | 0 | 0 | 0 | False | 0 | 0 | 6 | 1 | LGE+T2+C0 |  | NO_EXISTING_V4_ATLAS |
| Case7005 | CenterG | scar | BOTH_FAIL | 3 | 0 | 0 | 0 | False | 0 | 0 | 7 | 1 | LGE+T2+C0 |  | NO_EXISTING_V4_ATLAS |
| Case7006 | CenterG | scar | BOTH_FAIL | 4 | 0 | 0 | 0 | False | 0 | 0 | 16 | 1 | LGE+T2+C0 |  | NO_EXISTING_V4_ATLAS |
| Case6005 | CenterF | scar | BOTH_FAIL | 5 | 0 | 0 | 0 | True | 609 | 1 | 1 | 1 | LGE+T2+C0 |  | NO_EXISTING_V4_ATLAS |
| Case5001 | CenterE | scar | BOTH_FAIL | 6 | 0 | 0 | 0 | False | 0 | 0 | 3 | 1 | LGE+T2+C0 |  | NO_EXISTING_V4_ATLAS |
| Case5007 | CenterE | scar | BOTH_FAIL | 7 | 0 | 0 | 0 | False | 0 | 0 | 13 | 1 | LGE+T2+C0 |  | NO_EXISTING_V4_ATLAS |
| Case8021 | CenterH | scar | BOTH_FAIL | 8 | 0 | 0 | 0 | True | 60 | 1 | 0 | 1 | LGE+T2+C0 | results/20260730_care_failure_forensics_deep_research_packet/case_montages_v3/Case8021_v3_atlas.png | BOUND_EXISTING_V4_ATLAS |
| Case8028 | CenterH | scar | BOTH_FAIL | 9 | 0 | 0 | 0 | False | 0 | 0 | 5 | 1 | LGE+T2+C0 |  | NO_EXISTING_V4_ATLAS |
| Case8034 | CenterH | scar | BOTH_FAIL | 10 | 0 | 0 | 0 | True | 712 | 3 | 0 | 1 | LGE+T2+C0 |  | NO_EXISTING_V4_ATLAS |
| Case2009 | CenterB | scar | MOSAIC_RESCUES | 1 | 0.370286 | 0.739316 | 0.369031 | True | 987 | 1 | 3 | 1 | LGE+T2+C0 | results/20260730_care_failure_forensics_deep_research_packet/case_montages_v3/Case2009_v3_atlas.png | BOUND_EXISTING_V4_ATLAS |
| Case8016 | CenterH | scar | MOSAIC_RESCUES | 2 | 0.313695 | 0.632496 | 0.318801 | True | 1101 | 1 | 4 | 1 | LGE+T2+C0 |  | NO_EXISTING_V4_ATLAS |
| Case8007 | CenterH | scar | MOSAIC_RESCUES | 3 | 0.453521 | 0.659044 | 0.205523 | True | 1431 | 2 | 5 | 1 | LGE+T2+C0 |  | NO_EXISTING_V4_ATLAS |
| Case2002 | CenterB | scar | MOSAIC_RESCUES | 4 | 0.56027 | 0.748598 | 0.188328 | True | 998 | 2 | 5 | 1 | LGE+T2+C0 |  | NO_EXISTING_V4_ATLAS |
| Case5002 | CenterE | scar | MOSAIC_RESCUES | 5 | 0.228571 | 0.40197 | 0.173399 | True | 608 | 1 | 11 | 1 | LGE+T2+C0 |  | NO_EXISTING_V4_ATLAS |
| Case7002 | CenterG | scar | MOSAIC_RESCUES | 6 | 0.242 | 0.406417 | 0.164417 | True | 667 | 3 | 7 | 1 | LGE+T2+C0 |  | NO_EXISTING_V4_ATLAS |
| Case2017 | CenterB | scar | MOSAIC_RESCUES | 7 | 0.547059 | 0.692402 | 0.145343 | True | 810 | 1 | 2 | 1 | LGE+T2+C0 |  | NO_EXISTING_V4_ATLAS |
| Case3035 | CenterC | scar | MOSAIC_RESCUES | 8 | 0.447059 | 0.58587 | 0.138811 | True | 616 | 2 | 2 | 1 | LGE+T2+C0 |  | NO_EXISTING_V4_ATLAS |
| Case8020 | CenterH | scar | MOSAIC_RESCUES | 9 | 0.494778 | 0.61127 | 0.116492 | True | 941 | 1 | 2 | 1 | LGE+T2+C0 |  | NO_EXISTING_V4_ATLAS |
| Case3025 | CenterC | scar | MOSAIC_RESCUES | 10 | 0.588079 | 0.701926 | 0.113847 | True | 7858 | 1 | 2 | 1 | LGE+T2+C0 |  | NO_EXISTING_V4_ATLAS |
| Case3007 | CenterC | scar | NEAR_TIE | 1 | 0.61025 | 0.615149 | 0.00489928 | True | 3912 | 1 | 2 | 1 | LGE+T2+C0 |  | NO_EXISTING_V4_ATLAS |
| Case8035 | CenterH | scar | NEAR_TIE | 2 | 0.588312 | 0.594468 | 0.00615595 | True | 1450 | 1 | 1 | 1 | LGE+T2+C0 |  | NO_EXISTING_V4_ATLAS |
| Case2018 | CenterB | scar | NEAR_TIE | 3 | 0.642741 | 0.649444 | 0.00670346 | True | 1631 | 1 | 2 | 1 | LGE+T2+C0 |  | NO_EXISTING_V4_ATLAS |
| Case3020 | CenterC | scar | NEAR_TIE | 4 | 0.499558 | 0.49181 | -0.00774871 | True | 7151 | 4 | 1 | 1 | LGE+T2+C0 |  | NO_EXISTING_V4_ATLAS |
| Case3001 | CenterC | scar | NEAR_TIE | 5 | 0.56206 | 0.57045 | 0.00838973 | True | 3031 | 2 | 4 | 1 | LGE+T2+C0 |  | NO_EXISTING_V4_ATLAS |
| Case8006 | CenterH | scar | NEAR_TIE | 6 | 0.560872 | 0.545965 | -0.0149061 | True | 1190 | 3 | 8 | 1 | LGE+T2+C0 |  | NO_EXISTING_V4_ATLAS |
| Case8023 | CenterH | scar | NEAR_TIE | 7 | 0.455144 | 0.470472 | 0.015328 | True | 811 | 1 | 1 | 1 | LGE+T2+C0 |  | NO_EXISTING_V4_ATLAS |
| Case7009 | CenterG | scar | NEAR_TIE | 8 | 0.621955 | 0.639258 | 0.0173029 | True | 1392 | 1 | 2 | 1 | LGE+T2+C0 | results/20260730_care_failure_forensics_deep_research_packet/case_montages_v3/Case7009_v3_atlas.png | BOUND_EXISTING_V4_ATLAS |
| Case1015 | CenterA | scar | NEAR_TIE | 9 | 0.440196 | 0.461538 | 0.0213424 | True | 977 | 4 | 10 | 1 | LGE+T2+C0 |  | NO_EXISTING_V4_ATLAS |
| Case8019 | CenterH | scar | NEAR_TIE | 10 | 0.658802 | 0.627172 | -0.03163 | True | 437 | 1 | 1 | 1 | LGE+T2+C0 |  | NO_EXISTING_V4_ATLAS |
| Case7010 | CenterG | scar | NNUNET_PROTECTS | 1 | 1 | 0 | -1 | False | 0 | 0 | 0 | 1 | LGE+T2+C0 |  | NO_EXISTING_V4_ATLAS |
| Case3012 | CenterC | scar | NNUNET_PROTECTS | 2 | 0.826707 | 0 | -0.826707 | True | 2818 | 1 | 2 | 1 | LGE+T2+C0 | results/20260730_care_failure_forensics_deep_research_packet/case_montages_v3/Case3012_v3_atlas.png | BOUND_EXISTING_V4_ATLAS |
| Case2019 | CenterB | scar | NNUNET_PROTECTS | 3 | 0.818444 | 0 | -0.818444 | True | 345 | 1 | 1 | 1 | LGE+T2+C0 | results/20260730_care_failure_forensics_deep_research_packet/case_montages_v3/Case2019_v3_atlas.png | BOUND_EXISTING_V4_ATLAS |
| Case3036 | CenterC | scar | NNUNET_PROTECTS | 4 | 0.818232 | 0 | -0.818232 | True | 4108 | 1 | 1 | 1 | LGE+T2+C0 | results/20260730_care_failure_forensics_deep_research_packet/case_montages_v3/Case3036_v3_atlas.png | BOUND_EXISTING_V4_ATLAS |
| Case3017 | CenterC | scar | NNUNET_PROTECTS | 5 | 0.808207 | 0.0912586 | -0.716949 | True | 4834 | 1 | 1 | 1 | LGE+T2+C0 | results/20260730_care_failure_forensics_deep_research_packet/case_montages_v3/Case3017_v3_atlas.png | BOUND_EXISTING_V4_ATLAS |
| Case1042 | CenterA | scar | NNUNET_PROTECTS | 6 | 0.757377 | 0.0666667 | -0.69071 | True | 906 | 1 | 4 | 1 | LGE+T2+C0 |  | NO_EXISTING_V4_ATLAS |
| Case5006 | CenterE | scar | NNUNET_PROTECTS | 7 | 0.6808 | 0 | -0.6808 | True | 786 | 1 | 1 | 1 | LGE+T2+C0 | results/20260730_care_failure_forensics_deep_research_packet/case_montages_v3/Case5006_v3_atlas.png | BOUND_EXISTING_V4_ATLAS |
| Case1054 | CenterA | scar | NNUNET_PROTECTS | 8 | 0.689079 | 0.0213634 | -0.667716 | True | 2001 | 4 | 2 | 1 | LGE+T2+C0 | results/20260730_care_failure_forensics_deep_research_packet/case_montages_v3/Case1054_v3_atlas.png | BOUND_EXISTING_V4_ATLAS |
| Case1056 | CenterA | scar | NNUNET_PROTECTS | 9 | 0.70603 | 0.0423107 | -0.663719 | True | 5053 | 6 | 5 | 1 | LGE+T2+C0 |  | NO_EXISTING_V4_ATLAS |
| Case1005 | CenterA | scar | NNUNET_PROTECTS | 10 | 0.697007 | 0.039051 | -0.657956 | True | 3381 | 1 | 1 | 1 | LGE+T2+C0 | results/20260730_care_failure_forensics_deep_research_packet/case_montages_v3/Case1005_v3_atlas.png | BOUND_EXISTING_V4_ATLAS |
