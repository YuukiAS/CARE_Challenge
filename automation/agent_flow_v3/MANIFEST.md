# CARE Agent-Flow v3 bootstrap manifest

## Current status

The v3 policy and bootstrap assets are committed on `main`. The remote `develop` branch was created from the policy head for the future CARE-ASE faithful reimplementation experiment.

The live loop is intentionally not armed yet:

```text
REQUEST.enabled: false
CURRENT.state: PLAN_REQUESTED
next_action: CONFIGURE_VISUAL_SOURCES_AND_SCHEDULED_TASKS_THEN_ENABLE_REQUEST
```

This prevents the scheduled Planner, Critic or Codex runtime from starting before direct visual sources and exact task bindings are ready.

## Canonical files

```text
prompts/AGENT_FLOW_V3_PROTOCOL.md
automation/agent_flow_v3/README.md
automation/agent_flow_v3/schema.json
automation/agent_flow_v3/task_template.json
automation/agent_flow_v3/planner_scheduled_task_prompt.md
automation/agent_flow_v3/critic_scheduled_task_prompt.md
scripts/automation/validate_agent_flow_v3.py
tests/automation/test_agent_flow_v3.py
.github/workflows/agent-flow-v3-ci.yml
```

## CARE-ASE first-use files

```text
prompts/tasks/20260805_care_ase_develop_faithful_reimplementation_loop.md
prompts/tasks/20260805_care_ase_develop_faithful_reimplementation_role_plan.json
prompts/tasks/20260805_care_ase_develop_faithful_reimplementation_controller.md
automation/agent_flow_v3/tasks/care-ase-faithful/REQUEST.json
automation/agent_flow_v3/tasks/care-ase-faithful/CURRENT.json
automation/agent_flow_v3/tasks/care-ase-faithful/VISUAL_SOURCES.json
```

## Activation prerequisites

1. Provide stable visual access for every required diagram and pass a scheduled-GPT visual smoke.
2. Create or update the persistent Planner and Critic scheduled tasks from the tracked prompts.
3. Compute and bind the frozen contract SHA after Critic freeze.
4. Set REQUEST `enabled=true` with a new nonce and update CURRENT last.
5. Start the persistent Controller only after CURRENT reaches `PLAN_FROZEN`.

## Safety boundary

No current or historical CARE-ASE training process, checkpoint, permit, Docker artifact or `CURRENT.md` history is modified by this bootstrap. No training, outer access, deployment, upload or merge from `develop` to `main` is authorized.