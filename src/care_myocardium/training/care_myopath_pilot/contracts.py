
from __future__ import annotations
import json
from pathlib import Path
from typing import Any
VARIANT_CONTRACTS = {'A1': {'steps': 3000, 'optimizer': 'AdamW'}, 'A2': {'steps': 5000, 'optimizer': 'AdamW'}, 'A3': {'steps': 8000, 'optimizer': 'AdamW'}}
KNOWN_BAD_CASES = ['encoder_only','decoder_reset','a0_not_pixel_identity','no_t2_edema_loss_nonzero','scar_edema_shared_parameters','proposal_auxiliary_only','proposal_not_in_final_logits','intervention_gradient_only_no_label_change','variant_checkpoint_chaining','case_order_or_augmentation_mismatch','outer_used_for_selection','edema_zone_as_pure_edema','short_smoke_as_formal_training','scheduler_base_lr_overwritten','refiner_started_after_failed_proposal_gate','new_loss_or_module_after_a3_failure','pending_job_claims_completion','mean_dice_only_evaluator','scar_gain_masks_edema_failure','missing_hash_or_provenance']
def read_metric_truth_receipt(path: Path) -> dict[str, Any]:
    if not path.is_file(): return {'present': False, 'metric_contract_status': 'MISSING'}
    payload = json.loads(path.read_text(encoding='utf-8')); payload['present'] = True; return payload
def validate_contract_payload(payload: dict[str, Any]) -> list[str]:
    errors = []
    if payload.get('inherits_encoder_only'): errors.append('encoder-only inheritance is forbidden')
    if payload.get('decoder_reset'): errors.append('decoder reset is forbidden')
    if payload.get('a0_fp32_max_abs_error', 0.0) > 1e-6 or payload.get('a0_changed_argmax_voxels', 0) != 0: errors.append('A0 must reproduce stock logits and labels exactly')
    if payload.get('no_t2_edema_loss', 0.0) != 0.0: errors.append('no-T2 edema loss must be exactly zero')
    if payload.get('no_t2_edema_gradient', 0.0) != 0.0: errors.append('no-T2 edema gradient must be exactly zero')
    if payload.get('scar_edema_share_parameters'): errors.append('scar and edema parameters must not be shared')
    if payload.get('proposal_auxiliary_only'): errors.append('proposal cannot be auxiliary-only')
    if not payload.get('proposal_enters_final_logits', True): errors.append('proposal must enter final logits')
    if payload.get('on_off_changed_labels', 1) == 0 and payload.get('claims_intervention_success'): errors.append('on/off intervention cannot be gradient-only')
    if payload.get('checkpoint_chaining'): errors.append('A1/A2/A3 must independently start from A0 stock checkpoint')
    if payload.get('case_order_mismatch') or payload.get('augmentation_mismatch'): errors.append('variant case order, sampler seed, and augmentation must match')
    if payload.get('outer_used_for_selection'): errors.append('outer split cannot be used for selection')
    if payload.get('edema_zone_reported_as_pure_edema'): errors.append('edema-zone cannot be reported as pure edema')
    if payload.get('formal_training_status') in {'SMOKE_ONLY', 'PREFLIGHT_ONLY'} and payload.get('claims_formal_training'): errors.append('short smoke cannot claim formal training')
    if payload.get('scheduler_base_lr_overwritten'): errors.append('scheduler must not overwrite base LR each step')
    if payload.get('refiner_started') and not payload.get('proposal_gate_passed', True): errors.append('refiner is not authorized after failed proposal gate')
    if payload.get('added_new_loss_after_a3_failure') or payload.get('added_new_module_after_a3_failure'): errors.append('A3 failure cannot authorize new loss/module')
    if payload.get('job_state') in {'SUBMITTED', 'PENDING', 'RUNNING', 'AWAITING_SACCT', 'NEEDS_MONITOR'} and payload.get('claims_complete'): errors.append('pending/running job cannot claim completion')
    if payload.get('evaluator_metric_set') == ['mean_dice']: errors.append('mean Dice only evaluator is insufficient')
    if payload.get('scar_improved') and payload.get('edema_systematic_failure') and payload.get('claims_overall_success'): errors.append('scar improvement cannot mask systematic edema failure')
    if not payload.get('has_model_hashes', True) or not payload.get('has_config_hashes', True) or not payload.get('has_split_hashes', True): errors.append('model/config/split/checkpoint hashes are required')
    return errors
def known_bad_matrix() -> list[dict[str, Any]]:
    rows = []
    for case in KNOWN_BAD_CASES:
        payload = {'a0_fp32_max_abs_error': 0.0, 'a0_changed_argmax_voxels': 0, 'proposal_enters_final_logits': True, 'has_model_hashes': True, 'has_config_hashes': True, 'has_split_hashes': True, 'no_t2_edema_loss': 0.0, 'no_t2_edema_gradient': 0.0}
        if case == 'encoder_only': payload['inherits_encoder_only'] = True
        elif case == 'decoder_reset': payload['decoder_reset'] = True
        elif case == 'a0_not_pixel_identity': payload['a0_fp32_max_abs_error'] = 1e-3
        elif case == 'no_t2_edema_loss_nonzero': payload['no_t2_edema_loss'] = 0.1
        elif case == 'scar_edema_shared_parameters': payload['scar_edema_share_parameters'] = True
        elif case == 'proposal_auxiliary_only': payload['proposal_auxiliary_only'] = True
        elif case == 'proposal_not_in_final_logits': payload['proposal_enters_final_logits'] = False
        elif case == 'intervention_gradient_only_no_label_change': payload.update({'claims_intervention_success': True, 'on_off_changed_labels': 0})
        elif case == 'variant_checkpoint_chaining': payload['checkpoint_chaining'] = True
        elif case == 'case_order_or_augmentation_mismatch': payload['case_order_mismatch'] = True
        elif case == 'outer_used_for_selection': payload['outer_used_for_selection'] = True
        elif case == 'edema_zone_as_pure_edema': payload['edema_zone_reported_as_pure_edema'] = True
        elif case == 'short_smoke_as_formal_training': payload.update({'formal_training_status': 'SMOKE_ONLY', 'claims_formal_training': True})
        elif case == 'scheduler_base_lr_overwritten': payload['scheduler_base_lr_overwritten'] = True
        elif case == 'refiner_started_after_failed_proposal_gate': payload.update({'refiner_started': True, 'proposal_gate_passed': False})
        elif case == 'new_loss_or_module_after_a3_failure': payload['added_new_loss_after_a3_failure'] = True
        elif case == 'pending_job_claims_completion': payload.update({'job_state': 'RUNNING', 'claims_complete': True})
        elif case == 'mean_dice_only_evaluator': payload['evaluator_metric_set'] = ['mean_dice']
        elif case == 'scar_gain_masks_edema_failure': payload.update({'scar_improved': True, 'edema_systematic_failure': True, 'claims_overall_success': True})
        elif case == 'missing_hash_or_provenance': payload['has_model_hashes'] = False
        errors = validate_contract_payload(payload); rows.append({'case': case, 'rejected': bool(errors), 'errors': errors})
    return rows
