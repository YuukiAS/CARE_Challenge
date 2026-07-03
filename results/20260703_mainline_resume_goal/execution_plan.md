# Execution Plan: 20260703 Mainline Resume Goal

status: AUDITED_DIAGNOSTIC_PUBLISH
controller_task: `prompts/tasks/20260703_mainline_resume_goal.md`

diagnostic publication only; no route promotion

## Priority And Boundaries

MyoPS was primary. The controller launched
`prompts/tasks/20260703_srr_formal_training.md` first using formal GPU training
and `MAX_STEPS>=1800`.

Cine was secondary. The controller launched
`prompts/tasks/20260703_cine_temporal_resume.md` only after MyoPS Slurm jobs
completed and the MyoPS diagnostic packet was audited.

Hard boundaries preserved:

- no `MAX_STEPS=120`;
- no CPU smoke, syntax check, pending Slurm job, or step-1 checkpoint used as
  formal completion;
- no validation upload, upload-ready packaging, fold expansion,
  label/evaluator/fold split change, old SRR-v2 route, or learned anchor-refine
  training.

## Subagents

- SRR formal training executor: `019f28f4-9fec-7da3-9d7e-02230d4df19b`
- SRR formal aggregation executor: `019f2905-4675-79f1-89f0-b75701ea5a4e`
- SRR formal training auditor: `019f290b-64f7-7f50-9b90-46ec030f5d8b`
- Cine temporal executor: `019f290f-cdeb-7a82-a258-b709ded31677`
- Cine temporal auditor: `019f2916-404a-7e73-a690-04039c4f0cb8`

## MyoPS Formal Training

Slurm array `57655472` was submitted on `htzhulab` through:

```bash
sbatch --array=0-2 jobs/src/run_srr_propref_formal_myops_fold0.sh
```

Final Slurm accounting:

| array_task | variant | state | exit | elapsed |
| --- | --- | --- | --- | --- |
| `57655472_0` | `srr_propref_shared_dual_dict` | `COMPLETED` | `0:0` | `00:08:30` |
| `57655472_1` | `srr_propref_scar_precision` | `COMPLETED` | `0:0` | `00:07:47` |
| `57655472_2` | `srr_propref_no_proto_cascade` | `COMPLETED` | `0:0` | `00:06:21` |

Output root: `results/20260703_srr_formal_training/`

Final audited state:

- `experiment_adequacy_decision: FAIL`
- `route_promotion_decision: NOT_EVALUABLE`
- `route_negative_decision: STOP_NOT_SUPPORTED`
- `scientific_resolution_status: SCIENTIFIC_UNDERTRAINED`
- `diagnostic_publication_decision: PUBLISH_REVIEWED_DIAGNOSTIC_PACKET`

## Cine Temporal Resume

Cine was executed as CPU-only local diagnostic work after MyoPS audit. Output
root: `results/20260703_cine_temporal_resume/`

Final audited state:

- `audit_decision: AUDITED_DIAGNOSTIC_PUBLISH`
- `route_decision_recommendation: TEMPORAL_PROXY_SIGNAL_DIAGNOSTIC`
- `experiment_adequacy_decision: PARTIAL`
- `route_promotion_decision: NO_PROMOTION`
- `route_negative_decision: STOP_NOT_SUPPORTED`
- `scientific_resolution_status: SCIENTIFIC_UNRESOLVED`
- `diagnostic_publication_decision: PUBLISH_REVIEWED_DIAGNOSTIC_PACKET`

## Final Controller Action

Publish only the curated reviewed diagnostic packet listed in
`results/20260703_mainline_resume_goal/controller_report.md`. Do not publish
checkpoints, predictions, NIfTI outputs, full result trees, heavy logs, upload
packages, credentials, or environment dumps.
