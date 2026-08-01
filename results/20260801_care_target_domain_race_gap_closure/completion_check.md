# Completion Check

这轮不是“四个模型都失败”。四条 lane 都已完成 fold2/fold3 训练和 checkpoint reload 审计；后续 inner 全体积评价、global source freeze、outer deterministic replay 也已完成。科学上最诚实的结论是 scar-only candidate ready：scar 已经有可用本地候选，edema 仍不稳，不能包装成完整 target-domain candidate。

- controller_verification_decision: `VERIFIED_COMPLETE_PENDING_COMMIT_PUSH_NOTIFY`
- scientific_decision: `SCAR_ONLY_CANDIDATE_READY`
- validation_upload_authorized: `false`
- docker_upload_authorized: `false`
- hosted_metric_claim_authorized: `false`
- existing_interactive_job_id: `61220581`
- existing_interactive_partition: `htzhulab`
- existing_interactive_node: `g1807htzh01`
- old_M0_classification: `HIGH_LR_SHORT_FINETUNE_NEGATIVE`

## Lane Status

| lane | fold2/fold3 training | checkpoint audit | inner full-volume evaluation | best inner source |
|---|---:|---:|---:|---|
| M0R faithful control | complete, 4000 optimizer steps/fold, AdamW warmup-cosine | PASS | PASS | scar step3500, edema step4000 |
| M1 MyoPS-Net-L CARE | complete, 60 epochs/fold | PASS | PASS | weaker than M0R/M2 |
| M2 I-MMSeg CARE | complete, 60 epochs/fold; official source/assets used | PASS | PASS | second-best scar/edema, not selected |
| M3 CARE-TDS | complete, 4000 optimizer steps/fold | PASS | PASS | very weak pathology output, not selected |

## Frozen Sources

- global scar source: `m0r_faithful_control`, checkpoint step `3500`
- global edema source: `m0r_faithful_control`, checkpoint step `4000`
- source freeze evidence: `results/20260801_care_target_domain_race_gap_closure/inner_evaluation/global_source_selection.json`
- selection scope: fold2+fold3 inner only
- outer-driven selection: `false`

## Outer Replay

Outer deterministic replay used fold-specific stock anatomy plus frozen M0R scar and edema sources with fixed scar priority. It evaluated the complete fold2+fold3 outer set, including the sentinel cases `Case3008`, `Case3009`, `Case2019`, `Case2034`, and `Case2021`.

| pathology | outer case count | Dice mean | sensitivity mean | remote FP count |
|---|---:|---:|---:|---:|
| scar | 32 | 0.6500 | 0.7264 | 21 |
| pure edema | 32 | 0.4340 | 0.4124 | 13 |

Sentinel reading:

- `Case2019`: scar Dice `0.7651`, edema Dice `0.6764`; no remote FP for either pathology.
- `Case2034`: scar Dice `0.7747`, edema Dice `0.5533`; edema sensitivity is useful but volume is high.
- `Case2021`: scar Dice `0.7912`, edema Dice `0.5838`; this originally better case is not destroyed.
- `Case3009`: scar Dice `0.6840`, edema Dice `0.3173`; CenterC edema remains weak.
- `Case3008`: scar Dice `0.6170`, edema Dice `0.1581`, edema sensitivity `0.0885`; this is the main reason not to claim full target-domain candidate readiness.

## Terminal Accounting

- M1 lane job: `61576324 / htzhulab / COMPLETED / 0:0`
- M2 lane job: `61627615 / htzhulab / COMPLETED / 0:0`
- M3 interactive training: `61220581` steps complete
- M0R faithful rerun: `61220581` steps complete
- final required remaining operations: final validator, git commit, push to `origin/main`, remote SHA verification, valid completion `notification_brief.json`, notifier run, notifier receipt commit/push if generated
