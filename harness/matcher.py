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


def span_repair(text: str, old: str, new: str, span: tuple[int, int]) -> tuple[str, dict]:
    """Harness-side repair for a common small-model error: new_string covers a
    larger span than old_string (it repeats lines that sit just before or just
    after the matched region), so a plain replacement duplicates code.

    We drop leading lines of `new` that equal the file lines immediately before
    the match, and trailing lines of `new` that equal the lines immediately
    after it. Returns (repaired_new, info).
    """
    a, b = span
    before = text[:a].split("\n")
    after = text[b:].split("\n")
    # text[:a] ends with the (possibly partial) line prefix before the match;
    # old_string typically starts at a line start, so before[-1] is '' or indent.
    before_lines = [l for l in before[:-1]] if before and before[-1].strip() == "" else before
    after_lines = after[1:] if after and after[0] == "" else after  # skip the rest of the line the match ends in
    new_lines = new.split("\n")
    if new_lines and new_lines[-1] == "":
        new_lines.pop()  # trailing newline
    old_lines = old.split("\n")

    def nonblank(ls):
        return any(l.strip() for l in ls)

    # largest k such that the last k lines of new == first k lines after the match
    dropped_tail = 0
    for k in range(min(len(new_lines) - 1, len(after_lines)), 0, -1):
        if new_lines[-k:] == after_lines[:k] and nonblank(new_lines[-k:]):
            new_lines = new_lines[:-k]
            dropped_tail = k
            break
    # largest k such that the first k lines of new == last k lines before the match
    dropped_head = 0
    for k in range(min(len(new_lines) - 1, len(before_lines)), 0, -1):
        if new_lines[:k] == before_lines[-k:] and nonblank(new_lines[:k]):
            new_lines = new_lines[k:]
            dropped_head = k
            break
    return "\n".join(new_lines), {"dropped_head": dropped_head, "dropped_tail": dropped_tail}


def anchor_repair(text: str, old: str, new: str, span: tuple[int, int], window: int = 80) -> tuple[Optional[str], dict]:
    """Harness-side repair for span mismatch, by anchor expansion.

    Small models often write a new_string that spans a larger region than their
    old_string: it starts with lines that sit *before* the match and/or ends
    with lines that sit *after* it (sometimes with the actual fix in that
    overflow). Replacing only the old_string span then duplicates code.

    Repair: take the first and last non-blank lines of new_string as anchors.
    Search for the first anchor in the `window` lines before the match and for
    the last anchor in the `window` lines after it. If an anchor is found
    exactly once, extend the replaced region to it. Returns (new_text or None,
    info). None means no expansion was possible (anchors not found or ambiguous).
    """
    a, b = span
    lines = text.split("\n")
    # line index of span start / end
    start_line = text.count("\n", 0, a)
    end_line = text.count("\n", 0, b)  # line containing the last char of the match
    new_lines = new.rstrip("\n").split("\n")
    nb = [l for l in new_lines if l.strip()]
    if len(nb) < 2:
        return None, {"reason": "new too short"}
    first, last = nb[0], nb[-1]
    old_lines = old.strip("\n").split("\n")

    new_start, new_end = start_line, end_line
    info = {"head": 0, "tail": 0}
    if first != old_lines[0]:
        cands = [i for i in range(max(0, start_line - window), start_line) if lines[i] == first]
        if len(cands) == 1:
            new_start = cands[0]
            info["head"] = start_line - new_start
    if last != old_lines[-1]:
        cands = [i for i in range(end_line + 1, min(len(lines), end_line + 1 + window)) if lines[i] == last]
        if len(cands) == 1:
            new_end = cands[0]
            info["tail"] = new_end - end_line
    if (new_start, new_end) == (start_line, end_line):
        return None, {"reason": "no anchor expansion"}
    repaired = lines[:new_start] + new_lines + lines[new_end + 1:]
    return "\n".join(repaired), info
