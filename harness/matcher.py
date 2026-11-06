"""Reimplementation of the competition harness's `edit_file` matching ladder.

HARNESS_README (dataset version 2026-10-13) describes `edit_file(filepath,
old_string, new_string, allow_multiple)` as: "Tries an exact match, then a
whitespace-flexible match, then a regex match. Fails when more than one place
matches (unless allow_multiple), and on empty files."

We do not have the harness source, so the three tiers below are our reading of
that sentence. Results are reported per tier so a reader can discount the
tiers they do not trust. `exact` is unambiguous; `ws_flex` is the tier most
agent frameworks implement (compare after collapsing runs of whitespace);
`regex` compiles old_string as a Python regex.
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Optional


@dataclass
class MatchResult:
    tier: str                 # exact | ws_flex | regex | not_found | ambiguous | empty_file
    count: int
    new_text: Optional[str]   # file content after replacement, if applied
    span: Optional[tuple[int, int]] = None
    note: str = ""


def _ws_collapse(s: str) -> str:
    return re.sub(r"\s+", " ", s).strip()


def _ws_flex_find(text: str, old: str) -> list[tuple[int, int]]:
    """Find spans of `text` whose whitespace-collapsed form equals that of `old`.

    Implemented by turning `old` into a regex where every whitespace run matches
    `\\s+` (or `\\s*` at the ends), so indentation and blank-line differences are
    tolerated but tokens must match in order.
    """
    target = _ws_collapse(old)
    if not target:
        return []
    parts = [re.escape(p) for p in target.split(" ")]
    pattern = r"\s+".join(parts)
    spans = [m.span() for m in re.finditer(pattern, text)]
    return spans


def apply_edit(text: str, old: str, new: str, allow_multiple: bool = False) -> MatchResult:
    if not text:
        return MatchResult("empty_file", 0, None)
    if old == "":
        return MatchResult("not_found", 0, None, note="empty old_string")

    # Tier 1: exact
    n = text.count(old)
    if n == 1:
        i = text.index(old)
        return MatchResult("exact", 1, text[:i] + new + text[i + len(old):], (i, i + len(old)))
    if n > 1:
        if allow_multiple:
            return MatchResult("exact", n, text.replace(old, new))
        return MatchResult("ambiguous", n, None, note="exact match more than once")

    # Tier 2: whitespace-flexible
    spans = _ws_flex_find(text, old)
    if len(spans) == 1:
        a, b = spans[0]
        # Note: `new` is inserted as the model wrote it. If the model's
        # old_string had different indentation than the file, new_string
        # usually has it too, and the result may not compile. We measure that.
        return MatchResult("ws_flex", 1, text[:a] + new + text[b:], (a, b))
    if len(spans) > 1:
        return MatchResult("ambiguous", len(spans), None, note="ws_flex match more than once")

    # Tier 3: regex
    try:
        rx = re.compile(old, re.MULTILINE)
    except re.error as e:
        return MatchResult("not_found", 0, None, note=f"regex compile failed: {e}")
    ms = list(rx.finditer(text))
    if len(ms) == 1:
        a, b = ms[0].span()
        if a == b:
            return MatchResult("not_found", 0, None, note="regex matched empty string")
        return MatchResult("regex", 1, text[:a] + new + text[b:], (a, b))
    if len(ms) > 1:
        return MatchResult("ambiguous", len(ms), None, note="regex match more than once")
    return MatchResult("not_found", 0, None)


def diagnose_not_found(text: str, old: str) -> str:
    """Why did old_string not match? Heuristic labels for the paper."""
    if old.strip() == "":
        return "empty"
    lines = [l for l in old.split("\n") if l.strip()]
    stripped_all = all(l.strip() in text for l in lines)
    if stripped_all:
        # every line exists (modulo indentation) but not contiguously or with same indent
        if _ws_collapse(old) in _ws_collapse(text):
            return "indentation_or_blank_lines"
        return "lines_exist_not_contiguous"
    missing = [l for l in lines if l.strip() not in text]
    if len(missing) < len(lines):
        return "partially_hallucinated"
    return "hallucinated"
