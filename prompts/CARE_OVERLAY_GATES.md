# CARE Overlay Gates

This file is the CARE-specific overlay for GPT-Codex handoff tasks. It does not replace the Bridge Kit protocol or the shared medical-imaging skill.

Source-of-truth layering:

1. Bridge Kit handoff protocol: roles, state machine, task/result/review/controller report fields, review_required, promotion gates, and commit/push authorization.
2. `medical-imaging-deep-learning` skill: generic medical-imaging deep-learning mechanism gates, including U-Net-like segmentation, registration/warping, cine temporal modeling, missing-modality handling, external adapters, and proposal/refinement/cascade completion standards. Use `.agents/skills/domains-medical-imaging-medical-imaging-deep-learning/SKILL.md` and upstream `AI_Skills_Collection/skills/domains/medical-imaging/medical-imaging-deep-learning/` as the source of truth.
3. CARE overlay: CARE Challenge-specific leaderboard, label/export, T2-edema, CineMyoPS, controller, submission, and historical failure-escalation constraints.

If a generic mechanism rule conflicts with this file, the skill owns the generic method standard and this file owns only the CARE-specific challenge contract. Record the conflict in the task result or review instead of silently overriding it.

## 1. CARE Leaderboard Contract

- MyoPS primary objectives are `myops_scar` and `myops_edema`.
- CineMyoPS primary objective is `myocardium_cinemyops`, or an explicitly caveated local proxy when hosted validation is not run.
- Do not treat myocardium, LV, RV, foreground mean, or compact-label sanity metrics as the primary challenge objective.
- The validation package is one zip that returns three hosted metrics. Do not plan or report three separate uploads for the three metrics.

## 2. CARE Label And Export Contract

- Distinguish raw labels from compact labels in every model, metric, export, and review task.
- Submission/export must preserve the correct raw label mapping. A compact-label fold0 proxy gain is not automatically a challenge improvement.
- State the evaluator, decode mode, export path, and label remapping path or code path when claiming challenge-facing progress.

## 3. CARE T2-Edema Contract

- No-T2 cases must not be used as edema dense hard negatives.
- Edema results must report all-case, T2-present/complete, GT-positive, and no-T2 empty-GT stability slices when applicable.
- Report CenterB/CenterC behavior when the task or result touches center-specific generalization.
- Any route that treats missing-T2 samples as edema negatives must be blocked or marked `CONTRADICTED` by the auditor.

## 4. CARE Cine Contract

- Cine temporal tasks must state the reference frame, how non-reference frames enter the model, the motion/warping/aggregation/consistency route, and whether the target head exists.
- A frame0/reference-only anatomy prior is only a baseline or proxy. It is not temporal-method completion.
- If a motion descriptor is used, call it a descriptor route. Do not report it as completed registration unless the registration/warping gate from the skill is satisfied.

## 5. CARE Controller Contract

- A CARE execution controller may only orchestrate subtasks inside a GPT-authored controller task.
- The controller must not choose a new scientific route. If SRR, proposal, registration, or Cine evidence requires a new direction, write `NEEDS_GPT_PLANNER` and stop.
- The controller may commit only when `allow_git_commit: true` is explicit. It may push only when `allow_git_push: true` is explicit.
- Validation upload, external upload, submission packaging, fold expansion, and high-cost training require explicit task authorization plus audit/promotion-gate approval.

## 6. CARE Failure Escalation Contract

- If preflight passes but no metric exists, the next bounded action is fold0 train/eval, not another preflight.
- If a translation baseline is near zero, the next route is affine, deformable, TPS, feature-level, or optical-flow alignment with plausibility checks, or an explicit stop of the alignment route.
- If two substantive SRR/proposal variants remain far below the nnU-Net same-split baseline, stop or escalate to a stronger mechanism such as cascade, teacher, or refinement. Do not continue with only temperature, gate, or threshold tuning.
- `STOP_*`, `REVISE_*`, `selected_variant: none`, and `*_WAITING_*` block fold expansion, packaging, upload, and next-stage training unless the user explicitly overrides the block and the exception is recorded.

## 7. CARE Evidence Contract

- MyoPS tasks must report target metric, same-split baseline, subgroup metrics, HD95, component count, remote FP, volume ratio, checkpoint path, prediction path, metric path, log path, and cache isolation.
- Cine tasks must report reference frame, non-reference frame usage, transform/alignment type, temporal aggregation, pathology or target-head availability, and hosted-metric caveat.
- Label/export tasks must report evaluator, decode mode, raw-label mapping, exported zip or prediction path, and any validation-package caveat.
- Missing evidence must be written as `evidence not found` or `未找到证据`. Do not infer completion from intent, logs without metrics, or local proxy checks.
