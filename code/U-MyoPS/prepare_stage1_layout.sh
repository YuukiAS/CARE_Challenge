#!/usr/bin/env bash
# Bridge CARE-prepared U-MyoPS staging into the legacy Stage1 jrs layout.
# Upstream Stage1 expects:
#   third_party/U-MyoPS_myops/data/gen_<data_source>/data/
#   third_party/U-MyoPS_myops/data/gen_<data_source>/croped/
# CARE prepares data under:
#   data/benchmarks/U-MyoPS/gen_<data_source>/data/
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
CARE_ROOT="${CARE_ROOT:-$(cd "${SCRIPT_DIR}/../.." && pwd)}"
DATA_SOURCE="${UMYOPS_DATA_SOURCE:-ZS_unaligned}"
STAGED_ROOT="${UMYOPS_STAGE1_STAGED_ROOT:-${CARE_ROOT}/data/benchmarks/U-MyoPS/gen_${DATA_SOURCE}/data}"
LEGACY_ROOT="${UMYOPS_STAGE1_LEGACY_ROOT:-${CARE_ROOT}/third_party/U-MyoPS_myops/data/gen_${DATA_SOURCE}}"
LEGACY_DATA_LINK="${LEGACY_ROOT}/data"
LEGACY_CROPED_DIR="${LEGACY_ROOT}/croped"

if [[ ! -d "${STAGED_ROOT}" ]]; then
  echo "Missing CARE Stage1 staging root: ${STAGED_ROOT}" >&2
  echo "Run code/U-MyoPS/prepare_u_myops_from_care.py first, or override UMYOPS_STAGE1_STAGED_ROOT." >&2
  exit 1
fi

mkdir -p "${LEGACY_ROOT}" "${LEGACY_CROPED_DIR}"

if [[ -e "${LEGACY_DATA_LINK}" && ! -L "${LEGACY_DATA_LINK}" ]]; then
  echo "Legacy Stage1 data path exists and is not a symlink: ${LEGACY_DATA_LINK}" >&2
  echo "Move it aside or point UMYOPS_STAGE1_LEGACY_ROOT to a clean path." >&2
  exit 1
fi

ln -sfn "${STAGED_ROOT}" "${LEGACY_DATA_LINK}"

linked=0
for subject_dir in "${STAGED_ROOT}"/*; do
  [[ -d "${subject_dir}" ]] || continue
  subject_name="$(basename "${subject_dir}")"
  src_image=""
  for pattern in "*_img_de_*.nii.gz" "*_img_c0_*.nii.gz" "*_img_t2_*.nii.gz"; do
    for candidate in "${subject_dir}"/${pattern}; do
      if [[ -f "${candidate}" ]]; then
        src_image="${candidate}"
        break 2
      fi
    done
  done
  if [[ -z "${src_image}" ]]; then
    echo "Skip ${subject_name}: no Stage1 image found for croped link." >&2
    continue
  fi
  ln -sfn "${src_image}" "${LEGACY_CROPED_DIR}/${subject_name}.nii.gz"
  linked=$((linked + 1))
done

if [[ "${linked}" -eq 0 ]]; then
  echo "No croped links were created under ${LEGACY_CROPED_DIR}" >&2
  exit 1
fi

echo "Prepared U-MyoPS Stage1 legacy layout:"
echo "  staged_root=${STAGED_ROOT}"
echo "  legacy_data=${LEGACY_DATA_LINK}"
echo "  legacy_croped=${LEGACY_CROPED_DIR}"
echo "  linked_subjects=${linked}"
