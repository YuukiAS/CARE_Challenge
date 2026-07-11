# Architecture Delta Final

No model architecture changed.

Protocol architecture changed:

- field/schema ownership moved into `prompts/schemas/`;
- active policy discovery moved into `prompts/ACTIVE_POLICY_FILES.yaml`;
- planning review became a separate verifiable `critic` role with contract hash;
- current wiki review metadata became dynamic through `wiki/current_state.yaml`;
- executor-wave receipts became task-local and resumable.
