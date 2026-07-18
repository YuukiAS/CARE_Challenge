# Route B Round03 Architecture Delta Draft

created_at_utc: `2026-07-18T10:39:46Z`

This draft records route-local architecture deltas only. It does not update root wiki files and does not make a scientific decision.

Route-local additions:

- Full Round03 route_B namespace under `src/care_myocardium/route_B_round03/`.
- Formal B3-B9 training entrypoints under `scripts/training/route_B_round03/`.
- Strict validators under `scripts/validation/route_B_round03/`.
- Slurm wrappers under `jobs/route_B_round03/`.
- Controller evidence namespace under `results/route_B/round03/`.

Current evidence boundary:

- B0-B2 are locally verified.
- B3 is pending and therefore unverified.
- B4-B10 are not executed.

Pre-review decision fields:

- route_promotion_decision: `NOT_REVIEWED`
- route_negative_decision: `NOT_REVIEWED`
- scientific_resolution_status: `AWAITING_REVIEW`

Forbidden actions performed: none.
