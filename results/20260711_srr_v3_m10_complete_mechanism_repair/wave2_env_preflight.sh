#!/usr/bin/env bash
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=2
#SBATCH --job-name=M10W2Preflight
#SBATCH --output=/dev/null
#SBATCH --error=/dev/null
#SBATCH --mem=8G
#SBATCH --time=00:10:00
#SBATCH --gres=gpu:1
#SBATCH --partition=htzhulab
#SBATCH --qos=gpu_access
set -euo pipefail

CARE_ROOT="${CARE_ROOT:-/users/a/e/aereinh/CARE}"
cd "${CARE_ROOT}"
source "${CARE_ROOT}/.care-codex-env.sh"
source "${CARE_ROOT}/env_nnunet.sh"
export PATH=/users/a/e/aereinh/codex-runtime/bin:${CARE_ROOT}/envs/env_CARE/bin:${PATH}
mkdir -p logs
TS="$(date +%Y%m%d_%H%M%S)"
LOG_FILE="${LOG_FILE:-${CARE_ROOT}/logs/M10W2Preflight_${SLURM_JOB_ID:-local}_${TS}.log}"
exec > >(tee -a "${LOG_FILE}") 2>&1

echo "CARE_ROOT=${CARE_ROOT}"
echo "LOG_FILE=${LOG_FILE}"
echo "PYTHON=${CARE_ROOT}/envs/env_CARE/bin/python"

env_CARE/bin/python - <<'PY'
import mpmath
import sympy
import torch

p = torch.nn.Parameter(torch.ones(1))
torch.optim.AdamW([p], lr=1e-3)

print("mpmath", mpmath.__version__)
print("sympy", sympy.__version__)
print("optimizer_ok")
PY

"${CARE_ROOT}/envs/env_CARE/bin/python" - <<'PY'
import hashlib
import json
from pathlib import Path
import sys
import tempfile

import torch
import yaml

repo = Path.cwd()
if str(repo) not in sys.path:
    sys.path.insert(0, str(repo))

from scripts.training.run_srr_myops_fold0 import load_split  # noqa: E402


def sha256_path(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


print("python_executable", sys.executable)
print("python_version", sys.version.replace("\n", " "))
print("torch", torch.__version__)
print("cuda_available", torch.cuda.is_available())
print("cuda_device_count", torch.cuda.device_count())
if not torch.cuda.is_available():
    raise SystemExit("cuda_not_available")
print("cuda_device_0", torch.cuda.get_device_name(0))

config_path = repo / "configs/srr_v3_m10_complete_repair.yaml"
config = yaml.safe_load(config_path.read_text(encoding="utf-8"))
if config.get("task_key") != "20260711_srr_v3_m10_complete_mechanism_repair":
    raise SystemExit("config_task_key_mismatch")
print("config_task_key", config["task_key"])
print("config_designs", ",".join(sorted(config.get("designs", {}))))

for rel in [
    "logs",
    "results/20260711_srr_v3_m10_complete_mechanism_repair/logs",
    "results/20260711_srr_v3_m10_complete_mechanism_repair/locks",
    "results/20260711_srr_v3_m10_complete_mechanism_repair/runtime/m10_myops_training_executor",
]:
    path = repo / rel
    path.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(prefix=".m10_preflight_", dir=path, delete=True) as tmp:
        tmp.write(b"ok")
        tmp.flush()
    print("writable", rel)

train_ids, val_ids = load_split(0)
split_payload = json.dumps(
    {"fold": 0, "train": train_ids, "val": val_ids},
    sort_keys=True,
    separators=(",", ":"),
).encode("utf-8")
fingerprints = {
    "training_entrypoint": sha256_path(repo / "scripts/training/run_srr_v3_m10_complete_repair.py"),
    "evaluation_entrypoint": sha256_path(repo / "scripts/evaluation/evaluate_srr_v3_m10_full_case.py"),
    "aggregation_entrypoint": sha256_path(repo / "scripts/evaluation/aggregate_srr_v3_m10_myops.py"),
    "config": sha256_path(config_path),
    "executor_plan": sha256_path(repo / "prompts/tasks/20260711_srr_v3_m10_complete_mechanism_repair_executor_plan.yaml"),
    "preflight_script": sha256_path(repo / "results/20260711_srr_v3_m10_complete_mechanism_repair/wave2_env_preflight.sh"),
    "fold0_split_payload": hashlib.sha256(split_payload).hexdigest(),
}
print("fingerprints", json.dumps(fingerprints, sort_keys=True))
print("fold0_train_cases", len(train_ids))
print("fold0_val_cases", len(val_ids))
PY

"${CARE_ROOT}/envs/env_CARE/bin/python" scripts/training/run_srr_v3_m10_complete_repair.py --list-phases
for phase in \
  d0_control \
  d1_spatial_br2 \
  d2_hierarchical_psip \
  d3_full_propref \
  hard_negative_refresh \
  no_context_control \
  alignment_control
do
  echo "print_contract_phase=${phase}"
  "${CARE_ROOT}/envs/env_CARE/bin/python" scripts/training/run_srr_v3_m10_complete_repair.py --phase "${phase}" --print-contract
done
