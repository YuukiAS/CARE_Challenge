# Project Agent-Flow v3 Role Authority Adapter

Use `automation/agent_flow_v3/ROLE_AUTHORITY_POLICY.md` as the invariant policy.
Fill only the project-specific adapter fields below.

## Project Bootstrap Files

```text
<path/to/project/rules>
<path/to/scientific_or_task_contract>
<path/to/runtime_binding.example.json>
```

## Project-Specific Critical Paths

```text
<implementation paths>
<verification paths>
<runtime receipt paths>
```

## Project-Specific Authorizations

```text
training_authorized: false
outer_or_external_private_data_authorized: false
deployment_or_upload_authorized: false
promotion_branch_authorized: false
```

## Project-Specific Verifier Probes

List verifier probes that are allowed by requirement IDs. Diagnostics without a
requirement ID must remain non-blocking until Planner adjudication.
