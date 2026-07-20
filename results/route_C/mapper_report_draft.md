# Route C mapper draft

status: `ROUTE_LOCAL_DRAFT`

The mapper draft maps Route C merged code and evidence without editing root wiki. Root wiki remains at M09 reviewed state.

MyoPS route_C entrypoints inspected:

- `src/care_myocardium/route_C/myops/evidence_contract.py`
- `scripts/route_C/myops/replay_intervention_selector.py`
- `scripts/validation/route_C/myops/validate_lane_packet.py`

Cine route_C entrypoints inspected:

- `src/care_myocardium/route_C/cine/fidelity.py`
- `scripts/route_C/cine/preflight.py`
- `scripts/validation/route_C/cine/strict_validator.py`
- `scripts/validation/route_C/cine/known_bad_selftest.py`

Evidence state: MyoPS has real route_C replay/intervention evidence but fails the residual gate mechanism check. Cine has real adapter/preflight/known-bad execution but lacks required external anatomy weights and real case inputs for formal evidence.
