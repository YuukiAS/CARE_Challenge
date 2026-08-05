# CARE-ASE R2 step6000 stop decision

CARE-ASE 已按用户设定跑到 fold1/fold4 均 verified step6000，并完成同口径 held-out diagnostic fair comparison。step6000 仍未达到理想结果，因此已停止训练并取消相关 running/pending Slurm job。

## Step6000 result

| Metric | CARE-ASE | nnU-Net OOF | MoSAIC reference | CARE - nnU-Net | CARE - MoSAIC |
|---|---:|---:|---:|---:|---:|
| Scar Dice mean, 88 cases | 0.441313 | 0.567296 | 0.754335 | -0.125983 | -0.313022 |
| Pure-edema Dice mean, 32 T2-present cases | 0.400175 | 0.403762 | 0.405754 | -0.003587 | -0.005579 |

## Best observed checkpoints through step6000

| Target | Best step | CARE mean Dice | Delta vs nnU-Net | Delta vs MoSAIC |
|---|---:|---:|---:|---:|
| Scar | 500 | 0.549352 | -0.017943 | NA |
| Pure-edema | 3000 | 0.414737 | 0.010930 | 0.008983 |

Training stopped by user-defined step6000 rule. No validation upload, Docker upload, or organizer email was performed.
