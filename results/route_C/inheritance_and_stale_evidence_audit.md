# Route C inheritance and stale evidence audit

Decision: old M9/M10/follow-up/follow-up2 packets are `CONTEXT_ONLY`.

The route_C contract requires fresh route-local evidence under `results/route_C/` and route_C namespaces. Prior packets may be read to recover requirements, historical failure modes and reusable read-only assets, but none can satisfy route_C completion.

## Reviewed baseline

The current reviewed root state is M09:

| field | value |
| --- | --- |
| current milestone | `M09` |
| review token | `M9_FOLLOWUP_AUDITED_READY_NO_PROMOTION_DIAGNOSTIC_ONLY` |
| reviewed commit | `fa4e50ba77743322104e7d61ae69a2382f3a89c2` |
| route status | `M9_NO_PROMOTION_DIAGNOSTIC_ONLY` |

M09 component files under `wiki/history/M09/` are historical snapshots. They explicitly do not provide current route_C runtime evidence.

## M10 and follow-up context

Existing M10-related result directories found at bootstrap include:

```text
results/20260711_srr_v3_m10_cine_registration
results/20260711_srr_v3_m10_hard_negative_refresh
results/20260711_srr_v3_m10_no_nnunet_context_control
results/20260714_srr_v3_m10_followup_wave2_reconciliation
results/20260711_srr_v3_m10_myops_d0_control
results/20260711_srr_v3_m10_cine_learned_temporal
results/20260711_srr_v3_m10_cinema_adapter
results/20260711_srr_v3_m10_myops_d3_full_propref
results/20260711_srr_v3_m10_alignment_control
results/20260711_srr_v3_m10_mechanism_smoke
results/20260711_srr_v3_m10_architecture_fidelity
results/20260711_srr_v3_m10_component_causal_audit
results/20260714_srr_v3_m10_continuation_reconciliation
results/20260714_srr_v3_m10_followup_cine_fidelity
results/20260714_srr_v3_m10_followup_cine_runtime
results/20260711_srr_v3_m10_myops_d2_hierarchical_psip
results/20260711_srr_v3_m10_myops_d1_spatial_br2
results/20260711_srr_v3_m10_complete_mechanism_repair
```

These directories are not route_C completion evidence because they predate the route_C branch/namespace contract and include unreviewed, incomplete, smoke-only, timed-out or context-only packets.

## Required regeneration

Route C must regenerate or honestly classify, under route_C namespaces:

- MyoPS selected checkpoint replay with force/evaluate or equivalent cache-isolated fail-closed semantics;
- raw output manifests with state-dict SHA, case list, inference call count, decode/export path and output hashes;
- real D2/D3 and v3 bounded-correction interventions affecting final logits or labels, plus no-op controls;
- anchor-relative selector and eligibility/calibration hash fields;
- Cine anatomy-source provenance, pretrained/random controls, registration fidelity, temporal effect, checkpoint reload and cumulative resume evidence;
- strict known-bad self-tests that fail nonzero;
- route-local mapper draft/final reports and architecture fingerprint.

If those cannot be produced after authorized task-local recovery, the controller must end with an allowed route_C token such as `ROUTE_C_NEEDS_EVIDENCE`, `ROUTE_C_NEEDS_REVISION`, `ROUTE_C_NEEDS_MONITOR` or `ROUTE_C_SCIENTIFIC_UNDERTRAINED`.
