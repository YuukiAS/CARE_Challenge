# Cine Scope Contract

task: `prompts/tasks/20260705_srr_v3_m5_cine_secondary_contract.md`
status: `EXECUTED_UNAUDITED`
route_promotion_decision: `NO_PROMOTION`
hosted_metric_claim: `NOT_CLAIMED`
validation_packaging_upload: `NOT_RUN_FORBIDDEN_BY_TASK`

## Scope

M5 keeps Cine as a secondary diagnostic line. It aggregates existing CineMA anatomy-prior, registration, VoxelMorph, frame0/ED, temporal descriptor, and router evidence into a reviewer-visible packet.

This packet does not train Cine models, does not run validation packaging/upload, does not claim hosted `myocardium_cinemyops`, and does not block MyoPS milestones.

## Controlled Status

- registration_status: `CINE_REGISTRATION_GAP_REMAINS`
- temporal_dictionary_status: `TEMPORAL_DICTIONARY_NOT_READY`
- CineMA/anatomy_prior_status: `PARTIAL_SUPPORTED_ANATOMY_ONLY`
- VoxelMorph_status: `ADAPTER_RUNS_NOT_TRAINED_NOT_USABLE_REGISTRATION`
