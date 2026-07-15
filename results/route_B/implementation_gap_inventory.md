# Route B Implementation Gap Inventory

Current controller state: `ROUTE_B_IMPLEMENTATION_NEEDS_REVISION`.

The route_B-specific source, script, config, job, test, result, log, and lock namespaces were absent before this controller run. Historical SRR/Cine files exist outside the route_B namespace and are useful context, but they do not satisfy Route B's implementation-before-training gate by themselves.

| component | branch | gap |
| --- | --- | --- |
| `myops_modality_stems` | MyoPS | missing_route_B_namespace |
| `myops_multiscale_encoder` | MyoPS | missing_route_B_namespace |
| `myops_availability_router` | MyoPS | missing_route_B_gate_evidence |
| `myops_semantic_retrieval` | MyoPS | missing_route_B_trace |
| `myops_prototype_bank` | MyoPS | missing_route_B_provenance |
| `myops_anatomy_decoder` | MyoPS | missing_route_B_trace |
| `myops_scar_proposal` | MyoPS | missing_route_B_intervention |
| `myops_edema_proposal` | MyoPS | missing_route_B_intervention |
| `myops_soft_roi` | MyoPS | missing_route_B_trace |
| `myops_scar_refiner` | MyoPS | missing_route_B_intervention |
| `myops_edema_refiner` | MyoPS | missing_route_B_intervention |
| `myops_bounded_residual` | MyoPS | missing_route_B_anchor_identity |
| `myops_export` | MyoPS | missing_route_B_export_qa |
| `cine_anatomy_source` | Cine | missing_route_B_runtime_receipt |
| `cine_frame_policy` | Cine | missing_route_B_case_receipt |
| `cine_registration` | Cine | missing_route_B_warp_stats |
| `cine_syn_control` | Cine | missing_route_B_control_receipt |
| `cine_temporal_dictionary` | Cine | missing_route_B_temporal_runtime |
| `cine_temporal_refiner` | Cine | missing_route_B_intervention |
| `checkpoint_resume_export` | Shared | missing_route_B_runtime_receipt |
