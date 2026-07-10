# CARE Architecture Wiki

architecture_version: `care-agent-flow-v2-complete`
latest_verified_milestone: `M9 follow-up evidence reconciliation`
latest_review_token: `M9_FOLLOWUP_AUDITED_READY_NO_PROMOTION_DIAGNOSTIC_ONLY`
route_status: `M9_NO_PROMOTION_DIAGNOSTIC_ONLY`
code_fingerprint: `srr_propref=f7f9df91;srr_blocks=8d126023;srr_losses=dca8e5e1;wiki+validator+skills+toolkit-healthcheck`

This wiki is the root architecture and execution-observability entrypoint for GPT, Codex controller, mapper, finalizer, and reviewer threads. It is repository-tracked, validator-readable, and separate from historical `docs/wiki/` templates.

## Figures

![Current model](figures/model-current.png)

![Current gap](figures/model-gap.png)

![Execution flow](figures/execution-flow.png)

## Component Summary

| Branch | Current reading |
| --- | --- |
| MyoPS SRR | Implemented runtime route with retrieval/proposal/refiner/arbitration components, but M9 follow-up review keeps no-promotion because formal SRR-main candidates were negative against the M8 nnU-Net anchor. |
| nnU-Net anchor | Strong baseline/context/evidence/safety source; not a replacement for SRR route definition. |
| Cine | Local proxy/final-output evidence exists, but no hosted readiness or route promotion is authorized by M9 follow-up. |
| Controller flow | v2 requires planner-authored execution mode, controller-supervised continuity for long Slurm work, mapper draft/final, deterministic finalizer, validator, then independent reviewer. |

See:

- [MODEL.md](MODEL.md)
- [EXECUTION.md](EXECUTION.md)
- [COMPONENTS.csv](COMPONENTS.csv)
- [LINEAGE.md](LINEAGE.md)
- [architecture.yaml](architecture.yaml)
- [toolkit_healthcheck.json](toolkit_healthcheck.json)
