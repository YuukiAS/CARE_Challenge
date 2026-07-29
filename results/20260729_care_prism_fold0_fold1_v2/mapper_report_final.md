当前 CARE-PRISM v2 只能判为部分骨架，不能判为已经实现或可训练的机制路线：代码里已经出现了若干 PRISM v2 组件雏形，但训练前最关键的同折 ResEnc 强初始化没有证据成立，W1 在 transplant/parity 门前失败关闭。因此下一步不是评价模型好坏，而是先补齐合法同折 ResidualEncoderUNet checkpoint，或由 Planner 明确修改移植合同；在此之前 W2/W3/W4、验证上传、hosted metric claim 和 root wiki 状态推进都不被授权。

```text
mapper_id: care_prism_v2_mapper
task_key: 20260729_care_prism_fold0_fold1_v2
mapper_decision: ARCHITECTURE_PARTIAL_SCAFFOLD_UNVERIFIED
component_status: partial/scaffold
evidence_status: unverified
blocking_precondition: same-fold ResEnc checkpoint transplant and FP32 encoder parity
reviewer_decision: NOT_MADE_BY_MAPPER
validation_upload_authorized: false
wiki_current_advance_authorized: false
```

## Evidence Read

Required protocols and task state read:

- `AGENTS.md`
- `.agents/skills/care-mapper/SKILL.md`
- `.agents/skills/slurm-routing-partition/SKILL.md`
- `prompts/tasks/20260729_care_prism_execution_hardening_amendment_v2.md`
- `prompts/tasks/20260729_care_prism_fold0_fold1_executor_plan_v2.yaml`
- `prompts/routes/handoffs/CURRENT.md`
- `wiki/README.md`
- `results/20260729_care_prism_fold0_fold1_v2/controller_packet.json`
- `results/20260729_care_prism_fold0_fold1_v2/implementation_validator_report.json`

Additional lightweight result evidence read:

- `results/20260729_care_prism_fold0_fold1_v2/nnunet_asset_receipt.json`
- `results/20260729_care_prism_fold0_fold1_v2/init_transplant_report.json`
- `results/20260729_care_prism_fold0_fold1_v2/model_parameter_report.json`
- `results/20260729_care_prism_fold0_fold1_v2/implementation_intervention_report.json`
- `results/20260729_care_prism_fold0_fold1_v2/known_bad_report.json`
- `results/20260729_care_prism_fold0_fold1_v2/unit_test_report.json`
- `results/20260729_care_prism_fold0_fold1_v2/strict_validator_report.json`
- `results/20260729_care_prism_fold0_fold1_v2/implementation_snapshot.md`
- `results/20260729_care_prism_fold0_fold1_v2/controller_report.md`
- `results/20260729_care_prism_fold0_fold1_v2/completion_check.md`

Source files inspected:

- `src/care_myocardium/models/care_prism.py`
- `src/care_myocardium/training/care_prism_trainer.py`
- `src/care_myocardium/data/care_prism_dataset.py`
- `src/care_myocardium/inference/care_prism_predictor.py`

No raw data, NIfTI, checkpoint, large runtime tree, Slurm command, training command, upload package, reviewer file, or git push was inspected or executed by this Mapper.

## Blocking Finding

The ResEnc architecture plan exists, but same-fold ResEnc checkpoint evidence is missing. This means shared encoder transplant and source-vs-transplanted FP32 per-scale parity are not verified.

Concrete evidence:

- `results/20260729_care_prism_fold0_fold1_v2/nnunet_asset_receipt.json` records `resenc_plans_path` as `data/nnUNet/nnUNet_preprocessed/Dataset501_CAREMyoPS/nnUNetResEncUNetMPlans.json`, but `same_fold_resenc_checkpoint_candidates` is empty and status is `NOT_LOCATED_UNDER_Dataset501_CAREMyoPS_nnunet_results`.
- `results/20260729_care_prism_fold0_fold1_v2/init_transplant_report.json` records `status: FAIL`, `same_fold_resenc_checkpoint_candidates: []`, `required_byte_coverage_min: 0.9`, and `required_fp32_parity_max_abs: 1e-06`.
- `results/20260729_care_prism_fold0_fold1_v2/implementation_validator_report.json` records `W1_FAIL_CLOSED`, `status: FAIL`, `w2_allowed: false`, `w3_allowed: false`, and `w4_allowed: false`.
- `results/20260729_care_prism_fold0_fold1_v2/controller_packet.json` records `controller_verification_decision: OPERATIONALLY_BLOCKED`, `experiment_adequacy_decision: NO_TRAINING_STARTED_ZERO_FORMAL_CREDIT`, and `contract_compliance_status: FAIL_CLOSED_ON_REQUIRED_TRANSPLANT_ASSET`.

This is an execution/init precondition failure, not a trained mechanism failure. PlainConv checkpoint substitution is explicitly rejected by `init_transplant_report.json`, `implementation_validator_report.json`, and `known_bad_report.json`.

## Partial Code Mechanisms Present

These mechanisms appear as source-level scaffold or partial wiring, but are not credited as verified because W1 transplant/parity failed before formal intervention tests and before training.

| Mechanism | Source evidence | Mapper status | Evidence status | Reason |
|---|---|---:|---:|---|
| Exact 3-channel input policy | `CAREPRISMConfig.input_channels`, `CAREPRISM.input_channel_order`, and forward input checks in `src/care_myocardium/models/care_prism.py` | partial/scaffold | unverified | Code requires `[B,3,D,H,W]` and masks missing channels, but parity against transplanted same-fold source encoder is missing. |
| ResEnc plan instantiation | `CAREPRISMConfig.from_resenc_plans`, `nnunet_arch_kwargs`, `build_source_resenc` in `src/care_myocardium/models/care_prism.py` | partial/scaffold | unverified | Plan exists; checkpoint asset needed for strong initialization is absent. |
| Soft retrieval router | `SoftRetrievalRouter` and scar/edema router lists in `src/care_myocardium/models/care_prism.py` | partial/scaffold | unverified | Router code returns routed features and weights, but intervention report marks `router_changes_features_and_final_logits` as `NOT_CREDITED_PRECONDITION_FAILED`. |
| Stop-gradient anatomy exchange | `AnatomyToPathologyExchange.forward(... anatomy.detach())` and scar/edema exchange modules in `src/care_myocardium/models/care_prism.py` | partial/scaffold | unverified | Code suggests one-way anatomy-to-pathology exchange, but gradient isolation and final-logit effect are not credited. |
| Proposal and negative heads | `PathologyRefiner.positive_head`, `negative_head`, `proposal_head`, `proposal_attention` in `src/care_myocardium/models/care_prism.py` | partial/scaffold | unverified | Heads are present, but proposal/negative intervention evidence is blocked by missing transplant. |
| Full-volume continuous attention | `anatomy_band = 0.25 + 0.75 * ...` and `proposal_attention = 0.25 + 0.75 * sigmoid(...)` in `src/care_myocardium/models/care_prism.py` | partial/scaffold | unverified | Code avoids hard crop in inspected PRISM model, but output-effect evidence is not credited. |
| No-T2 edema probability mask | T2 gating in model forward and `decode_care_prism_outputs` / `predict_with_tta` in inference helper | partial/scaffold | unverified | Code zeros edema probability/mask for no-T2 paths, but no-T2 probability/mask/loss/gradient exact-zero is not formally credited. |
| Checkpoint fields | `save_care_prism_checkpoint` in `src/care_myocardium/training/care_prism_trainer.py` | partial/scaffold | unverified | Model/optimizer/scheduler/scaler/stage/step/sampler/RNG/prototype/hard-negative/contract fields are present, but resume exactness is not tested or credited. |
| Synthetic W1 fixtures | `CAREPRISMSyntheticDataset` and `synthetic_w1_batch` in `src/care_myocardium/data/care_prism_dataset.py` | scaffold | unverified | Fixture support exists only for deterministic W1 smoke context; `unit_test_report.json` says no formal tests were run after fail-closed. |

## Not Credited

The following required PRISM v2 mechanisms must not be counted as implemented or verified in this partial W1 state:

- Shared encoder byte transplant coverage `>=0.90`.
- FP32 source-vs-transplanted encoder per-scale parity `<=1e-6`.
- Router causal effect on final logits.
- Anatomy exchange final-logit effect and pathology-gradient blocking.
- Proposal/negative/full-volume attention causal effect on final logits.
- Formal loss finite/nonnegative gradient evidence.
- No-T2 edema probability, mask, loss, and gradient exact-zero proof.
- Complete checkpoint/resume equivalence.
- W2 real-case 400-step preflight.
- W3 fold0 development training or W4 fold1 clean training.
- Any hosted metric, validation upload, route promotion, or final scientific decision.

## Wiki And CURRENT Status

`wiki/README.md` already records `latest_verified_runtime: CARE-ARC W3 terminal diagnostic complete; PRISM v2 planned, unimplemented` and `route_status: MAIN_ONLY_PRISM_V2_PLANNED_UNVERIFIED`. `prompts/routes/handoffs/CURRENT.md` records CARE-PRISM v2 as the active planned line and preserves upload/hosted-claim/fold1-boundary restrictions.

Mapper final recommendation: root wiki and `CURRENT.md` should remain planned/unverified. They should not be advanced to implemented, verified, W2-ready, W3-ready, or scientifically resolved from this partial W1 scaffold.

## Final Mapper Conclusion

CARE-PRISM v2 has source-level partial/scaffold components, but the architecture evidence state is unverified. The controlling blocker is missing same-fold Dataset501 ResidualEncoderUNet checkpoint evidence for required transplant and FP32 parity. Until that precondition is repaired or the contract is explicitly revised, no PRISM v2 mechanism receives final-output-effect credit and no downstream training or challenge-facing action is authorized.
