# EditProbe results

Each cell: tasks (of N) reaching that stage. One attempt per task, temperature 0.

## Outcome by model x protocol

| model | protocol | think | N | tool call ok | edit applied | compiles | resolved | 95% CI | == gold | extraneous lines (mean) | completion tok (mean) | wall s (mean) |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| e2b | edit_file | off | 2 | 2 (100%) | 2 (100%) | 1 (50%) | **0 (0%)** | 0–0% | 0 | 0.0 | 201 | 22 |

## Failure ladder (where attempts end)

| model | protocol | think | no_tool_call | multiple_calls | wrong_tool | bad_args | no_diff_found | old_not_found | old_ambiguous | patch_failed | truncated_output | syntax_error | tests_fail | tests_fail_regression | pass |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| e2b | edit_file | off | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 1 | 1 | 0 | 0 |

## edit_file match tier (how old_string was located)

| model | protocol | think | exact | ws_flex | regex | ambiguous | not_found | resolved given exact | resolved given ws_flex/regex |
|---|---|---|---|---|---|---|---|---|---|
| e2b | edit_file | off | 2 | 0 | 0 | 0 | 0 | 0/2 | 0/0 |

## Why old_string was not found


## Per-task outcomes

| task | e2b/edit_file |
|---|---|
| httpx_byte_chunker | syntax |
| httpx_cookie_domain | fail |

## Did the applied edit touch the gold region?

Applied edits whose removed lines intersect the gold buggy lines (the model localized the bug) vs. not.

| model | protocol | think | applied | touched gold region | resolved among touched | resolved among untouched |
|---|---|---|---|---|---|---|
| e2b | edit_file | off | 1 | 1 | 0/1 | 0/0 |
