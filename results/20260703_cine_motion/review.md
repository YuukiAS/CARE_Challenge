# Review 20260703 Cine Motion

audit_decision: AUDITED_GO
route_decision_recommendation: TEMPORAL_PROXY_SIGNAL_DIAGNOSTIC
promotion_recommendation: No hosted-metric promotion, validation-route promotion, fold expansion, packaging/upload, next-stage training, commit, or push is authorized by this review.

## Scope

Auditor role: separate read-only Codex auditor for `prompts/tasks/20260703_cine_motion.md` under controller task `prompts/tasks/20260703_hardmode_goal.md`.

Files reviewed include the required handoff rules, CARE overlay, medical-imaging deep-learning skill and reference, prior Cine/rescue selections, the current `results/20260703_cine_motion/` package, and `scripts/evaluation/cine_motion_hardmode_20260703.py`.

## Output And Manifest Audit

SUPPORTED: Required outputs exist under `results/20260703_cine_motion/`: `result.md`, `MANIFEST.md`, `resource_audit.md`, `safe_cases_used.csv`, `reference_frame_contract.md`, `motion_or_warp_metrics.csv`, `warp_sanity.csv`, `temporal_metrics_summary.md`, `case_metrics.csv`, `anatomy_prior_adapter_audit.md`, `failure_interpretation.md`, `command_transcript.md`, `summary_metrics.csv`, and `center_summary_metrics.csv`.

SUPPORTED: `MANIFEST.md` indexes the required task/result/review paths and required artifacts.

PARTIAL: The script also writes `motion_or_warp_summary.csv`; this extra file is present but not listed in `MANIFEST.md`. This is a small indexing gap, not a blocker for the required artifact set.

## Claim Ledger

SUPPORTED: Reference frame selection is stated. `reference_frame_contract.md` defines `frame0 / ED-like adapter t00` as the reference and states frame0/reference-only is a control, not temporal completion.

SUPPORTED: Non-reference frames enter both formal routes. `safe_cases_used.csv` records non-reference `flow_frame_indices` and multi-frame `descriptor_frame_indices`; the script reads non-reference adapter predictions, runs optical flow for `cine_deformable_or_feature_warp`, and builds descriptor-weighted temporal fusion for `cine_motion_descriptor_temporal_refiner`.

SUPPORTED: `cine_deformable_or_feature_warp` is correctly framed as a dense slice-wise optical-flow/feature-warp proxy with warp sanity. It is not claimed as validated registration.

SUPPORTED: `cine_motion_descriptor_temporal_refiner` is correctly framed as descriptor/temporal aggregation. It is not claimed as registration.

SUPPORTED: Local proxy metrics compare against reference control. `temporal_metrics_summary.md` reports reference myocardium/LV Dice `0.5626`/`0.7709`, optical-flow deltas `+0.0406`/`+0.0454`, and descriptor deltas `-0.0002`/`-0.0001`.

SUPPORTED: Required reporting includes 59 safe cases, 5 mismatch cases held out, runtime `63.17s`, warp sanity, frame-to-reference similarity, reference dominance, component count, HD95, volume ratio, center summaries, and hosted metric caveat.

SUPPORTED: The hosted `myocardium_cinemyops` metric is explicitly caveated as `evidence not found`; no validation upload or upload-ready package evidence is present or claimed.

PARTIAL: The optical-flow route has positive local anatomy-proxy signal, but the warp sanity is only a proxy and shows substantial folding proxy burden (`5335.4068` mean pixels; `jacobian_min_proxy_min` in `motion_or_warp_summary.csv` is negative). This supports diagnostic temporal-proxy signal only, not validated registration or challenge-facing promotion.

PARTIAL: The descriptor route genuinely uses non-reference frames, but it is reference-weighted (`mean descriptor reference weight 0.7414`, dominance rate `0.3559`) and does not improve the local proxy over reference control. It supports descriptor evidence and failure interpretation, not a promoted temporal route.

UNSUPPORTED: Validated registration completion is not supported. The executor correctly records it as `evidence not found`.

UNSUPPORTED: A learned pathology or scar target head is not supported. The CineMA source is myocardium/LV only and class 3 remains a scar sanity negative control.

UNSUPPORTED: Hosted challenge improvement is not supported because no validation package/upload or hosted evaluator result exists.

SUPPORTED: Forbidden actions were not evidenced in the reviewed package. `result.md` and `command_transcript.md` report no GPU job, network, upload, validation package, fold expansion, evaluator or label-mapping change, commit, or push; this audit did not perform those actions.

## Decision

The executor's route decision `TEMPORAL_PROXY_SIGNAL_DIAGNOSTIC` is supported as a local diagnostic result. The package satisfies the hardmode requirement to move beyond frame0/reference-only and translation-only by testing a non-reference optical-flow/feature-warp proxy and a descriptor temporal-refiner, with explicit caveats.

This review does not authorize validation packaging/upload, fold expansion, next-stage training, hosted metric claims, route promotion, commit, or push. Any continuation beyond diagnostic interpretation requires the controller/GPT planner path specified by `prompts/tasks/20260703_hardmode_goal.md`.
