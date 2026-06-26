# SRR Rescue Ablation Metrics Summary

## Matrix

| ablation | variant | edema GT+ Dice | edema GT+ HD95 | scar all Dice | scar all HD95 | job |
| --- | --- | ---: | ---: | ---: | ---: | --- |
| B0 | best_conditional_control | 0.1103 | 138.1377 | 0.0581 | 113.4492 | `20260621_anchor` |
| B1 | best_srr_recovered | 0.1928 | 97.7248 | 0.0923 | 127.0317 | `56315547` |
| B2 | late_fusion_no_dictionary | 0.0601 | 129.9965 | 0.0442 | 130.5623 | `56469952` |
| B3 | retrieval_no_sip_or_weak_sip | 0.1358 | 115.4910 | 0.0702 | 129.1230 | `56469990` |

## Interpretation

- `best_srr_recovered` is the strongest ablation by both edema GT-positive Dice and scar all-case Dice.
- `retrieval_no_sip_or_weak_sip` remains below the recovered SRR variant and has worse edema HD95/component burden.
- `late_fusion_no_dictionary` underperforms both recovered SRR and the previous conditional anchor, so dictionary retrieval is not rejected by this ablation.
- Absolute pathology Dice remains low and component/remote-FP burden remains high; selection is a fold0 route choice, not a production-ready model claim.
