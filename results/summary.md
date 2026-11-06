# EditProbe results

Each cell: tasks (of N) reaching that stage. One attempt per task, temperature 0.

## Outcome by model x protocol

| model | protocol | think | N | tool call ok | edit applied | compiles | resolved | 95% CI | == gold | extraneous lines (mean) | completion tok (mean) | wall s (mean) |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| e2b | edit_file | off | 35 | 35 (100%) | 32 (91%) | 27 (77%) | **9 (26%)** | 11–40% | 3 | 0.4 | 210 | 23 |
| e2b | edit_file+hint | off | 35 | 35 (100%) | 35 (100%) | 34 (97%) | **34 (97%)** | 91–100% | 34 | 0.0 | 75 | 10 |
| e2b | edit_file_v | off | 35 | 35 (100%) | 33 (94%) | 30 (86%) | **10 (29%)** | 14–46% | 5 | 0.3 | 192 | 18 |
| e2b | edit_file_v+hint | off | 35 | 35 (100%) | 35 (100%) | 35 (100%) | **33 (94%)** | 86–100% | 32 | 0.1 | 75 | 7 |
| e2b | udiff | off | 35 | 35 (100%) | 31 (89%) | 31 (89%) | **10 (29%)** | 14–43% | 6 | 0.7 | 156 | 18 |
| e2b | udiff+hint | off | 35 | 35 (100%) | 29 (83%) | 28 (80%) | **25 (71%)** | 57–86% | 22 | 0.0 | 116 | 14 |
| e2b | write_file | off | 35 | 33 (94%) | 33 (94%) | 33 (94%) | **18 (51%)** | 34–69% | 9 | 0.5 | 481 | 48 |
| e2b | write_file+hint | off | 35 | 35 (100%) | 35 (100%) | 35 (100%) | **34 (97%)** | 91–100% | 31 | 0.1 | 475 | 47 |

## Failure ladder (where attempts end)

| model | protocol | think | no_tool_call | multiple_calls | wrong_tool | bad_args | no_diff_found | old_not_found | old_ambiguous | patch_failed | truncated_output | noop_edit | syntax_error | tests_fail | tests_fail_regression | pass |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| e2b | edit_file | off | 0 | 0 | 0 | 0 | 0 | 3 | 0 | 0 | 0 | 6 | 5 | 10 | 2 | 9 |
| e2b | edit_file+hint | off | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 1 | 0 | 0 | 34 |
| e2b | edit_file_v | off | 0 | 0 | 0 | 0 | 0 | 2 | 0 | 0 | 0 | 8 | 3 | 10 | 2 | 10 |
| e2b | edit_file_v+hint | off | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 2 | 0 | 33 |
| e2b | udiff | off | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 4 | 0 | 8 | 0 | 11 | 2 | 10 |
| e2b | udiff+hint | off | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 6 | 0 | 3 | 1 | 0 | 0 | 25 |
| e2b | write_file | off | 2 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 9 | 0 | 6 | 0 | 18 |
| e2b | write_file+hint | off | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 1 | 0 | 0 | 0 | 34 |

## edit_file match tier (how old_string was located)

| model | protocol | think | exact | ws_flex | regex | ambiguous | not_found | resolved given exact | resolved given ws_flex/regex |
|---|---|---|---|---|---|---|---|---|---|
| e2b | edit_file | off | 31 | 1 | 0 | 0 | 3 | 9/31 | 0/1 |
| e2b | edit_file+hint | off | 35 | 0 | 0 | 0 | 0 | 34/35 | 0/0 |
| e2b | edit_file_v | off | 32 | 1 | 0 | 0 | 2 | 10/32 | 0/1 |
| e2b | edit_file_v+hint | off | 35 | 0 | 0 | 0 | 0 | 33/35 | 0/0 |

## Why old_string was not found

- e2b / edit_file: partially_hallucinated=2, lines_exist_not_contiguous=1
- e2b / edit_file_v: partially_hallucinated=2

## Per-task outcomes

| task | e2b/edit_file | e2b/edit_file+hint | e2b/edit_file_v | e2b/edit_file_v+hint | e2b/udiff | e2b/udiff+hint | e2b/write_file | e2b/write_file+hint |
|---|---|---|---|---|---|---|---|---|
| httpx_byte_chunker | syntax | PASS | noop | PASS | fail | nopatch | noop | PASS |
| httpx_cookie_domain | fail | PASS | fail | PASS | PASS | PASS | fail | PASS |
| httpx_line_decoder | fail | PASS | fail | PASS | fail | PASS | fail | PASS |
| httpx_multipart_boundary | fail | PASS | fail | PASS | fail | PASS | fail | PASS |
| httpx_normalize_port | noop | PASS | noop | PASS | fail | PASS | PASS | PASS |
| httpx_obfuscate_headers | fail | PASS | notfound | PASS | nopatch | nopatch | noop | PASS |
| httpx_peek_filelike_length | syntax | PASS | fail | PASS | noop | syntax | noop | noop |
| httpx_primitive_value | PASS | syntax | PASS | fail | PASS | PASS | PASS | PASS |
| httpx_same_origin | PASS | PASS | PASS | PASS | noop | PASS | noop | PASS |
| httpx_text_chunker | noop | PASS | noop | PASS | fail | nopatch | PASS | PASS |
| httpx_timeout | syntax | PASS | syntax | PASS | nopatch | noop | noop | PASS |
| httpx_url_pattern | fail | PASS | fail | PASS | fail | PASS | noop | PASS |
| req_case_insensitive_dict | PASS | PASS | PASS | PASS | noop | PASS | nocall | PASS |
| req_check_header_validity | notfound | PASS | fail | PASS | noop | nopatch | PASS | PASS |
| req_dotted_netmask | notfound | PASS | PASS | PASS | PASS | PASS | PASS | PASS |
| req_get_auth_from_url | PASS | PASS | PASS | PASS | regress | PASS | PASS | PASS |
| req_get_encoding_from_headers | fail | PASS | fail | PASS | fail | PASS | fail | PASS |
| req_guess_json_utf | notfound | PASS | notfound | PASS | PASS | PASS | PASS | PASS |
| req_iter_slices | regress | PASS | regress | PASS | PASS | PASS | PASS | PASS |
| req_parse_dict_header | noop | PASS | noop | PASS | noop | PASS | PASS | PASS |
| req_parse_header_links | PASS | PASS | syntax | PASS | PASS | PASS | PASS | PASS |
| req_prepend_scheme | noop | PASS | noop | PASS | noop | PASS | fail | PASS |
| req_super_len | fail | PASS | fail | PASS | nopatch | PASS | noop | PASS |
| req_unquote_unreserved | fail | PASS | noop | PASS | PASS | PASS | PASS | PASS |
| rich_ansi_strip | noop | PASS | PASS | PASS | fail | nopatch | PASS | PASS |
| rich_chop_cells | PASS | PASS | PASS | PASS | fail | PASS | PASS | PASS |
| rich_color_triplet | PASS | PASS | PASS | PASS | PASS | PASS | PASS | PASS |
| rich_divide_line | fail | PASS | fail | PASS | noop | PASS | PASS | PASS |
| rich_filesize_decimal | noop | PASS | noop | PASS | noop | PASS | noop | PASS |
| rich_lookup_pick_bool | regress | PASS | regress | PASS | regress | PASS | PASS | PASS |
| rich_loop_last | PASS | PASS | PASS | fail | PASS | noop | PASS | PASS |
| rich_markup_escape | syntax | PASS | syntax | PASS | fail | noop | noop | PASS |
| rich_ratio_distribute | PASS | PASS | PASS | PASS | PASS | PASS | PASS | PASS |
| rich_ratio_resolve | fail | PASS | fail | PASS | fail | nopatch | fail | PASS |
| rich_style_parse_color | syntax | PASS | noop | PASS | nopatch | PASS | nocall | PASS |

## Did the applied edit touch the gold region?

Applied edits whose removed lines intersect the gold buggy lines (the model localized the bug) vs. not.

| model | protocol | think | applied | touched gold region | resolved among touched | resolved among untouched |
|---|---|---|---|---|---|---|
| e2b | edit_file | off | 32 | 14 | 7/14 | 2/18 |
| e2b | edit_file+hint | off | 35 | 35 | 34/35 | 0/0 |
| e2b | edit_file_v | off | 33 | 13 | 8/13 | 2/20 |
| e2b | edit_file_v+hint | off | 35 | 34 | 33/34 | 0/1 |
| e2b | udiff | off | 31 | 14 | 8/14 | 2/17 |
| e2b | udiff+hint | off | 29 | 24 | 24/24 | 1/5 |
| e2b | write_file | off | 33 | 21 | 17/21 | 1/12 |
| e2b | write_file+hint | off | 35 | 33 | 33/33 | 1/2 |
