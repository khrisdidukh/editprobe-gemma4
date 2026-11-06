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

All numbers: 35 tasks, one attempt each, temperature 0. The raw records (full model output, parsed edit, matcher tier, test output) are in `results/*.jsonl`; the tables below are produced by `harness/analyze.py` and `harness/rescore.py`.

### 4.1 Gemma 4 E2B

**Table 2. E2B by protocol, without and with the gold fix given as a hint.** "applied" = the edit reached the file; "resolved" = all hidden tests pass (bootstrap 95% CI over tasks).

| protocol | tool call ok | applied | compiles | resolved | 95% CI | == gold | mean tokens out | mean s/task |
|---|---|---|---|---|---|---|---|---|
| edit_file | 35 | 32 | 27 | **9 (26%)** | 11–40% | 3 | 210 | 23 |
| edit_file_v | 35 | 33 | 30 | **10 (29%)** | 14–46% | 5 | 192 | 18 |
| udiff | 35 | 31 | 31 | **10 (29%)** | 14–43% | 6 | 156 | 18 |
| write_file | 33 | 33 | 33 | **18 (51%)** | 34–69% | 9 | 481 | 48 |
| edit_file + hint | 35 | 35 | 34 | **34 (97%)** | 91–100% | 34 | 75 | 10 |
| edit_file_v + hint | 35 | 35 | 35 | **33 (94%)** | 86–100% | 32 | 75 | 7 |
| udiff + hint | 35 | 29 | 28 | **25 (71%)** | 57–86% | 22 | 116 | 14 |
| write_file + hint | 35 | 35 | 35 | **34 (97%)** | 91–100% | 31 | 475 | 47 |

**Landing an edit is not E2B's problem.** Given the fix in words, `edit_file` lands it and passes the tests in 34 of 35 tasks, and 34 of those 35 files are byte-identical to the gold file. Every `old_string` matched at the exact tier; the whitespace-flexible and regex tiers were never needed. The one failure is a span mismatch (below). `write_file` with the hint is equally good (34/35, 31 byte-identical). Unified diffs are the weak format for transcription: 6 of 35 diffs did not apply under any of our six passes (wrong context lines, hallucinated `-` lines) and 3 applied but changed nothing.

**Without the hint, the protocol changes the outcome by a factor of two.** Rewriting the whole file resolves 18 tasks; search/replace resolves 9 (10 with the verbatim-copy instruction); unified diff 10. The union over the four protocols is 21 tasks; only 4 tasks are solved by all four. `write_file` costs 2.3× the output tokens and 2× the wall time of `edit_file`, and it did not damage the files: 22 of 33 rewrites changed no line outside the gold region, and the mean number of extraneous changed lines is 0.5 (max 4).

Figure 1 shows where the attempts end.

![Figure 1. Failure ladder per condition.](results/ladder.png)

**Table 3. Failure ladder, E2B without hint.**

| protocol | no tool call | old_string not found | patch failed | no-op edit | syntax error | tests fail | regression | pass |
|---|---|---|---|---|---|---|---|---|
| edit_file | 0 | 3 | – | 6 | 5 | 10 | 2 | 9 |
| edit_file_v | 0 | 2 | – | 8 | 3 | 10 | 2 | 10 |
| udiff | – | – | 4 | 8 | 0 | 11 | 2 | 10 |
| write_file | 2 | – | – | 9 | 0 | 6 | 0 | 18 |

Three failure modes stand out.

*No-op edits.* In 6–9 of 35 tasks per protocol the model emits a syntactically perfect edit that changes nothing: `new_string == old_string`, or a whole-file rewrite identical to the input, or a diff whose `+` lines equal its `-` lines. One task (`rich_filesize_decimal`) is a no-op under all four protocols and eight tasks under at least two. These attempts cost a tool call and look like progress to an agent loop that only checks for errors. With the hint, no-ops fall to 0–1 (3 for udiff).

*Span mismatch.* All 5 syntax errors in `edit_file` and all 3 in `edit_file_v` have the same shape: `new_string` repeats lines that sit before or after `old_string` in the file (2 to 20 lines), so the replacement duplicates them. In one case (`httpx_timeout`) the correct fix was inside that overflow, outside the `old_string` span. A harness-side **anchor repair** — when the plain replacement does not compile, extend the replaced region to the first and last lines of `new_string` if each is found exactly once within 80 lines — makes 3 of the 4 repairable edits compile and turns `httpx_timeout` into a pass (Table 5). The repair never touches an edit that compiles, so it cannot lower the score.

*Hallucinated `old_string`.* 3 of 35 (`edit_file`) and 2 (`edit_file_v`) did not match: the model renamed an identifier or dropped a token while "copying" (e.g. `HEADER_VALIDATORS` → `_HEADER_VALIDATORS`, `(1 << 32 - mask) - 1` → `(1 << 33 - mask)`). These are not whitespace problems, so the harness's flexible tiers would not rescue them.

**Localization inside a 50-line file is the real bottleneck.** Among applied `edit_file` edits, only 14 of 32 touched the gold lines at all; 7 of those 14 resolved, against 2 of 18 that edited elsewhere. `write_file` touched the gold lines in 21 of 33 rewrites (17 resolved). The whole-file protocol seems to let the model re-read and re-emit the function it is fixing, where search/replace asks it to commit to a region first; [KD: this is an interpretation — keep, soften, or cut].

**Table 5. Anchor repair, replayed on the logged edits (no model calls).**

| condition | base resolved | syntax errors | repair compiles | repaired → pass | resolved with repair |
|---|---|---|---|---|---|
| E2B edit_file | 9 | 5 | 3 of 4 attempted | 1 | **10** |
| E2B edit_file_v | 10 | 3 | 1 of 1 | 0 | 10 |
| E2B edit_file + hint | 34 | 1 | 0 of 0 | 0 | 34 |
| [E4B rows TBD] | | | | | |

### 4.2 Gemma 4 E4B

[E4B RESULTS TBD — runs in progress]

### 4.3 Cost

The whole E2B grid (8 conditions × 35 tasks) took [TBD] hours of wall time on two CPU cores; E4B [TBD]. Prompts are 685–833 tokens on average; `write_file` answers are a median 448 tokens.

## 5. What this means for an agent built on E2B/E4B

1. **For files that fit in one `read_file` window, prefer `write_file` over `edit_file` on E2B.** It doubled the resolve rate here at ~2× the tokens. The competition's `write_file` tool exists; the sample agent instructions push `edit_file`. [KD: you may want to state this more carefully — it is one benchmark, 35 tasks]
2. **Check for no-op edits in the harness or the instruction.** A tool result that says "file unchanged" (string compare before/after) is free and would have flagged 17–26% of E2B's edits.
3. **Add anchor repair to the edit tool.** It is 40 lines, replayable, and only acts when the plain edit does not compile.
4. **Do not ask E2B for unified diffs.** Even when told the exact fix, 10 of 35 diffs failed to land or changed nothing.
5. **Localization, not transcription, is where to spend tokens.** With the fix known, E2B lands it 97% of the time in 75 tokens. Agent designs that first make the model name the lines to change (and verify they exist) and only then edit would address the failure we actually observe.

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
