# Loss Component Gradient Fix Report

status: `EXECUTED_UNAUDITED`

M7 continued reran gradient sanity using existing M7 checkpoints, real M7 fold0 cases, real patches, labels, availability masks, nnU-Net anchors, and component context. It did not use M6 synthetic tensors.

- `m7_full_srr_context_arbitration`: checkpoint_final step `12382`, batch `Case2002,Case1002`, statuses `{'PASS': 34, 'PASS_ZERO_JUSTIFIED': 3}`.
- `m7_conservative_component_arbitration`: checkpoint_final step `17660`, batch `Case2002,Case1002`, statuses `{'PASS': 29, 'PASS_ZERO_JUSTIFIED': 4}`.
- `m7_scar_precision_edema_safe`: checkpoint_final step `14029`, batch `Case2002,Case1002`, statuses `{'PASS': 30, 'PASS_ZERO_JUSTIFIED': 7}`.
