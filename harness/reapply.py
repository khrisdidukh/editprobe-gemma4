#!/usr/bin/env python3
"""Re-score every logged record from its logged model output (no model calls).

Use after changing the apply/scoring logic so all result files reflect the same
rules. Rewrites results/*.jsonl in place, keeping model, timings and hint flags.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
sys.path.insert(0, str(HERE))
from run import score  # noqa: E402

KEEP = ("model", "served_model", "thinking", "hint", "ts", "wall_s", "gen_tok_per_s", "prompt_tokens", "completion_tokens")


def main():
    paths = [Path(p) for p in sys.argv[1:]] or sorted(p for p in (ROOT / "results").glob("*.jsonl") if not p.name.startswith("rescore"))
    for p in paths:
        new_lines = []
        changed = 0
        for line in p.read_text().splitlines():
            if not line.strip():
                continue
            r = json.loads(line)
            resp = {"choices": [{"message": r["raw_message"], "finish_reason": r.get("finish_reason")}],
                    "usage": {"prompt_tokens": r.get("prompt_tokens"), "completion_tokens": r.get("completion_tokens")},
                    "timings": {"predicted_per_second": r.get("gen_tok_per_s")}, "_wall_s": r.get("wall_s")}
            nr = score(ROOT / "tasks" / r["task"], r["protocol"], resp)
            for k in KEEP:
                if k in r:
                    nr[k] = r[k]
            if nr["stage"] != r["stage"] or nr["resolved"] != r["resolved"]:
                changed += 1
                print(f"  {p.name} {r['task']}: {r['stage']} -> {nr['stage']}")
            new_lines.append(json.dumps(nr, ensure_ascii=False))
        p.write_text("\n".join(new_lines) + "\n")
        print(f"{p.name}: {len(new_lines)} records, {changed} changed")


if __name__ == "__main__":
    main()
