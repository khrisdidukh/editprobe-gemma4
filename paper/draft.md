# EditProbe: where small Gemma 4 agents lose a localized fix

**Subtitle:** A 35-task diagnostic for the `edit_file` step of offline bug-fixing agents, run on CPU with Gemma 4 E2B and E4B

**Author:** Khrystyna Didukh (Vienna). Code, tasks and logs: [KD: GitHub URL], Apache-2.0.

## Abstract

Small open models fail most bug-fixing tasks in the Gemma 4 Developer Agent competition, but it is unclear which step fails. EditProbe is a 35-task diagnostic that hands the model the one buggy file (18–97 lines) and scores the edit it makes under the competition's tool semantics, with hidden tests as the judge. Run on two CPU cores with Gemma 4 E2B and E4B across four edit protocols, it shows that landing an edit is not the problem: given the fix in words, both models land it in 94–97% of tasks. Without the hint they resolve 26–51% (E2B) and 43–63% (E4B). E2B loses tasks to no-op edits and duplicated code; E4B's edits are clean but often change the wrong lines. In both models, an edit that misses the buggy lines almost never passes. Whole-file rewrites beat `edit_file` for both sizes.

## 1. Introduction

The Gemma 4 Developer Agent competition asks for an offline agent that fixes bugs in Python repositories. The agent reads files, runs commands and changes code through a small tool set; the change itself goes through `edit_file(filepath, old_string, new_string)` or `write_file(filepath, content)`. Hidden tests decide.

Public dev-set numbers show how little the small models manage: in a pre-registered study of 104 public tasks, Gemma 4 E4B resolved 10% of tasks with a minimal scaffold and 15% with a maximal one (Toeda, 2026). The gold patches in that dev set are small: median 12 changed lines, 91 of 129 tasks touch one file (Fearoff5214, 2026). So a large share of the work is: find a few lines, write a few lines, land them in the file.

This note isolates the last two steps. The model sees the one file that contains the bug (18–97 lines), and we ask: when a small Gemma 4 model has the bug in front of it, does its edit (a) get emitted as a valid tool call, (b) match the file, (c) leave the file syntactically valid, (d) fix the bug without breaking other tests? We also give the model the gold fix in words to separate "cannot land an edit" from "cannot find the fix".

Contributions:

1. **EditProbe**, 35 single-file tasks adapted from the competition's dev-set repositories (requests, rich, httpx), each with a user-style problem statement, a 1–5 line gold fix and hidden FAIL_TO_PASS / PASS_TO_PASS tests.
2. A harness that drives Gemma 4 through native tool calls on `llama-server`, applies edits with a reimplementation of the harness's three-tier `edit_file` matcher (exact → whitespace-flexible → regex), and logs every model output.
3. Measurements for E2B and E4B (official QAT q4_0 GGUF) across four edit protocols, with and without the gold fix given as a hint. Both models land a known fix almost perfectly; without the fix, the edit usually fails because it touches the wrong lines.
4. A named failure mode, **span mismatch** (new_string covers more of the file than old_string, so a plain replacement duplicates code), and a harness-side repair that recovers part of it without any model change.

The full grid (560 attempts) re-runs in about 10 hours on two CPU cores; nothing is gated or paid.

## 2. Related work

**Repository-level bug fixing.** SWE-bench (Jimenez et al., 2024) set the format the competition uses: issue in, patch out, hidden tests decide. SWE-agent (Yang et al., 2024) showed that the agent–computer interface (how files are viewed and edited) moves success rates for the same model, and lints edits before accepting them. Agentless (Xia et al., 2024) splits the work into localization, repair and validation; OpenHands (Wang et al., 2024) is the common open framework. Our tasks sit at the repair end, with file-level localization given.

**Edit formats.** Aider (Gauthier, 2023) found that unified diffs reduced "lazy" partial rewrites of GPT-4 Turbo and ships whole-file, search/replace and udiff formats with per-model defaults. Diff-XYZ (Glukhov et al., 2025) reports that the best diff format depends on model size and that small open models score near zero. We ask the same question for two small Gemma 4 sizes under the competition's exact tool semantics, with tests as the judge.

**Synthetic bugs.** SWE-smith (Yang et al., 2025) and HumanEvalFix (Muennighoff et al., 2023) inject bugs into real code; EditProbe is smaller but uses the competition's own dev repositories.

**Gemma 4 agents.** Toeda (2026) measured scaffold effects for E4B, 12B and 26B-A4B on the public tasks. A study of tool-call loops in Gemma 4 31B and 12B (Gemma4_paper_track, 2026) found that loops often sit on failing edits. We measure the failing edits themselves.

## 3. EditProbe

### 3.1 Tasks

Each task is a directory with `src.py` (buggy module), `gold.py`, hidden `test_task.py` and `task.json` (problem statement, source, gold region). To build one we took a function or small class from requests, rich or httpx (14 modules, e.g. `requests/utils.py`, `rich/cells.py`, `httpx/_urlparse.py`), made it standalone, wrote 4–5 pytest tests, and injected one bug as a string replacement: off-by-one, dropped `.lower()`, wrong constant, missing `max(...)`, removed branch, wrong regex, inverted condition. The reversed mutation is the gold fix. The problem statement reads like a user report (observed vs expected output), never naming the line or the fix. Licenses (Apache-2.0, MIT, BSD-3) are in `NOTICE`.

`bench/build_tasks.py` refuses any task where the gold module fails a test, the buggy module passes all tests, or the mutation is not unique.

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

The competition README says `edit_file` tries an exact match, then a whitespace-flexible match, then a regex match, and fails when more than one place matches. `harness/matcher.py` is our reading of that: exact substring, then the same tokens with any whitespace between them, then `old_string` as a Python regex; each tier requires a unique match. Every applied edit is tagged with its tier.

### 3.4 Failure ladder

Each attempt ends at exactly one stage:

`no_tool_call` · `bad_args` · `no_diff_found` → `old_not_found` · `old_ambiguous` · `patch_failed` · `truncated_output` → `noop_edit` (file unchanged) → `syntax_error` → `tests_fail` · `tests_fail_regression` (FAIL_TO_PASS fixed, a PASS_TO_PASS broken) → `pass`.

`pass` follows the competition rule: every FAIL_TO_PASS and PASS_TO_PASS test passes. We also record changed lines outside the gold region, output tokens and wall time.

### 3.5 Setup

llama.cpp commit 954de24 (6 Nov 2026) built for CPU; `llama-server --jinja`, 2 threads, context 8192 (6144 for part of the E4B runs; prompts are under 1k tokens, so this does not change outputs). Models: `google/gemma-4-E2B-it-qat-q4_0-gguf` and `google/gemma-4-E4B-it-qat-q4_0-gguf` (official QAT checkpoints, not gated). Temperature 0, thinking off, one attempt per task, `max_tokens` 1200 (3000 for `write_file`). Machine: 2 vCPU, 7.8 GB RAM. E2B generates at 10–12 tokens/s here.

## 4. Results

All numbers: 35 tasks, one attempt each, temperature 0. Raw records (model output, parsed edit, matcher tier, test output) are in `results/*.jsonl`; tables come from `harness/analyze.py` and `harness/rescore.py`.

### 4.1 Gemma 4 E2B

**Table 2. E2B by protocol, without and with the gold fix as a hint.** "applied" = the edit reached the file; "resolved" = all hidden tests pass (bootstrap 95% CI over tasks).

| protocol | applied | compiles | resolved | 95% CI | == gold | mean tokens out |
|---|---|---|---|---|---|---|
| edit_file | 32 | 27 | **9 (26%)** | 11–40% | 3 | 210 |
| edit_file_v | 33 | 30 | **10 (29%)** | 14–46% | 5 | 192 |
| udiff | 31 | 31 | **10 (29%)** | 14–43% | 6 | 156 |
| write_file | 33 | 33 | **18 (51%)** | 34–69% | 9 | 481 |
| edit_file + hint | 35 | 34 | **34 (97%)** | 91–100% | 34 | 75 |
| edit_file_v + hint | 35 | 35 | **33 (94%)** | 86–100% | 32 | 75 |
| udiff + hint | 29 | 28 | **25 (71%)** | 57–86% | 22 | 116 |
| write_file + hint | 35 | 35 | **34 (97%)** | 91–100% | 31 | 475 |

**Landing an edit is not E2B's problem.** Given the fix in words, `edit_file` passes in 34 of 35 tasks, all 34 byte-identical to the gold file, and every `old_string` matched at the exact tier: the whitespace-flexible and regex tiers were never needed. Unified diffs are the weak format even for transcription: 6 of 35 did not apply under any of our passes (wrong context, invented `-` lines) and 3 changed nothing.

**Without the hint, the protocol changes the outcome by a factor of two.** `write_file` resolves 18 tasks, search/replace 9–10, unified diff 10. The union over the four protocols is 21 tasks; only 4 are solved by all four. `write_file` costs 2.3× the output tokens of `edit_file` and did not damage files: mean 0.5 changed lines outside the gold region (max 4).

![Figure 1. Where attempts end, per model and condition.](results/ladder.png)

Figure 1 shows three E2B failure modes.

*No-op edits.* In 6–9 tasks per protocol the model emits a valid edit that changes nothing: `new_string == old_string`, a rewrite identical to the input, or a diff whose `+` and `-` lines are equal. One task (`rich_filesize_decimal`) is a no-op under all four protocols. An agent loop that only checks for errors sees progress.

*Span mismatch.* All 5 syntax errors in `edit_file` and all 3 in `edit_file_v` have one shape: `new_string` repeats 2–20 lines that sit before or after `old_string`, so the replacement duplicates them. A harness-side **anchor repair** (when the plain replacement does not compile, extend the replaced region to the first and last lines of `new_string` if each occurs once within 80 lines) makes 3 of 4 repairable edits compile and turns one into a pass (Table 5). It never touches an edit that compiles, so it cannot lower the score.

*Hallucinated `old_string`.* 5 edits across the two search/replace protocols did not match because the model renamed an identifier while copying (`HEADER_VALIDATORS` → `_HEADER_VALIDATORS`). These are not whitespace problems; the flexible tiers cannot rescue them.

### 4.2 Gemma 4 E4B

**Table 4. E4B, same protocols.**

| protocol | applied | compiles | resolved | 95% CI | == gold | mean tokens out |
|---|---|---|---|---|---|---|
| edit_file | 34 | 33 | **16 (46%)** | 29–63% | 13 | 113 |
| edit_file_v | 34 | 32 | **15 (43%)** | 26–60% | 11 | 117 |
| udiff | 32 | 32 | **17 (49%)** | 31–66% | 14 | 149 |
| write_file | 35 | 35 | **22 (63%)** | 46–80% | 8 | 510 |
| edit_file + hint | 35 | 34 | **33 (94%)** | 86–100% | 32 | 68 |
| edit_file_v + hint | 35 | 34 | **33 (94%)** | 86–100% | 31 | 70 |
| udiff + hint | 32 | 32 | **30 (86%)** | 74–97% | 25 | 115 |
| write_file + hint | 35 | 35 | **34 (97%)** | 91–100% | 28 | 474 |

**E4B fixes the mechanics, not the diagnosis.** No-op edits almost disappear (0 in `edit_file`, against 6 for E2B), syntax errors drop to 1–2, and unified diffs apply in 32 of 35 tasks, with or without the hint. Resolution rises to 43–63% and the four protocols agree far more: 12 tasks are solved by all four (E2B: 4), 23 by at least one. The dominant failure is now `tests_fail`, a clean compiling edit with the wrong lines or logic: 16 of 35 for `edit_file`. `write_file` is still the best protocol without a hint, but its lead over `edit_file` shrinks from 2× to 1.4×. The verbatim-copy instruction (`edit_file_v`) helps neither model.

**Localization separates success from failure in both models.** We check whether an applied edit's removed lines intersect the buggy lines:

| condition | applied | touched gold lines | resolved if touched | resolved if not |
|---|---|---|---|---|
| E2B edit_file | 32 | 14 | 7/14 | 2/18 |
| E2B write_file | 33 | 21 | 17/21 | 1/12 |
| E4B edit_file | 34 | 22 | 15/22 | 1/12 |
| E4B write_file | 35 | 24 | 21/24 | 1/11 |

Across the four rows, edits that miss the buggy lines pass 5 times in 53 attempts. E4B localizes better than E2B (22 vs 14 of the applied `edit_file` edits), and that is most of its gain. Nine tasks were never solved without the hint by either model under any protocol; with the hint, every task is solved by both.

**Table 5. Anchor repair, replayed on the logged edits (no model calls).**

| condition | base resolved | syntax errors | repair compiles | resolved with repair |
|---|---|---|---|---|
| E2B edit_file | 9 | 5 | 3 of 4 attempted | **10** |
| E2B edit_file_v | 10 | 3 | 1 of 1 | 10 |
| E4B edit_file | 16 | 1 | 1 of 1 | 16 |
| E4B edit_file_v | 15 | 2 | 1 of 1 | 15 |

The repair matters for E2B and is idle for E4B, which rarely produces span mismatches.

### 4.3 Cost

E2B's grid (8 conditions × 35 tasks) took 1.8 hours of wall time on two CPU cores; E4B's took 7.9 hours, inflated by shared-machine load and several container restarts (runs resume per task). Prompts average 685–833 tokens; `write_file` answers about 480.

## 5. What this means for an agent built on E2B/E4B

1. **Spend tokens on localization, not on edit formats.** With the fix known, both models land it in 94–97% of tasks for about 70 output tokens. Without it, an edit that misses the buggy lines almost never passes. An agent that first makes the model name the lines it will change (and checks they exist and relate to the failing test) targets the failure we actually observe.
2. **For files that fit in one `read_file` window, consider `write_file`.** It led for both sizes here (51% vs 26% on E2B, 63% vs 46% on E4B) at 2.3–4.5× the output tokens. This is one 35-task benchmark; the intervals overlap for E4B.
3. **Report no-op edits back to the model.** A string compare before and after the edit is free and would have flagged 17–26% of E2B's edits.
4. **Add anchor repair to `edit_file` if you run E2B.** It is about 40 lines and acts only when the plain edit does not compile.
5. **Do not ask E2B for unified diffs.** Even with the exact fix, 10 of 35 failed to land or changed nothing. E4B handles diffs well.

## 6. Limitations

- 35 tasks, one attempt each at temperature 0. Confidence intervals are wide; differences of a few tasks are not evidence.
- Bugs are injected mutations in code we made standalone. Real issues are longer and files larger; ours stay under one `read_file` call (150 lines) by design.
- The matcher is reimplemented from the competition README; the GGUF q4_0 files are the same QAT family as the competition's w4a16 checkpoints in a different container, and llama.cpp's tool-call parser differs from vLLM's.
- Thinking was off for all runs.
- One person wrote the tasks before any model run; no task was changed after seeing results.

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
- Gemma4_paper_track (2026). Why Gemma 4 31B loops on tool calls: ablations G1–G4 and a 12B control. https://github.com/usp787/Gemma4_paper_track (findings.md).
- Fearoff5214 (2026). Gemma_4_Kaggle_hackathon: dataset inventory and harness notes. https://github.com/Fearoff5214/Gemma_4_Kaggle_hackathon
- Google DeepMind (2026). Gemma 4. https://blog.google/innovation-and-ai/technology/developers-tools/gemma-4/ (released 2 Apr 2026, Apache-2.0).
- Kaggle (2026). Google – The Gemma 4 Developer Agent; Paper Track. https://www.kaggle.com/competitions/gemma-4-developer-agent-paper
- ggml-org (2026). llama.cpp. https://github.com/ggml-org/llama.cpp
