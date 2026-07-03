# Mechanism Gate Template

Use this file as a generic evidence-gate pattern. Project-specific repositories
should define their own domain gates in `AGENTS.md`, project rules, or skills,
then reference those gates from task frontmatter.

## Gate Name

`<gate-name>`

## Mechanism Class

`<bugfix | feature | refactor | documentation | release | audit | experiment | other>`

## Completion Definition

- What user-visible or repository-visible behavior must change?
- What files, commands, tests, or artifacts prove the change?
- What must remain unchanged?

## Forbidden Substitutes

- Workarounds that look similar but do not satisfy the goal.
- Cosmetic edits that do not affect the required behavior.
- Evidence from unrelated files, stale logs, or unreviewed self-assessment.

## Required Evidence

- File or diff evidence:
- Command evidence with exit status:
- Test or validation evidence:
- Artifact or manifest evidence:
- Audit/review evidence:

## Experiment Adequacy Gate

For model/training mechanisms, define the minimum experiment evidence required
before promotion or a route-negative stop can be supported:

- one-batch or one-case overfit sanity:
- minimum optimizer steps:
- minimum train-loop seconds:
- actual steps and optimizer steps:
- validation events:
- loss decrease:
- prediction sanity:
- proposal/refinement sanity, if applicable:
- logs, config, checkpoint, prediction, metric, and cache provenance:
- same-split baseline comparability:

## Promotion Gate

Promotion is allowed only when all required claims are supported by evidence and
the auditor decision is `AUDITED_GO` or the task explicitly waives review.

## Route Negative Gate

A scientific route-negative stop is allowed only when the experiment adequacy
gate passes, forbidden substitutes are absent, the same-split baseline
comparison exists, failure is not explained by undertraining or pipeline bugs,
and an auditor explicitly supports the route-negative conclusion.

If this gate fails, use `SCIENTIFIC_UNDERTRAINED`,
`SCIENTIFIC_PIPELINE_BUG`, `SCIENTIFIC_NEEDS_EVIDENCE`,
`SCIENTIFIC_NEEDS_REVISION`, or `SCIENTIFIC_UNRESOLVED` instead of
`STOP_NO_SIGNAL`-style conclusions.

## Failure Escalation Policy

- What can the execution controller try within this task?
- What must stop and return `NEEDS_GPT_PLANNER`?
- What requires human approval?
