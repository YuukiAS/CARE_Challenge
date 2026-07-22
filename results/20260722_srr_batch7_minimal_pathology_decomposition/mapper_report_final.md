# Mapper Report Final

review_token: BATCH7_MINIMAL_DECOMPOSITION_CONTROLLER_VERIFIED

mapper_scope: executor_supplied_architecture_evidence

## Files Inspected

- `src/care_myocardium/models/srr_propref.py`
- `src/care_myocardium/losses/srr_losses.py`
- `src/care_myocardium/srr_production/checkpoint.py`
- `scripts/training/run_srr_batch7_minimal_decomposition.py`
- `scripts/evaluation/calibrate_srr_batch7_sip_weight.py`
- `scripts/evaluation/aggregate_srr_batch7_minimal_decomposition.py`
- `scripts/evaluation/validate_srr_batch7_minimal_decomposition_packet.py`
- `configs/srr_production/myops_batch7_minimal_decomposition.yaml`
- `results/20260722_srr_batch7_minimal_pathology_decomposition/`

## Architecture Status

- Lightweight BR2 representers are implemented for the Batch7 minimal decomposition path.
- The formal path disables old M10 spatial dictionary, prototype maps, semantic negative memory, refiner, source arbiter, and production gate training.
- Center is used for training coefficients, source-balanced sampling, and diagnostics only.
- Availability-pattern beta is the validation/deployment coefficient source.
- No-T2 edema sources are excluded from edema beta, SIP, and loss authority.

## Runtime Evidence

- Scar runtime attempt: `batch7_minimal_decomposition_scar_htzhulab_rngrestore_20260722_041704`.
- Edema runtime attempt: `batch7_minimal_decomposition_edema_htzhulab_formal_20260722_045900`.
- Static diagnostics: `representer_scale_checks.csv`, `beta_hierarchy_checks.csv`, `availability_mask_checks.csv`, `sip_formula_unit_tests.json`, and `br2_staged_gradient_checks.json`.
- Aggregated metrics: `casewise_metrics.csv`, `deployment_subgroup_metrics.csv`, `proposal_mechanism_metrics.csv`, `br2_increment_matrix.csv`, and `sip_increment_matrix.csv`.

## Component Status Delta

- Batch7 minimal decomposition orchestration: implemented, verified.
- Center-hierarchical signed beta table: implemented, verified by static diagnostics.
- Full-center-table SIP calculation: implemented, verified by unit diagnostics and runtime calibration rows.
- Source-balanced sampler: implemented, verified by per-variant sampler summaries.
- Final deployment claim: unsupported; no later route scope is authorized.

## Wiki State

`wiki/README.md` and `prompts/routes/handoffs/CURRENT.md` are updated in this packet to record the terminal six-run result and to keep later scopes unauthorized.
