# 20260629 Rescue Goal GPU Action Status

- generated_at: `2026-07-01 23:18:36 EDT`
- open_actions: `3`
- recheck_policy: `2h interval, max 12 checks before partition/work audit`

| item | route | status | job_id | partition | scheduler_state | pending_hours | wait_policy_status | next_recheck_after | required_action |
| --- | --- | --- | --- | --- | --- | ---: | --- | --- | --- |
| repaired_proposal_formal | repaired_proposal | DONE | 57094448 | htzhulab | COMPLETED |  | not_pending |  | inspect_outputs |
| srr_v2_basic_formal | srr_v2 | DONE_RECOVERED | 57094446 | htzhulab | FAILED |  | not_pending |  | inspect_outputs |
| srr_v2_missing_variants_a100 | srr_v2 | UNKNOWN_RECHECK | 57095505 | a100-gpu | CANCELLED by 397557 |  | not_pending |  | inspect_outputs |
| srr_v2_missing_variants_htzhulab_fallback | srr_v2 | DONE | 57272337 | htzhulab | COMPLETED |  | not_pending |  | inspect_outputs |
| cascade_formal_array | cascade_teacher | DONE | 57272502 | htzhulab | COMPLETED |  | not_pending |  | inspect_outputs |
| cascade_component_guard_revision | cascade_teacher_revision_component_guard | DONE | 57274444 | htzhulab | COMPLETED |  | not_pending |  | inspect_outputs |
| cascade_signal_seek_revision | cascade_teacher_revision_signal_seek | DONE | 57275246 | htzhulab | COMPLETED |  | not_pending |  | inspect_outputs |
| srr_v2_light_refine_extras | srr_v2_light_refine_extras | DONE | 57277361 | htzhulab | COMPLETED |  | not_pending |  | inspect_outputs |
| srr_v2_capacity_extras | srr_v2_capacity_extras | DONE | 57279322 | htzhulab | COMPLETED |  | not_pending |  | inspect_outputs |
| srr_v2_targeted_extras | srr_v2_targeted_extras | QUEUED_OR_RUNNING | 57334792 | htzhulab | PENDING | 5.01 | continue_monitoring | 2026-07-02 00:17:53 | monitor |
| srr_v2_targeted_extras_a100 | srr_v2_targeted_extras_a100 | QUEUED_OR_RUNNING | 57340171 | a100-gpu | PENDING | 3.95 | continue_monitoring | 2026-07-01 23:21:46 | monitor |
| srr_v2_targeted_extras_volta | srr_v2_targeted_extras_volta | QUEUED_OR_RUNNING | 57340161 | volta-gpu | PENDING | 3.97 | continue_monitoring | 2026-07-01 23:20:25 | monitor |

## Notes

- This file records scheduler/action state only; it is not a route selection.
- `ACTION_REQUIRED` rows are not submitted jobs. They require explicit approval after command-review rejection.
- Existing queued jobs should be monitored before duplicating variants on another partition.
- The two-hour wait policy is advisory state tracking; it does not by itself authorize duplicate GPU submissions or blocked completion.
