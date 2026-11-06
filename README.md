# EditProbe — where small Gemma 4 agents lose a localized fix

EditProbe is a small diagnostic benchmark and harness for one step of an offline
bug-fixing agent: **turning a known fix into an edit that actually lands in the
file**. It targets the `edit_file(filepath, old_string, new_string)` tool of the
Kaggle *Gemma 4 Developer Agent* harness and the small Gemma 4 models (E2B, E4B)
that the competition allows.

- 35 single-file Python tasks adapted from the competition's dev-set repositories
  (`requests`, `rich`, `httpx`). Each task has a user-style problem statement, a
  buggy module (`src.py`), the gold module (`gold.py`), a 1–4 line gold fix and
  hidden pytest tests with FAIL_TO_PASS / PASS_TO_PASS sets.
- A runner that asks a Gemma 4 model (served by `llama-server`) for the fix under
  one of four edit protocols, applies it as the harness would, runs the tests and
  logs the full model output.
- A reimplementation of the harness's three-tier `edit_file` matcher
  (exact → whitespace-flexible → regex), reported per tier.
- All numbers in `results/` come from the logged runs in `results/*.jsonl`.

Everything runs on CPU. No GPU, no API keys, no gated downloads.

## Layout

```
bench/            task sources (one Python dict per task) and build_tasks.py
tasks/<id>/       materialized tasks: src.py, gold.py, test_task.py, task.json
harness/run.py    runner (OpenAI-compatible chat API, native tool calls)
harness/matcher.py  edit_file matching ladder
harness/analyze.py  tables -> results/summary.md
results/          raw JSONL logs (one record per task attempt) and summary.md
scripts/          run_model.sh
paper/            the Kaggle writeup draft
```

## Reproduce

Tested on Linux, 2 vCPU, 8 GB RAM, Python 3.13.

```bash
# 1. llama.cpp (any build after Gemma 4 support; we used commit 954de24, Nov 2026)
git clone --depth 1 https://github.com/ggml-org/llama.cpp
cmake -S llama.cpp -B llama.cpp/build -DCMAKE_BUILD_TYPE=Release -DLLAMA_CURL=OFF
cmake --build llama.cpp/build -j2 --target llama-server

# 2. official QAT q4_0 GGUF weights (not gated)
mkdir -p models
curl -L -o models/gemma-4-E2B_q4_0-it.gguf https://huggingface.co/google/gemma-4-E2B-it-qat-q4_0-gguf/resolve/main/gemma-4-E2B_q4_0-it.gguf
curl -L -o models/gemma-4-E4B_q4_0-it.gguf https://huggingface.co/google/gemma-4-E4B-it-qat-q4_0-gguf/resolve/main/gemma-4-E4B_q4_0-it.gguf

# 3. build and verify the tasks (gold passes, buggy fails)
pip install pytest
python bench/build_tasks.py

# 4. serve a model and run all protocols for it
llama.cpp/build/bin/llama-server -m models/gemma-4-E2B_q4_0-it.gguf --port 8080 -c 8192 -t 2 --jinja -np 1 &
scripts/run_model.sh e2b            # edit_file edit_file_v udiff write_file
# swap the model, then
scripts/run_model.sh e4b

# 5. tables
python harness/analyze.py
```

`harness/run.py --tasks <id> ...` runs a subset; `--resume` skips tasks already
logged; `--thinking` turns Gemma 4 thinking on (off by default — CPU budget).

## Protocols

| name | how the model edits | how we apply |
|---|---|---|
| `edit_file` | native tool call `edit_file(filepath, old_string, new_string)` | harness-style matcher: exact → whitespace-flexible → regex; fails if ambiguous |
| `edit_file_v` | same tool, plus an instruction to copy `old_string` verbatim with ≥2 lines of context | same |
| `write_file` | native tool call `write_file(filepath, content)` with the whole file | replace the file |
| `udiff` | unified diff in a ```diff block, no tools | `git apply`, then `patch -F3` |

## Failure ladder

Each attempt ends at exactly one stage:
`no_tool_call` / `bad_args` / `no_diff_found` → `old_not_found` / `old_ambiguous` / `patch_failed` / `truncated_output` → `syntax_error` → `tests_fail` / `tests_fail_regression` → `pass`.

`resolved` uses the competition's rule: pytest exits 0, every FAIL_TO_PASS and PASS_TO_PASS test passes.

## Licenses

Code and task text: Apache-2.0 (see `LICENSE`). Task modules are adapted from
`psf/requests` (Apache-2.0), `Textualize/rich` (MIT) and `encode/httpx`
(BSD-3-Clause); see `NOTICE`.
