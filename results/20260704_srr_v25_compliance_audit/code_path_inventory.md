# Code Path Inventory

## Task And Rules Read

- `AGENTS.md`
- `prompts/AGENT_RULES.md`
- `prompts/EXPERIMENT_ADEQUACY_GATE.md`
- `prompts/DIAGNOSTIC_PUBLICATION_GATE.md`
- `prompts/tasks/20260704_srr_v25_compliance_audit.md`
- `.agents/skills/agent-task-executor/SKILL.md`
- `.agents/skills/domains-medical-imaging-medical-imaging-deep-learning/SKILL.md`
- `.agents/skills/domains-medical-imaging-medical-imaging-deep-learning/references/reference.md`
- `/users/a/e/aereinh/.codex-global/skills/core-codex-system-codex-workflow-protocol/SKILL.md`

## Diagram Evidence

- `images/SRR-v2.png`
- `images/SRR-v2.5.png`
- Embedded diagram contract in `prompts/tasks/20260704_srr_v25_compliance_audit.md`

## Model And Loss Code

- `src/care_myocardium/models/srr_propref.py`
  - formal route class: `SRRProposeRefineMyoPS`
  - proposal dictionary: `ProposalDictionary`
  - full-volume residual refiner: `SoftROIRefinementHead`
- `src/care_myocardium/models/srr_v2_unet.py`
  - `ModalityEncoder`
  - `ScaleRetrieval`
  - `TaskDecoder`
  - `SRRV2MyoPSUNet`
- `src/care_myocardium/models/srr_myops.py`
  - older SRR lite path and `PathologyProposalHead`
- `src/care_myocardium/models/pathology_heads.py`
  - `AnatomyPathologyHeads`
- `src/care_myocardium/losses/srr_losses.py`
  - T2-masked edema training loss
  - scar/anatomy/retrieval/prior losses

## Runner And Job Code

- `scripts/training/run_srr_propref_myops_fold0.py`
  - formal training loop
  - decode functions
  - proposal/ROI/prediction sanity export
- `jobs/src/run_srr_propref_formal_myops_fold0.sh`
  - formal job wrapper
- `scripts/evaluation/run_nnunet_oof_component_20260703.py`
  - contrasting nnU-Net OOF component path that actually consumes nnU-Net predictions/probabilities/components

## Formal Run Evidence

- `results/20260703_srr_formal_training/result.md`
- `results/20260703_srr_formal_training/review.md`
- `results/20260703_srr_formal_training/metrics_summary.md`
- `results/20260703_srr_formal_training/prediction_sanity.md`
- `results/20260703_srr_formal_training/subgroup_metrics.csv`
- `results/20260703_srr_formal_training/proposal_pr_sweep.csv`
- `results/20260703_srr_formal_training/variants/*/summary.json`
- `results/20260703_srr_formal_training/variants/*/training_log.csv`
- `results/20260703_srr_formal_training/variants/*/prediction_sanity_checkpoint_*.csv`

## nnU-Net Anchor/Reference Evidence

- `results/20260703_nnunet_oof_component/review.md`
- `scripts/evaluation/run_nnunet_oof_component_20260703.py`
- `data/nnUNet/nnUNet_results/Dataset501_CAREMyoPS/nnUNetTrainer_500epochs__nnUNetPlans__3d_fullres/fold_0/validation/summary.json` as referenced by formal metrics
- `results/metrics/unified/nnUNet501/fold_0/evaluation_summary.json` as referenced by formal metrics

## Commands Run

- `find images docs/images docs/figures assets docs src prompts ...`
- `rg -n "SRR-v2|v2.5|Selective Representation Retrieval|..." ...`
- `nl -ba ... | sed -n ...` for source files
- `rg -n "nnU|nnunet|teacher|anchor|prob|component|checkpoint_best|npz|prediction|baseline|load_state|logits" ...`
- Python read-only CSV/JSON summaries for no-T2 edema counts, proposal precision/FP burden, and formal summary fields

No training, Slurm job, validation package, upload, model edit, or git action was run.
