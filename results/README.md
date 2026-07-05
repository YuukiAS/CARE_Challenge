# Results Directory

`results/` stores file artifacts produced by Codex tasks, scripts, audits, or experiments.

Use the same task key as `prompts/tasks/<task_key>.md`:

```text
prompts/tasks/<task_key>.md
results/<task_key>/result.md
results/<task_key>/review.md
results/<task_key>/controller_report.md   # controller tasks
results/<task_key>/MANIFEST.md
```

`task_key` should be `<id>_<short_slug>`, with `short_slug` limited to 1-3 words joined by underscores.

`results/<task_key>/result.md` is the execution report and evidence index. Keep large logs, CSV/JSON files, figures, archives, long reports, and intermediate outputs under `results/<task_key>/`, then list them in `results/<task_key>/MANIFEST.md` and the result report.

For controller tasks, `results/<task_key>/controller_report.md` is the
execution-controller summary. It must list executor/auditor prompt, result, and
review paths; session/command/log evidence; audited decision; controller run
status; operational completion status; experiment adequacy decision; route
promotion decision; route negative decision; scientific resolution status;
diagnostic publication decision; git commit/push decisions; published files;
blocked actions; next required action; incomplete items; and whether GPT
planner is needed.

`controller_run_status: COMPLETE` means the controller workflow completed. It
does not imply scientific completion. A model route can remain
`SCIENTIFIC_UNRESOLVED`, `SCIENTIFIC_UNDERTRAINED`,
`SCIENTIFIC_PIPELINE_BUG`, `SCIENTIFIC_NEEDS_EVIDENCE`, or
`SCIENTIFIC_NEEDS_REVISION` after an operationally complete run.

Generated `results/20??????_*` run directories are ignored by default. A
controller may publish a minimal reviewed diagnostic packet with explicit
`git add -f <path>` paths when `diagnostic_publication_gate` passes, but it must
not publish the whole result tree. Diagnostic publication is not route
promotion and does not authorize validation packaging/upload, fold expansion,
hosted metric claims, label/evaluator/fold split changes, or next-stage
training.

For routine handoff publication commits, Codex should stage the safe first-level
Markdown packet automatically with:

```bash
python scripts/git/stage_handoff_result_packet.py results/<task_key>
```

This helper uses `git add -f` internally but only for first-level Markdown files
under `results/<task_key>/`, skips transcript/secret/env-dump style names, and
does not stage nested artifacts, CSV/JSON dumps, logs, predictions,
checkpoints, NIfTI outputs, zips, or upload packages. Use explicit `git add -f
<path>` only when a reviewed nonstandard packet file is intentionally needed.

Allowed diagnostic packet defaults: controller `controller_report.md`,
`execution_plan.md`, relevant subtask `result.md`/`review.md`, small reviewed
Markdown decision packets, and reviewed first-party scripts needed to reproduce
the diagnostic conclusion. Forbidden defaults: checkpoints, predictions, NIfTI
outputs, heavy logs, command transcripts with secrets or environment dumps,
large or privacy-sensitive raw CSV dumps, full result trees, upload packages,
hosted validation packages, credentials, and `.env` files.

Route-negative conclusions such as `STOP_NO_SIGNAL` require
`experiment_adequacy_decision: PASS`, `route_negative_decision:
STOP_SUPPORTED`, same-split baseline comparison, and explicit auditor support.
Otherwise record the scientific state as undertrained, unresolved, needs
evidence/revision, or pipeline bug.

Do not mix artifacts from different tasks in the same `results/<task_key>/` directory.
