# Result4 SRR-v2 Core Rebuild Preflight Note

## Current Gap

The existing `SRRMyoPSLite` already enforces modality availability at the input stem and masks unavailable experts in routing. However, `ExpertBank.forward()` applies private experts to the same fused feature tensor. This means private experts are private by route identity, not by modality-specific input evidence.

This is not enough for the Result4/Result5 method claim that scar should route through LGE-private evidence and edema through T2-private evidence.

## Required Isolated Route

Proposed future variant name: `srr_v2_multiscale_private_sparse`.

The route should be isolated from current formal jobs and should not change behavior of existing variants.

Required components:

- modality-private stems remain separate through expert blocks;
- shared experts receive fused evidence;
- scar router receives a prior toward LGE-private and LGE-interaction experts;
- edema router receives a prior toward T2-private and T2-interaction experts;
- at least two spatial scales are exposed in the sprint route;
- sparse top-k routing is available with softmax fallback;
- usage logging is grouped by task, modality, scale, and availability pattern.

## Why Deferred Now

The current sprint has already found nearer pipeline-level blockers:

- ignore-label voxels contributed to core SRR losses before the repair;
- raw argmax decode underuses calibrated pathology logits;
- checkpoint selection by patch loss can select the wrong pathology point;
- current proposal formal jobs have not all completed.

Starting SRR-v2 formal training before those facts are integrated would make attribution weak and risk burning another fold0 GPU budget without knowing whether the architecture is the primary bottleneck.

## Preflight Contract

When implementation starts, the CPU smoke should verify:

- unavailable modality-private experts have zero feature input and no gradient;
- sparse gates sum to one over valid experts only;
- top-k gates never activate invalid experts;
- LGE-only cases still provide scar route evidence but no T2-private edema route;
- no-T2 cases are never treated as edema negatives except true background per the edema safety contract.
