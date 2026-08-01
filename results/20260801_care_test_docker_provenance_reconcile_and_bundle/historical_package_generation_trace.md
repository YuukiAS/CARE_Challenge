# Historical Package Generation Trace

自然结论：package A 的完整数组差异不是单纯 scar 替换问题。按语义标签审计，生产会使用的 anatomy `1/2/3` 与 pure edema `4` 也没有达到 15/15 exact；历史 hosted lineage 仍未闭合。更关键的是，当前冻结部署源第二次 fresh replay 与上一轮 fresh replay 也只达到 7/15 array exact，虽然 geometry 是 15/15，因此本任务在部署源可复现性门槛处停止。

## Direct Evidence

- Package A: `/users/a/e/aereinh/CARE/results/submissions/care_myocardium_validation/upload_ready/20260519_084057__nnUNet_MyoPS+nnUNet_CineMyoPS_5fold_baseline_round8/CARE-Myocardium-OrganAgent.zip`; SHA256 `d594a763577d235bdc1ccbb41479de22c647bcbecc1ef6e9a3125fc66d543e24`; manifest declares MyoPS source `explicit` from `results/submissions/care_myocardium_validation/nnunet_5fold_best/nnunet_predictions/Dataset501_CAREMyoPS`.
- Cached nnU-Net manifest: `results/submissions/care_myocardium_validation/nnunet_5fold_best/manifest.json` records folds `0..4`, checkpoint `checkpoint_best.pth`, device `cuda`.
- Cached MyoPS predict args exist at `results/submissions/care_myocardium_validation/nnunet_5fold_best/nnunet_predictions/Dataset501_CAREMyoPS/predict_from_raw_data_args.json`; it records `overwrite=false`, `save_probabilities=false`, and old `/overflow/htzhu/CARE/...` input/output paths.
- Current submission helper `scripts/submission/prepare_care_myocardium_validation.py` MyoPS branch calls `nnUNetv2_predict` with `-d 501`, `-c 3d_fullres`, `-tr nnUNetTrainer_500epochs`, `-p nnUNetPlans`, folds, checkpoint, device, `-npp 1`, `-nps 1`, and does not add `--disable_tta` for MyoPS.

## Replay Matrix

| variant | checkpoint | TTA | full exact | used 1/2/3/4 exact | geometry exact | changed voxels | decision |
| --- | --- | --- | ---: | ---: | ---: | ---: | --- |
| `v1_final_default_tta` | `checkpoint_final.pth` | `default` | 0/15 | 0/15 | 15/15 | 2226 | `NOT_EXACT` |
| `v2_best_no_tta` | `checkpoint_best.pth` | `disabled` | 0/15 | 0/15 | 15/15 | 6230 | `NOT_EXACT` |
| `v3_final_no_tta` | `checkpoint_final.pth` | `disabled` | 0/15 | 0/15 | 15/15 | 6440 | `NOT_EXACT` |

## Evidence Classification

| Claim | Evidence class | Finding |
| --- | --- | --- |
| Package A exists and has 15 MyoPS + 15 CineMyoPS files | DIRECT_EVIDENCE | ZIP and manifest present locally. |
| Package A MyoPS branch came from cached nnU-Net prediction directory | DIRECT_EVIDENCE | Package A manifest records explicit pred_dir. |
| Cached prediction command used `checkpoint_best.pth`, folds 0-4 | DIRECT_EVIDENCE | Cached manifest records these fields. |
| Cached prediction exact CLI/environment is fully reconstructable | INDIRECT_EVIDENCE | `predict_from_raw_data_args.json` records nnU-Net internal args, but not full shell environment, CUDA/kernel determinism, or source commit. |
| Package A used `checkpoint_final.pth` | NO_EVIDENCE | No direct manifest or command evidence found; V1/V3 did not exact reproduce. |
| Package A MyoPS used no TTA | NO_EVIDENCE | MyoPS helper has no `--disable_tta`; V2/V3 did not exact reproduce. |
| Current deployment source is deterministic under two fresh CUDA replays | DIRECT_EVIDENCE | Failed: 7/15 array exact, 15/15 geometry exact, 13 changed voxels. |

## Boundary

No hosted `0.6691` claim is authorized. No validation upload, Docker upload, cloud upload, organizer email, sudo, `/etc` edit, system Docker/rootless install, or new training was performed.
