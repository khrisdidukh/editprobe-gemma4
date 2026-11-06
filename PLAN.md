# Plan — Kaggle "Gemma 4 Developer Agent — Paper Track"

Deadline: **12 Nov 2026, 23:59 UTC**. Entrant: Khrystyna Didukh (solo). Working dir: `/home/claude/kaggle-gemma4`.

## Коротко українською

**Кут:** маленькі моделі Gemma 4 (E2B, E4B) в офлайн-агенті падають не тільки на «знайти баг», а й на останньому кроці — **застосувати правку через `edit_file(old_string, new_string)`**. Ми будуємо невеликий відкритий ресурс **EditProbe**: 36 локалізованих задач з багами, адаптованих із реальних файлів репозиторіїв dev-набору змагання (requests, rich, httpx), кожна з прихованими pytest-тестами, плюс харнес, який вимірює, де саме ламається правка: (1) неправильний формат виклику інструмента, (2) `old_string` не знайдено / знайдено кілька разів, (3) знайдено лише завдяки «м'якому» збігу пробілів, (4) правка застосована, але тести не проходять, (5) успіх. Порівнюємо 3 протоколи правки (edit_file, write_file повного фрагмента, unified diff) × 2 моделі (E2B, E4B, офіційні QAT q4_0 GGUF) на CPU через llama.cpp. Усі числа — тільки з реальних прогонів, логи зберігаються.

**Чому саме це:** judging = Novelty/Quality/Relevance/Verifiability/Clarity по 20%. Нічого про надійність правок малих Gemma 4 ще не опубліковано (перевірено 6 листопада: конкуруючі роботи — про цикли викликів інструментів у 31B/12B і про «scaffolding» для E4B). Повністю відтворюється на CPU без GPU → максимальна Verifiability. Цілиться в **Best New Resource ($10k)**, з шансом на Overall.

**Що маєш зробити сама (Клод не може):**
1. **До 10 листопада:** увійти на Kaggle, пройти верифікацію телефону, відкрити https://www.kaggle.com/competitions/gemma-4-developer-agent-paper і натиснути **Join / Accept rules**. (Також прийняти правила основного змагання https://www.kaggle.com/competitions/gemma-4-developer-agent — це відкриває дані і не зобов'язує ні до чого.)
2. **До 11 листопада:** створити публічний GitHub-репозиторій (наприклад `khrisdidukh/editprobe-gemma4`) і запушити вміст `/home/claude/kaggle-gemma4` (без папки `models/`). Ліцензія Apache-2.0 вже в репо.
3. **До 12 листопада, ~20:00 UTC (запас 4 години):** створити Kaggle Writeup у Paper Track: вставити текст з `paper/draft.md` (поля: Title, Subtitle, Abstract + решта), додати лінк на GitHub у Project Links, натиснути **Submit** (чернетка не оцінюється!).
4. Переглянути місця `[KD: ...]` у `paper/draft.md` — там потрібна твоя думка/формулювання.
5. HuggingFace: нічого не треба — GGUF-ваги Gemma 4 не закриті (gated: false), вже скачані. API-ключі не потрібні.

## English details

### Research angle (one)
**EditProbe: where do small Gemma 4 agents lose a localized fix?** A diagnostic benchmark + harness measuring the *edit-application* step of the competition's `edit_file(filepath, old_string, new_string)` tool for Gemma 4 E2B/E4B, isolated from bug localization (the model sees the buggy region as the harness's `read_file` would show it, and a user-style issue text).

- Tasks: 36 single-file Python tasks adapted from requests (Apache-2.0), rich (MIT), httpx (BSD-3) — the competition dev-set repos. Each has a gold minimal fix (1–4 lines), a user-style problem statement, and hidden pytest tests (FAIL_TO_PASS + PASS_TO_PASS).
- Failure ladder per attempt: `no_tool_call` → `bad_args` → `old_not_found` / `old_ambiguous` → applied (`exact` | `ws_flex` tier) → `syntax_error` → `tests_fail` → `pass`. Plus extraneous-change size (lines changed outside the gold region) and tokens/latency.
- Conditions: edit protocol ∈ {edit_file (harness-like, native tool call), write_file (full region rewrite), unified diff}; model ∈ {E2B, E4B} (official QAT q4_0 GGUF, llama.cpp, CPU); thinking off (CPU budget), T=0. Optional: a prompt mitigation ("copy at least 3 verbatim lines incl. indentation") if time allows.
- Relevance to main track: gold patches are small (median 12 lines, 91/129 single-file). If a small model can localize but cannot land the edit, agent designers should pick a different edit protocol or instruction; our numbers tell them which.

### Feasibility (measured 6 Nov)
- Container: 2 CPUs, 7.8 GB RAM. llama.cpp built from source (commit 954de24, Gemma 4 supported). E2B q4_0: ~12 tok/s generation, ~95–160 tok/s prefill. Native tool calling works through the Gemma 4 chat template (`--jinja`). E4B q4_0 downloaded (5.15 GB).
- Weights: `google/gemma-4-E2B-it-qat-q4_0-gguf`, `google/gemma-4-E4B-it-qat-q4_0-gguf` — **not gated**, no license click needed.
- Budget: ~36 tasks × 3 protocols × 2 models ≈ 216 runs × ~40–90 s ≈ 3–5 h of CPU. Fits.

### Deliverables
- `bench/` task sources + builder, `harness/` runner + matcher, `results/` JSONL logs and tables, `paper/draft.md`, `README.md` (reproduction), `LICENSE` (Apache-2.0).

### Known limitations to state in the paper
- llama.cpp q4_0 GGUF instead of the competition's vLLM `w4a16-ct` checkpoints (both QAT int4; not identical).
- Our `edit_file` matcher is a reimplementation of the behaviour described in HARNESS_README (exact → whitespace-flexible → regex), not the harness code.
- Thinking disabled; single sample at T=0 (deterministic, so no seeds). Bootstrap CIs over tasks.

### Blockers encountered
- The sandbox denies running cloned third-party test suites (`pip install -e` + pytest on rich/requests/httpx). Workaround used: tasks are standalone modules adapted from those repos with our own tests. No other blocker.
