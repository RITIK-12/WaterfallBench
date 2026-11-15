"""WaterfallBench leaderboard: aggregate Valkyrie runs of the single-call harness into one comparable table.

For each run ID it downloads the graded results (`valkyrie run results`) and the harness's per-task usage files
(`valkyrie run outputs`, direct/usage.json), then prints one row per model:

  fully resolved %   every output field exact to the cent        (headline / rank)
  non-trivial acc %  fields that are not zero and changed from the prior report (tie-break)
  line-item acc %    all fields (inflated by zeros / unchanged lines - context only)
  +-$1 acc %         money within one dollar (rounding slips vs logic errors)
  answered %, errors, mean input / output tokens, mean seconds, estimated cost per task and in total

Usage: python tools/eval/leaderboard.py RUN_ID [RUN_ID ...] [--out tools/eval/results]
"""

from __future__ import annotations

import argparse
import json
import statistics
import subprocess
from collections import defaultdict
from pathlib import Path


def sh(cmd: list[str]) -> str:
    return subprocess.run(cmd, capture_output=True, text=True, check=True).stdout


def fetch(run_id: str, cache: Path) -> tuple[dict, dict[str, dict]]:
    d = cache / run_id
    d.mkdir(parents=True, exist_ok=True)
    res_path = d / "results.json"
    if not res_path.exists():
        sh(["valkyrie", "run", "results", run_id, "--path", str(res_path)])
    if not (d / "outputs").exists():
        sh(["valkyrie", "run", "outputs", run_id, "--output-dir", str(d / "outputs")])
    usage = {}
    for p in (d / "outputs").rglob("usage.json"):
        u = json.loads(p.read_text())
        if u.get("est_cost_usd") is None:
            u["est_cost_usd"] = est_cost(u)
        usage[u.get("task_id") or p.parts[-3]] = u
    return json.loads(res_path.read_text()), usage


# List prices (USD per 1M tokens) for models the harness does not price itself: (threshold, (in, out) at or below
# the threshold, (in, out) above it - the long-context rate applies to the whole request).
EXTRA_PRICES = {
    "gpt-6-astra": (272_000, (10.00, 50.00), (20.00, 75.00)),
    "gpt-6-luna": (272_000, (0.10, 0.50), (0.20, 0.75)),
}


def est_cost(u: dict) -> float | None:
    model = str(u.get("model", "")).split("/")[-1]
    tin, tout = u.get("input_tokens"), u.get("output_tokens")
    if model not in EXTRA_PRICES or tin is None or tout is None:
        return None
    limit, low, high = EXTRA_PRICES[model]
    p_in, p_out = high if tin > limit else low
    return round(tin / 1e6 * p_in + tout / 1e6 * p_out, 4)


def regrade(run_dir: Path, meta_dir: Path, task_ids) -> dict[str, dict]:
    """Grade the saved replies (direct/response.txt) again against the current answer keys, with the service's own
    grading code. Used after an answer key changes (e.g. a field found not derivable is dropped from grading)."""
    import sys
    repo = Path(__file__).resolve().parents[2]
    sys.path[:0] = [str(repo / "service" / "src"), str(repo / "agents" / "waterfallbench-direct")]
    import direct
    from waterfallbench_benchmark_service import grading
    out = {}
    for tid in task_ids:
        meta = json.loads((meta_dir / f"{tid}.json").read_text())
        reply = run_dir / "outputs" / tid / "direct" / "response.txt"
        try:
            answer = direct.parse_json(reply.read_text())
        except Exception:           # no reply or no JSON object: graded as a missing answer (zero)
            answer = None
        r = grading.grade_submission(meta, answer)
        r["answer_status"] = "ok" if answer is not None else "malformed"
        out[meta["task_id"]] = r
    return out


def pct(xs) -> str:
    xs = [x for x in xs if x is not None]
    return f"{100 * statistics.mean(xs):.1f}" if xs else "-"


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("runs", nargs="+")
    ap.add_argument("--out", default=str(Path(__file__).parent / "results"))
    ap.add_argument("--regrade", metavar="META_DIR", help="re-grade the saved replies against the answer keys in META_DIR")
    a = ap.parse_args()
    out = Path(a.out)
    rows_by_model: dict[str, list[dict]] = defaultdict(list)
    for run_id in a.runs:
        res, usage = fetch(run_id, out / "runs")
        evals = res.get("evaluation_results") or {}
        if a.regrade:   # also tasks whose harness ran but failed (e.g. an empty reply): they score zero, not vanish
            evals = regrade(out / "runs" / run_id, Path(a.regrade), sorted(set(evals) | set(usage)))
        for tid, r in evals.items():
            u = usage.get(tid, {})
            model = u.get("model") or (res.get("benchmark_arguments") or {}).get("model") or "unknown"
            rows_by_model[model].append({
                "run": run_id, "task_id": tid, "category": r.get("category"), "family": r.get("family"),
                "fully_resolved": bool(r.get("fully_resolved")), "nontrivial": r.get("nontrivial_accuracy"),
                "line_item": r.get("line_item_accuracy"), "tolerance": r.get("tolerance_accuracy"),
                "n_fields": r.get("n_fields"), "answer_status": r.get("answer_status"),
                "consecutive": r.get("consecutive_periods_correct"),
                "input_tokens": u.get("input_tokens"), "output_tokens": u.get("output_tokens"),
                "cost": u.get("est_cost_usd"), "seconds": u.get("seconds"), "error": u.get("error"),
                "truncated": u.get("truncated") or [],
            })
    # a task run more than once for one model (a retry after an unbilled failure such as a rate limit): keep one row,
    # preferring the attempt that produced an answer, so a retry never counts twice
    for model, rows in rows_by_model.items():
        best: dict[str, dict] = {}
        for r in rows:
            cur = best.get(r["task_id"])
            if cur is None or (cur["answer_status"] != "ok" and r["answer_status"] == "ok"):
                best[r["task_id"]] = r
        rows_by_model[model] = list(best.values())
    lines = ["# WaterfallBench leaderboard (single-call harness)", "",
             "| model | tasks | fully resolved % | non-trivial acc % | line-item acc % | ±$1 acc % | answered % | "
             "mean input tok | mean output tok | mean s | est $/task | est $ total |",
             "|---|---|---|---|---|---|---|---|---|---|---|---|"]
    board = []
    for model, rows in rows_by_model.items():
        costs = [r["cost"] for r in rows if r["cost"] is not None]
        mean = lambda k: statistics.mean([r[k] for r in rows if r[k] is not None]) if any(r[k] is not None for r in rows) else None
        entry = {"model": model, "tasks": len(rows), "fully_resolved": pct([r["fully_resolved"] for r in rows]),
                 "nontrivial": pct([r["nontrivial"] for r in rows]), "line_item": pct([r["line_item"] for r in rows]),
                 "tolerance": pct([r["tolerance"] for r in rows]),
                 "answered": pct([r["answer_status"] == "ok" for r in rows]),
                 "in": mean("input_tokens"), "outp": mean("output_tokens"), "sec": mean("seconds"),
                 "cost_task": statistics.mean(costs) if costs else None, "cost_total": sum(costs) if costs else None}
        board.append(entry)
    board.sort(key=lambda e: (-float(e["fully_resolved"] if e["fully_resolved"] != "-" else -1),
                              -float(e["nontrivial"] if e["nontrivial"] != "-" else -1)))
    fmt = lambda v, f: "-" if v is None else format(v, f)
    for e in board:
        lines.append(f"| {e['model']} | {e['tasks']} | {e['fully_resolved']} | {e['nontrivial']} | {e['line_item']} | "
                     f"{e['tolerance']} | {e['answered']} | {fmt(e['in'], ',.0f')} | {fmt(e['outp'], ',.0f')} | "
                     f"{fmt(e['sec'], '.0f')} | {fmt(e['cost_task'], '.2f')} | {fmt(e['cost_total'], '.2f')} |")
    lines += ["", "## Per task", "", "| model | task | category | fully resolved | non-trivial | line-item | ±$1 | fields | "
              "input tok | output tok | est $ | s | note |", "|---|---|---|---|---|---|---|---|---|---|---|---|---|"]
    for model, rows in rows_by_model.items():
        for r in sorted(rows, key=lambda r: r["task_id"]):
            note = (r["error"] or "")[:80] + (f" truncated: {r['truncated']}" if r["truncated"] else "")
            lines.append(f"| {model} | {r['task_id']} | {r['category']} | {'yes' if r['fully_resolved'] else 'no'} | "
                         f"{fmt(r['nontrivial'], '.0%')} | {fmt(r['line_item'], '.0%')} | {fmt(r['tolerance'], '.0%')} | "
                         f"{r['n_fields']} | {fmt(r['input_tokens'], ',')} | {fmt(r['output_tokens'], ',')} | "
                         f"{fmt(r['cost'], '.2f')} | {fmt(r['seconds'], '.0f')} | {note} |")
    text = "\n".join(lines) + "\n"
    out.mkdir(parents=True, exist_ok=True)
    (out / "leaderboard.md").write_text(text)
    (out / "leaderboard.json").write_text(json.dumps({"board": board, "tasks": rows_by_model}, indent=1, default=str))
    print(text)


if __name__ == "__main__":
    main()
