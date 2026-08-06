# CARE Agent-Flow v3 Care-ASE Infrastructure Packet

source task: `prompts/tasks/20260805_care_ase_develop_faithful_reimplementation_controller.md`

status: blocked before request arm

This packet records Agent-Flow v3 infrastructure activation evidence on `develop`. Local visual URL/SHA audit, independent non-scheduled visual observations, role-session isolation smoke, exact resume smoke, and deterministic watcher Smoke A passed. The real scheduled Planner visual receipt appeared on `origin/develop` and validated, but the real scheduled Critic receipt was still missing after two complete scheduling windows. Therefore the scheduled visual smoke did not pass and real GPT-to-Codex Smoke B was not started.

## Files

- `visual_smoke/visual_source_access_receipt.json`: 11 PNG local/raw URL SHA and anonymous access audit.
- `visual_smoke/planner_visual_observation_receipt.json`: independent Planner-style visual observation; not scheduled GPT.
- `visual_smoke/critic_visual_observation_receipt.json`: independent Critic-style visual observation; not scheduled GPT.
- `controller_session_receipt.json`: Controller role CLI smoke session receipt.
- `verifier_session_receipt.json`: Verifier role CLI smoke session receipt.
- `executor_session_receipt.json`: Executor role CLI smoke session receipt.
- `session_smoke/role_receipt_validation.json`: role receipt separation validation.
- `watcher_smoke/exact_resume_receipt.json`: actual exact-session Executor resume proof.
- `watcher_smoke/wake_smoke_receipt.json`: valid synthetic revise event routes to Executor exact thread.
- `watcher_smoke/wake_smoke_duplicate_ignored.json`: duplicate event ignored.
- `watcher_smoke/wake_smoke_old_nonce_rejected.json`: old nonce rejected.
- `watcher_smoke/wake_smoke_old_sha_rejected.json`: stale integration SHA rejected.
- `watcher_smoke/wake_smoke_wrong_thread_rejected.json`: wrong thread ID rejected.
- `gpt_loop_smoke_receipt.json`: Smoke B block receipt.
- `scheduled_task_observation.json`: scheduled task connector availability observation.
- `runtime_receipt_manifest.json`: receipt index.
- `ci_receipt.json`: deterministic local checks.
- `final_state.json`: final blocked state for this activation attempt.
- `result.md`: human-readable summary.
- `controller_report.md`: controller acceptance report.
- `notification_brief.json`: notifier payload, updated after commit/push accounting.
