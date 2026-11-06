#!/usr/bin/env bash
# Full experiment pipeline after the first E2B no-hint pass (run_model.sh e2b) is running.
set -uo pipefail
cd "$(dirname "$0")/.."
LLAMA=.tmp_llamacpp/build/bin/llama-server
run() { # label protocol [extra]
  echo "=== $1 $2 $3 $(date -u +%FT%TZ)"
  python3 harness/run.py --model "$1" --protocol "$2" --resume $3 2>&1 | tee -a "logs/run_$1_$2${3// /}.log"
}
# wait for the e2b no-hint pass
until grep -q "ALL_DONE e2b" logs/run_e2b_all.log; do sleep 20; done
for p in edit_file write_file udiff edit_file_v; do run e2b $p --hint; done
# swap server to E4B
pkill -f "llama-server -m models/gemma-4-E2B" || true; sleep 3
nohup $LLAMA -m models/gemma-4-E4B_q4_0-it.gguf --port 8080 -c 8192 -t 2 --jinja -np 1 --no-warmup > logs/server_e4b.log 2>&1 &
until curl -sf http://127.0.0.1:8080/health >/dev/null; do sleep 3; done
for p in edit_file write_file udiff edit_file_v; do run e4b $p ""; done
for p in edit_file write_file udiff edit_file_v; do run e4b $p --hint; done
echo "PIPELINE_DONE $(date -u +%FT%TZ)"
