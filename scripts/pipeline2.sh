#!/usr/bin/env bash
# E4B passes with a server watchdog. Order = priority. Resumable.
set -uo pipefail
cd "$(dirname "$0")/.."
LLAMA=.tmp_llamacpp/build/bin/llama-server
MODEL=models/gemma-4-E4B_q4_0-it.gguf
ensure_server() {
  if ! curl -sf http://127.0.0.1:8080/health >/dev/null 2>&1; then
    pkill -f "llama-server -m" || true; sleep 2
    nohup $LLAMA -m $MODEL --port 8080 -c 6144 -t 2 --jinja -np 1 --no-warmup --no-repack >> logs/server_e4b.log 2>&1 &
    until curl -sf http://127.0.0.1:8080/health >/dev/null 2>&1; do sleep 3; done
    echo "server (re)started $(date -u +%FT%TZ)"
  fi
}
run() { # protocol extra
  for attempt in 1 2 3 4 5; do
    ensure_server
    echo "=== e4b $1 $2 attempt $attempt $(date -u +%FT%TZ)"
    if python3 harness/run.py --model e4b --protocol "$1" --resume $2 2>&1 | tee -a "logs/run_e4b_$1${2// /}.log"; then
      if [ "${PIPESTATUS[0]}" -eq 0 ]; then return 0; fi
    fi
    sleep 5
  done
}
run write_file ""
run edit_file --hint
run udiff ""
run write_file --hint
run edit_file_v ""
run udiff --hint
run edit_file_v --hint
echo "PIPELINE2_DONE $(date -u +%FT%TZ)"
