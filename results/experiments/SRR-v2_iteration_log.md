# SRR-v2 Iteration Log

## 2026-07-02 targeted/capacity/balanced extras

Context: required repaired proposal, SRR-v2, cascade teacher, and Cine secondary routes completed, but none selected a route that approaches the nnU-Net reference gates. The best first-party SRR-v2 scar signal so far is `srr_v2_capacity12_hardneg` with scar all-case Dice `0.3090`, still below the conservative 80% nnU-Net floor `0.4481`. Best edema GT-positive signal remains below the `0.3155` floor.

Current round keeps fold/evaluator/labels unchanged and tests narrow hypotheses rather than expanding folds:

| route | job | variants | hypothesis | status at 2026-07-02 02:59 EDT |
| --- | --- | --- | --- | --- |
| `srr_v2_targeted_extras` | `57334792_[0-1]` | `srr_v2_edema_t2_focus`; `srr_v2_scar_precision_nointeract` | Test whether edema improves from stronger T2-positive sampling and whether scar improves from hard-negative precision with interactions disabled. | Running on `htzhulab`, about `1h13m`; no formal summary/metrics yet. |
| `srr_v2_capacity_targeted_extras` | `57354982_[0-1]` | `srr_v2_capacity12_edema_t2_focus`; `srr_v2_capacity12_scar_precision_nointeract` | Repeat the same focused probes with base_channels `12`, because prior capacity extras gave the strongest scar signal. | Pending on `htzhulab`; next wait-policy recheck after `2026-07-02 04:29:25`. |
| `srr_v2_balanced_targeted_extras` | `57358073_[0-1]` | `srr_v2_capacity12_balanced_lowmix`; `srr_v2_capacity12_scar_precision_interact` | Test whether low proposal final mix preserves evidence signal and whether scar precision needs cross-modal interactions rather than disabling them. | Pending on `htzhulab`; next wait-policy recheck after `2026-07-02 04:51:50`. |

Preflight evidence:

- `results/20260629_srr_v2_unet_core/targeted_extras_cpu_preflight/README.md`
- `results/20260629_srr_v2_unet_core/capacity_targeted_extras_cpu_preflight/README.md`
- `results/20260629_srr_v2_unet_core/balanced_targeted_extras_cpu_preflight/variants/srr_v2_capacity12_balanced_lowmix/summary.json`
- `results/20260629_srr_v2_unet_core/balanced_targeted_extras_cpu_preflight/variants/srr_v2_capacity12_scar_precision_interact/summary.json`

Aggregation commands:

```bash
./envs/env_CARE/bin/python scripts/evaluation/finalize_rescue_srr_route.py --route srr_v2_targeted_extras
./envs/env_CARE/bin/python scripts/evaluation/finalize_rescue_srr_route.py --route srr_v2_capacity_targeted_extras
./envs/env_CARE/bin/python scripts/evaluation/finalize_rescue_srr_route.py --route srr_v2_balanced_targeted_extras
```

Decision rule: do not select a route merely for improving over weak SRR. Compare against nnU-Net reference floors and inspect `myops_scar` all-case Dice, `myops_edema` GT-positive Dice, HD95, component burden, remote FP, and no-T2 behavior. If none of the six active variants improves materially over `srr_v2_capacity12_hardneg`, the mechanism interpretation should remain that current SRR-v2 is still capacity/proposal/decoder-limited relative to nnU-Net and cascade-style anatomy localization.
