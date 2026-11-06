# EditProbe: where small Gemma 4 agents lose a localized fix

**Subtitle:** A 35-task diagnostic for the `edit_file` step of offline bug-fixing agents, run on CPU with Gemma 4 E2B and E4B

**Author:** Khrystyna Didukh (Vienna). Code, tasks and logs: [KD: GitHub URL], Apache-2.0.

## Abstract

[TO BE WRITTEN FROM FINAL NUMBERS]

## 1. Introduction

The Gemma 4 Developer Agent competition asks for an offline agent that fixes bugs in Python repositories. The agent reads files, runs commands and changes code through a small tool set; the change itself goes through `edit_file(filepath, old_string, new_string)` or `write_file(filepath, content)`. A task counts only if the patched repository passes hidden tests.

Public dev-set numbers show how little the small models manage: in a pre-registered study of 104 public tasks, Gemma 4 E4B resolved 10% of tasks with a minimal scaffold and 15% with a maximal one (Toeda, 2026). The gold patches in that dev set are small: median 12 changed lines, 91 of 129 tasks touch one file (Fearoff5214, 2026). So a large share of the work is: find a few lines, write a few lines, land them in the file.

This note isolates the last two steps. We remove localization across a repository (the model sees the one file that contains the bug, 18–97 lines) and ask: when a small Gemma 4 model has the bug in front of it, does its edit (a) get emitted as a valid tool call, (b) match the file, (c) leave the file syntactically valid, (d) fix the bug without breaking other tests? We also give the model the gold fix in words to separate "cannot land an edit" from "cannot find the fix".

Contributions:

1. **EditProbe**, 35 single-file tasks adapted from the competition's dev-set repositories (requests, rich, httpx), each with a user-style problem statement, a 1–5 line gold fix and hidden FAIL_TO_PASS / PASS_TO_PASS tests. Built and verified by one script.
2. A harness that drives Gemma 4 through native tool calls on `llama-server`, applies edits with a reimplementation of the harness's three-tier `edit_file` matcher (exact → whitespace-flexible → regex), and logs every model output. CPU only; 2 vCPUs are enough.
3. Measurements for E2B and E4B (official QAT q4_0 GGUF) across four edit protocols, with and without the gold fix given as a hint. [KD: one-sentence headline once numbers are final]
4. A named failure mode, **span mismatch** (new_string covers more of the file than old_string, so a plain replacement duplicates code), and a harness-side repair that recovers part of it without any model change.

Everything here is cheap to re-run: the full grid took [TBD] hours on two CPU cores. Nothing is gated or paid.

## 2. Related work

**Repository-level bug fixing.** SWE-bench (Jimenez et al., 2024) set the task format the competition uses: issue text in, patch out, hidden tests decide. SWE-agent (Yang et al., 2024) showed that the *agent–computer interface* — how files are viewed and edited — changes success rates by several points for the same model, and introduced linting of edits before they are accepted. Agentless (Xia et al., 2024) split the problem into localization, repair and validation and found that a simple pipeline competes with agents. OpenHands (Wang et al., 2024) is the common open framework. Our tasks sit at the "repair" end of that split, with localization given.

**Edit formats.** Aider's edit-format experiments (Gauthier, 2023) found that unified diffs cut "lazy" partial rewrites of GPT-4 Turbo, and Aider ships whole-file, search/replace and udiff formats with per-model defaults. Diff-XYZ (Glukhov et al., 2025) benchmarks applying, reversing and generating diffs in several formats and reports that the best format depends on model size; search/replace generation worked well for large proprietary models but faithful application was weak, and small open models scored near zero. We ask the same question for one model family, two small sizes, and the exact tool semantics of the competition harness, with tests as the judge rather than exact match.

**Synthetic bugs in real code.** SWE-smith (Yang et al., 2025) injects bugs into real repositories at scale to make training data; HumanEvalFix (Muennighoff et al., 2023) gives small buggy functions with tests; QuixBugs and Defects4J are the classic small-program and Java sets. EditProbe is far smaller and hand-made, but every bug is in code adapted from the competition's own dev repositories and every task has a verified gold fix.

**Gemma 4 agents in this competition.** Toeda (2026) measured scaffold effects for E4B, 12B and 26B-A4B on the public tasks (E4B: 10.0% → 15.4%). A study of tool-call loops in Gemma 4 31B and 12B (Gemma4_paper_track, 2026) found that at 12B loops often sit on failing edits and truncated reads. We measure the failing edits themselves.

## 3. EditProbe

### 3.1 Tasks

Each task is one directory: `src.py` (buggy module), `gold.py`, `test_task.py` (hidden), `task.json` (problem statement, source attribution, gold region). We wrote them as follows.

- Pick a function or small class from `requests/utils.py`, `requests/structures.py`, `rich/_loop.py`, `rich/_ratio.py`, `rich/cells.py`, `rich/_wrap.py`, `rich/filesize.py`, `rich/markup.py`, `rich/color*.py`, `httpx/_decoders.py`, `httpx/_utils.py`, `httpx/_urlparse.py`, `httpx/_multipart.py`, `httpx/_config.py` and make it standalone (docstrings kept, imports inlined). Licenses: Apache-2.0, MIT, BSD-3; see `NOTICE`.
- Write 4–5 pytest tests.
- Inject one bug as a string replacement (`mutation = (gold_text, buggy_text)`): off-by-one, dropped `.lower()`, wrong constant, missing `max(...)`, removed branch, wrong regex, inverted condition, lost tail element. The reversed mutation is the gold fix.
- Write the problem statement as a user would: observed output, expected output, what still works. Never the line number or the fix.

`bench/build_tasks.py` materializes the 35 tasks and refuses any task where the gold module fails a test, the buggy module passes all tests, or the mutation string is not unique. Table 1 summarizes the set.

| | |
|---|---|
| tasks | 35 (12 requests, 11 rich, 12 httpx) |
| module length | median 47 lines (18–97) |
| gold fix | 1 line in 32 tasks, 2 lines in 1, 5 lines in 2 |
| problem statement | median 258 characters |
| tests | 51 FAIL_TO_PASS, 92 PASS_TO_PASS in total |

### 3.2 Protocols

The model gets one system message and one user message: problem statement, the whole `src.py` in a code block, an optional hint, and one instruction line. Four protocols:

| protocol | model output | how it is applied |
|---|---|---|
| `edit_file` | native tool call `edit_file(filepath, old_string, new_string)` | three-tier matcher (below) |
| `edit_file_v` | same, with an instruction to copy `old_string` verbatim with ≥2 lines of context | same |
| `write_file` | native tool call `write_file(filepath, content)` | file replaced |
| `udiff` | unified diff in a fenced block, no tools | `git apply`, then `patch -F3` |

The **hint** condition appends the gold fix in words: "The bug is in these lines: ‹buggy lines›. They should become: ‹gold lines›". With the hint, the task is pure transcription into an edit.

### 3.3 Matcher

HARNESS_README describes `edit_file` as "tries an exact match, then a whitespace-flexible match, then a regex match; fails when more than one place matches". We do not have the harness source, so `harness/matcher.py` is our reading of that sentence: tier 1 exact substring (must be unique); tier 2 the same tokens with any whitespace between them (`\s+`), unique; tier 3 `old_string` compiled as a Python regex, unique. Every applied edit is tagged with its tier.

### 3.4 Failure ladder

Each attempt ends at exactly one stage:

`no_tool_call` · `bad_args` · `no_diff_found` → `old_not_found` · `old_ambiguous` · `patch_failed` · `truncated_output` → `noop_edit` (file unchanged) → `syntax_error` → `tests_fail` · `tests_fail_regression` (FAIL_TO_PASS fixed, a PASS_TO_PASS broken) → `pass`.

`pass` follows the competition rule: pytest exits 0 and every FAIL_TO_PASS and PASS_TO_PASS test passes. We also record `extraneous_lines` (changed lines of `src.py` outside the gold region), completion tokens and wall time.

### 3.5 Setup

llama.cpp commit 954de24 (6 Nov 2026) built for CPU; `llama-server --jinja`, context 8192, 2 threads. Models: `google/gemma-4-E2B-it-qat-q4_0-gguf` and `google/gemma-4-E4B-it-qat-q4_0-gguf` (official QAT checkpoints, not gated). Temperature 0, thinking off, one attempt per task, `max_tokens` 1200 (3000 for `write_file`). Machine: 2 vCPU, 7.8 GB RAM. E2B generates at 10–12 tokens/s here.

The competition serves `*-it-qat-w4a16-ct` through vLLM; our GGUF q4_0 files are the same QAT family in a different container. Tool calls use llama.cpp's Gemma 4 chat template, which is not byte-identical to vLLM's parser. Both are limitations, and both are reproducible.

## 4. Results

[TO BE FILLED FROM results/summary.md AND results/rescore.md]

## 5. What this means for an agent built on E2B/E4B

[TO BE WRITTEN]

## 6. Limitations

- 35 tasks, one attempt each at temperature 0. Confidence intervals are wide (bootstrap over tasks); differences of a few tasks are not evidence.
- Bugs are injected mutations in code we made standalone; real issues are longer and the files larger. Our file sizes stay under one `read_file` call (150 lines), by design.
- The matcher and the apply policy are reimplemented from the README's description.
- Thinking was off. [KD: decide whether to keep or cut any thinking-on subset results]
- Tasks were written by one person who also knows the models' typical mistakes; they were written before any model run, and no task was changed after seeing results.

## References

- Jimenez, C. E., Yang, J., Wettig, A., Yao, S., Pei, K., Press, O., Narasimhan, K. (2024). SWE-bench: Can Language Models Resolve Real-World GitHub Issues? ICLR 2024. arXiv:2310.06770.
- Yang, J., Jimenez, C. E., Wettig, A., Lieret, K., Yao, S., Narasimhan, K., Press, O. (2024). SWE-agent: Agent-Computer Interfaces Enable Automated Software Engineering. NeurIPS 2024. arXiv:2405.15793.
- Xia, C. S., Deng, Y., Dunn, S., Zhang, L. (2024). Agentless: Demystifying LLM-based Software Engineering Agents. arXiv:2407.01489.
- Wang, X. et al. (2024). OpenHands: An Open Platform for AI Software Developers as Generalist Agents. arXiv:2407.16741.
- Gauthier, P. (2023). Unified diffs make GPT-4 Turbo 3X less lazy. https://aider.chat/docs/unified-diffs.html
- Glukhov, E., Bogomolov, E., Conti, M., Golubev, Y., Bezzubov, A. (2025). Diff-XYZ: A Benchmark for Evaluating Diff Understanding. NeurIPS 2025 Workshop on Deep Learning for Code in the Agentic Era. arXiv:2510.12487.
- Yang, J., Lieret, K., Jimenez, C. E., Wettig, A., Khandpur, K., Zhang, Y., Hui, B., Press, O., Schmidt, L., Yang, D. (2025). SWE-smith: Scaling Data for Software Engineering Agents. arXiv:2504.21798.
- Muennighoff, N. et al. (2023). OctoPack: Instruction Tuning Code Large Language Models. arXiv:2308.07124 (HumanEvalFix).
- Toeda, T. (2026). Scaffolding Helps the Smallest Gemma 4 Agent, Not the Larger Ones: run records, pre-registration and analysis code. Zenodo. doi:10.5281/zenodo.23834104.
- Gemma4_paper_track (2026). Why Gemma 4 31B loops on tool calls: ablations G1–G4 and a 12B control. https://github.com/usp787/Gemma4_paper_track (findings.md). [KD: the author name is not given in the repo; keep as repository citation or drop]
- Fearoff5214 (2026). Gemma_4_Kaggle_hackathon: dataset inventory and harness notes. https://github.com/Fearoff5214/Gemma_4_Kaggle_hackathon
- Google DeepMind (2026). Gemma 4. https://blog.google/innovation-and-ai/technology/developers-tools/gemma-4/ (released 2 Apr 2026, Apache-2.0).
- Kaggle (2026). Google – The Gemma 4 Developer Agent; Paper Track. https://www.kaggle.com/competitions/gemma-4-developer-agent-paper
- ggml-org (2026). llama.cpp. https://github.com/ggml-org/llama.cpp
