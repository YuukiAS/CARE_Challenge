当前架构变化不能从“计划”推进为“已实现”：CARE-PRISM v2 的若干代码构件已经落到源码中，但它们仍停留在 partial/scaffold 状态，因为共享 ResEnc 主干没有同折 checkpoint 移植和 FP32 奇偶校验证据。科学含义是，这次结果只证明执行器正确地在训练前 fail-closed，没有证明 PRISM v2 机制有效或已完整接入；下一步必须先补齐合法 ResEnc checkpoint 或修改合同。

```text
task_key: 20260729_care_prism_fold0_fold1_v2
architecture_delta_scope: mapper_final_partial_w1
architecture_status_delta: planned/unverified -> partial/scaffold/unverified
verified_runtime_delta: none
training_delta: none
wiki_current_update_recommendation: keep_planned_unverified
```

## Delta Summary

| Area | Planned PRISM v2 target | Current partial source delta | Credited status |
|---|---|---|---|
| Shared encoder | Exact 3-channel same-fold nnU-Net ResEnc transplant with parity | `CAREPRISM` instantiates `ResidualEncoderUNet` encoder from ResEnc plan kwargs and enforces `[LGE,T2,C0]` input | partial/scaffold, unverified |
| Modality routing | Scar/edema pathology-specific soft retrieval with availability masking | `SoftRetrievalRouter` exists for scar and edema routes with shared floor and modality preference | partial/scaffold, unverified |
| Anatomy exchange | Stop-gradient one-way anatomy-to-pathology residual exchange | `AnatomyToPathologyExchange` uses `anatomy.detach()` and zero-initialized gate/projection | partial/scaffold, unverified |
| Proposal and negative space | Learned positive evidence, safe-negative logits, full-volume soft proposal attention | `PathologyRefiner` includes positive, negative, proposal, and attention paths | partial/scaffold, unverified |
| Full-volume soft cascade | Anatomy band and proposal attention retain whole volume, no hard crop | Model forward computes `0.25 + 0.75 * ...` anatomy/proposal factors | partial/scaffold, unverified |
| No-T2 behavior | Edema probability, mask, loss, and gradient exactly zero when T2 absent | Model/inference code gates edema probability and masks by T2 availability | partial/scaffold, unverified |
| Checkpoint completeness | Model, optimizer, scheduler, scaler, stage, step, sampler, augmentation RNG, prototype, hard-negative, contract hashes | `save_care_prism_checkpoint` stores these fields | partial/scaffold, unverified |
| Training/evaluation entrypoints | W2/W3/W4 executable path and strict validators | `model_parameter_report.json` records `scripts/training/run_care_prism.py`, `scripts/evaluation/evaluate_care_prism.py`, and `scripts/evaluation/validate_care_prism_packet.py` as missing | missing/unverified |

## Failed Precondition

The hard precondition for credit is not met:

- ResEnc plan evidence exists at `data/nnUNet/nnUNet_preprocessed/Dataset501_CAREMyoPS/nnUNetResEncUNetMPlans.json`.
- Same-fold ResEnc checkpoint candidates are empty in both `nnunet_asset_receipt.json` and `init_transplant_report.json`.
- Required byte coverage `>=0.90` is therefore not proven.
- Required FP32 encoder parity `<=1e-6` is therefore not proven.
- `implementation_validator_report.json` blocks W2/W3/W4.

Because this precondition failed before training and before formal intervention tests, the partial code cannot receive final-output-effect credit for router, anatomy exchange, proposal/negative attention, no-T2 exact zero, losses, checkpoint resume, or refinement behavior.

## Architecture State

```text
component_group: CARE-PRISM v2
current_status: partial/scaffold
evidence_status: unverified
implemented_credit: false
verified_credit: false
reason: W1 transplant/parity failed before training and before formal intervention evidence
```

`wiki/README.md` and `prompts/routes/handoffs/CURRENT.md` should remain planned/unverified. They should not be changed to implemented, verified, W2-ready, W3-ready, route-promoted, or scientifically resolved based on this partial W1 state.

## Boundary

This Mapper delta does not authorize training, Slurm submission, validation packaging, upload, reviewer approval, hosted metric claims, fold expansion, wiki advancement, `CURRENT.md` advancement, commit, push, or route promotion. It records only the architecture evidence state of the current partial W1 scaffold.
