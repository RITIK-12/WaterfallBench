"""Collect per-task answers into one WaterfallBench submission file for the grader Space.

Looks under DIR for <task_id>/answer.json, or a saved harness reply <task_id>/direct/response.txt (Valkyrie run
outputs), and prints {"<task_id>": {answer}, ...}. Tasks with no parseable answer are left out (they score 0).

Usage: python hf/make_submission.py DIR > submission.json
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path


def parse(text: str):
    t = re.sub(r"^```(?:json)?\s*|\s*```$", "", text.strip())
    a, b = t.find("{"), t.rfind("}")
    return json.loads(t[a:b + 1]) if 0 <= a < b else None


def main() -> None:
    root = Path(sys.argv[1])
    out = {}
    for p in sorted(root.rglob("*")):
        if p.name not in ("answer.json", "response.txt"):
            continue
        tid = next((part for part in reversed(p.parts) if part.startswith("fw-")), None)
        if not tid or tid in out and p.name == "response.txt":
            continue
        try:
            ans = parse(p.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, UnicodeDecodeError):
            ans = None
        if isinstance(ans, dict):
            out[tid] = ans
    print(json.dumps(out))
    print(f"{len(out)} task answers collected", file=sys.stderr)


if __name__ == "__main__":
    main()
