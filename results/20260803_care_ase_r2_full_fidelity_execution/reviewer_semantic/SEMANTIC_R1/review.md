# CARE-ASE R2 Semantic Oracle Review

Decision: `REVISE_CONTINUE_CURRENT_GOAL`

该候选不能给语义 PASS。源码中正式 Slurm wrapper 的单 chunk walltime 为 12 小时，超过合同冻结的每 job 不超过 8 小时；同时本轮语义 oracle 没有独立重跑 GPU case coverage，只能把已有 G2 GPU receipt 当辅助证据。按用户规则，高风险未验证项必须返回 REVISE。

## Findings
- `SEMANTIC_R1_001_FORMAL_CHUNK_WALLTIME_EXCEEDS_CONTRACT` (critical): `jobs/care_ase_r2/run_fold_chunk_htzhulab.sh:8` expected Formal CARE-ASE R2 training chunks request no more than 8 hours per job. observed Wrapper requests 12:00:00, i.e. 12.0 hours, exceeding the frozen chunk budget. Repair: Change the formal wrapper walltime to <=8h and rerun affected source hash / wrapper / semantic reviewer gates before crediting formal training launched through this wrapper.
- `SEMANTIC_R1_002_GPU_CASE_COVERAGE_NOT_INDEPENDENTLY_RERUN_BY_SEMANTIC_ORACLE` (critical): `results/20260803_care_ase_r2_full_fidelity_execution/g2_real_gpu_fidelity_receipt_fold{1,4}.json; gpu_case_coverage_oracle.json` expected This semantic review independently reruns or otherwise directly verifies complete CenterB, complete CenterC, LGE-only, LGE+C0, small scar, no-T2 zero-gradient, sampler, scheduler, resume, and module-off checks on GPU. observed Existing project GPU receipts are present and report PASS on H100 for folds 1 and 4, but this semantic oracle did not independently rerun GPU coverage in this review process; marked high_risk_unverified=true. Repair: Run an independent semantic GPU oracle under the reviewer namespace, bind its command/device/case coverage to this candidate SHA, and resubmit a new immutable candidate/review packet.

## Oracle Summary
- `MODEL_STOCK_INHERITANCE`: `PASS` (source inspection)
- `DYNAMIC_INTROSPECTION`: `PASS` (source inspection)
- `ZERO_INIT_EVIDENCE`: `PASS` (source inspection)
- `NO_STOCK_PATHOLOGY_FALLBACK`: `PASS` (source inspection with decode oracle)
- `PHYSICAL_TARGETS`: `PASS` (physical_target_oracle.json)
- `LOSS_NO_T2`: `PASS` (loss_formula_oracle.json)
- `SAMPLER_AB_400`: `PASS` (sampler_composition_oracle.json)
- `SAMPLER_STAGE_C`: `PASS` (sampler_composition_oracle.json)
- `CANONICAL_OOF`: `PASS` (canonical_stock_oof_oracle.json)
- `PARAM_GROUP_ID`: `PASS` (parameter_group_oracle.json)
- `EXACT_RESUME_DESCRIPTOR`: `PASS` (exact_resume_oracle.json)
- `GPU_CASE_COVERAGE`: `UNVERIFIED` (gpu_case_coverage_oracle.json)
- `FORMAL_WRAPPER_WALLTIME`: `FAIL` (jobs/care_ase_r2/run_fold_chunk_htzhulab.sh:8)

Note: sampler/resume oracles used the candidate checkout source with the read-only main CARE data root because `data/benchmarks/protocol/cases_MyoPS.json` is untracked and absent from detached git worktrees.
Temporary outputs: `/users/a/e/aereinh/.tmp/codex-CARE/20260803_care_ase_r2_full_fidelity_execution/reviewer_semantic_oracles/SEMANTIC_R1/a527f5e7a569c5378b2e66582fd978af6ba1ef07`
Tracked outputs: `/users/a/e/aereinh/CARE/results/20260803_care_ase_r2_full_fidelity_execution/reviewer_semantic/SEMANTIC_R1`
