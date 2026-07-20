# Cine Call Graph Truth

Batch 0 did not run Cine training or inference. This file records the current
static implementation truth.

## Legacy B7 Path

`scripts/training/route_B_round04/cine/B7/run_B7_cinema_control.py`

```text
manifest JSON
  -> case_count only
  -> run_official_cinema_probe()
       -> external CineMA source/weight/config probe on a zero tensor
       -> provenance/parameter-count receipt
  -> RouteBRound03CineMAAdapter()
       -> train_adapter()
            -> frame = torch.randn(...)
            -> synthetic target = torch.zeros(...)
            -> MSE(features.mean repeat, target)
       -> save B7_pretrained_adapter.pt and B7_random_adapter.pt
       -> per_frame_feature_manifest.csv
```

Truth classification:

- real 4D cine file: declared in manifest, not read by B7.
- ED/reference/key frames: absent.
- official CineMA weights: probed for provenance only.
- official logits/features/uncertainty downstream: absent.
- downstream adapter: local Conv3d wrapper trained on synthetic frames.
- temporal aggregation: absent.
- export: absent.
- scientific status: synthetic/proxy, forbidden formal entrypoint.

## Legacy B8 Path

`scripts/training/route_B_round04/cine/B8/run_B8_registration.py`

```text
manifest JSON
  -> case_ids only
  -> B7 completion token and per_frame_feature_manifest existence check
  -> RouteBRound04CineRegistration()
       -> train_registration()
            -> make_pair()
                 -> fixed = torch.randn(...)
                 -> moving = torch.roll(fixed) + noise
            -> loss = MSE(warped, fixed) + smoothness + inverse
       -> build_receipts()
            -> make_pair() again for synthetic frame labels
            -> record reference_frame='ED' string
       -> syn_control_rows()
            -> shutil.which(antsRegistrationSyNQuick.sh or antsRegistration)
            -> currently records ANTS_EXECUTABLE_NOT_FOUND when absent
```

Truth classification:

- real 4D cine file: manifest contains paths, B8 does not read them.
- ED/reference/key frames: ED is a receipt label, not a real frame policy.
- registration fixed/moving pair: synthetic random/rolled tensors.
- transform/warp: normalized-grid `grid_sample` helper from Route B Round03,
  not a persisted physical-space transform or ED-space export.
- copy/identity warp: not the main issue; no real image warp/export exists.
- temporal aggregation: absent.
- downstream B7 consumption: token/file existence only; B7 checkpoint and
  official CineMA features are not loaded.
- missing executable: SyN control can record `ANTS_EXECUTABLE_NOT_FOUND`.
- scientific status: synthetic/proxy, forbidden formal entrypoint.

## Existing Real Cine-Related Paths Outside B7/B8

- `scripts/submission/prepare_care_myocardium_validation.py` contains real
  CineMyoPS validation packaging and frame staging helpers, but validation
  packaging/upload is outside Batch 0 and not part of B7/B8 authority.
- `scripts/external_adapters/cinema_care_adapter.py` contains a separate
  adapter for CARE CineMyoPS raw 4D cine, but it is not wired into current
  formal SRR production entrypoints.

## Batch 1 Repair Target

Batch 1 must add or bind an existing real Cine path that:

1. reads `data/CARE_Challenge/CineMyoPS_train` or approved validation inputs as
   real 4D files;
2. records ED/reference/key-frame policy from the real volume;
3. routes official CineMA logits/features/uncertainty into downstream tensors;
4. constructs real fixed/moving frame pairs and records transform family;
5. performs temporal aggregation and ED-space output/export; and
6. fails formal authority if any of these are replaced by synthetic pairs or
   probe-only receipts.
