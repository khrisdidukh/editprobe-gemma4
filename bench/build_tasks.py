#!/usr/bin/env python3
"""Materialize EditProbe tasks into tasks/<id>/ and verify them.

For every task:
  tasks/<id>/gold.py        correct module
  tasks/<id>/src.py         buggy module (mutation applied to gold)
  tasks/<id>/test_task.py   hidden pytest tests
  tasks/<id>/task.json      metadata: problem statement, source, gold region

Verification: gold passes all tests; src fails at least one (FAIL_TO_PASS) and
the mutation's old_string occurs exactly once in gold.
"""
from __future__ import annotations

import difflib
import json
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
TASKS_DIR = ROOT / "tasks"

sys.path.insert(0, str(HERE))
import tasks_httpx  # noqa: E402
import tasks_requests  # noqa: E402
import tasks_rich  # noqa: E402

ALL = tasks_requests.TASKS + tasks_rich.TASKS + tasks_httpx.TASKS


def run_pytest(module_src: str, tests: str) -> tuple[int, list[str], list[str]]:
    """Run tests against module_src in a temp dir. Returns (rc, passed, failed)."""
    with tempfile.TemporaryDirectory() as td:
        (Path(td) / "src.py").write_text(module_src)
        (Path(td) / "test_task.py").write_text(tests)
        proc = subprocess.run(
            [sys.executable, "-m", "pytest", "-q", "-p", "no:cacheprovider", "-rA", "test_task.py"],
            cwd=td, capture_output=True, text=True, timeout=120,
        )
    passed, failed = [], []
    for line in proc.stdout.splitlines():
        if line.startswith("PASSED "):
            passed.append(line.split("::", 1)[1].strip())
        elif line.startswith(("FAILED ", "ERROR ")):
            name = line.split(" ", 1)[1].split(" - ")[0]
            failed.append(name.split("::", 1)[1] if "::" in name else name)
    return proc.returncode, passed, failed, proc.stdout + proc.stderr


def gold_region(gold: str, buggy: str) -> dict:
    """Line numbers (1-based, in the buggy file) that the fix touches."""
    g, b = gold.splitlines(), buggy.splitlines()
    sm = difflib.SequenceMatcher(a=b, b=g, autojunk=False)
    buggy_lines, gold_lines = [], []
    for tag, i1, i2, j1, j2 in sm.get_opcodes():
        if tag == "equal":
            continue
        buggy_lines.extend(range(i1 + 1, i2 + 1))
        gold_lines.extend(range(j1 + 1, j2 + 1))
    return {"buggy_lines": buggy_lines, "gold_lines": gold_lines,
            "buggy_line_count": len(b), "gold_line_count": len(g)}


def main() -> int:
    ok = True
    if TASKS_DIR.exists():
        shutil.rmtree(TASKS_DIR)
    TASKS_DIR.mkdir()
    summary = []
    ids = set()
    for t in ALL:
        tid = t["id"]
        assert tid not in ids, f"duplicate id {tid}"
        ids.add(tid)
        gold = t["gold"]
        old, new = t["mutation"]
        n = gold.count(old)
        if n != 1:
            print(f"[{tid}] mutation old_string occurs {n} times in gold (need 1)")
            ok = False
            continue
        buggy = gold.replace(old, new)
        if buggy == gold:
            print(f"[{tid}] mutation is a no-op")
            ok = False
            continue
        try:
            compile(buggy, "src.py", "exec")
        except SyntaxError as e:
            print(f"[{tid}] buggy module has a syntax error: {e}")
            ok = False
            continue

        rc_g, p_g, f_g, out_g = run_pytest(gold, t["tests"])
        rc_b, p_b, f_b, out_b = run_pytest(buggy, t["tests"])
        if rc_g != 0 or f_g:
            print(f"[{tid}] GOLD FAILS: {f_g}\n{out_g[-1500:]}")
            ok = False
            continue
        if not f_b:
            print(f"[{tid}] BUGGY PASSES ALL TESTS (mutation not detected)")
            ok = False
            continue
        fail_to_pass = sorted(set(f_b))
        pass_to_pass = sorted(set(p_b))

        d = TASKS_DIR / tid
        d.mkdir()
        (d / "gold.py").write_text(gold)
        (d / "src.py").write_text(buggy)
        (d / "test_task.py").write_text(t["tests"])
        region = gold_region(gold, buggy)
        meta = {
            "id": tid,
            "source": t["source"],
            "problem_statement": t["problem_statement"].strip(),
            "fail_to_pass": fail_to_pass,
            "pass_to_pass": pass_to_pass,
            "gold_patch_old": new,   # what must be replaced in src.py
            "gold_patch_new": old,   # with what
            **region,
        }
        (d / "task.json").write_text(json.dumps(meta, indent=2, ensure_ascii=False))
        summary.append((tid, region["buggy_line_count"], len(region["buggy_lines"]), len(fail_to_pass), len(pass_to_pass)))
        print(f"[{tid}] ok  lines={region['buggy_line_count']:4d} fix_lines={len(region['buggy_lines'])} F2P={len(fail_to_pass)} P2P={len(pass_to_pass)}")

    print(f"\n{len(summary)} tasks built, ok={ok}")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
