# Review 20260703 MyoPS Audit

audit_decision: AUDITED_GO
role: read-only re-auditor
audited_task: `prompts/tasks/20260703_myops_audit.md`
audited_result: `results/20260703_myops_audit/result.md`
audited_manifest: `results/20260703_myops_audit/MANIFEST.md`

## Audit History

- First audit decision: `NEEDS_EVIDENCE`.
- First audit missing-evidence items: per-route result/selection/metric/prediction/checkpoint/log path table; saved command transcript or transcript caveat; fuller cache-isolation table.
- Current re-audit decision: `AUDITED_GO` for the revised evidence-only audit package. This does not authorize training, fold expansion, validation packaging/upload, commit, push, or route promotion by itself.

## Re-Audit Summary

补充包已解决第一轮 `NEEDS_EVIDENCE` 的核心缺口。`route_evidence_index.csv` 现在按 route/variant 列出 result、selection、metric、prediction、checkpoint、training log、job log 路径；`cache_isolation_table.csv` 现在列出 evidence root、prediction/checkpoint/metric/log cache 和缺失项；`command_transcript.md` 明确保留当前 revision 的命令与 exit status，并把原始 executor transcript 标为 `evidence not found`。

MyoPS 主结论仍然成立：当前 custom SRR/cascade 路线是 `PARTIAL_MECHANISM_INCOMPLETE`，未达到 same-split nnU-Net-relative gate；label/export、T2/no-T2 dense edema supervision、architecture gap、same-split baseline 和 forbidden-substitute caveats 均有可复核证据。未发现会推翻主要机制结论的 contradiction。

## Required Reads

- Repo/protocol: `AGENTS.md`, `prompts/AGENT_RULES.md`, `prompts/CHATGPT_RULES.md`, `prompts/HANDOFF_ROLES.md`, `prompts/HANDOFF_STATE_MACHINE.md`, `prompts/CONTROLLER_TASK_PROTOCOL.md`, `prompts/CARE_OVERLAY_GATES.md`.
- Skill: `.agents/skills/domains-medical-imaging-medical-imaging-deep-learning/SKILL.md`, `.agents/skills/domains-medical-imaging-medical-imaging-deep-learning/references/reference.md`.
- Task/controller/supplement prompt: `prompts/tasks/20260703_myops_audit.md`, `prompts/tasks/20260703_hardmode_goal.md`, `results/20260703_hardmode_goal/subagents/myops_audit_evidence_revision_executor_prompt.md`.
- Current package: `results/20260703_myops_audit/result.md`, `MANIFEST.md`, previous `review.md`, `mechanism_audit.md`, `label_export_qc.md`, `architecture_gap_audit.md`, `route_gap_table.csv`, `failure_case_table.csv`, `code_path_audit.md`, `next_route_gate.md`, `route_evidence_index.csv`, `cache_isolation_table.csv`, `command_transcript.md`, `scripts/evaluation/audit_myops_mechanism_20260703.py`.
- Source evidence spot-checks: `results/20260629_rescue_goal/final_status.md`, `completion_audit.md`, `route_status.csv`, label/export/evaluator code, SRR loss/training code, SRR/cascade model code and cascade selection metrics.

## Claim Ledger

| claim | status | audit finding |
| --- | --- | --- |
| `claim.route_completion` | SUPPORTED | `results/20260629_rescue_goal/route_status.csv` and `completion_audit.md` support 21 ready rows and 4 not-selected duplicate A100/Volta rows. MyoPS selected routes have result/selection/metric/prediction evidence. Cine rows are present in the rescue ledger but remain secondary/out of this MyoPS audit scope. |
| `claim.route_evidence_index` | SUPPORTED | `route_evidence_index.csv` has 25 rows with explicit result, selection, metric, prediction, checkpoint, training-log, job-log, source-root, task, and stop-reason columns. Read-only path validation found zero broken non-`evidence not found` paths. |
| `claim.cache_isolation` | SUPPORTED | `cache_isolation_table.csv` has 25 rows and enumerates evidence roots plus prediction/checkpoint/metric/log caches. For selected MyoPS variant rows, roots are variant-specific and assessed `low`; missing caches are explicit. The two selected Cine rows are marked `requires auditor review` with `prediction_dir;checkpoint_path;job_log_path` missing, which is outside the MyoPS mechanism gate. |
| current command transcript | SUPPORTED | `command_transcript.md` records revision commands and exit statuses and states `original_executor_transcript: evidence not found`. This satisfies the evidence supplement prompt's original-transcript caveat requirement. |
| `claim.label_mapping` | SUPPORTED | `code/nnUNet/nnunet_label_utils.py` maps raw MyoPS labels to compact `1..5`; Dataset501 channel/label semantics match the QC report; `scripts/submission/prepare_care_myocardium_validation.py` maps compact MyoPS labels back to raw `200,500,600,1220,2221`; evaluator labels class_4/class_5 as `myops_edema`/`myops_scar`. Hosted validation remains `evidence not found`, correctly caveated. |
| `claim.t2_contract` | SUPPORTED | `src/care_myocardium/losses/srr_losses.py` gates dense edema loss by `availability[:, 1]`; `scripts/training/run_srr_myops_fold0.py` gates proposal edema dense BCE by T2-present and excludes myocardium/scar voxels from no-T2 edema hard negatives. No contradictory no-T2 myocardium-as-edema-negative code path was found in the audited SRR paths. |
| `claim.architecture_gap` | SUPPORTED | `srr_v2_unet.py` has multiscale encoder/decoder machinery, but `pathology_heads.py` still uses 1x1 scar/edema heads and `PathologyProposalHead` directly mixes evidence/proposal logits into final logits. Cascade metrics mark formal variants `fail_stop_refiner_candidate` with tiny deltas. |
| same-split nnU-Net reference | SUPPORTED | Fold0 checkpoint and validation/subgroup metric paths exist; audit inputs match scar all-case `0.5602`, edema GT-positive `0.3944`, and 80% gates `0.4481`/`0.3155`. |
| best custom metric claims | SUPPORTED | `route_gap_table.csv` supports best custom scar all-case `srr_v2_capacity12_hardneg` Dice `0.308969` and best custom edema GT-positive `srr_v2_capacity12_scar_precision_interact` Dice `0.206302`, both below the 80% nnU-Net gates. |
| `claim.next_state` | SUPPORTED | Executor stopped at `EXECUTED_UNAUDITED` and did not self-audit. This re-audit now supplies the independent review. |

## Forbidden Substitute Checks

| forbidden substitute | finding |
| --- | --- |
| preflight/smoke-only completion | Not used. The package labels the domain evidence `PARTIAL_MECHANISM_INCOMPLETE`, not `TRUE_DONE`. |
| compact-label proxy as hosted challenge evidence | Not promoted. `label_export_qc.md` explicitly caveats that compact fold0 metrics are not hosted validation evidence. |
| no-T2 myocardium as edema negative | Not found in audited SRR loss/proposal paths. |
| metrics without file paths | Resolved for the current supplement: metric paths are enumerated in `route_evidence_index.csv` and `cache_isolation_table.csv`. |
| missing evidence inferred from logs | Not used as completion; missing entries remain `evidence not found`. |
| executor self-review | Not used. The executor left audit to a separate review. |
| validation upload/package generation | Not found in this audit package; hosted validation/upload-ready evidence remains `evidence not found`. |
| fold expansion/training rerun | Not found in the revised audit package. The supplement is a report/table/script update only. |

## Remaining Missing Or Partial Evidence

- Original first-executor stdout/stderr transcript: `evidence not found`; current revision transcript is present and sufficient for this supplement.
- Hosted validation metrics: `evidence not found`; validation upload/package was forbidden by task scope.
- Official upload-ready raw-label package evidence: `evidence not found`; label/export code paths only were audited.
- Cine rescue rows in `route_evidence_index.csv` and `cache_isolation_table.csv` still lack prediction/checkpoint/job-log caches. This is explicit and not a blocker for the MyoPS audit gate, but it must not be reused as Cine temporal completion evidence.

## Contradictions

未发现 `CONTRADICTED` claims. 未发现 compact-label metrics 被当作 hosted challenge evidence、no-T2 myocardium 被当作 edema dense hard negative、validation upload/package 由本 task 生成、或 executor 自评替代 audit。

## Promotion Boundary

This `AUDITED_GO` applies only to accepting the revised `20260703_myops_audit` evidence package as auditable. It permits the controller/strategic planner to use the audit as Phase 1 evidence, but it does not itself promote any MyoPS custom route, expand folds, launch training, package validation, upload, commit, or push.
