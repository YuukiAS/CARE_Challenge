# Lesion Compact Failure Interpretation

Status: `COMPLETE`

## Cross-Variant Failure Mode

The compactness batch exposed useful but incomplete signals. The base D4 dictionary route remains the correct backbone for another repair round, but none of the tested lesion packages simultaneously improved Dice, HD95, component burden, remote false positives, no-T2 stability, and scar/edema balance.

A shared implementation caveat is that all four jobs ended by `max_steps` before the requested effective-time budget. The job wrappers have been updated to `--max-steps 1000000` for the next repeat.

## L1 `soft_anatomy_containment`

Soft containment improved sensitivity rather than compactness. It slightly raised edema GT-positive Dice and scar all-case Dice, but HD95 and component/remote-FP burden worsened sharply. This suggests the outside-union penalty was too weak or too indirect; it did not create a stable myocardium-localized lesion prior.

## L2 `component_compactness_loss`

The compactness proxy produced the clearest positive localization signal by improving both primary HD95 values relative to D4. However, it did not preserve scar Dice and did not sufficiently reduce no-T2 false positives or fragmented components. This is the best mechanism to revise, but it is not selectable as-is.

## L3 `scar_lge_fallback_boost`

The scar/LGE boost failed to improve scar. Scar Dice dropped and HD95 worsened, while edema also degraded. Dictionary usage shifted toward a few experts, consistent with the scar-weighted sampling/router changes narrowing the route rather than stabilizing an LGE fallback.

## L4 `edema_t2_center_balance`

The T2/CenterC balancing route collapsed on GT-positive edema and also harmed scar. Its low HD95 is mostly an empty-prediction artifact, not real localization improvement. This route should not be repeated without a Dice/recall guard.
