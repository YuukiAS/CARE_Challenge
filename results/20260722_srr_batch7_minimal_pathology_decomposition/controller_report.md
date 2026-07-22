# Controller Evidence Report

report_role: executor_evidence_for_controller
controller_verification_decision: READY_FOR_CONTROLLER_VERIFICATION

## Practical Judgment

本次六组 matched 实验证明轻量分解链路已经可运行、可聚合、可验证，但没有产生可保留的 pathology proposal 机制。Scar 明显失败；edema 虽有小幅提升，但未达到 minimal 保留门，因此不能作为后续 Batch8/refiner/gate 的授权依据。

## Terminal Runtime

- Scar winner: job `59992434`, `htzhulab`, `g180702`, `COMPLETED`, `0:0`, `00:18:16`.
- Edema winner: job `59994167`, `htzhulab`, `g180702`, `COMPLETED`, `0:0`, `00:25:18`.
- No a100 edema mirror was started because the htzhulab edema job began immediately.
- Scar a100 preflight mirror `59979732` was controller-cancelled after htzhulab preflight success.

## Acceptance Evidence

- Six experiments completed 400 optimizer-step budgets and 44-case evaluations at configured checkpoints.
- `matched_run_manifest.csv` marks all six rows `TERMINAL_AGGREGATED_PASS`.
- no-SIP/SIP pairs share warmup state and sampler sequence; the explicit pair difference is `loss_br2_selective_integration_penalty_weight`.
- `sip_weight_calibration.csv` selected `0.005` for scar and `0.005` for edema using train-only center-balanced calibration.
- `pathology_decision_matrix.csv` records all required terminal decisions.

## Decisions

- `scar_minimal`: `RETIRE`
- `scar_br2`: `NOT_APPLICABLE`
- `scar_sip`: `NOT_APPLICABLE`
- `edema_minimal`: `RETIRE`
- `edema_br2`: `NOT_APPLICABLE`
- `edema_sip`: `NOT_APPLICABLE`

## Unauthorized Scope

No Batch8, old M10 dictionary/prototype/memory continuation, refiner, arbiter, production gate, Cine, fold expansion, validation upload, hosted metric claim, route promotion, or final scientific stop was started.
