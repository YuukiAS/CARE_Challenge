# SRR-v3 M4 MyoPS Mechanism Ablation Readiness Result

status: `EXECUTED_UNAUDITED`
completion_state: `M4_READY_FOR_REVIEW`

## Summary

Ran `8` bounded inference ablations on the audited M3 checkpoint and listed `2` training-only ablations as `NOT_RUN_WITH_REASON`.

The evidence supports mechanism attribution for the current harmful/near-closed M3 behavior, but does not promote the route.

## Commands

- `scripts/evaluation/run_srr_v3_m4_mechanism_ablation.py --output-dir results/20260705_srr_v3_m4_myops_mechanism_ablation_readiness --m3-dir results/20260705_srr_v3_m3_myops_min_effective_pilot_training --m3-variant srr_v3_m3_shared_dual_dict_pilot --device cuda`
- Slurm submit: `sbatch --partition=a100-gpu --qos=gpu_access --gres=gpu:nvidia_a100-pcie-40gb:1 jobs/src/run_srr_v3_m4_myops_mechanism_ablation.sh`
- Slurm result: `57981754 COMPLETED 0:0 00:07:25`
