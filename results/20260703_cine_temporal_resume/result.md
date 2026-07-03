# Result Cine Temporal Resume

self_assessed_status: EXECUTED_UNAUDITED
route_decision: TEMPORAL_PROXY_SIGNAL_DIAGNOSTIC
experiment_adequacy_decision: PARTIAL
route_promotion_decision: NO_PROMOTION
route_negative_decision: STOP_NOT_SUPPORTED
scientific_resolution_status: SCIENTIFIC_UNRESOLVED
domain_evidence_label: PARTIAL_MECHANISM_INCOMPLETE

## Execution Summary

- Evaluated `59` safe CineMyoPS cases and held out `5` mismatch cases.
- Completed baseline `cine_reference_control_recheck`.
- Completed `cine_deformable_or_feature_warp` as dense slice-wise optical-flow/feature-warp proxy with warp sanity.
- Completed `cine_motion_descriptor_temporal_refiner` as descriptor/temporal aggregation proxy.
- No GPU job, network, upload, validation package, fold expansion, evaluator change, or label mapping change was performed.

## Key Metrics

- reference myocardium Dice / LV Dice: `0.5626` / `0.7709`
- optical-flow myocardium Dice delta / LV Dice delta: `0.0406` / `0.0454`
- descriptor myocardium Dice delta / LV Dice delta: `-0.0002` / `-0.0001`
- descriptor mean reference weight / dominance rate: `0.7414` / `0.3559`
- optical-flow folding proxy mean pixels / smoothness mean: `5335.4068` / `0.2203`

## Claims

claim.reference_frame_contract: frame0 is the reference-control frame, selected from prior safe geometry evidence and used only as a baseline.
claim.nonreference_route: non-reference frames enter both the optical-flow feature-warp route and the descriptor temporal-refiner route.
claim.local_proxy_only: all reported metrics are local safe-subset proxies; hosted `myocardium_cinemyops` evidence is not present.
claim.no_forbidden_actions: no validation upload/package, fold expansion, evaluator/label mapping change, network download, commit, or push was performed.

## Files Read

- `AGENTS.md`
- handoff protocol files under `prompts/`
- `.agents/skills/agent-task-executor/SKILL.md`
- `.agents/skills/domains-medical-imaging-medical-imaging-deep-learning/SKILL.md` and `references/reference.md`
- `prompts/tasks/20260703_cine_temporal_resume.md`
- `prompts/CONTROLLER_TASK_PROTOCOL.md`
- `prompts/EXPERIMENT_ADEQUACY_GATE.md`
- `prompts/DIAGNOSTIC_PUBLICATION_GATE.md`
- `prompts/CARE_OVERLAY_GATES.md`
- `results/20260703_srr_formal_training/review.md`
- `results/20260703_cine_motion/result.md` and `review.md`
- prior Cine result files under `results/20260625_cine_geometry/`, `results/20260629_cine_motion_alignment/`, `results/20260629_cine_motion_pathology/`, and `results/cinema_adapter/`
- current controller report and selected MyoPS reviews under `results/20260703_hardmode_goal/` and `results/20260703_myops_*`

## Files Changed

- `scripts/evaluation/cine_motion_hardmode_20260703.py`
- `results/20260703_cine_temporal_resume/*`

## Commands

- `/users/a/e/aereinh/CARE/envs/env_CARE/bin/python scripts/evaluation/cine_motion_hardmode_20260703.py --output-dir results/20260703_cine_temporal_resume --task-key 20260703_cine_temporal_resume --controller-task-key 20260703_mainline_resume_goal` -> exit `0`, elapsed `102.25s`

## Incomplete Evidence

- independent audit: `evidence not found` in this executor session; review is required separately.
- hosted `myocardium_cinemyops`: `evidence not found` because upload/package generation was forbidden.
- learned target pathology head: `evidence not found`; source CineMA prior has no scar head.
- validated registration: `evidence not found`; optical flow is a proxy with warp sanity, and descriptor route is not registration.

## Blocked Actions

- validation packaging/upload remains blocked.
- fold expansion remains blocked.
- hosted metric claims remain blocked.
- label/evaluator/fold split changes remain blocked.
- next-stage training remains blocked unless a later GPT-authored task explicitly authorizes it.
