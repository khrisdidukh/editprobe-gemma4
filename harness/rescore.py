#!/usr/bin/env python3
"""Post-hoc rescoring of logged edit_file attempts with a harness-side repair.

Policy "anchor repair": apply the edit as logged; if the result does not
compile, try `matcher.anchor_repair` (expand the replaced span to the first and
last lines of new_string when they are found uniquely nearby); if that compiles,
run the hidden tests. No model call is made, so this is an exact replay of what
the harness would have done with a more tolerant edit_file.

Writes results/rescore.md and results/rescore.jsonl.
"""
from __future__ import annotations

import json
import sys
from collections import Counter, defaultdict
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
sys.path.insert(0, str(HERE))
from matcher import anchor_repair, apply_edit  # noqa: E402
from run import run_tests  # noqa: E402


def main():
    paths = sorted((ROOT / "results").glob("*edit_file*.jsonl"))
    groups = defaultdict(list)
    out_recs = []
    for p in paths:
        for line in p.read_text().splitlines():
            if not line.strip():
                continue
            r = json.loads(line)
            key = (r["model"], r["protocol"] + ("+hint" if r.get("hint") else ""))
            groups[key].append(r)

    lines_md = ["# Rescoring edit_file attempts with anchor repair\n",
                "Replay of logged edits. `base` = plain replacement (what was scored). "
                "`repair` = if the plain result does not compile, expand the replaced span to the "
                "first/last lines of new_string when found uniquely within 80 lines; then run tests.\n",
                "| model | protocol | N | base resolved | syntax errors | repair attempted | repaired compiles | repaired resolved | resolved with repair |",
                "|---|---|---|---|---|---|---|---|---|"]
    for key in sorted(groups):
        recs = groups[key]
        base = sum(r["resolved"] for r in recs)
        syn = [r for r in recs if r["stage"] == "syntax_error"]
        attempted = compiles = fixed = 0
        for r in syn:
            tdir = ROOT / "tasks" / r["task"]
            src = (tdir / "src.py").read_text()
            meta = json.loads((tdir / "task.json").read_text())
            m = apply_edit(src, r["old_string"], r["new_string"])
            if m.span is None:
                continue
            new_text, info = anchor_repair(src, r["old_string"], r["new_string"], m.span)
            rec = {"model": key[0], "protocol": key[1], "task": r["task"], "repair_info": info, "repaired": None}
            if new_text is None:
                out_recs.append(rec); continue
            attempted += 1
            try:
                compile(new_text, "src.py", "exec")
            except SyntaxError as e:
                rec["repaired"] = f"syntax_error: {e}"; out_recs.append(rec); continue
            compiles += 1
            t = run_tests(new_text, (tdir / "test_task.py").read_text(), meta)
            rec["repaired"] = "pass" if t["resolved"] else "tests_fail"
            rec["tests"] = {k: t[k] for k in ("passed", "failed", "f2p_ok", "p2p_ok")}
            fixed += t["resolved"]
            out_recs.append(rec)
        lines_md.append(f"| {key[0]} | {key[1]} | {len(recs)} | {base} | {len(syn)} | {attempted} | {compiles} | {fixed} | **{base + fixed}** |")

    (ROOT / "results" / "rescore.jsonl").write_text("\n".join(json.dumps(r) for r in out_recs) + "\n")
    text = "\n".join(lines_md) + "\n"
    (ROOT / "results" / "rescore.md").write_text(text)
    print(text)


if __name__ == "__main__":
    main()
