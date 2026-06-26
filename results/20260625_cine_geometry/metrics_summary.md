# CineMyoPS Reference-Frame Preflight

## Setup

- source predictions: `results/cinema_adapter/20260619_131229__cinema_acdc_seed0_ed_mid_repr/predictions/train/*/*_t00_cinema_acdc_s0.nii.gz`
- case filter: `results/20260625_cine_geometry/safe_cases.csv`
- prediction remap: CineMA `2` -> CARE compact myocardium `1`, CineMA `3` -> CARE compact LV `2`; no scar output is produced by this anatomy prior.
- reference frame: raw Cine frame 0.

## Metadata Gates

- prediction metadata matched frame0 for all safe cases: True
- label metadata matched frame0 for all safe cases: True

## Metrics

| metric | mean | median |
| --- | ---: | ---: |
| class_1_myocardium_dice | 0.5626 | 0.6688 |
| class_1_myocardium_hd95 | 11.3331 | 6.0000 |
| class_2_lv_dice | 0.7709 | 0.9082 |
| class_2_lv_hd95 | 11.0440 | 6.0000 |
| class_3_scar_sanity_dice | 0.0000 | 0.0000 |
| class_3_scar_sanity_hd95 | NA | NA |

## Interpretation

- scar-positive safe cases: 58
- cases with scar-like class-3 prediction after CineMA remap: 0
- The class-3 scar sanity metric is expected to fail for this frozen anatomy prior because CineMA has no scar head; this is a negative control, not a submission-ready pathology model.
- The myocardium/LV anatomy signal and metadata gate are sufficient to proceed to a temporal/anatomy preflight on the safe subset.
