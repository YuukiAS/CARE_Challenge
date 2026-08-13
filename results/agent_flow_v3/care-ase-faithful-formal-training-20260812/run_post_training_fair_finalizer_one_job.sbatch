#!/usr/bin/env bash
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=8
#SBATCH --job-name=ASEFAIR
#SBATCH --output=/dev/null
#SBATCH --error=/dev/null
#SBATCH --mem=64G
#SBATCH --time=3-00:00:00
#SBATCH --gres=gpu:1
#SBATCH --partition=htzhulab
#SBATCH --qos=gpu_access

set -euo pipefail

MAIN_ROOT="/users/a/e/aereinh/CARE"
WORKTREE="${MAIN_ROOT}/.worktrees/care-ase-faithful-formal-training-20260812"
RESULT_ROOT="${WORKTREE}/results/agent_flow_v3/care-ase-faithful-formal-training-20260812"
FOLD2_RUNTIME_DIR="${RESULT_ROOT}/runtime/fold_2"
FOLD3_RUNTIME_DIR="${RESULT_ROOT}/runtime/fold_3_parallel"
SUPERSEDED_SEQUENTIAL_JOB_ID="${SUPERSEDED_SEQUENTIAL_JOB_ID:-63244446}"
LOG_DIR="${WORKTREE}/logs"
mkdir -p "${LOG_DIR}"
TS="$(date +%Y%m%d_%H%M%S)"
LOG_FILE="${LOG_FILE:-${LOG_DIR}/ASEFAIR_${SLURM_JOB_ID:-local}_${TS}.log}"
exec > >(tee -a "${LOG_FILE}") 2>&1

cd "${WORKTREE}"
source "${MAIN_ROOT}/.care-codex-env.sh"
source "${MAIN_ROOT}/env_nnunet.sh"
export PATH="${MAIN_ROOT}/envs/env_CARE/bin:${PATH}"
export PYTHONPATH="${WORKTREE}:${PYTHONPATH:-}"

echo "JOB_START_UTC=$(date -u +%Y-%m-%dT%H:%M:%SZ)"
echo "LOG_FILE=${LOG_FILE}"
hostname
nvidia-smi || true

status_json() {
  local path="$1"
  local payload="$2"
  "${MAIN_ROOT}/envs/env_CARE/bin/python" - "${path}" "${payload}" <<'PY'
import json
import pathlib
import sys
path = pathlib.Path(sys.argv[1])
payload = json.loads(sys.argv[2])
path.parent.mkdir(parents=True, exist_ok=True)
path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
PY
}

runtime_dir_for_fold() {
  local fold="$1"
  if [[ "${fold}" == "3" ]]; then
    printf '%s\n' "${FOLD3_RUNTIME_DIR}"
  else
    printf '%s\n' "${FOLD2_RUNTIME_DIR}"
  fi
}

wait_for_checkpoint() {
  local fold="$1"
  local step="$2"
  local runtime_dir
  runtime_dir="$(runtime_dir_for_fold "${fold}")"
  local ckpt="${runtime_dir}/$(printf 'checkpoint_step%05d.pt' "${step}")"
  local verified="${ckpt}.verified.json"
  local waited=0
  while [[ ! -f "${ckpt}" || ! -f "${verified}" ]]; do
    if [[ "${waited}" -ge 259200 ]]; then
      echo "timeout waiting for required checkpoint or verified receipt: fold=${fold} step=${step} runtime_dir=${runtime_dir}" >&2
      return 1
    fi
    echo "waiting for checkpoint: fold=${fold} step=${step} waited=${waited}s runtime_dir=${runtime_dir}"
    sleep 600
    waited=$((waited + 600))
  done
}

cancel_superseded_sequential_after_fold2() {
  local ckpt="${FOLD2_RUNTIME_DIR}/checkpoint_step14000.pt"
  local verified="${ckpt}.verified.json"
  if [[ ! -f "${ckpt}" || ! -f "${verified}" ]]; then
    return 0
  fi
  if squeue -h -j "${SUPERSEDED_SEQUENTIAL_JOB_ID}" >/dev/null 2>&1; then
    status_json "${RESULT_ROOT}/post_training_fair_finalizer_status.json" "{\"status\":\"RUNNING\",\"slurm_job_id\":\"${SLURM_JOB_ID:-local}\",\"phase\":\"cancel_superseded_sequential_after_fold2_14000\",\"outer_accessed\":false,\"superseded_job_id\":\"${SUPERSEDED_SEQUENTIAL_JOB_ID}\"}"
    scancel "${SUPERSEDED_SEQUENTIAL_JOB_ID}" || true
    status_json "${RESULT_ROOT}/asefull_superseded_after_fold2.json" "{\"status\":\"SUPERSEDED_AFTER_FOLD2_14000_VERIFIED\",\"superseded_job_id\":\"${SUPERSEDED_SEQUENTIAL_JOB_ID}\",\"replacement_fold3_runtime\":\"${FOLD3_RUNTIME_DIR}\",\"outer_accessed\":false}"
  fi
}

run_monitor_if_missing() {
  local fold="$1"
  local step="$2"
  local split_csv="$3"
  local out_dir="$4"
  local runtime_dir
  runtime_dir="$(runtime_dir_for_fold "${fold}")"
  local ckpt="${runtime_dir}/$(printf 'checkpoint_step%05d.pt' "${step}")"
  if [[ -f "${out_dir}/monitor_packet.json" && -f "${out_dir}/casewise_metrics.csv" ]]; then
    echo "monitor exists; keeping immutable packet: ${out_dir}"
    return 0
  fi
  wait_for_checkpoint "${fold}" "${step}"
  if [[ "${fold}" == "2" && "${step}" == "14000" ]]; then
    cancel_superseded_sequential_after_fold2
  fi
  status_json "${RESULT_ROOT}/post_training_fair_finalizer_status.json" "{\"status\":\"RUNNING\",\"slurm_job_id\":\"${SLURM_JOB_ID:-local}\",\"phase\":\"monitor_fold_${fold}_step_${step}\",\"output_dir\":\"${out_dir}\",\"outer_accessed\":false}"
  "${MAIN_ROOT}/envs/env_CARE/bin/python" \
    scripts/evaluation/care_ase/monitor_care_ase_r2_inner_trend.py \
    --fold "${fold}" \
    --checkpoint-step "${step}" \
    --checkpoint "${ckpt}" \
    --split-case-lists "${split_csv}" \
    --output-dir "${out_dir}"
}

run_core_comparison_status_if_missing() {
  local fold="$1"
  local step="$2"
  local out_dir="${RESULT_ROOT}/comparisons/fold_${fold}/$(printf 'step%05d' "${step}")"
  if [[ -f "${out_dir}/comparison_status.json" ]]; then
    echo "comparison status exists; keeping immutable packet: ${out_dir}"
    return 0
  fi
  wait_for_checkpoint "${fold}" "${step}"
  if [[ "${fold}" == "2" && "${step}" == "14000" ]]; then
    cancel_superseded_sequential_after_fold2
  fi
  status_json "${RESULT_ROOT}/post_training_fair_finalizer_status.json" "{\"status\":\"RUNNING\",\"slurm_job_id\":\"${SLURM_JOB_ID:-local}\",\"phase\":\"comparison_status_fold_${fold}_step_${step}\",\"output_dir\":\"${out_dir}\",\"outer_accessed\":false,\"fair_claim_allowed\":false}"
  "${MAIN_ROOT}/envs/env_CARE/bin/python" \
    "${RESULT_ROOT}/audit_and_backfill_comparison_status.py"
  if [[ ! -f "${out_dir}/comparison_status.json" ]]; then
    echo "comparison status backfill did not produce expected packet: ${out_dir}/comparison_status.json" >&2
    return 1
  fi
}

run_formal_selector() {
  local fold="$1"
  local output="${RESULT_ROOT}/inner_checkpoint_selection_fold${fold}_formal_2000step.json"
  status_json "${RESULT_ROOT}/post_training_fair_finalizer_status.json" "{\"status\":\"RUNNING\",\"slurm_job_id\":\"${SLURM_JOB_ID:-local}\",\"phase\":\"formal_selector_fold_${fold}\",\"outer_accessed\":false}"
  "${MAIN_ROOT}/envs/env_CARE/bin/python" - "${fold}" "${RESULT_ROOT}" "${output}" <<'PY'
import json
import pathlib
import sys

fold = int(sys.argv[1])
result_root = pathlib.Path(sys.argv[2])
output = pathlib.Path(sys.argv[3])
formal_eval_steps = [2000, 4000, 6000, 8000, 10000, 12000, 14000]
selection_candidate_steps = [4000, 6000, 8000, 10000, 12000, 14000]
required = [
    "scar_dice_mean",
    "scar_hd95_mean",
    "stock_scar_hd95_mean",
    "scar_remote_fp_volume_mm3_mean",
    "scar_harm_fraction_vs_nnunet",
    "pure_edema_dice_mean",
    "pure_edema_sensitivity_mean",
    "pure_edema_volume_ratio_mean",
    "pure_edema_hd95_mean",
    "stock_pure_edema_hd95_mean",
]

def score(summary):
    scar = float(summary["scar_dice_mean"])
    scar_hd95 = float(summary["scar_hd95_mean"])
    stock_scar_hd95 = float(summary["stock_scar_hd95_mean"])
    remote_fp = float(summary["scar_remote_fp_volume_mm3_mean"])
    harm_fraction = float(summary["scar_harm_fraction_vs_nnunet"])
    edema = float(summary["pure_edema_dice_mean"])
    edema_sens = float(summary["pure_edema_sensitivity_mean"])
    edema_ratio = float(summary["pure_edema_volume_ratio_mean"])
    edema_hd95 = float(summary["pure_edema_hd95_mean"])
    stock_edema_hd95 = float(summary["stock_pure_edema_hd95_mean"])
    scar_score = scar - 0.002 * max(0.0, scar_hd95 - stock_scar_hd95) - 0.00002 * remote_fp - 0.05 * max(0.0, harm_fraction - 0.35)
    edema_score = edema + 0.20 * edema_sens - 0.05 * abs(edema_ratio - 1.0) - 0.002 * max(0.0, edema_hd95 - stock_edema_hd95)
    return {"scar_score": scar_score, "edema_score": edema_score, "joint_score": 0.5 * (scar_score + edema_score)}

ranked = []
packets = []
for step in selection_candidate_steps:
    path = result_root / "inner_checkpoint_monitor" / f"fold_{fold}" / f"step{step:05d}" / "monitor_packet.json"
    payload = json.loads(path.read_text(encoding="utf-8"))
    if payload.get("status") != "PASS":
        raise RuntimeError(f"monitor packet is not PASS: {path}")
    if int(payload.get("checkpoint_step", -1)) != step:
        raise RuntimeError(f"step mismatch in {path}")
    if int(payload.get("fold", -1)) != fold:
        raise RuntimeError(f"fold mismatch in {path}")
    if payload.get("split_case_lists_path", "").endswith("fair_panel_split_case_lists.csv"):
        raise RuntimeError(f"formal selector received CORE panel packet, not full inner packet: {path}")
    summary = payload.get("summary")
    missing = [name for name in required if name not in summary]
    if missing:
        raise RuntimeError(f"selector metrics missing {missing}: {path}")
    scores = score(summary)
    ranked.append((scores["joint_score"], step, payload, scores))
    packets.append(str(path.relative_to(result_root.parent.parent.parent)))
ranked.sort(key=lambda item: (item[0], item[1]), reverse=True)
best_joint, best_step, best_packet, best_scores = ranked[0]
result = {
    "status": "PASS",
    "selector_contract": "CARE_ASE_FORMAL_INNER_SELECTOR_ALLOWED_CANDIDATES_4000_TO_14000_V1",
    "formal_eval_steps": formal_eval_steps,
    "candidate_steps": selection_candidate_steps,
    "selected_checkpoint_step": best_step,
    "joint_score": best_joint,
    "scar_score": best_scores["scar_score"],
    "edema_score": best_scores["edema_score"],
    "tie_break": "later_step",
    "excluded_from_selection": {
        "steps": [2000],
        "reason": "objective allows 2000-step formal inner evaluation for monitoring, but formal selection candidates are 4000/6000/8000/10000/12000/14000",
    },
    "forbidden_inputs": ["outer", "threshold_search", "pathology_specific_checkpoint_splicing"],
    "packet_paths": packets,
    "selected_packet_checkpoint_sha256": best_packet.get("checkpoint_sha256"),
    "outer_accessed": False,
}
output.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
print(json.dumps(result, indent=2, sort_keys=True))
PY
}

run_user_authorized_outer_final_if_missing() {
  local out="${RESULT_ROOT}/outer_diagnostic_user_authorized/outer_diagnostic_final_14000_combined_summary.json"
  if [[ -f "${out}" ]]; then
    echo "user-authorized outer final diagnostic exists; keeping immutable packet: ${out}"
    return 0
  fi
  wait_for_checkpoint 2 14000
  cancel_superseded_sequential_after_fold2
  wait_for_checkpoint 3 14000
  status_json "${RESULT_ROOT}/post_training_fair_finalizer_status.json" "{\"status\":\"RUNNING\",\"slurm_job_id\":\"${SLURM_JOB_ID:-local}\",\"phase\":\"user_authorized_outer_diagnostic_final_14000\",\"outer_accessed\":true,\"fairness_status\":\"USER_AUTHORIZED_OUTER_DIAGNOSTIC_OLD_ASE_LOGIC\",\"output_path\":\"${out}\"}"
  "${MAIN_ROOT}/envs/env_CARE/bin/python" \
    scripts/evaluation/care_ase/run_current_user_authorized_outer_diagnostic.py \
    --fold-step 2:14000 \
    --fold-step 3:14000 \
    --force \
    --output-name outer_diagnostic_final_14000_combined_summary.json
}

CORE_SPLIT="${RESULT_ROOT}/fair_panel_split_case_lists.csv"
FULL_SPLIT="${RESULT_ROOT}/split_case_lists.csv"

for fold in 2 3; do
  for step in 1000 2000 3000 4000 5000 6000 7000 8000 9000 10000 11000 12000 13000 14000; do
    run_core_comparison_status_if_missing "${fold}" "${step}"
  done

  for step in 2000 4000 6000 8000 10000 12000 14000; do
    run_monitor_if_missing \
      "${fold}" \
      "${step}" \
      "${FULL_SPLIT}" \
      "${RESULT_ROOT}/inner_checkpoint_monitor/fold_${fold}/$(printf 'step%05d' "${step}")"
  done

  run_formal_selector "${fold}"
done

run_user_authorized_outer_final_if_missing

status_json "${RESULT_ROOT}/post_training_fair_finalizer_status.json" "{\"status\":\"COMPLETE\",\"slurm_job_id\":\"${SLURM_JOB_ID:-local}\",\"phase\":\"comparison_status_formal_inner_and_user_authorized_outer_diagnostic_complete\",\"outer_accessed\":true,\"fairness_status\":\"USER_AUTHORIZED_OUTER_DIAGNOSTIC_OLD_ASE_LOGIC\",\"outer_diagnostic_final_path\":\"${RESULT_ROOT}/outer_diagnostic_user_authorized/outer_diagnostic_final_14000_combined_summary.json\",\"core_panel_metric_use\":\"diagnostic_only_not_direct_fair_claim\",\"log_file\":\"${LOG_FILE}\"}"
echo "JOB_END_UTC=$(date -u +%Y-%m-%dT%H:%M:%SZ)"
