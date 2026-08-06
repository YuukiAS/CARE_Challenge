# CARE Agent-Flow v3 Visual Smoke Contract

This task is an isolated scheduled-GPT visual smoke. It must not start Codex
Controller, Verifier, Executor, CARE-ASE implementation, training, outer access,
Docker, upload, organizer email, or a `develop` to `main` merge.

The scheduled Planner and scheduled Critic must independently visually inspect:

- `docs/architecture/figures/CARE-ASE.png`
- `docs/architecture/figures/SRR-v3.png`
- `docs/architecture/figures/MoSAIC.png`

Each scheduled role must write a separate receipt under:

```text
results/agent_flow_v3/care-visual-smoke/planner_visual_receipt.json
results/agent_flow_v3/care-visual-smoke/critic_visual_receipt.json
```

Each receipt must bind the task nonce and the SHA256 of all three images, and
must answer:

- main modules visible in each diagram;
- key data flow;
- missing-modality and no-T2 safety rules;
- components explicitly absent from the figure;
- structural differences between CARE-ASE, SRR-v3, and MoSAIC.

The smoke passes only when both receipts are committed by the real scheduled GPT
tasks on `origin/develop`. Filename, README, prior summary, raw URL metadata, or
Codex-authored observations do not satisfy this contract.
