#!/usr/bin/env python3
"""Failure-ladder figure: one horizontal stacked bar per (model, protocol, hint).

Writes results/ladder.png. Stages are ordered, so the fill is one ordinal ramp
(light = early failure, dark = late failure) with `pass` in a separate hue.
Every segment >= 2 tasks is labeled with its count, so color is not the only
carrier of the number.
"""
from __future__ import annotations

import json
import sys
from collections import Counter, defaultdict
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent

GROUPS = [
    ("tool call / diff missing", ["no_tool_call", "multiple_calls", "wrong_tool", "bad_args", "no_diff_found"]),
    ("edit did not apply", ["old_not_found", "old_ambiguous", "patch_failed", "truncated_output"]),
    ("no-op edit", ["noop_edit"]),
    ("syntax error", ["syntax_error"]),
    ("tests fail", ["tests_fail", "tests_fail_regression"]),
    ("pass", ["pass"]),
]
# ordinal ramp (light -> dark) for failures, one green for pass
COLORS = ["#d9dde3", "#aeb6c2", "#7d8898", "#4e5a6b", "#2b3443", "#2e7d4f"]


def main():
    runs = defaultdict(dict)
    for p in sorted((ROOT / "results").glob("*.jsonl")):
        if p.name.startswith("rescore"):
            continue
        for line in p.read_text().splitlines():
            if not line.strip():
                continue
            r = json.loads(line)
            if r.get("apply_ok") and r.get("candidate") is not None:
                src = (ROOT / "tasks" / r["task"] / "src.py").read_text()
                if r["candidate"] == src:
                    r["stage"] = "noop_edit"
            key = (r["model"], r["protocol"], bool(r.get("hint")))
            runs[key][r["task"]] = r
    order_p = ["edit_file", "edit_file_v", "write_file", "udiff"]
    keys = sorted(runs, key=lambda k: (k[0], k[2], order_p.index(k[1]) if k[1] in order_p else 9))
    labels, data = [], []
    for k in keys:
        c = Counter(r["stage"] for r in runs[k].values())
        labels.append(f"{k[0].upper()} · {k[1]}{' + hint' if k[2] else ''}  (n={len(runs[k])})")
        data.append([sum(c.get(s, 0) for s in stages) for _, stages in GROUPS])

    fig_h = 0.5 * len(labels) + 1.6
    fig, ax = plt.subplots(figsize=(9, fig_h), dpi=160)
    y = list(range(len(labels)))[::-1]
    left = [0] * len(labels)
    for gi, (gname, _) in enumerate(GROUPS):
        vals = [d[gi] for d in data]
        ax.barh(y, vals, left=left, color=COLORS[gi], label=gname, height=0.62, edgecolor="white", linewidth=1.5)
        for yi, v, l in zip(y, vals, left):
            if v >= 2:
                ax.text(l + v / 2, yi, str(v), ha="center", va="center", fontsize=8,
                        color="white" if gi >= 2 else "#2b3443")
        left = [l + v for l, v in zip(left, vals)]
    ax.set_yticks(y)
    ax.set_yticklabels(labels, fontsize=8.5)
    ax.set_xlabel("tasks (one attempt each, temperature 0)", fontsize=9)
    ax.set_xlim(0, max(left) if left else 35)
    for s in ("top", "right", "left"):
        ax.spines[s].set_visible(False)
    ax.tick_params(axis="y", length=0)
    ax.grid(axis="x", color="#e6e8eb", linewidth=0.8)
    ax.set_axisbelow(True)
    ax.set_title("EditProbe: where each attempt ends", fontsize=11, loc="left")
    handles, names = ax.get_legend_handles_labels()
    fig.legend(handles, names, ncol=6, fontsize=8, frameon=False, loc="lower center")
    fig.tight_layout(rect=[0, 0.9 / fig_h, 1, 1])
    out = ROOT / "results" / "ladder.png"
    fig.savefig(out, bbox_inches="tight")
    print("wrote", out)


if __name__ == "__main__":
    main()
