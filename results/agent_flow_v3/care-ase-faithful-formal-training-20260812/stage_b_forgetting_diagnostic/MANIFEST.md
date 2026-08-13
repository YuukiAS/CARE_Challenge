# Stage-B Forgetting Diagnostic Manifest

- task: `care-ase-faithful-formal-training-20260812`
- runtime_repo: `/users/a/e/aereinh/CARE/.worktrees/care-ase-faithful-formal-training-20260812`
- mode: read-only diagnostic evidence
- training_runtime_mutated: false
- outer_accessed_by_this_script: false
- updated_utc: `2026-08-13T18:45:37Z`
- slurm_status: `63560023:a100-gpu:COMPLETED:0:0:00:02:15;63587878:a100-gpu:COMPLETED:0:0:00:02:57`

## Completed GPU Diagnostic Runs

- `gpu_readonly_63560023` status=`PASS` device=`NVIDIA A100-PCIE-40GB` steps=`[2000, 6000]` selected_case_counts_by_fold=`{'2': 7, '3': 7}`
- `gpu_readonly_63587878_step4000` status=`PASS` device=`NVIDIA A100-PCIE-40GB` steps=`[4000]` selected_case_counts_by_fold=`{'2': 7, '3': 7}`

## Artifacts

- `DIAGNOSTIC_REPORT_FOR_GPT.md` sha256=`05f22b8e9b378abbf0757638c5b10a47b3517c225cf195d34f817631097bc63e`
- `diagnostic_summary.json` sha256=`fb6d5e2cb7c34bfc6731899100a7c4a77b9364133dd1089e7bb5e5c634d79a94`
- `subgroup_checkpoint_trend.csv` sha256=`70ccff96c6f9627007d559c1196259d45b5e880a6972f320efb3f625b34b5435`
- `actual_train_vs_inner_partial.csv` sha256=`df50dfeee48d8508a8f005a21882bcef7018a8e02c9990031ecbaf149d4a4eaa`
- `logit_margin_trend.csv` sha256=`2526558251b1c1e18ea4e000172cf0db6feeb4b925edc4da845eb5afdcb76797`
- `logit_margin_summary.csv` sha256=`9340f9a3b59f3a76a66a50c89c44edcf9f195eecb04396c7020921fdaac88ada`
- `extent_wall_intervention.csv` sha256=`43720738ff342785494cee548d7be03c96d804524552629addbe817aa6047a87`
- `extent_wall_intervention_summary.csv` sha256=`d53d62d36fab3d7dd22ac2bd62fce98b559cec5feaaeec32291ef82ca76503f3`
- `evidence_intervention.csv` sha256=`9b20d00d636fe8be8c4075710ba79a152cc8d138ee02433deae5d5257e9e6b61`
- `evidence_intervention_summary.csv` sha256=`f34744376b9e3eac9ae5623383f2bbc7f37a843111ee2a7195fcdc9261257288`
- `parameter_drift.csv` sha256=`01b2a899236ba0c5f9c57539fdc7897af86de09823427be37157d7af0ec83ffe`
- `sampler_effective_supervision.csv` sha256=`683492289f095a500139c21a85b2eadbc7d73bb16b6020e6a78c76a0fc94c641`
- `runtime_semantic_audit.json` sha256=`ec31dd7e65605e0e0cc104c669469fbf507aacda34325ea3f2c5bc7446bb9cc1`
