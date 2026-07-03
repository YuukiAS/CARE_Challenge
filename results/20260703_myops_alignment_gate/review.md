# Review 20260703 MyoPS Alignment Gate

audit_decision: AUDITED_GO
route_decision_recommendation: STOP_ALIGNMENT_NOT_PRIMARY
role: read-only auditor
audited_task: `prompts/tasks/20260703_myops_alignment_gate.md`
audited_result: `results/20260703_myops_alignment_gate/result.md`
audited_manifest: `results/20260703_myops_alignment_gate/MANIFEST.md`
controller_task: `prompts/tasks/20260703_hardmode_goal.md`

## Audit Summary

The executor produced the required alignment-gate artifact package and stopped after Phase 1 diagnosis. The stop is supported: complete C0+LGE+T2 fold0 evidence does not show cross-sequence mismatch as a major pathology failure driver. The package reports 16 complete cases across CenterB and CenterC, computes raw C0/LGE/T2 header and numeric alignment proxies, compares those proxies with existing nnU-Net fold0 pathology failures, and reports scar/edema Dice, HD/HD95, component, small-FP, and remote-FP metrics.

This review accepts `STOP_ALIGNMENT_NOT_PRIMARY` as the audited route decision. It does not promote registration, and it does not authorize Phase 3, validation packaging/upload, fold expansion, next-stage training, commit, or push.

## Required Reads

- Repo/protocol: `AGENTS.md`, `prompts/AGENT_RULES.md`, `prompts/CHATGPT_RULES.md`, `prompts/HANDOFF_ROLES.md`, `prompts/HANDOFF_STATE_MACHINE.md`, `prompts/CONTROLLER_TASK_PROTOCOL.md`, `prompts/CARE_OVERLAY_GATES.md`.
- Skill: `.agents/skills/domains-medical-imaging-medical-imaging-deep-learning/SKILL.md`, `.agents/skills/domains-medical-imaging-medical-imaging-deep-learning/references/reference.md`.
- Task/controller: `prompts/tasks/20260703_myops_alignment_gate.md`, `prompts/tasks/20260703_hardmode_goal.md`.
- Prior audits: `results/20260703_myops_audit/review.md`, `results/20260703_myops_fp_control/review.md`, `results/20260703_myops_srr_propose_refine/review.md`.
- Current package: `result.md`, `MANIFEST.md`, `alignment_diagnosis.md`, `registration_metrics.csv`, `warp_sanity.csv`, `subgroup_metrics.csv`, `component_hd_by_case.csv`, `visual_sanity_index.md`, `failure_interpretation.md`, `command_transcript.md`.
- Code: `scripts/evaluation/myops_alignment_gate_20260703.py`.

## Claim Ledger

| claim | status | audit finding |
| --- | --- | --- |
| required outputs exist and are indexed | SUPPORTED | All required artifacts are nonempty and `MANIFEST.md` indexes `result.md`, `alignment_diagnosis.md`, `registration_metrics.csv`, `warp_sanity.csv`, `subgroup_metrics.csv`, `component_hd_by_case.csv`, `visual_sanity_index.md`, `failure_interpretation.md`, `command_transcript.md`, and the diagnostic script. |
| complete-case scope | SUPPORTED | `alignment_diagnosis.md` and the generated CSVs report 16 fold0 complete C0+LGE+T2 cases, with CenterB and CenterC represented. |
| alignment diagnosis evidence | SUPPORTED | `registration_metrics.csv` contains per-case LGE-vs-C0/T2 header, geometry, center-of-mass, slice correspondence, intensity, mutual-information, and edge-correlation proxy rows, plus correlation rows against pathology failures. |
| pathology failure correlation supports stop | SUPPORTED | Aggregate pathology failure correlation is weak/negative: Pearson `-0.2612`, Spearman `-0.3647`; top pathology failures overlap top alignment mismatches in `0/5` cases. Scar-only correlation is moderate positive, but edema is negative and the task gate requires complete-case evidence that mismatch is a major failure mode. |
| CenterB/CenterC and scar/edema metrics | SUPPORTED | `subgroup_metrics.csv` reports complete, CenterB, CenterC, scar-positive, edema-positive, and T2-present rows for both `myops_scar` and `myops_edema`; `component_hd_by_case.csv` reports case-level Dice, HD, HD95, component count, small-FP, and remote-FP. |
| `STOP_ALIGNMENT_NOT_PRIMARY` | SUPPORTED | The task explicitly allows stopping when mismatch is not correlated with pathology failure. The executor did not stop on translation failure; translation and non-translation candidates were not executed because Phase 1 failed to support the alignment-primary hypothesis. |
| non-translation candidates not forced | SUPPORTED | `warp_sanity.csv` marks slice/TPS and BSpline/Demons/feature-level candidates as not attempted after `STOP_ALIGNMENT_NOT_PRIMARY`, which is consistent with the task's Phase 1 stop condition. |
| command transcript | SUPPORTED | `command_transcript.md` records the diagnostic command, exit status `0`, elapsed time `9.26s`, Python executable, available SimpleITK/scipy/numpy, and git head `e535589`. |
| visual sanity | PARTIAL | `visual_sanity_index.md` provides numeric visual proxies and explicitly states expert overlay review and image overlays are `evidence not found` / not generated. This is acceptable for the stop decision but must not be reused as expert visual validation. |
| translation baseline | PARTIAL | Translation rows are placeholders marked not executed. This is not a completion substitute because the stop comes from Phase 1 alignment-not-primary evidence, but it is not evidence of translation performance. |
| hosted/raw-label validation evidence | PARTIAL | `failure_interpretation.md` correctly marks hosted validation metrics and raw-label validation package/export evidence as `evidence not found`. This blocks any challenge-facing promotion. |
| executor self-review absence | SUPPORTED | The executor wrote `result.md` and left `review.md` for a separate read-only audit. |

## Forbidden Substitute Checks

| forbidden substitute | finding |
| --- | --- |
| translation-only completion | Not found. Translation was not executed and was not used as completion. |
| image-similarity-only success | Not found. Image/intensity proxies were used only to decide whether alignment is a plausible bottleneck, and pathology metrics were reported. |
| registration without pathology delta | Not found. No registration was promoted; no pathology delta was claimed for an alignment method. |
| warping labels into leakage | Not found. The script resamples predictions to GT for evaluation and moving raw images to LGE for measurement; it does not warp labels into training or tune on warped labels. |
| preflight-only completion | Not found. The package includes complete-case proxy metrics and pathology metrics, not just preflight readiness. |
| fold expansion or validation upload | Not found. The script and transcript are fold0/local and no upload/package evidence is present. |
| evaluator, label mapping, or split changes | Not found in the audited script or artifacts. |
| executor self-review | Not found. |

## Audit Boundary

This `AUDITED_GO` means the evidence package is sufficient to accept the route stop `STOP_ALIGNMENT_NOT_PRIMARY`. It is not `AUDITED_GO` for registration promotion.

This review does not authorize Phase 3, validation packaging, validation upload, fold expansion, next-stage training, commit, or push. Any new scientific direction or override of this stop must return to the user-supervised GPT strategic planner.
