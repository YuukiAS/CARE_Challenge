这次目标域病灶竞赛没有找到可继续推进的候选模型。唯一完成正式训练和外层评价的 M0 在 fold2/fold3 上相对 stock nnU-Net 下降，尤其是 edema 和 scar；M1/M2/M3 没有形成正式候选，原因分别是 CARE full-volume wrapper 未实现、官方 I-MMSEG 资产缺失、CARE-TDS 独立 heads/losses 未实现。下一步不应包装、上传或声称 leaderboard 改进，而应回到模型设计和资产补齐。

# Controller Report

- controller_verification_decision: `VERIFIED_COMPLETE`
- scientific_decision: `NO_GO_TARGET_DOMAIN_RACE`
- task_key: `20260801_care_target_domain_pathology_specialist_race`
- generated_at: `2026-08-01T03:19:28.238350+00:00`

## M0 Result

| fold | td class4 edema | stock class4 edema | delta | td class5 scar | stock class5 scar | delta | td foreground_mean | stock foreground_mean | delta |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| 2 | 0.484734 | 0.505825 | -0.021091 | 0.675649 | 0.700019 | -0.024370 | 0.748735 | 0.761083 | -0.012348 |
| 3 | 0.395639 | 0.443471 | -0.047833 | 0.581958 | 0.643922 | -0.061965 | 0.705677 | 0.738027 | -0.032349 |
| mean | 0.440186 | 0.474648 | -0.034462 | 0.628803 | 0.671971 | -0.043167 | 0.727206 | 0.749555 | -0.022349 |

## Lane Boundary

- M0 TD-NNUNET: fold2/fold3 completed 4000 optimizer steps each and full outer prediction/evaluation was run.
- M1 MYOPSNET-L-CARE: `PREFLIGHT_NEEDS_IMPLEMENTATION`; CARE-specific complete-trimodal MyoPS-Net-L full-volume training entrypoint is not yet implemented; old third_party code exists but cannot be used as formal race lane without wrapper repair.
- M2 I-MMSEG-CARE: `LANE_BLOCKED_EXTERNAL_ASSET`; Pinned official I_MMSeg source/assets are not present in the repository. The contract forbids replacing this lane with hand-crafted rank channels.
- M3 CARE-TDS: `PREFLIGHT_NEEDS_IMPLEMENTATION`; Independent scar/pure-edema/injury/boundary heads and direct-gradient losses are not yet implemented as a formal lane.

## Operational Notes

- Existing interactive allocation `61220581` was used after the user authorized serial fallback and extra Slurm jobs.
- Slurm job `61528800` completed fold3 training. Failed startup/eval attempts are recorded in `slurm_accounting.csv` and repaired by successful interactive reruns.
- No validation package, upload, hosted metric claim, route promotion, or remote branch publication is authorized by this packet.
