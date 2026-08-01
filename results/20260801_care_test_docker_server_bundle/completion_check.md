# Completion Check

decision: SERVER_BUNDLE_BLOCKED
controller_verification_decision: OPERATIONALLY_BLOCKED
blocking_token: NNUNET_PROVENANCE_REPLAY_MISMATCH
validator_expected: PASS_FOR_BLOCKED_PACKET

The server must not write `SERVER_BUNDLE_READY.json`: fresh nnU-Net replay produced 15/15 files and 15/15 geometry equality but did not reproduce package A arrays for all cases.
