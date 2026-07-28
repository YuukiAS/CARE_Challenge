# CARE-DG Architecture Delta Draft After Gate B-R2

created_at_utc: `2026-07-28T03:52:35Z`
base_git_head: `67dac96a22e6179e0a7fcc02815b36aab30a8bfc`
status: `DRAFT_NOT_FINAL_WIKI_NOT_UPDATED`

## Delta Summary

CARE-DG introduced a new active experimental architecture relative to the current wiki: frozen nnU-Net anchor plus a compact dual-gated residual correction network with independent scar and edema-zone decoders. The implementation and fold0 Gate B evidence are present, but the architecture must remain `partial/unverified_for_final_candidate` because Gate B-R2 found no safe fold0 expansion candidate and W3-W6 are incomplete.

## Component Delta Table

| component_id | intended current_status | evidence_status | source/evidence |
|---|---|---|---|
| `care_dg_anchor_context` | implemented | verified through Gate A/B | nnU-Net anchor logits/log-probabilities loaded by `run_care_dg.py`; no MoSAIC/MMRD runtime dependency |
| `care_dg_shared_encoder` | implemented | verified through Gate A tests/preflight | `CAREDG.encoder`, modality stems and anchor_context |
| `care_dg_scar_decoder` | implemented | verified through Gate A/B mechanism evidence | independent `scar_decoder`, scar FN/FP gates and magnitudes |
| `care_dg_edema_decoder` | implemented | verified through Gate A/B mechanism evidence | independent `edema_decoder`, no-T2 exact identity |
| `care_dg_scar_priority_decode` | implemented | verified through Gate B hotfix tests/evaluator | `anchor -> edema correction -> scar correction -> argmax`; post-scar overwrite count `0` |
| `care_dg_full_volume_inference` | implemented | verified for fold0 R1/R2 only | overlap `0.5`, Gaussian delta aggregation, full-volume one-time composition |
| `care_dg_candidate_selection` | partial | verified fail-closed for Gate B-R2, missing W3/W4 | 512 train-side candidates, eligible_count `0`; no validation package candidate |
| `care_dg_oof_aggregation` | missing | missing | 220-case W3 OOF not produced |
| `care_dg_all_data_fit` | missing | not authorized | candidate gate failed before all-data fit |
| `care_dg_validation_package` | missing | not authorized | no upload-ready CARE-DG ZIP or Docker-equivalent smoke |

## Required Wiki Action If Terminalized

If GPT/user directs terminalization as `NO_CARE_DG_CANDIDATE_SAFE_FOR_VALIDATION`, final Mapper should update root wiki and CURRENT to say: CARE-DG was implemented and fold0-tested, but no safe candidate survived Gate B-R2; folds 1-4/all-data/validation package are not authorized; MoSAIC/MMRD/SRR/Cascade remain historical evidence only; final Docker must not substitute an external model for failed CARE-DG.

If GPT/user instead authorizes a new same-scope repair or explicitly overrides the expansion gate, this draft must be superseded and final wiki must wait for the new terminal evidence.

## Hashes

```json
{
  "configs/care_dg/care_dg_v1.yaml": "69c276d66ffa1328da7a1e06ee446280981cac1fe3ed3d497327ad714fe757b4",
  "scripts/evaluation/build_care_dg_validation_packet.py": "254a0bc436aa584fd162126706a9702770475b6dc2632cde23545c74987e6f14",
  "scripts/evaluation/evaluate_care_dg.py": "f1e32230fc1d40ce2d8680d27e9943fb633ae0c4db42b0a57f7690c4d4fad0dc",
  "scripts/evaluation/select_care_dg_candidate.py": "d319535426cb49800710e8a9e8056ae97cf4abae99bd342dfd2df09b153f5080",
  "scripts/evaluation/validate_care_dg_gate_a_consistency.py": "f85369fa70fe735ad01a2d809e0e023cf74fb63dd8476de11e176edde4441615",
  "scripts/evaluation/validate_care_dg_packet.py": "d02ef03752072a97d72301bf42338d11e851442b67e403a5e8cd2a6875fcb48b",
  "scripts/inference/run_care_dg_inference.py": "ceef29361a4ce6eb2224e315ca800381944b2a9c624aa7b8017dab80d54ee771",
  "scripts/training/run_care_dg.py": "8c8432ee844b956c13230be6235e82b6fce4b4d65cd4849b7b140c1113cd7623",
  "src/care_myocardium/data/care_dg_dataset.py": "96d18e1914b7e08fc029a77c0e7c21467809fa0a5e9e12ad4f1ef2208eba803a",
  "src/care_myocardium/inference/care_dg_predictor.py": "71b3f935617b42a1190aa6937165ee09ce1a3c52e8a05ad4f6d4e53f9dcacf7c",
  "src/care_myocardium/models/care_dg.py": "ee38bd7d86ca37944ef4108fa4d5904d9ead1f7ae2dc4b7ec518d784acb71d55",
  "src/care_myocardium/training/care_dg_trainer.py": "009b5f8f0d38622a958774c808600cb7c90f9d8c9b2b6064088fc9df9b3532b1",
  "tests/care_dg/test_care_dg_model.py": "664c965d47c208be0b51107162ab2a53e298c37712ca263db94187572aeb39ff"
}
```
