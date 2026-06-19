---
task_id: "20260620_cinema_t2_edema_pilots"
project: "CARE-Myocardium"
status: "superseded_by_split_tasks"
executor: "Codex"
risk_level: "low"
allow_code_change: false
allow_shell_command: false
allow_network: false
allow_external_upload: false
requires_human_approval: false
---

# Dispatcher: split tasks for CARE CineMA and T2-present edema pilots

This file originally bundled two execution actions into one task. It has been superseded to match the `prompts/` handoff rule that tasks should be small and clear.

Codex should not execute this dispatcher directly. Execute the split tasks instead:

1. `prompts/tasks/20260620_cinema_adapter_pilot_task.md`
   - Purpose: run the CineMA -> CARE CineMyoPS anatomy adapter/pilot.
   - Result path: `prompts/tasks/20260620_cinema_adapter_pilot_result.md`.

2. `prompts/tasks/20260620_t2_present_edema_pilot_task.md`
   - Purpose: run the MyoPS T2-present edema expert/routing pilot.
   - Result path: `prompts/tasks/20260620_t2_present_edema_pilot_result.md`.

Run order recommendation:

- Start with `20260620_cinema_adapter_pilot_task.md` if the goal is to test the external CineMA resource and the `myocardium_cinemyops` branch first.
- Start with `20260620_t2_present_edema_pilot_task.md` if GPU/network availability blocks CineMA or if the immediate priority is `myops_edema`.
- The two tasks are intentionally independent. Do not let one task continue into the other unless the second task file is explicitly opened and followed.

This dispatcher exists only to preserve audit history and point to the two executable task files.
