# M10 Wave 1 Architecture Fidelity

task_key: `20260711_srr_v3_m10_complete_mechanism_repair`
executor_id: `m10_shared_architecture_executor`
status: `READY_FOR_CONTROLLER_MERGE`

## Scope

Wave 1 implemented shared architecture/loss/config/test fidelity only. No
formal training, validation packaging, validation upload, hosted metric claim,
route promotion, scientific stop, M11, wave 2, or wave 3 work was performed.

## Implemented Contract Surface

- Canonical modality order remains `[LGE, T2, C0]`.
- `srr_v3_m10_16slot` declares exact 16 slots per scale: 4 shared, 2
  LGE-private, 2 T2-private, 2 C0-private, 2 LGE-T2, 2 LGE-C0, and 2 T2-C0.
- New `M10TwoPassSpatialDictionary` implements voxelwise two-pass
  lesion-conditioned routing with invalid-slot masking.
- Invalid slots are zero for expert output and gate weights; the wave 1 test
  checks zero gradients for all T2-dependent slots when T2 is absent.
- `pattern_sip_integrativeness_loss` is independent from
  `semantic_retrieval_regularization`, with separate metric keys and graph.
- `M10CrossFittedPrototypeMemory` adds four deterministic shards, 8 positive
  and 12 negative slots per pathology, and rejects no-T2 edema memory updates
  with accepted count zero.
- M10 PropRef variants are declared for D0-D3, and D1-D3 wire the spatial
  dictionary into proposal/refiner features.
- M10 final-output metadata records `final_output_base:
  SRR_PROPOSAL_REFINEMENT`; no-T2 edema final probability is exactly zero in
  the tested M10 path.

## Evidence

- `src/care_myocardium/tests/test_srr_v3_m10_fidelity.py`: 5 wave-specific
  tests passed.
- `configs/srr_v3_m10_complete_repair.yaml`: D0-D3 shared design/config
  contract.
- `m10_slot_contract.csv`: slot count and invalid-slot evidence summary.
- `m10_loss_component_contract.csv`: loss accounting summary.
- `m10_source_fingerprints.json`: source/config/test hashes after wave 1.
