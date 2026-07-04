# Audit Notes

## Scope

This executor performed a read/report-only compliance audit for `prompts/tasks/20260704_srr_v25_compliance_audit.md`.

No training, Slurm job, validation packaging, upload, fold expansion, model edit, runner edit, or git commit/push was performed.

## Commands Run

Read rules and task:

```bash
sed -n '1,260p' AGENTS.md
sed -n '260,520p' AGENTS.md
sed -n '1,240p' .agents/skills/agent-task-executor/SKILL.md
sed -n '1,280p' .agents/skills/domains-medical-imaging-medical-imaging-deep-learning/SKILL.md
sed -n '1,260p' .agents/skills/domains-medical-imaging-medical-imaging-deep-learning/references/reference.md
sed -n '1,300p' prompts/tasks/20260704_srr_v25_compliance_audit.md
sed -n '1,260p' prompts/AGENT_RULES.md
sed -n '1,260p' prompts/EXPERIMENT_ADEQUACY_GATE.md
sed -n '1,260p' prompts/DIAGNOSTIC_PUBLICATION_GATE.md
```

Find diagrams and text evidence:

```bash
find images docs/images docs/figures assets docs src prompts -maxdepth 4 ...
rg -n "SRR-v2|SRR v2|v2\\.5|Selective Representation Retrieval|..." ...
```

Inspect code:

```bash
nl -ba src/care_myocardium/models/srr_propref.py | sed -n '1,280p'
nl -ba src/care_myocardium/models/srr_v2_unet.py | sed -n '1,280p'
nl -ba src/care_myocardium/models/srr_myops.py | sed -n '1,320p'
nl -ba src/care_myocardium/models/pathology_heads.py | sed -n '1,260p'
nl -ba src/care_myocardium/losses/srr_losses.py | sed -n '1,360p'
nl -ba scripts/training/run_srr_propref_myops_fold0.py | sed -n '1,1160p'
nl -ba jobs/src/run_srr_propref_formal_myops_fold0.sh | sed -n '1,220p'
nl -ba scripts/evaluation/run_nnunet_oof_component_20260703.py | sed -n '1,320p'
```

Search for nnU-Net anchors:

```bash
rg -n "nnU|nnunet|teacher|anchor|prob|component|checkpoint_best|npz|prediction|baseline|load_state|logits" \
  src/care_myocardium/models/srr_propref.py \
  src/care_myocardium/models/srr_v2_unet.py \
  src/care_myocardium/models/srr_myops.py \
  scripts/training/run_srr_propref_myops_fold0.py \
  src/care_myocardium/losses/srr_losses.py
```

Summarize existing result CSV/JSON:

```bash
python - <<'PY'
# read-only CSV/JSON summaries for prediction_sanity, proposal_pr_sweep, summary.json
PY
```

One optional dynamic model parameter-count command was interrupted after hanging on import. The audit does not rely on that command.

## Caveats

- This is executor self-assessment only. A separate auditor should review these files before diagnostic publication.
- The formal training audit already classified the run as `SCIENTIFIC_UNDERTRAINED` due to the explicit train-loop-seconds gate. This audit adds architecture compliance evidence and does not override the need for review.
- The diagram images exist in `images/`, but the report maps primarily against the embedded task contract and visible diagram blocks.

## Forbidden Actions Avoided

- no new training
- no validation package or upload
- no fold expansion
- no model/runner/loss code edit
- no git commit or push
- no recommendation to continue current PropRef with only more steps/time
