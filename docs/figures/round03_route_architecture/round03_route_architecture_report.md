# Round03 Route B / Route C Network Architecture Visualization Audit

## Scope and Authority Boundary

This repair keeps the earlier status/provenance figures and adds block-level network architecture figures. It does not train, submit Slurm jobs, start a controller or reviewer, package or upload validation, promote a route, start M11, claim hosted metrics, or make a final scientific decision.

Active repo: `/users/a/e/aereinh/CARE`.

Starting state after fetch: branch `main`, HEAD `82fe38df724a8262fbb8f73fe9c380fd6904cb08`, local branch ahead of `origin/main` by one commit. That prior local commit deleted legacy/status figures; this repair restores them.

## Files Produced

New block-level network-detail figures:

| File | Purpose |
| --- | --- |
| `round03_routeB_routeC_aligned_network_detail.d2/svg/png` | main two-route aligned network detail figure with the same six stage columns |
| `round03_routeB_network_detail.d2/svg/png` | Route B detailed network expansion using the same six-panel template |
| `round03_routeC_network_detail.d2/svg/png` | Route C detailed network expansion using the same six-panel template |
| `round03_route_network_architecture_spec.yaml` | machine-readable block architecture spec |
| `round03_route_architecture_components.csv` | CSV block table matching the YAML fields |

Restored/kept legacy status/provenance appendix figures:

| Restored legacy/status file set | Current role |
| --- | --- |
| `round03_routeB_structure.d2/svg/png` | appendix status/provenance figure, not current network-detail source |
| `round03_routeC_structure.d2/svg/png` | appendix status/provenance figure, not current network-detail source |
| `round03_routeB_vs_routeC_gap.d2/svg/png` | appendix evidence gap/status figure |
| `round03_routeB_implemented_vs_planned_model.d2/svg/png` | appendix Route B implemented-vs-planned overview |

The current network-detail source of truth is the YAML plus the three `*_network_detail.d2` files.

## Shared Six-Panel Template

Route B and Route C now use the same left-to-right template:

1. Inputs
2. Encoder / trunk
3. Routing / prototype / proposal
4. ROI / refiner / composition
5. CineMA / registration / temporal
6. Final output / evidence boundary

Status encoding is shared: green solid means reviewer-verified, blue dashed means smoke-only, yellow dashed means planned or not executed, red solid means blocker or adequate negative, gray dashed means stale historical evidence, and purple dashed means forbidden authority boundary.

## Route B Implementation Boundary

Route B has real model code through the MyoPS forward path and smoke-level Cine/register/temporal scaffolds:

| Stage | Code-confirmed network detail | Round03 evidence state |
| --- | --- | --- |
| Inputs | `RouteBRound03MyoPS.forward` expects `x [B,3,Z,H,W]`, `availability [B,3]`, and `anchor_logits [B,6,Z,H,W]` | B2/B3 evidenced |
| Encoder | modality stems are `Conv3d(1,32,k=3)`, pyramid is `32->64->128->256` with stride-2 Conv3d | smoke evidenced |
| Expert routing | `ExpertScale` has 16 experts per scale: 4 shared, 6 private, 6 pair-interaction; `ResidualExpert` is Conv/GN/SiLU plus Conv/GN residual | B3 boundary evidenced |
| Router | query is fused feature + 16 availability embedding + 6 anchor channels + 2 proposal channels; router is Conv3d -> GroupNorm -> SiLU -> Conv3d; invalid logits are `-1e4`, then `torch.softmax` | invalid-weight checks passed at B3 boundary |
| Prototype/proposal | `OfflinePrototypeBank` has scar 8/12 and edema 8/12 banks; proposal heads are scar `36->1` dilation 2 and edema `37->1` dilation 3 | B2 smoke; B4 not executed |
| ROI/refiner/final | anatomy head is `480->4`; refiners are `ResidualExpert(32)+Conv3d(32,1)`; gate is `Conv3d 12->16->1`; final logits are `[B,6,Z,H,W]` with scar class 5 and edema class 4 deltas | B2 final-logit smoke; B5/B6 not executed |
| Cine/register/temporal | Cine adapter is `1->32`, `32->4`, `32->16`; SVF scaffold is `2->16->16->3` with 7-step integration; temporal scaffold is `35->32`, router `36->8->8`, 8 slots, head `32->4` | B2 smoke only; B7-B9 not executed |

Latest Route B reviewer token is `ROUTE_B_ROUND03_REVIEW_ADEQUATE_NEGATIVE`. The actual stop is B3: `anatomy_union_overfit=false` after 43003 steps, 1800.8 seconds, and 22 validation events. This is not a full route negative because B4-B9 were not executed.

## Route C Implementation Boundary

Route C has reviewer-verified model and evidence wiring across MyoPS, CineMA, registration, and temporal final-output paths:

| Stage | Code-confirmed network detail | Round03 evidence state |
| --- | --- | --- |
| Inputs | `SRRProposeRefineMyoPS.forward` requires 3 input channels but does not fix spatial shape in code; context shape is checked against input; cine temporal path consumes registered evidence tensors | reviewer verified |
| Encoder | default `base_channels=10`; default `tiny_3scale` gives `[10,20,40]`; `ModalityEncoder` uses ConvBlock stages with missing-modality closure | reviewer verified |
| Retrieval/decoder | `ScaleRetrieval` wraps multi-slot shared/private/interaction retrieval; `FlexibleTaskDecoder` uses ConvTranspose up blocks with skip concatenation; task features feed `AnatomyPathologyHeads` | reviewer verified |
| M10 dictionary/proposal | `M10TwoPassSpatialDictionary` has exact 16-slot bank, anatomy router, scar/edema pass0, scar/edema pass1, top-k 4 then 2; `ProposalDictionary` uses embedding C->C, score C->1, positive-negative-memory similarities, evidence/context terms, and no-T2 edema -20 | reviewer verified where enabled/contextual; proposal swap verified |
| ROI/refiner/final | `AnatomyDistanceROIPrior` emits P_union/P_LV/P_RV, distance and uncertainty maps; `CropSoftROIRefinementHead` uses `channels+18 -> channels -> channels -> 1`; `BaselinePreservingResidualGate` uses `16->6`; `BranchArbitrationGate` uses `10->4` and emits final logits/labels | reviewer verified final-output effect |
| Cine/register/temporal | Official CineMA provenance is verified, but external ConvUNetR depth is not introspected in repo. Local `CineMAAdapter` is `2->16`, residual 16, head `16->4`. `RegistrationUNet` uses channels `(16,32,64,128)` with enc/dec skips and velocity `16->3`. Temporal dictionary uses encoder `C->24->24`, 8 Conv3d experts, router `24->8`, and `CineTemporalModel` head `28->24->4` | reviewer verified |

Latest Route C reviewer token is `ROUTE_C_ROUND03_REVIEW_EVIDENCE_COMPLETE`. This means the packet is evidence-complete for later planner/reconciliation consideration, not route promotion and not a final scientific decision.

## Final-Output Evidence

Route B final-output evidence is limited: B2 smoke reports final logits changed, but B6 formal final-output ablation was not executed because B3 failed first.

Route C final-output evidence is formal and reviewer-verified: R1 positive/negative prototype swap has 88/88 rows changing logits and voxels and 80/88 rows changing components; no-op and anchor residual-off controls remain zero-effect. R3 has 12 temporal final-output rows changing logits, voxels, and components, supported by 60 registration pair receipts and real SyN controls.

## Stale / Conflict Handling

`/users/a/e/aereinh/CARE_worktrees/route_C/results/route_C/architecture_delta_final.md` remains a stale historical conflict because it predates the repaired final reviewer decision. The new detail diagrams mark it as stale and do not let it override `review.md`.

## Validation Commands

The following lightweight checks are the intended validation surface for this docs-only repair:

```bash
d2 --version
for f in docs/figures/round03_route_architecture/round03_routeB_routeC_aligned_network_detail docs/figures/round03_route_architecture/round03_routeB_network_detail docs/figures/round03_route_architecture/round03_routeC_network_detail; do d2 "$f.d2" "$f.svg"; rsvg-convert "$f.svg" -o "$f.png"; done
file docs/figures/round03_route_architecture/*.png
python - <<'PY'
from pathlib import Path
import csv
root = Path('/users/a/e/aereinh/CARE/docs/figures/round03_route_architecture')
required = ['route','panel','block_id','source_file','class_or_function','input_tensor','output_tensor','channels','operation','status','evidence_file','final_output_effect']
with (root/'round03_route_architecture_components.csv').open(newline='', encoding='utf-8') as f:
    for i, row in enumerate(csv.DictReader(f), start=2):
        for key in required:
            assert row[key].strip(), (i, key)
        for key in ('source_file','evidence_file'):
            for raw in row[key].split(';'):
                path = raw.strip()
                assert not path or Path(path).exists(), (i, key, path)
assert (root/'round03_route_network_architecture_spec.yaml').read_text(encoding='utf-8').count('block_id:') > 0
PY
git diff --check
```

No tests that train, run Slurm, start controllers/reviewers, read raw data, read checkpoints, upload validation, or promote routes are appropriate for this visualization-only task.
