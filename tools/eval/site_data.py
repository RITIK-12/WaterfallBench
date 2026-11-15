"""Build site/data.json for the GitHub Pages leaderboard from tools/eval/results/leaderboard.json.

Only scores and non-secret task metadata are written (deal, family, date, class and field counts). No answer value
and no ungraded value ever leaves dataset-fw/meta.

Usage: python tools/eval/site_data.py
"""

from __future__ import annotations

import json
import math
import statistics
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
BOARD = REPO / "tools" / "eval" / "results" / "leaderboard.json"
META = REPO / "dataset-fw" / "meta"
TASKS = REPO / "dataset-fw" / "tasks"
OUT = REPO / "site" / "data.json"

MODELS = {
    "openai/gpt-6-astra": {"name": "GPT-6 Astra", "lab": "OpenAI"},
    "anthropic/claude-fable-5-2": {"name": "Claude Fable 5.2", "lab": "Anthropic"},
    "openai/gpt-6-luna": {"name": "GPT-6 Luna", "lab": "OpenAI"},
    "anthropic/claude-haiku-5-5": {"name": "Claude Haiku 5.5", "lab": "Anthropic"},
    "fireworks/kimi-k3p1-pro": {"name": "Kimi K3.1 Pro", "lab": "Moonshot AI"},
    "fireworks/minimax-m3p1-flash": {"name": "MiniMax M3.1 Flash", "lab": "MiniMax"},
}
FAMILIES = {"carmax": "CarMax Auto Owner Trust", "worldomni": "World Omni Auto Receivables Trust",
            "deere": "John Deere Owner Trust", "nissanlease": "Nissan Auto Lease Trust"}
UNGRADED_WHY = {  # short public labels; the full reasons (with figures) stay in the private keys
    "deere": "First servicing fee needs a mid-period pool balance no document provides",
    "carmax": "Servicer report departs from the agreement's overcollateralization target",
    "worldomni": "Agreement prorates the first servicing fee without a day count",
}


def main() -> None:
    board = json.loads(BOARD.read_text())
    claude_tokens = {r["task_id"]: r.get("input_tokens") for r in board["tasks"].get("anthropic/claude-fable-5-2", [])}
    tasks = {}
    for p in sorted(META.glob("fw-*.json")):
        m = json.loads(p.read_text())
        fam = m["task_id"].split("-")[1]
        tasks[m["task_id"]] = {
            "id": m["task_id"], "family": fam, "family_name": FAMILIES[fam], "deal": m["deal"],
            "period": m["graded_periods"][0]["period_of_report"][:6],
            "classes": len(m["classes"]), "graded": len(m["fields"]),
            "nontrivial": sum(1 for f in m["fields"].values() if not f["trivial"]),
            "ungraded": len(m.get("ungraded", {})),
            "ungraded_why": UNGRADED_WHY[fam] if m.get("ungraded") else None,
            "docs": len(list((TASKS / m["task_id"] / "docs" / "full").glob("*.html"))),
            "html_mb": round(sum(f.stat().st_size for f in (TASKS / m["task_id"]).rglob("*.html")) / 1e6, 2),
            "prompt_tokens": claude_tokens.get(m["task_id"]),   # Claude tokenizer, as sent by the harness
        }
    models = []
    for key, rows in board["tasks"].items():
        info = MODELS[key]
        n = len(rows)
        fr = sum(1 for r in rows if r["fully_resolved"]) / n
        mean = lambda k: statistics.mean(r[k] for r in rows if r.get(k) is not None)
        models.append({
            "key": key, **info, "tasks": n,
            "fully_resolved": round(100 * fr, 2), "se": round(100 * math.sqrt(fr * (1 - fr) / n), 2),
            "nontrivial": round(100 * mean("nontrivial"), 2), "line_item": round(100 * mean("line_item"), 2),
            "tolerance": round(100 * mean("tolerance"), 2),
            "cost": round(mean("cost"), 4), "cost_total": round(sum(r["cost"] or 0 for r in rows), 2),
            "tokens": round(mean("input_tokens") + mean("output_tokens")),
            "input_tokens": round(mean("input_tokens")), "output_tokens": round(mean("output_tokens")),
            "seconds": round(mean("seconds"), 1),
            "results": {r["task_id"]: {"ok": bool(r["fully_resolved"]), "nt": round(100 * r["nontrivial"], 1),
                                       "li": round(100 * r["line_item"], 1)} for r in rows},
        })
    models.sort(key=lambda m: (-m["fully_resolved"], -m["nontrivial"], m["cost"]))
    out = {"name": "WaterfallBench", "version": "1.0", "updated": "2026-11-15", "harness": "single call, no tools",
           "models": models, "tasks": sorted(tasks.values(), key=lambda t: (t["family"], t["period"]))}
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(out, indent=1))
    print(f"wrote {OUT.relative_to(REPO)}: {len(models)} models, {len(tasks)} tasks")


if __name__ == "__main__":
    main()
