# CARE Documentation

This directory stores durable project documentation. For CARE Myocardium, the
source of truth is split as follows:

| Path | Purpose |
| --- | --- |
| `plans/` | Governed execution plans and controllers. Filenames must follow `plans/care_myocardium_plan_registry_rules.md`. |
| `notes/baseline/` | Durable baseline notes and tracked summaries of generated diagnostics. Use this for conclusions from ignored `results/diagnostics/` outputs. |
| `notes/deep_research/` | Deep research PDFs and extracted mechanism notes. Use as mechanism sources, not as direct authorization to clone/train external repos. |
| `notes/domain_adaptation/` | Domain adaptation relevance notes and constraints. |
| `archive/` | Retired root-level runbooks, historical notes, and presentation snapshots that should not drive current execution. |
| `literature/` | Local literature copies used for method/background review. |

For current CARE Myocardium status, read the top-level `README.md` first, then
the relevant `docs/plans/lane*_round*` controller or execution file.

For handoff/controller status semantics, use `prompts/CONTROLLER_TASK_PROTOCOL.md`,
`prompts/DIAGNOSTIC_PUBLICATION_GATE.md`, and
`prompts/EXPERIMENT_ADEQUACY_GATE.md`. Operational controller completion,
diagnostic publication, and scientific route resolution are separate decisions.
