# Four-lane Scientific Interpretation

这次重新核对后，旧的 scar-only 候选结论不能直接保留。M0R 在真正未见的 fold2+fold3 outer 病例上没有超过同病例 stock nnU-Net；M2 补做 outer 后也没有达到预设的候选门槛。因此当前最稳妥的判断是撤销本地候选，把四条 lane 归档为已经纠偏但没有可打包候选；下一步应回到 Planner，而不是继续调阈值、重训、上传验证集或声称 hosted 指标。

## Decision

scientific_decision: `FOUR_LANE_EVIDENCE_CORRECTED_NO_CANDIDATE`
old_decision_superseded: `SCAR_ONLY_CANDIDATE_READY`

## Same-case Stock Comparison

| pathology | stock Dice | M0R Dice | M0R-stock Dice | stock HD95 mm | M0R HD95 mm | M0R-stock HD95 mm |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| scar | 0.673016 | 0.671004 | -0.002012 | 19.208503 | 19.605292 | 0.396789 |
| pure_edema | 0.465825 | 0.435711 | -0.030114 | 19.713855 | 22.099011 | 2.385156 |

M0R scar harmed 9/32 scar-positive outer rows under the predefined help/harm rule. Its inner 0.888/0.792 selection numbers are contaminated development evidence because the fold-specific stock checkpoints had seen the inner-selection cases during their original training.

## M2 Gate

| pathology | gate_pass | Dice delta | HD95 delta mm | sensitivity delta | precision delta | harm fraction |
| --- | --- | ---: | ---: | ---: | ---: | ---: |
| scar | False | -0.050115 | -1.789972 | -0.056336 | -0.038034 | 0.593750 |
| pure_edema | False | 0.018926 | -1.305211 | 0.089306 | -0.039616 | 0.468750 |

## M1/M3 Fidelity

M1 is classified as `M1_IMPLEMENTATION_NEGATIVE_NOT_SCIENTIFIC` because the CARE adapter uses pinned MyoPS-Net pieces but keeps a hard argmax anatomy mask and lacks the full official CMFF/MPC/pathology-inclusiveness contract, lesion-balanced sampling, augmentation, and full-volume training semantics.

M3 is classified as `M3_IMPLEMENTATION_NEGATIVE_NOT_SCIENTIFIC` because the current code freezes the stock adapter and adds shallow BCE heads with limited containment losses; it does not implement the blueprint's Dice/Focal/component-Tversky/MIL/remote-FP/boundary-distance loss stack or hard-negative loss path.
