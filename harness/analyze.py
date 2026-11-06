#!/usr/bin/env python3
"""Summarize EditProbe result files into Markdown tables (results/summary.md).

Usage: python harness/analyze.py [results/*.jsonl]
"""
from __future__ import annotations

import json
import random
import sys
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

LADDER = ["no_tool_call", "multiple_calls", "wrong_tool", "bad_args", "no_diff_found",
          "old_not_found", "old_ambiguous", "patch_failed", "truncated_output",
          "noop_edit", "syntax_error", "tests_fail", "tests_fail_regression", "pass"]


def load(paths):
    runs = defaultdict(dict)  # (model, protocol, thinking) -> {task: rec}
    for p in paths:
        for line in Path(p).read_text().splitlines():
            if not line.strip():
                continue
            r = json.loads(line)
            if r.get("apply_ok") and r.get("candidate") is not None:
                src = (ROOT / "tasks" / r["task"] / "src.py").read_text()
                if r["candidate"] == src:
                    r["stage"] = "noop_edit"
            key = (r["model"], r["protocol"] + ("+hint" if r.get("hint") else ""), bool(r.get("thinking")))
            runs[key][r["task"]] = r  # last write wins
    return runs


def boot_ci(flags, n=5000, seed=0):
    rnd = random.Random(seed)
    k = len(flags)
    if k == 0:
        return (0.0, 0.0)
    means = []
    for _ in range(n):
        s = sum(flags[rnd.randrange(k)] for _ in range(k))
        means.append(s / k)
    means.sort()
    return means[int(0.025 * n)], means[int(0.975 * n)]


def pct(x, k):
    return f"{100*x/k:.0f}%" if k else "-"


def main():
    paths = sys.argv[1:] or sorted((ROOT / "results").glob("*.jsonl"))
    runs = load(paths)
    out = []
    out.append("# EditProbe results\n")
    out.append("Each cell: tasks (of N) reaching that stage. One attempt per task, temperature 0.\n")

    # Main table
    out.append("## Outcome by model x protocol\n")
    out.append("| model | protocol | think | N | tool call ok | edit applied | compiles | resolved | 95% CI | == gold | extraneous lines (mean) | completion tok (mean) | wall s (mean) |")
    out.append("|---|---|---|---|---|---|---|---|---|---|---|---|---|")
    for key in sorted(runs):
        recs = list(runs[key].values())
        k = len(recs)
        call_ok = sum(r["stage"] not in ("no_tool_call", "multiple_calls", "wrong_tool", "bad_args", "no_diff_found") for r in recs)
        applied = sum(r["apply_ok"] for r in recs)
        compiles = sum(bool(r.get("compiles")) for r in recs)
        resolved = [int(r["resolved"]) for r in recs]
        lo, hi = boot_ci(resolved)
        gold = sum(r["equals_gold"] for r in recs)
        ext = [r["extraneous_lines"] for r in recs if r.get("extraneous_lines") is not None]
        tok = [r["completion_tokens"] for r in recs if r.get("completion_tokens")]
        wall = [r["wall_s"] for r in recs if r.get("wall_s")]
        out.append(f"| {key[0]} | {key[1]} | {'on' if key[2] else 'off'} | {k} | {call_ok} ({pct(call_ok,k)}) | {applied} ({pct(applied,k)}) | {compiles} ({pct(compiles,k)}) | "
                   f"**{sum(resolved)} ({pct(sum(resolved),k)})** | {100*lo:.0f}–{100*hi:.0f}% | {gold} | "
                   f"{sum(ext)/len(ext):.1f}" if ext else f"| {key[0]} | {key[1]} | {'on' if key[2] else 'off'} | {k} | {call_ok} ({pct(call_ok,k)}) | {applied} ({pct(applied,k)}) | {compiles} ({pct(compiles,k)}) | **{sum(resolved)} ({pct(sum(resolved),k)})** | {100*lo:.0f}–{100*hi:.0f}% | {gold} | -")
        out[-1] += f" | {sum(tok)/len(tok):.0f} | {sum(wall)/len(wall):.0f} |" if tok else " | - | - |"

    # Failure ladder
    out.append("\n## Failure ladder (where attempts end)\n")
    stages = [s for s in LADDER]
    out.append("| model | protocol | think | " + " | ".join(stages) + " |")
    out.append("|---|---|---|" + "---|" * len(stages))
    for key in sorted(runs):
        c = Counter(r["stage"] for r in runs[key].values())
        out.append(f"| {key[0]} | {key[1]} | {'on' if key[2] else 'off'} | " + " | ".join(str(c.get(s, 0)) for s in stages) + " |")

    # Match tiers for edit_file
    out.append("\n## edit_file match tier (how old_string was located)\n")
    out.append("| model | protocol | think | exact | ws_flex | regex | ambiguous | not_found | resolved given exact | resolved given ws_flex/regex |")
    out.append("|---|---|---|---|---|---|---|---|---|---|")
    for key in sorted(runs):
        if not key[1].startswith("edit_file"):
            continue
        recs = [r for r in runs[key].values() if r.get("match_tier")]
        c = Counter(r["match_tier"] for r in recs)
        ex = [r for r in recs if r["match_tier"] == "exact"]
        fl = [r for r in recs if r["match_tier"] in ("ws_flex", "regex")]
        out.append(f"| {key[0]} | {key[1]} | {'on' if key[2] else 'off'} | {c.get('exact',0)} | {c.get('ws_flex',0)} | {c.get('regex',0)} | {c.get('ambiguous',0)} | {c.get('not_found',0)} | "
                   f"{sum(r['resolved'] for r in ex)}/{len(ex)} | {sum(r['resolved'] for r in fl)}/{len(fl)} |")

    # not-found reasons
    out.append("\n## Why old_string was not found\n")
    for key in sorted(runs):
        if not key[1].startswith("edit_file"):
            continue
        c = Counter(r.get("not_found_reason") for r in runs[key].values() if r["stage"] in ("old_not_found", "old_ambiguous"))
        if c:
            out.append(f"- {key[0]} / {key[1]}: " + ", ".join(f"{k}={v}" for k, v in c.most_common()))

    # Per-task matrix
    out.append("\n## Per-task outcomes\n")
    keys = sorted(runs)
    tasks = sorted({t for k in keys for t in runs[k]})
    out.append("| task | " + " | ".join(f"{k[0]}/{k[1]}{'/think' if k[2] else ''}" for k in keys) + " |")
    out.append("|---|" + "---|" * len(keys))
    short = {"pass": "PASS", "noop_edit": "noop", "tests_fail": "fail", "tests_fail_regression": "regress", "old_not_found": "notfound",
             "old_ambiguous": "ambig", "no_tool_call": "nocall", "syntax_error": "syntax", "patch_failed": "nopatch",
             "no_diff_found": "nodiff", "truncated_output": "trunc", "bad_args": "badargs", "wrong_tool": "wrongtool",
             "multiple_calls": "multi"}
    for t in tasks:
        row = []
        for k in keys:
            r = runs[k].get(t)
            row.append(short.get(r["stage"], r["stage"]) if r else "·")
        out.append(f"| {t} | " + " | ".join(row) + " |")

    # Localization sanity: did the model touch the gold lines?
    out.append("\n## Did the applied edit touch the gold region?\n")
    out.append("Applied edits whose removed lines intersect the gold buggy lines (the model localized the bug) vs. not.\n")
    out.append("| model | protocol | think | applied | touched gold region | resolved among touched | resolved among untouched |")
    out.append("|---|---|---|---|---|---|---|")
    tasks_meta = {p.name: json.loads((p / "task.json").read_text()) for p in (ROOT / "tasks").iterdir() if p.is_dir()}
    for key in sorted(runs):
        recs = [r for r in runs[key].values() if r["apply_ok"] and r.get("candidate")]
        touched, untouched = [], []
        for r in recs:
            meta = tasks_meta[r["task"]]
            src = (ROOT / "tasks" / r["task"] / "src.py").read_text()
            import difflib
            sm = difflib.SequenceMatcher(a=src.splitlines(), b=r["candidate"].splitlines(), autojunk=False)
            removed = set()
            for tag, i1, i2, j1, j2 in sm.get_opcodes():
                if tag != "equal":
                    removed.update(range(i1 + 1, i2 + 1))
                    if tag == "insert":
                        removed.update({i1, i1 + 1})
            gold_lines = set(meta["buggy_lines"]) or set(meta.get("gold_lines", []))
            (touched if removed & gold_lines or not meta["buggy_lines"] else untouched).append(r)
        out.append(f"| {key[0]} | {key[1]} | {'on' if key[2] else 'off'} | {len(recs)} | {len(touched)} | "
                   f"{sum(r['resolved'] for r in touched)}/{len(touched)} | {sum(r['resolved'] for r in untouched)}/{len(untouched)} |")

    text = "\n".join(out) + "\n"
    (ROOT / "results" / "summary.md").write_text(text)
    print(text)


if __name__ == "__main__":
    main()
