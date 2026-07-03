# CARE Prompts

This directory stores reusable prompts and historical execution prompts. Active
project state should live in `README.md` and governed plans under `docs/plans/`;
prompts are source material, not the source of truth. The former root
`TODO.md` roadmap has been retired.

## Layout

| Path | Purpose |
| --- | --- |
| `Baseline/` | Archived baseline-improvement prompts for MyoPS-Net, U-MyoPS, and CineMyoPS. These are historical inputs for negative evidence and should not be treated as current mainline plans. |
| `LaneA/` | Lane A MyoPS prompt drafts for later rounds. Use the matching `docs/plans/laneA_roundXX_*` file as the controller before executing. |
| `DeepResearch/` | Deep research prompt material and mechanism-source notes. External methods still require license, compliance, input/output, label mapping, and one-case smoke gates before use. |
| `CARE_Challenge_Analysis.md` | General CARE challenge analysis prompt/material. |
| `Baseline_report.md` | Legacy baseline reporting prompt/material. |
| `DIAGNOSTIC_PUBLICATION_GATE.md` | Migration note and policy split between route promotion and diagnostic artifact publication. |
| `EXPERIMENT_ADEQUACY_GATE.md` | Migration note and policy split between operational completion and scientific route resolution. |

## Rules

- Do not execute directly from a prompt if it conflicts with `docs/plans/care_myocardium_plan_registry_rules.md`.
- Do not treat old baseline prompts as authorization to continue patching third-party baselines as the mainline.
- For current CARE Myocardium execution, start from `README.md` and the relevant `docs/plans/` file.
- For handoff/controller publication decisions, distinguish `route_promotion_gate` from `diagnostic_publication_gate`. Diagnostic publication can make reviewed evidence visible to GPT planning, but it is not model promotion or validation readiness.
- For model/training route conclusions, distinguish controller operational completion from `scientific_resolution_status`. Undertrained or smoke-scale experiments cannot support `STOP_NO_*` route-negative conclusions.
