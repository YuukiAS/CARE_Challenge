# 20260629 Rescue Goal GPU Action Status

- generated_at: `2026-07-01 17:35:42 EDT`
- open_actions: `3`
- recheck_policy: `2h interval, max 12 checks before partition/work audit`

| item | route | status | job_id | partition | scheduler_state | pending_hours | wait_policy_status | next_recheck_after | required_action |
| --- | --- | --- | --- | --- | --- | ---: | --- | --- | --- |
| repaired_proposal_formal | repaired_proposal | UNKNOWN_RECHECK | 57094448 |  | UNKNOWN |  | not_pending |  | inspect_outputs |
| srr_v2_basic_formal | srr_v2 | UNKNOWN_RECHECK | 57094446 |  | UNKNOWN |  | not_pending |  | inspect_outputs |
| srr_v2_missing_variants_a100 | srr_v2 | UNKNOWN_RECHECK | 57095505 |  | UNKNOWN |  | not_pending |  | inspect_outputs |
| srr_v2_missing_variants_htzhulab_fallback | srr_v2 | UNKNOWN_RECHECK | 57272337 |  | UNKNOWN |  | not_pending |  | inspect_outputs |
| cascade_formal_array | cascade_teacher | UNKNOWN_RECHECK | 57272502 |  | UNKNOWN |  | not_pending |  | inspect_outputs |
| cascade_component_guard_revision | cascade_teacher_revision_component_guard | UNKNOWN_RECHECK | 57274444 |  | UNKNOWN |  | not_pending |  | inspect_outputs |
| cascade_signal_seek_revision | cascade_teacher_revision_signal_seek | UNKNOWN_RECHECK | 57275246 |  | UNKNOWN |  | not_pending |  | inspect_outputs |
| srr_v2_light_refine_extras | srr_v2_light_refine_extras | QUEUED_OR_RUNNING | 57277361 | htzhulab | RUNNING |  | not_pending |  | monitor |
| srr_v2_capacity_extras | srr_v2_capacity_extras | QUEUED_OR_RUNNING | 57279322 | htzhulab | RUNNING |  | not_pending |  | monitor |
| srr_v2_targeted_extras | srr_v2_targeted_extras | QUEUED_OR_RUNNING | 57334792 | htzhulab | PENDING |  | pending_submit_time_unknown |  | monitor |

## Notes

- This file records scheduler/action state only; it is not a route selection.
- `ACTION_REQUIRED` rows are not submitted jobs. They require explicit approval after command-review rejection.
- Existing queued jobs should be monitored before duplicating variants on another partition.
- The two-hour wait policy is advisory state tracking; it does not by itself authorize duplicate GPU submissions or blocked completion.
