# Route B Round03 Mapper Report Draft

created_at_utc: `2026-07-18T10:39:46Z`

Mapper status: `DRAFT_PENDING_B3_RUNTIME`

Inspected current route-local surfaces:

- `src/care_myocardium/route_B_round03/model.py`: Route B Round03 MyoPS SRR-v3 model scaffold with canonical `[LGE,T2,C0]`, four scales, 16 experts per scale, OOF prototype-bank surface, proposal/refiner paths, bounded deltas, and exact no-T2 edema zero policy.
- `src/care_myocardium/route_B_round03/cinema.py`: route-local CineMA provenance and adapter surface.
- `src/care_myocardium/route_B_round03/registration.py`: seven-step SVF scaling-and-squaring registration surface.
- `src/care_myocardium/route_B_round03/temporal.py`: temporal model consuming reference evidence, registered evidence, velocity, displacement, Jacobian, motion, quality, position, and valid mask fields.
- `scripts/route_B_round03/run_implementation_gate.py`: B2 gate with official CineMA code/weight/config/forward proof.
- `scripts/training/route_B_round03/*.py`: B3-B9 training entrypoints.
- `jobs/route_B_round03/*.sh`: Slurm wrappers and B3 atomic race lock setup.

Evidence status:

- Source-level implementation: `partial`, because B3-B9 formal runtime evidence is not terminal.
- B0 evidence: `verified`.
- B1 static test evidence: `verified`.
- B2 official CineMA/implementation evidence: `verified`.
- B3-B9 runtime evidence: `missing` until Slurm jobs run and aggregate.
- B10 final packet evidence: `missing`.

No root wiki update is made in this draft. Final mapper status must be rerun after B3-B10 runtime evidence is terminal.
