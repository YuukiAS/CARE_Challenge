# Documentation Update Summary

## Files Updated

- `prompts/AGENT_RULES.md`
- `prompts/CHATGPT_RULES.md`
- `prompts/templates/CONTROLLER_TASK_TEMPLATE.md`
- `prompts/CARE_OVERLAY_GATES.md`

## Summary

Docs/templates now explicitly reference:

- `prompts/HANDOFF_GATE_POLICY.md`
- `prompts/GPT_HARD_GATE_PROMPT.md`

The updated text requires high-risk CARE controller work to enforce:

- exact ordered task graph;
- exact `results/<task_key>/` directories;
- exact required output filenames;
- strict validator nonzero exit on errors;
- completion-check readiness before final audit;
- terminal controller report fields;
- minimum effective training / smoke-scale evidence classification;
- current bad packet regression when applicable.

## Scope Control

The docs update does not authorize validation packaging, upload, fold expansion, hosted metric claims, or new SRR/Cine route planning.
