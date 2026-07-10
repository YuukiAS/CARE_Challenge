# Architecture Delta Final

This repair changed system observability and handoff architecture only.

## Current wiki

- `wiki/COMPONENTS.csv` and `wiki/architecture.yaml` now share the same current component ID set.
- Current model and gap diagrams are generated from machine-readable sources.
- `controller_continuity` and `mapper_wiki_observability` remain `partial` / `unverified` until real controller runtime evidence exists.

## History wiki

- M8 and M9 originals are archived with SHA256 and drive migration coverage.
- M8 and M9 history diagrams no longer present a flat chain of anonymous historical relationships.
- M09 delta now explicitly shows:
  - loss wiring fixed
  - anchor-residual to SRR-main final output shift
  - dictionary still global
  - Pattern-SIP still alias-like
  - prototype memory not closed
  - refiner causal evidence insufficient
  - checkpoint selection incomplete
  - Cine still local proxy

## Protocol impact

Future M10 or system-level milestones must list history files read. Long milestone staging files must split active executor/controller/mapper content into shared executor prompts and reviewer content into shared reviewer prompts, while keeping executor plans under `prompts/tasks/<task_key>_executor_plan.yaml`.
