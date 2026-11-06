# EditProbe results

Each cell: tasks (of N) reaching that stage. One attempt per task, temperature 0.

## Outcome by model x protocol

| model | protocol | think | N | tool call ok | edit applied | compiles | resolved | 95% CI | == gold | extraneous lines (mean) | completion tok (mean) | wall s (mean) |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| e2b | edit_file | off | 11 | 11 (100%) | 11 (100%) | 8 (73%) | **2 (18%)** | 0–45% | 0 | 0.1 | 191 | 21 |

## Failure ladder (where attempts end)

| model | protocol | think | no_tool_call | multiple_calls | wrong_tool | bad_args | no_diff_found | old_not_found | old_ambiguous | patch_failed | truncated_output | noop_edit | syntax_error | tests_fail | tests_fail_regression | pass |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| e2b | edit_file | off | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 2 | 3 | 4 | 0 | 2 |

## edit_file match tier (how old_string was located)

| model | protocol | think | exact | ws_flex | regex | ambiguous | not_found | resolved given exact | resolved given ws_flex/regex |
|---|---|---|---|---|---|---|---|---|---|
| e2b | edit_file | off | 11 | 0 | 0 | 0 | 0 | 2/11 | 0/0 |

## Why old_string was not found


## Per-task outcomes

| task | e2b/edit_file |
|---|---|
| httpx_byte_chunker | syntax |
| httpx_cookie_domain | fail |
| httpx_line_decoder | fail |
| httpx_multipart_boundary | fail |
| httpx_normalize_port | noop |
| httpx_obfuscate_headers | fail |
| httpx_peek_filelike_length | syntax |
| httpx_primitive_value | PASS |
| httpx_same_origin | PASS |
| httpx_text_chunker | noop |
| httpx_timeout | syntax |

## Did the applied edit touch the gold region?

Applied edits whose removed lines intersect the gold buggy lines (the model localized the bug) vs. not.

| model | protocol | think | applied | touched gold region | resolved among touched | resolved among untouched |
|---|---|---|---|---|---|---|
| e2b | edit_file | off | 8 | 2 | 0/2 | 2/6 |
