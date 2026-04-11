#!/usr/bin/env bash
# Thin wrapper; implementation lives in scripts/nnunet/run_smoke.sh
set -euo pipefail
exec "$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/nnunet/run_smoke.sh" "$@"
