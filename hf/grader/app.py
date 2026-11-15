"""WaterfallBench grader (Hugging Face Space).

Upload one JSON file with your model's answers to the 20 tasks and get the benchmark scores back. The answer keys
live in a private dataset that this Space reads with its HF_TOKEN secret; they never leave the Space. Results show
per-task scores only, never which field was wrong or any expected value.

Submission format (either):
  {"fw-carmax-2025-2-2025-04": {<answer.json>}, "fw-deere-2026-b-2026-08": {...}, ...}
  or JSON lines: {"task_id": "fw-carmax-2025-2-2025-04", "answer": {<answer.json>}}
"""

from __future__ import annotations

import json
import math
import os
from pathlib import Path

import gradio as gr

import grading

KEYS_REPO = os.environ.get("WFB_KEYS_REPO", "")
MAX_BYTES = 5_000_000


def load_keys() -> dict[str, dict]:
    if not KEYS_REPO:
        return {}
    from huggingface_hub import snapshot_download
    d = Path(snapshot_download(repo_id=KEYS_REPO, repo_type="dataset", token=os.environ.get("HF_TOKEN")))
    return {m["task_id"]: m for m in (json.loads(p.read_text()) for p in sorted(d.glob("fw-*.json")))}


try:
    KEYS = load_keys()
    LOAD_ERROR = "" if KEYS else "The grader has no answer keys configured yet."
except Exception as e:  # noqa: BLE001 - shown to the visitor as a configuration problem
    KEYS, LOAD_ERROR = {}, f"The grader could not load its answer keys ({type(e).__name__})."


def parse_submission(raw: str) -> dict[str, object]:
    raw = raw.strip()
    try:
        obj = json.loads(raw)
        if isinstance(obj, dict) and not ("task_id" in obj and "answer" in obj):
            return obj
        if isinstance(obj, list):
            return {r["task_id"]: r["answer"] for r in obj}
        return {obj["task_id"]: obj["answer"]}
    except json.JSONDecodeError:
        out = {}
        for line in raw.splitlines():
            if line.strip():
                r = json.loads(line)
                out[r["task_id"]] = r["answer"]
        return out


def score(rows: list[dict]) -> dict:
    n = len(rows)
    fr = sum(r["fully_resolved"] for r in rows) / n
    mean = lambda k: sum(r[k] for r in rows) / n
    return {"fully_resolved": 100 * fr, "se": 100 * math.sqrt(fr * (1 - fr) / n),
            "field_accuracy": 100 * mean("field_accuracy"), "all_fields": 100 * mean("all_fields")}


def grade_file(path: str | None, model: str):
    if LOAD_ERROR:
        return f"**{LOAD_ERROR}**", None
    if not path:
        return "Upload a submission file first.", None
    raw = Path(path).read_bytes()
    if len(raw) > MAX_BYTES:
        return f"File too large ({len(raw):,} bytes; limit {MAX_BYTES:,}).", None
    try:
        sub = parse_submission(raw.decode("utf-8"))
    except Exception as e:  # noqa: BLE001
        return f"Could not read the file as JSON or JSON lines ({type(e).__name__}).", None
    unknown = sorted(k for k in sub if k not in KEYS)
    rows = []
    for tid, meta in sorted(KEYS.items()):
        r = grading.grade_submission(meta, sub.get(tid))
        rows.append({"task_id": tid, "deal": meta.get("deal", ""), "answered": tid in sub,
                     "status": r.get("answer_status"), "fully_resolved": bool(r.get("fully_resolved")),
                     "field_accuracy": r.get("nontrivial_accuracy") or 0.0, "all_fields": r.get("line_item_accuracy") or 0.0})
    s = score(rows)
    answered = sum(r["answered"] for r in rows)
    md = (f"### {model.strip() or 'Your model'}\n\n"
          f"| Fully resolved | Field accuracy | All fields | Tasks answered |\n|---|---|---|---|\n"
          f"| **{s['fully_resolved']:.1f}%** ±{s['se']:.1f} | {s['field_accuracy']:.1f}% | {s['all_fields']:.1f}% | {answered} / {len(rows)} |\n\n"
          "Missing or unparseable answers score 0. Field accuracy counts non-trivial fields only.")
    if unknown:
        md += f"\n\nIgnored {len(unknown)} unknown task id(s): {', '.join(unknown[:5])}{' …' if len(unknown) > 5 else ''}"
    table = [[r["task_id"], r["deal"], "✓" if r["fully_resolved"] else "✗", f"{100 * r['field_accuracy']:.0f}%",
              f"{100 * r['all_fields']:.0f}%", r["status"] if r["answered"] else "missing"] for r in rows]
    return md, table


with gr.Blocks(title="WaterfallBench grader") as demo:
    gr.Markdown(
        "# WaterfallBench grader\n"
        "Score your model on the 20 first-distribution tasks. Download the tasks from the "
        "[dataset](https://huggingface.co/datasets/__NS__/WaterfallBench), run your model, and upload one JSON file "
        "mapping each `task_id` to its `answer.json` object (or JSON lines `{\"task_id\": ..., \"answer\": {...}}`). "
        "[Leaderboard](https://huggingface.co/spaces/__NS__/WaterfallBench) · "
        "[Code](https://github.com/RITIK-12/WaterfallBench)\n\n"
        "Answer keys stay private: results show per-task scores, never which field was wrong.")
    with gr.Row():
        f = gr.File(label="Submission (.json or .jsonl)", file_types=[".json", ".jsonl"], type="filepath")
        model = gr.Textbox(label="Model name (shown in your result only)", placeholder="e.g. my-model-high")
    btn = gr.Button("Grade", variant="primary")
    out = gr.Markdown()
    tbl = gr.Dataframe(headers=["task_id", "deal", "fully resolved", "field accuracy", "all fields", "status"],
                       interactive=False, wrap=True)
    btn.click(grade_file, inputs=[f, model], outputs=[out, tbl])

if __name__ == "__main__":
    demo.launch()
