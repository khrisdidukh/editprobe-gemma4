#!/usr/bin/env python3
"""EditProbe runner: ask a Gemma 4 model (via llama-server, OpenAI-compatible API)
to fix a localized bug using one edit protocol, apply the edit the way the
competition harness would, run the hidden tests, and log everything.

Usage:
  python harness/run.py --model e2b --protocol edit_file --out results/e2b_edit_file.jsonl
  python harness/run.py --model e2b --protocol write_file --tasks req_iter_slices rich_loop_last

Protocols:
  edit_file   native tool call edit_file(filepath, old_string, new_string)  [harness-like]
  edit_file_v native tool call, plus a verbatim-copy instruction (mitigation)
  write_file  native tool call write_file(filepath, content) with the whole file
  udiff       no tools; answer with a unified diff in a ```diff block
"""
from __future__ import annotations

import argparse
import difflib
import json
import os
import re
import subprocess
import sys
import tempfile
import time
from pathlib import Path

import urllib.request

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
sys.path.insert(0, str(HERE))
from matcher import apply_edit, diagnose_not_found  # noqa: E402

SERVER = os.environ.get("LLAMA_SERVER", "http://127.0.0.1:8080")

SYSTEM = """You are an autonomous software engineer working offline in a repository checkout at /workspace.
You are given a bug report and the content of the one file that contains the bug.
Fix the bug with the smallest possible change. Do not change tests. Do not add comments or explanations to the code.
"""

PROTOCOL_INSTRUCTIONS = {
    "edit_file": "Fix the bug by calling the edit_file tool exactly once.",
    "edit_file_v": (
        "Fix the bug by calling the edit_file tool exactly once. "
        "old_string must be copied verbatim from the file shown above: same indentation, same spacing, "
        "no line numbers, and it must include enough surrounding lines (at least 2) to occur only once in the file. "
        "new_string must keep the same indentation as the file."
    ),
    "write_file": (
        "Fix the bug by calling the write_file tool exactly once with the complete corrected content of src.py. "
        "Keep every line that is not part of the fix unchanged."
    ),
    "udiff": (
        "Fix the bug by answering with a unified diff only, inside a ```diff code block, "
        "with headers `--- a/src.py` and `+++ b/src.py`, correct @@ hunk headers, and at least 3 lines of context. "
        "Do not write anything else."
    ),
}

TOOLS = {
    "edit_file": [{
        "type": "function",
        "function": {
            "name": "edit_file",
            "description": "Replace a unique occurrence of old_string in the file at filepath with new_string. "
                           "old_string must match the file content exactly and occur exactly once.",
            "parameters": {
                "type": "object",
                "properties": {
                    "filepath": {"type": "string", "description": "Path of the file to edit, relative to /workspace."},
                    "old_string": {"type": "string", "description": "Exact text to replace."},
                    "new_string": {"type": "string", "description": "Replacement text."},
                },
                "required": ["filepath", "old_string", "new_string"],
            },
        },
    }],
    "write_file": [{
        "type": "function",
        "function": {
            "name": "write_file",
            "description": "Write content to the file at filepath, replacing its previous content.",
            "parameters": {
                "type": "object",
                "properties": {
                    "filepath": {"type": "string", "description": "Path of the file to write, relative to /workspace."},
                    "content": {"type": "string", "description": "The complete new content of the file."},
                },
                "required": ["filepath", "content"],
            },
        },
    }],
}
TOOLS["edit_file_v"] = TOOLS["edit_file"]


def build_messages(task: dict, src: str, protocol: str, hint: bool = False) -> list[dict]:
    hint_block = ""
    if hint:
        hint_block = (
            "## Hint\n\nThe bug is in these lines:\n\n```python\n"
            f"{task['gold_patch_old'].rstrip(chr(10))}\n```\n\nThey should become:\n\n```python\n"
            f"{task['gold_patch_new'].rstrip(chr(10))}\n```\n\n"
        )
    user = (
        f"## Problem statement\n\n{task['problem_statement']}\n\n"
        f"## File: src.py ({src.count(chr(10))} lines)\n\n```python\n{src}```\n\n"
        f"{hint_block}"
        f"## Instructions\n\n{PROTOCOL_INSTRUCTIONS[protocol]}"
    )
    return [{"role": "system", "content": SYSTEM}, {"role": "user", "content": user}]


def call_model(messages, tools, max_tokens: int, thinking: bool) -> dict:
    body = {
        "messages": messages,
        "temperature": 0.0,
        "max_tokens": max_tokens,
        "chat_template_kwargs": {"enable_thinking": thinking},
    }
    if tools:
        body["tools"] = tools
    req = urllib.request.Request(
        f"{SERVER}/v1/chat/completions",
        data=json.dumps(body).encode(),
        headers={"Content-Type": "application/json"},
    )
    t0 = time.time()
    with urllib.request.urlopen(req, timeout=3600) as r:
        out = json.load(r)
    out["_wall_s"] = round(time.time() - t0, 2)
    return out


def run_tests(module_src: str, tests: str, meta: dict) -> dict:
    with tempfile.TemporaryDirectory() as td:
        (Path(td) / "src.py").write_text(module_src)
        (Path(td) / "test_task.py").write_text(tests)
        proc = subprocess.run(
            [sys.executable, "-m", "pytest", "-q", "-p", "no:cacheprovider", "-rA", "test_task.py"],
            cwd=td, capture_output=True, text=True, timeout=120,
        )
    passed, failed = set(), set()
    for line in proc.stdout.splitlines():
        if line.startswith("PASSED "):
            passed.add(line.split("::", 1)[1].strip())
        elif line.startswith(("FAILED ", "ERROR ")):
            name = line.split(" ", 1)[1].split(" - ")[0]
            failed.add(name.split("::", 1)[1] if "::" in name else name)
    f2p_ok = all(t in passed for t in meta["fail_to_pass"])
    p2p_ok = all(t in passed for t in meta["pass_to_pass"])
    return {
        "rc": proc.returncode,
        "passed": sorted(passed),
        "failed": sorted(failed),
        "f2p_ok": f2p_ok,
        "p2p_ok": p2p_ok,
        "resolved": proc.returncode == 0 and f2p_ok and p2p_ok and len(passed) > 0,
        "tail": (proc.stdout + proc.stderr)[-1500:],
    }


def diff_stats(before: str, after: str) -> dict:
    b, a = before.splitlines(), after.splitlines()
    sm = difflib.SequenceMatcher(a=b, b=a, autojunk=False)
    removed = added = 0
    removed_lines = []
    for tag, i1, i2, j1, j2 in sm.get_opcodes():
        if tag == "equal":
            continue
        removed += i2 - i1
        added += j2 - j1
        removed_lines.extend(range(i1 + 1, i2 + 1))
    return {"lines_removed": removed, "lines_added": added, "removed_line_numbers": removed_lines}


def extraneous(before: str, after: str, gold_buggy_lines: list[int]) -> int:
    """Changed lines of the buggy file that the gold fix does not touch."""
    st = diff_stats(before, after)
    return len([n for n in st["removed_line_numbers"] if n not in set(gold_buggy_lines)])


def recount_hunks(diff_text: str) -> str:
    """Rewrite @@ -a,b +c,d @@ headers with counts recomputed from the hunk body
    (models often get the counts wrong). Line starts are kept."""
    out, hunk, header = [], [], None

    def flush():
        if header is None:
            return
        old = sum(1 for l in hunk if l[:1] in (" ", "-"))
        new = sum(1 for l in hunk if l[:1] in (" ", "+"))
        m = re.match(r"@@ -(\d+)(?:,\d+)? \+(\d+)(?:,\d+)? @@(.*)", header)
        if m:
            out.append(f"@@ -{m.group(1)},{old} +{m.group(2)},{new} @@{m.group(3)}")
        else:
            out.append(header)
        out.extend(hunk)

    for line in diff_text.split("\n"):
        if line.startswith("@@"):
            flush(); header, hunk = line, []
        elif header is None:
            out.append(line)
        else:
            if line == "" :
                hunk.append(" ")  # blank context line written without the leading space
            else:
                hunk.append(line)
    flush()
    return "\n".join(out)


def apply_udiff(src: str, diff_text: str) -> tuple[str, str | None]:
    """Apply passes, lenient to strict: git apply; patch -F3 (p1, p0); the same
    two after recounting hunk headers. Returns (tier, new_src)."""
    def try_apply(td: Path, dfile: str, args: list[str]) -> str | None:
        (td / "src.py").write_text(src)
        r = subprocess.run(args + [dfile], cwd=td, capture_output=True, text=True)
        return (td / "src.py").read_text() if r.returncode == 0 else None

    with tempfile.TemporaryDirectory() as td:
        td = Path(td)
        text = diff_text if diff_text.endswith("\n") else diff_text + "\n"
        (td / "p.diff").write_text(text)
        (td / "r.diff").write_text(recount_hunks(text))
        subprocess.run(["git", "init", "-q"], cwd=td, capture_output=True)
        passes = [
            ("strict", "p.diff", ["git", "apply", "--whitespace=nowarn"]),
            ("fuzzy", "p.diff", ["patch", "-p1", "-F3", "--no-backup-if-mismatch", "-i"]),
            ("fuzzy", "p.diff", ["patch", "-p0", "-F3", "--no-backup-if-mismatch", "-i"]),
            ("recount", "r.diff", ["git", "apply", "--whitespace=nowarn"]),
            ("recount_fuzzy", "r.diff", ["patch", "-p1", "-F3", "--no-backup-if-mismatch", "-i"]),
            ("recount_fuzzy", "r.diff", ["patch", "-p0", "-F3", "--no-backup-if-mismatch", "-i"]),
        ]
        for tier, dfile, args in passes:
            new = try_apply(td, dfile, args)
            if new is not None:
                return tier, new
    return "failed", None


def extract_diff(text: str) -> str | None:
    m = re.search(r"```(?:diff|patch)?\s*\n(.*?)```", text, re.S)
    body = m.group(1) if m else text
    if "@@" not in body or ("---" not in body and "+++" not in body):
        return None
    # strip anything before the first ---
    i = body.find("---")
    return body[i:]


def parse_tool_call(resp: dict, expected_name: str) -> tuple[str, dict | None, str]:
    """Return (status, args, raw_text). status: ok | no_tool_call | wrong_tool | bad_args | multiple_calls"""
    choice = resp["choices"][0]
    msg = choice["message"]
    calls = msg.get("tool_calls") or []
    text = msg.get("content") or ""
    if not calls:
        return "no_tool_call", None, text
    if len(calls) > 1:
        return "multiple_calls", None, text
    fn = calls[0]["function"]
    if fn["name"] != expected_name:
        return "wrong_tool", None, text
    try:
        args = json.loads(fn["arguments"])
    except json.JSONDecodeError:
        return "bad_args", None, fn["arguments"]
    if not isinstance(args, dict):
        return "bad_args", None, fn["arguments"]
    return "ok", args, text


def evaluate(task_dir: Path, protocol: str, max_tokens: int, thinking: bool, hint: bool = False) -> dict:
    meta = json.loads((task_dir / "task.json").read_text())
    src = (task_dir / "src.py").read_text()
    messages = build_messages(meta, src, protocol, hint)
    tools = TOOLS.get(protocol)
    resp = call_model(messages, tools, max_tokens, thinking)
    rec = score(task_dir, protocol, resp)
    rec["hint"] = hint
    return rec


def score(task_dir: Path, protocol: str, resp: dict) -> dict:
    """Turn a model response into a scored record. Pure function of the logged
    response, so results can be recomputed without the model (harness/reapply.py)."""
    meta = json.loads((task_dir / "task.json").read_text())
    src = (task_dir / "src.py").read_text()
    gold = (task_dir / "gold.py").read_text()
    tests = (task_dir / "test_task.py").read_text()
    usage = resp.get("usage", {})
    timings = resp.get("timings", {})
    rec = {
        "task": meta["id"],
        "protocol": protocol,
        "finish_reason": resp["choices"][0].get("finish_reason"),
        "prompt_tokens": usage.get("prompt_tokens"),
        "completion_tokens": usage.get("completion_tokens"),
        "wall_s": resp.get("_wall_s"),
        "gen_tok_per_s": timings.get("predicted_per_second"),
        "raw_message": resp["choices"][0]["message"],
        "stage": None,          # failure ladder label
        "match_tier": None,
        "apply_ok": False,
        "compiles": None,
        "resolved": False,
        "equals_gold": False,
        "extraneous_lines": None,
        "lines_added": None,
        "lines_removed": None,
        "not_found_reason": None,
        "tests": None,
    }
    candidate = None

    if protocol in ("edit_file", "edit_file_v"):
        status, args, _ = parse_tool_call(resp, "edit_file")
        if status != "ok":
            rec["stage"] = status
            return rec
        old = args.get("old_string"); new = args.get("new_string")
        if not isinstance(old, str) or not isinstance(new, str):
            rec["stage"] = "bad_args"; return rec
        rec["old_string"] = old; rec["new_string"] = new
        rec["filepath"] = args.get("filepath")
        m = apply_edit(src, old, new)
        rec["match_tier"] = m.tier
        if m.new_text is None:
            rec["stage"] = "old_" + ("ambiguous" if m.tier == "ambiguous" else "not_found")
            rec["not_found_reason"] = diagnose_not_found(src, old) if m.tier == "not_found" else m.note
            return rec
        candidate = m.new_text

    elif protocol == "write_file":
        status, args, _ = parse_tool_call(resp, "write_file")
        if status != "ok":
            rec["stage"] = status
            return rec
        content = args.get("content")
        if not isinstance(content, str) or not content.strip():
            rec["stage"] = "bad_args"; return rec
        rec["filepath"] = args.get("filepath")
        rec["match_tier"] = "whole_file"
        candidate = content if content.endswith("\n") else content + "\n"
        if rec["finish_reason"] == "length":
            rec["stage"] = "truncated_output"
            rec["apply_ok"] = False
            # still measure how much was lost
            rec["lines_added"] = candidate.count("\n"); rec["lines_removed"] = src.count("\n")
            return rec

    elif protocol == "udiff":
        text = resp["choices"][0]["message"].get("content") or ""
        d = extract_diff(text)
        if d is None:
            rec["stage"] = "no_diff_found"; return rec
        tier, new_src = apply_udiff(src, d)
        rec["match_tier"] = tier
        if new_src is None:
            rec["stage"] = "patch_failed"; return rec
        candidate = new_src
    else:
        raise ValueError(protocol)

    rec["apply_ok"] = True
    rec["candidate"] = candidate
    if candidate == src:
        rec["stage"] = "noop_edit"
        rec["compiles"] = True
        rec["lines_added"] = rec["lines_removed"] = rec["extraneous_lines"] = 0
        return rec
    try:
        compile(candidate, "src.py", "exec")
        rec["compiles"] = True
    except SyntaxError as e:
        rec["compiles"] = False
        rec["stage"] = "syntax_error"
        rec["syntax_error"] = str(e)
        return rec
    st = diff_stats(src, candidate)
    rec["lines_added"] = st["lines_added"]; rec["lines_removed"] = st["lines_removed"]
    rec["extraneous_lines"] = extraneous(src, candidate, meta["buggy_lines"])
    rec["equals_gold"] = candidate == gold
    t = run_tests(candidate, tests, meta)
    rec["tests"] = {k: t[k] for k in ("rc", "passed", "failed", "f2p_ok", "p2p_ok", "resolved")}
    rec["resolved"] = t["resolved"]
    rec["stage"] = "pass" if t["resolved"] else ("tests_fail_regression" if t["f2p_ok"] and not t["p2p_ok"] else "tests_fail")
    return rec


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--model", required=True, help="label for the model being served (e2b, e4b, ...)")
    ap.add_argument("--protocol", required=True, choices=list(PROTOCOL_INSTRUCTIONS))
    ap.add_argument("--tasks", nargs="*", help="task ids (default: all)")
    ap.add_argument("--out", help="output JSONL (default results/<model>_<protocol>.jsonl)")
    ap.add_argument("--max-tokens", type=int, default=None)
    ap.add_argument("--thinking", action="store_true")
    ap.add_argument("--hint", action="store_true", help="give the gold fix in words (pure edit-landing test)")
    ap.add_argument("--resume", action="store_true", help="skip tasks already in the output file")
    a = ap.parse_args()

    tasks_dir = ROOT / "tasks"
    ids = a.tasks or sorted(p.name for p in tasks_dir.iterdir() if p.is_dir())
    out = Path(a.out) if a.out else ROOT / "results" / f"{a.model}_{a.protocol}{'_think' if a.thinking else ''}{'_hint' if a.hint else ''}.jsonl"
    out.parent.mkdir(parents=True, exist_ok=True)
    done = set()
    if a.resume and out.exists():
        for line in out.read_text().splitlines():
            try:
                done.add(json.loads(line)["task"])
            except Exception:
                pass
    max_tokens = a.max_tokens or (3000 if a.protocol == "write_file" else 1200)
    if a.thinking:
        max_tokens += 4096

    # server identity for the log
    try:
        with urllib.request.urlopen(f"{SERVER}/v1/models", timeout=10) as r:
            served = json.load(r)["data"][0]["id"]
    except Exception as e:
        served = f"unknown ({e})"

    n_res = 0
    with out.open("a") as f:
        for i, tid in enumerate(ids, 1):
            if tid in done:
                continue
            t0 = time.time()
            rec = evaluate(tasks_dir / tid, a.protocol, max_tokens, a.thinking, a.hint)
            rec["model"] = a.model
            rec["served_model"] = served
            rec["thinking"] = a.thinking
            rec["ts"] = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
            f.write(json.dumps(rec, ensure_ascii=False) + "\n"); f.flush()
            n_res += rec["resolved"]
            print(f"[{i}/{len(ids)}] {tid:32s} {rec['stage']:22s} tier={rec['match_tier']} "
                  f"tok={rec['completion_tokens']} {time.time()-t0:5.1f}s  resolved so far {n_res}", flush=True)


if __name__ == "__main__":
    main()
