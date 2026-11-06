# EditProbe results

Each cell: tasks (of N) reaching that stage. One attempt per task, temperature 0.

## Outcome by model x protocol

| model | protocol | think | N | tool call ok | edit applied | compiles | resolved | 95% CI | == gold | extraneous lines (mean) | completion tok (mean) | wall s (mean) |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| e2b | edit_file | off | 35 | 35 (100%) | 32 (91%) | 27 (77%) | **9 (26%)** | 11–40% | 3 | 0.4 | 210 | 23 |
| e2b | edit_file_v | off | 35 | 35 (100%) | 33 (94%) | 30 (86%) | **10 (29%)** | 14–46% | 5 | 0.3 | 192 | 18 |
| e2b | udiff | off | 1 | 1 (100%) | 0 (0%) | 0 (0%) | **0 (0%)** | 0–0% | 0 | - | 389 | 39 |

## Failure ladder (where attempts end)

| model | protocol | think | no_tool_call | multiple_calls | wrong_tool | bad_args | no_diff_found | old_not_found | old_ambiguous | patch_failed | truncated_output | noop_edit | syntax_error | tests_fail | tests_fail_regression | pass |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| e2b | edit_file | off | 0 | 0 | 0 | 0 | 0 | 3 | 0 | 0 | 0 | 6 | 5 | 10 | 2 | 9 |
| e2b | edit_file_v | off | 0 | 0 | 0 | 0 | 0 | 2 | 0 | 0 | 0 | 8 | 3 | 10 | 2 | 10 |
| e2b | udiff | off | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 1 | 0 | 0 | 0 | 0 | 0 | 0 |

## edit_file match tier (how old_string was located)

| model | protocol | think | exact | ws_flex | regex | ambiguous | not_found | resolved given exact | resolved given ws_flex/regex |
|---|---|---|---|---|---|---|---|---|---|
| e2b | edit_file | off | 31 | 1 | 0 | 0 | 3 | 9/31 | 0/1 |
| e2b | edit_file_v | off | 32 | 1 | 0 | 0 | 2 | 10/32 | 0/1 |

## Why old_string was not found

- e2b / edit_file: partially_hallucinated=2, lines_exist_not_contiguous=1
- e2b / edit_file_v: partially_hallucinated=2

## Per-task outcomes

| task | e2b/edit_file | e2b/edit_file_v | e2b/udiff |
|---|---|---|---|
| httpx_byte_chunker | syntax | noop | nopatch |
| httpx_cookie_domain | fail | fail | · |
| httpx_line_decoder | fail | fail | · |
| httpx_multipart_boundary | fail | fail | · |
| httpx_normalize_port | noop | noop | · |
| httpx_obfuscate_headers | fail | notfound | · |
| httpx_peek_filelike_length | syntax | fail | · |
| httpx_primitive_value | PASS | PASS | · |
| httpx_same_origin | PASS | PASS | · |
| httpx_text_chunker | noop | noop | · |
| httpx_timeout | syntax | syntax | · |
| httpx_url_pattern | fail | fail | · |
| req_case_insensitive_dict | PASS | PASS | · |
| req_check_header_validity | notfound | fail | · |
| req_dotted_netmask | notfound | PASS | · |
| req_get_auth_from_url | PASS | PASS | · |
| req_get_encoding_from_headers | fail | fail | · |
| req_guess_json_utf | notfound | notfound | · |
| req_iter_slices | regress | regress | · |
| req_parse_dict_header | noop | noop | · |
| req_parse_header_links | PASS | syntax | · |
| req_prepend_scheme | noop | noop | · |
| req_super_len | fail | fail | · |
| req_unquote_unreserved | fail | noop | · |
| rich_ansi_strip | noop | PASS | · |
| rich_chop_cells | PASS | PASS | · |
| rich_color_triplet | PASS | PASS | · |
| rich_divide_line | fail | fail | · |
| rich_filesize_decimal | noop | noop | · |
| rich_lookup_pick_bool | regress | regress | · |
| rich_loop_last | PASS | PASS | · |
| rich_markup_escape | syntax | syntax | · |
| rich_ratio_distribute | PASS | PASS | · |
| rich_ratio_resolve | fail | fail | · |
| rich_style_parse_color | syntax | noop | · |

## Did the applied edit touch the gold region?

Applied edits whose removed lines intersect the gold buggy lines (the model localized the bug) vs. not.

| model | protocol | think | applied | touched gold region | resolved among touched | resolved among untouched |
|---|---|---|---|---|---|---|
| e2b | edit_file | off | 27 | 11 | 7/11 | 2/16 |
| e2b | edit_file_v | off | 33 | 13 | 8/13 | 2/20 |
| e2b | udiff | off | 0 | 0 | 0/0 | 0/0 |
