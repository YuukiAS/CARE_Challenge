---
task_key: "20260703_care_handoff"
project: "CARE_Challenge"
status: "EXECUTED_UNAUDITED"
executor: "Codex executor session"
self_assessed_status: "DONE_DOCS_ONLY"
review_required: false
---

# Result: CARE handoff overlay reinforcement

## Execution Summary

Completed a CARE-only documentation and template patch. No training, validation submission, upload, fold split change, label mapping change, evaluator change, or AI_Skills_Collection edit was performed.

The `/users/a/e/aereinh/CARE` checkout already had the Bridge Kit two-layer file handoff deployed. It was not fully validator-clean because old task/result records predated the new protocol. The three invalid task filenames called out in the prior validation were normalized and given alias result directories so the current handoff tree now validates with zero errors.

## Conflict And Overlap Audit

Layer 1, Bridge Kit generic handoff:

- Owns GPT planner, GPT strategic controller, Codex execution controller, executor, auditor, controller task behavior, task/result/review/controller report mapping, controlled states, `review_required`, promotion gates, and commit/push authorization.
- CARE should not redefine the generic state machine or role model. CARE rules should reference it.

Layer 2, `medical-imaging-deep-learning` skill:

- Owns generic medical-imaging mechanism gates: U-Net-like segmentation, registration/warping, cine temporal modeling, missing-modality fusion, external adapters, proposal/refinement/cascade routes, and the completion labels `TRUE_DONE`, `PARTIAL_MECHANISM_INCOMPLETE`, `PREFLIGHT_SMOKE_ONLY`, `NOT_DONE`.
- CARE should not copy the skill text into repo rules or task templates. CARE tasks should cite the installed skill and upstream AI_Skills_Collection source as the method gate authority.

Layer 3, CARE overlay:

- Owns CARE Challenge-specific contracts: `myops_scar`, `myops_edema`, `myocardium_cinemyops`, raw-vs-compact label mapping, no-T2 edema semantics, one-zip validation package, CenterB/CenterC reporting, HD95/component/remote FP evidence, CineMyoPS temporal evidence, and historical stop/revise failure rules.
- Added `prompts/CARE_OVERLAY_GATES.md` to keep this layer short and challenge-specific.

Conflicts found:

- No direct conflict was found between the installed medical-imaging skill and the new CARE overlay. The observed problem was overlap risk: older CARE notes and tasks sometimes embedded generic method-gate logic directly. The new overlay now says the skill is authoritative for generic mechanism completion and CARE only adds challenge-specific constraints.
- Existing older tasks still lack many Bridge Kit frontmatter fields and many old result directories still lack independent reviews. Those are historical migration debt, not a conflict in the new overlay.

## Files Read

- `AGENTS.md`
- `prompts/AGENT_RULES.md`
- `prompts/CHATGPT_RULES.md`
- `prompts/templates/TASK_TEMPLATE.md`
- `prompts/templates/CONTROLLER_TASK_TEMPLATE.md`
- `prompts/templates/REVIEW_TEMPLATE.md`
- `docs/notes/codex/codex_thread_audit_20260702.md`
- `.agents/skills/domains-medical-imaging-medical-imaging-deep-learning/SKILL.md`
- `/overflow/htzhu/mingcheng_new/AI_Skills_Collection/skills/domains/medical-imaging/medical-imaging-deep-learning/SKILL.md`
- `/overflow/htzhu/mingcheng_new/AI_Skills_Collection/skills/domains/medical-imaging/medical-imaging-deep-learning/references/reference.md`
- `prompts/tasks/20260629_srr_v2_unet_core.md` before rename
- `prompts/tasks/20260629_cine_motion_alignment.md`
- `prompts/tasks/20260629_rescue_goal.md`

## Files Modified

- `prompts/CARE_OVERLAY_GATES.md` added as the CARE-specific overlay gate document.
- `prompts/CHATGPT_RULES.md` now requires CARE GPT tasks to choose execution vs controller mode and declare CARE mechanism/evidence/promotion fields.
- `prompts/AGENT_RULES.md` now reinforces executor/controller/auditor boundaries for CARE and blocks automatic continuation after stop/revise/waiting states.
- `prompts/templates/TASK_TEMPLATE.md` now contains CARE-specific fields and references the Bridge Kit state machine plus the medical-imaging skill instead of copying it.
- `prompts/templates/CONTROLLER_TASK_TEMPLATE.md` now describes CARE controller workflow, subagent fallback, and CARE-specific commit/push authorization.
- `prompts/templates/REVIEW_TEMPLATE.md` now requires read-only CARE evidence audit, claim ledger, audited status, promotion decision, and next allowed action.
- `prompts/tasks/20260629_result4_srr_core_rebuild.md` renamed to `prompts/tasks/20260629_result4_srr.md` with protocol-normalized frontmatter.
- `prompts/tasks/20260629_srr_v2_unet_core.md` renamed to `prompts/tasks/20260629_srr_v2.md` with protocol-normalized frontmatter.
- `prompts/tasks/20260629_true_soft_roi_refine.md` renamed to `prompts/tasks/20260629_soft_roi.md` with protocol-normalized frontmatter.
- `results/20260629_result4_srr/`, `results/20260629_srr_v2/`, and `results/20260629_soft_roi/` added as alias result directories pointing to legacy artifact dirs.
- `prompts/tasks/20260628_result5_goal.md`, `prompts/tasks/20260629_rescue_goal.md`, and `prompts/tasks/20260629_result5_continuation_goal.md` updated to reference renamed task files.
- `prompts/tasks/20260703_care_handoff.md` and `results/20260703_care_handoff/` added to record this docs-only handoff task.

## Commands Run

- `git status --short --branch`
- `git diff --check`
- path existence check for handoff docs, templates, task files, result files, installed skill, and upstream skill references
- `python -m ai_bridge_kit.cli validate --target /users/a/e/aereinh/CARE`

## Validation Results

Final validation:

- `git diff --check`: exit 0
- path existence check: exit 0, `checked_paths=16`
- `python -m ai_bridge_kit.cli validate --target /users/a/e/aereinh/CARE`: exit 0, `PASSED: 0 errors, 55 warning(s)`
- `python -m ai_bridge_kit.cli validate --target /users/a/e/aereinh/CARE --strict`: exit 1, `FAILED: 29 error(s), 26 warning(s)`

The remaining non-strict warnings and strict errors are historical migration debt: old medium/high-risk tasks missing new protocol fields, old result directories missing review files, and a few old result dirs missing `result.md` or `MANIFEST.md`. The three filename errors from the prior validation are resolved.

## Claims

- `claim.bridge_latest_deployed`: The CARE repo has the Bridge Kit handoff protocol deployed; it was usable before this patch but not validator-clean because of legacy records.
- `claim.invalid_task_names_fixed`: The three mentioned old task filenames were normalized to valid `<id>_<short_slug>.md` names.
- `claim.care_overlay_added`: CARE-specific handoff overlay gates were added without copying the medical-imaging skill.
- `claim.role_boundaries_strengthened`: GPT planner/strategic controller, Codex execution controller, executor, and read-only auditor boundaries were strengthened in CARE prompt rules/templates.
- `claim.no_training_or_upload`: No training, validation submission, upload, label mapping change, fold split change, evaluator change, or cross-repo edit was performed.

## Self-Assessed Status

`DONE_DOCS_ONLY`. This is not a scientific/model completion status and does not authorize CARE fold expansion, validation packaging, or upload.

## Not Done

- Did not migrate every old task/result to strict-clean new frontmatter and review coverage.
- Did not modify AI_Skills_Collection or the medical-imaging skill.
- Did not run training, hosted validation, submission packaging, or upload.

## Next Step

Future GPT-generated CARE tasks should cite three sources explicitly: Bridge Kit state machine for handoff state, `.agents/skills/domains-medical-imaging-medical-imaging-deep-learning/SKILL.md` for generic mechanism gates, and `prompts/CARE_OVERLAY_GATES.md` for CARE-specific leaderboard/label/T2/Cine/submission/failure constraints.
