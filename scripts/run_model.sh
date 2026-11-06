#!/usr/bin/env bash
# Run all protocols for the model currently served by llama-server.
# Usage: scripts/run_model.sh <label> [protocols...]
set -euo pipefail
cd "$(dirname "$0")/.."
label="$1"; shift
protos=("$@"); [ ${#protos[@]} -eq 0 ] && protos=(edit_file edit_file_v udiff write_file)
for p in "${protos[@]}"; do
  echo "=== $label $p $(date -u +%FT%TZ)"
  python3 harness/run.py --model "$label" --protocol "$p" --resume 2>&1 | tee -a "logs/run_${label}_${p}.log"
done
echo "ALL_DONE $label $(date -u +%FT%TZ)"
