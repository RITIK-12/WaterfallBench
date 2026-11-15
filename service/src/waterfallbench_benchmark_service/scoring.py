"""Aggregate per-task grader results into the run's score and metadata (pure, no I/O)."""

from __future__ import annotations

from collections import Counter, defaultdict
from collections.abc import Iterable, Mapping
from typing import Any

from waterfallbench_benchmark_service.data import TaskInfo
from waterfallbench_benchmark_service.grading import as_object

BREAKDOWN_DIMENSIONS: tuple[str, ...] = ("category", "asset_class", "family", "window_tag", "continuity_pending")
ALLOCATION_DIMENSIONS: tuple[str, ...] = ("category", "asset_class", "family", "window_tag")


def _pct(values: Iterable[float | bool | None]) -> float | None:
    """Mean as a percentage, rounded to 4 places; None when there is nothing to average."""
    kept = [float(v) for v in values if v is not None]
    return round(100.0 * sum(kept) / len(kept), 4) if kept else None


def _number(value: Any) -> float | None:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return None
    return float(value)


def _task_row(task_id: str, raw_result: Any, info: TaskInfo | None) -> dict[str, Any]:
    """One task's scored metrics. A task with no result (None) scores 0 everywhere it applies."""
    has_nontrivial = info.n_nontrivial_fields > 0 if info is not None else True
    category = info.category if info is not None else "unknown"
    result = as_object(raw_result)
    if result is None:
        return {
            "task_id": task_id,
            "status": "no_result",
            "fully_resolved": False,
            "line_item_accuracy": 0.0,
            "nontrivial_accuracy": 0.0 if has_nontrivial else None,
            "tolerance_accuracy": 0.0,
            "consecutive_periods_correct": 0.0 if category == "C2" else None,
            "precision": 0.0 if category == "C4" else None,
            "recall": 0.0 if category == "C4" else None,
            "f1": 0.0 if category == "C4" else None,
        }
    row: dict[str, Any] = {
        "task_id": task_id,
        "status": str(result.get("answer_status", "unknown")),
        "fully_resolved": result.get("fully_resolved") is True,
        "line_item_accuracy": _number(result.get("line_item_accuracy")) or 0.0,
        "nontrivial_accuracy": _number(result.get("nontrivial_accuracy")),
        "tolerance_accuracy": _number(result.get("tolerance_accuracy")) or 0.0,
        "consecutive_periods_correct": _number(result.get("consecutive_periods_correct")),
        "precision": _number(result.get("precision")),
        "recall": _number(result.get("recall")),
        "f1": _number(result.get("f1")),
    }
    if row["nontrivial_accuracy"] is None and has_nontrivial:
        row["nontrivial_accuracy"] = 0.0
    return row


def _summary(rows: list[dict[str, Any]]) -> dict[str, Any]:
    summary: dict[str, Any] = {
        "n_tasks": len(rows),
        "n_fully_resolved": sum(1 for r in rows if r["fully_resolved"]),
        "score": _pct(r["fully_resolved"] for r in rows) or 0.0,
        "line_item_accuracy_pct": _pct(r["line_item_accuracy"] for r in rows),
        "nontrivial_field_accuracy_pct": _pct(r["nontrivial_accuracy"] for r in rows),
        "tolerance_1usd_accuracy_pct": _pct(r["tolerance_accuracy"] for r in rows),
    }
    periods = [r["consecutive_periods_correct"] for r in rows if r["consecutive_periods_correct"] is not None]
    if periods:
        summary["mean_consecutive_periods_correct"] = round(sum(periods) / len(periods), 4)
    for key in ("precision", "recall", "f1"):
        mean = _pct(r[key] for r in rows)
        if mean is not None:
            summary[f"{key}_pct"] = mean
    return summary


def _baseline_summary(task_ids: list[str], infos: Mapping[str, TaskInfo]) -> dict[str, Any]:
    by_name: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for task_id in task_ids:
        info = infos.get(task_id)
        if info is None:
            continue
        for name, metrics in info.baselines.items():
            by_name[name].append(_task_row(task_id, {"answer_status": "baseline", **metrics}, info))
    return {name: _summary(rows) for name, rows in sorted(by_name.items())}


def final_score(
    evaluation_results: Mapping[str, Any], infos: Mapping[str, TaskInfo], dataset: str
) -> tuple[float, dict[str, Any]]:
    """Headline score (percent of tasks fully resolved) and the reporting metadata."""
    task_ids = list(evaluation_results)
    rows = [_task_row(task_id, evaluation_results[task_id], infos.get(task_id)) for task_id in task_ids]
    overall = _summary(rows)

    breakdowns: dict[str, dict[str, Any]] = {}
    for dimension in BREAKDOWN_DIMENSIONS:
        groups: dict[str, list[dict[str, Any]]] = defaultdict(list)
        for task_id, row in zip(task_ids, rows, strict=True):
            info = infos.get(task_id)
            groups[info.group_value(dimension) if info is not None else "unknown"].append(row)
        breakdowns[f"by_{dimension}"] = {value: _summary(group) for value, group in sorted(groups.items())}

    allocation = Counter(
        tuple(infos[t].group_value(d) for d in ALLOCATION_DIMENSIONS) if t in infos else ("unknown",) * 4
        for t in task_ids
    )

    metadata: dict[str, Any] = {
        "dataset": dataset,
        "total_tasks": overall["n_tasks"],
        "resolved_tasks": overall["n_fully_resolved"],
        "tasks_without_result": sum(1 for r in rows if r["status"] == "no_result"),
        "answer_status_counts": dict(sorted(Counter(r["status"] for r in rows).items())),
        "unknown_task_ids": sorted(t for t in task_ids if t not in infos),
        "line_item_accuracy_pct": overall["line_item_accuracy_pct"],
        "nontrivial_field_accuracy_pct": overall["nontrivial_field_accuracy_pct"],
        "tolerance_1usd_accuracy_pct": overall["tolerance_1usd_accuracy_pct"],
        **breakdowns,
        "allocation": [
            {**dict(zip(ALLOCATION_DIMENSIONS, key, strict=True)), "n_tasks": count}
            for key, count in sorted(allocation.items())
        ],
        "baselines": _baseline_summary(task_ids, infos),
    }
    return overall["score"], metadata
