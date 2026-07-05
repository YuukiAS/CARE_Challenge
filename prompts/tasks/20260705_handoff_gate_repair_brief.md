# Handoff Gate Repair Brief

Create or update repository checks so a controller task cannot be marked complete when required subtask result directories are missing. The current regression example is `prompts/tasks/20260704_srr_v25_full_completion_goal.md`: it required `20260704_cine_temporal_dictionary_integration` and `20260704_srr_v25_completion_check`, but those result directories are missing.

The repair should make this regression fail strict validation. The repair should also require a completion check before final audit, and should classify very small training probes as diagnostic or undertrained rather than full route evidence.

Required outputs should be written under `results/20260705_handoff_gate_repair_brief/` with a result, validator summary, regression report, unit test report, and manifest.
