# Legacy Hardcode Scan

Allowed concrete milestone references:

- immutable `wiki/history/M*/` content;
- task-specific result packets;
- legacy regression fixtures;
- synthetic tests using `M12`, `M27`, or `M103`.

Forbidden active-surface scan:

```text
rg concrete milestone tokens over active policy, templates, skills, generic scripts
```

Result after repair: no concrete milestone-number control-flow references found
in active policy/templates/skills/generic validator and ops scripts.
