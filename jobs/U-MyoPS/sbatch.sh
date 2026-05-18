#!/bin/bash
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=8
#SBATCH --job-name=U-MyoPS-Stage1-D501
#SBATCH --output=/dev/null
#SBATCH --error=/dev/null
#SBATCH --mem=64G
#SBATCH --time=2-00:00:00
#SBATCH --gres=gpu:1
#SBATCH --partition=htzhulab
#SBATCH --qos=gpu_access
#
# Legacy entrypoint: same as sbatch_stage1.sh (U-MyoPS stage 1 only). For stage 2 use sbatch_stage2.sh.
set -euo pipefail
export PATH="/usr/local/bin:/usr/bin:/bin:${PATH:-}"
if [[ -n "${SLURM_SUBMIT_DIR:-}" ]]; then
  _CARE_ROOT="$(cd "${SLURM_SUBMIT_DIR}" && pwd)"
else
  _HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
  _CARE_ROOT="$(cd "${_HERE}/../.." && pwd)"
fi
exec /bin/bash "${_CARE_ROOT}/jobs/U-MyoPS/sbatch_stage1.sh" "$@"
