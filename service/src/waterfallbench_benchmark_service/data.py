"""Reading the pipeline's private data root.

Layout (produced by the separate WaterfallBench pipeline)::

    $WFB_DATA_DIR/
      tasks/<task_id>/docs/{full,excerpt}/*.{md,pdf}
      tasks/<task_id>/reports/*.{md,pdf}
      tasks/<task_id>/instructions.md
      tasks/<task_id>/answer_schema.json
      meta/<task_id>.json            # PRIVATE answer key; never uploaded

Task metadata kept in memory (``TaskInfo``) holds no answer values. The answer key is read
from disk by :func:`read_answer_key_meta`, which only ``evaluate_instance`` calls.
"""

from __future__ import annotations

import json
import logging
import os
import re
from collections.abc import Mapping
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from waterfallbench_benchmark_service.grading import (
    C2_HEADLINE_KEYS,
    C4_HEADLINE_KEYS,
    HEADLINE_KEYS,
    MetaError,
    as_object,
    field_groups,
    parse_answer_key,
)

logger = logging.getLogger(__name__)

DEFAULT_DATA_DIR = str(Path(__file__).resolve().parents[3] / "dataset")  # <repo>/dataset: tasks/ + private meta/
WORKSPACE = "/workspace"
DOCS_DIR = f"{WORKSPACE}/docs"
REPORTS_DIR = f"{WORKSPACE}/reports"
SCHEMA_PATH = f"{WORKSPACE}/answer_schema.json"
ANSWER_PATH = f"{WORKSPACE}/answer.json"
PROBLEM_PATH = "/tmp/problem_statement.txt"

_TASK_ID = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,199}$")


def data_root() -> Path:
    return Path(os.environ.get("WFB_DATA_DIR") or DEFAULT_DATA_DIR)


@dataclass(frozen=True)
class Variant:
    name: str
    docs_subdir: str  # "full" | "excerpt"
    extension: str  # ".html" | ".md" | ".pdf"
    excerpt_only: bool


ALL_VARIANTS: dict[str, Variant] = {
    # Pilot decision: packets are SEC EDGAR HTML as filed (no markdown/PDF conversion, no excerpts).
    "full-html": Variant("full-html", "full", ".html", excerpt_only=False),
    "full-md": Variant("full-md", "full", ".md", excerpt_only=False),
    "full-pdf": Variant("full-pdf", "full", ".pdf", excerpt_only=False),
    "excerpt-md": Variant("excerpt-md", "excerpt", ".md", excerpt_only=True),
    "excerpt-pdf": Variant("excerpt-pdf", "excerpt", ".pdf", excerpt_only=True),
}
# Active dataset variants (comma-separated, first = default). The pilot data root ships HTML only.
VARIANTS: dict[str, Variant] = {
    n: ALL_VARIANTS[n] for n in (x.strip() for x in os.environ.get("WFB_VARIANTS", "full-html").split(",")) if n
}
DEFAULT_DATASET = next(iter(VARIANTS))


def resolve_variant(dataset: str | None) -> Variant:
    name = dataset or "default"
    if name == "default":
        name = DEFAULT_DATASET
    if name not in VARIANTS:
        raise ValueError(f"Unknown dataset {name!r}; expected one of {sorted(VARIANTS)} or 'default'")
    return VARIANTS[name]


@dataclass(frozen=True)
class TaskInfo:
    """Public, answer-free description of one task (what lives in ``self.datasets``)."""

    task_id: str
    category: str
    excerpt_derivable: bool
    asset_class: str
    family: str
    deal: str
    window_tag: str
    continuity_pending: bool
    n_fields: int
    n_nontrivial_fields: int
    # baseline name -> headline metrics (accuracies, never answer values)
    baselines: dict[str, dict[str, Any]] = field(default_factory=dict)

    def group_value(self, dimension: str) -> str:
        return str(getattr(self, dimension))


def _label(meta: Mapping[str, Any], key: str) -> str:
    value = meta.get(key)
    return value if isinstance(value, str) and value else "unknown"


def _baselines(meta: Mapping[str, Any], category: str) -> dict[str, dict[str, Any]]:
    raw = as_object(meta.get("baselines") or {})
    if raw is None:
        raise MetaError("'baselines' must be an object")
    keys = list(HEADLINE_KEYS)
    keys += list(C2_HEADLINE_KEYS) if category == "C2" else []
    keys += list(C4_HEADLINE_KEYS) if category == "C4" else []
    baselines: dict[str, dict[str, Any]] = {}
    for name, value in raw.items():
        metrics = as_object(value)
        if metrics is None:
            raise MetaError(f"baselines.{name} must be an object")
        baselines[name] = {k: metrics.get(k) for k in keys if k in metrics}
    return baselines


def task_info_from_meta(meta: Mapping[str, Any], expected_task_id: str) -> TaskInfo:
    """Validate the non-answer part of a meta file and return its answer-free summary."""
    task_id = meta.get("task_id")
    if task_id != expected_task_id:
        raise MetaError(f"task_id {task_id!r} does not match the file name {expected_task_id!r}")
    if not isinstance(task_id, str) or not _TASK_ID.match(task_id):
        raise MetaError(f"task_id {task_id!r} is not a safe identifier")
    groups = field_groups(meta)  # validates category and field specs, reads no answer values
    excerpt_derivable = meta.get("excerpt_derivable")
    if not isinstance(excerpt_derivable, bool):
        raise MetaError("'excerpt_derivable' must be a boolean")
    specs = [spec for group in groups.values() for spec in group.values()]
    category: str = meta["category"]
    return TaskInfo(
        task_id=task_id,
        category=category,
        excerpt_derivable=excerpt_derivable,
        asset_class=_label(meta, "asset_class"),
        family=_label(meta, "family"),
        deal=_label(meta, "deal"),
        window_tag=_label(meta, "window_tag"),
        continuity_pending=bool(meta.get("continuity_pending", False)),
        n_fields=len(specs),
        n_nontrivial_fields=sum(1 for spec in specs if not spec.trivial),
        baselines=_baselines(meta, category),
    )


def _read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def load_task_infos(root: Path) -> tuple[dict[str, TaskInfo], list[str]]:
    """Every valid task under ``root``, plus a list of problems for the ones skipped.

    A missing ``meta/`` directory means the pipeline has produced nothing yet: zero tasks.
    """
    infos: dict[str, TaskInfo] = {}
    problems: list[str] = []
    meta_dir = root / "meta"
    if not meta_dir.is_dir():
        return infos, problems
    for path in sorted(meta_dir.glob("*.json")):
        try:
            meta = as_object(_read_json(path))
            if meta is None:
                raise MetaError("meta file must hold a JSON object")
            info = task_info_from_meta(meta, path.stem)
            task_dir = root / "tasks" / info.task_id
            for required in ("instructions.md", "answer_schema.json"):
                if not (task_dir / required).is_file():
                    raise MetaError(f"tasks/{info.task_id}/{required} is missing")
        except (OSError, ValueError) as exc:  # MetaError and JSONDecodeError are ValueErrors
            problems.append(f"{path.name}: {exc}")
            continue
        infos[info.task_id] = info
    return infos, problems


def build_datasets(infos: Mapping[str, TaskInfo]) -> dict[str, dict[str, TaskInfo]]:
    datasets: dict[str, dict[str, TaskInfo]] = {}
    for name, variant in VARIANTS.items():
        datasets[name] = {
            task_id: info
            for task_id, info in sorted(infos.items())
            if info.excerpt_derivable or not variant.excerpt_only
        }
    datasets["default"] = datasets[DEFAULT_DATASET]
    return datasets


# --------------------------------------------------------------------------- sandbox inputs


def _safe_source(path: Path, task_dir: Path, meta_dir: Path) -> Path:
    """Refuse anything that resolves outside the task folder or into meta/ (e.g. via symlinks)."""
    real = path.resolve()
    if not real.is_relative_to(task_dir.resolve()) or real.is_relative_to(meta_dir.resolve()):
        raise PermissionError(f"Refusing to upload {path}: it resolves outside the task folder")
    if not real.is_file():
        raise FileNotFoundError(f"{path} is not a regular file")
    return real


def workspace_files(root: Path, task_id: str, variant: Variant) -> list[tuple[str, Path]]:
    """(sandbox path, local path) pairs that ``setup_task`` uploads for one task and variant.

    Only the variant's documents, the reports in the variant's format, and the answer
    schema. Nothing under ``meta/`` is ever selected.
    """
    if not _TASK_ID.match(task_id):
        raise ValueError(f"Unsafe task id {task_id!r}")
    task_dir = root / "tasks" / task_id
    meta_dir = root / "meta"

    def pick(directory: Path, remote_dir: str) -> list[tuple[str, Path]]:
        if not directory.is_dir():
            return []
        chosen: list[tuple[str, Path]] = []
        for path in sorted(directory.iterdir()):
            if path.name.startswith(".") or path.suffix.lower() != variant.extension or path.is_dir():
                continue
            chosen.append((f"{remote_dir}/{path.name}", _safe_source(path, task_dir, meta_dir)))
        return chosen

    docs = pick(task_dir / "docs" / variant.docs_subdir, DOCS_DIR)
    reports = pick(task_dir / "reports", REPORTS_DIR)
    if not docs:
        raise FileNotFoundError(f"No {variant.extension} files in tasks/{task_id}/docs/{variant.docs_subdir}/")
    if not reports:
        raise FileNotFoundError(f"No {variant.extension} files in tasks/{task_id}/reports/")
    schema = _safe_source(task_dir / "answer_schema.json", task_dir, meta_dir)
    return [*docs, *reports, (SCHEMA_PATH, schema)]


def read_instructions(root: Path, task_id: str) -> str:
    task_dir = root / "tasks" / task_id
    return _safe_source(task_dir / "instructions.md", task_dir, root / "meta").read_text(encoding="utf-8")


def problem_statement(instructions: str, variant: Variant, uploads: list[tuple[str, Path]]) -> str:
    """The task's instructions plus a listing of the files this variant provides."""
    listing = "\n".join(f"- {remote}" for remote, _ in uploads)
    return (
        f"{instructions.rstrip()}\n\n"
        "---\n\n"
        f"## Files in this sandbox ({variant.name})\n\n"
        f"{listing}\n\n"
        f"Write your answer as JSON to {ANSWER_PATH}, in the shape described by {SCHEMA_PATH}.\n"
    )


# --------------------------------------------------------------------------- answer key


def read_answer_key_meta(root: Path, task_id: str) -> dict[str, Any]:
    """Read the PRIVATE meta (with the answer key) for one task. Only evaluate_instance calls this."""
    if not _TASK_ID.match(task_id):
        raise ValueError(f"Unsafe task id {task_id!r}")
    meta = as_object(_read_json(root / "meta" / f"{task_id}.json"))
    if meta is None or meta.get("task_id") != task_id:
        raise MetaError(f"meta/{task_id}.json does not describe task {task_id}")
    return dict(meta)


def validate_data_root(root: Path) -> list[str]:
    """Operator check for the pipeline hand-off: every problem a run would hit, as text."""
    infos, problems = load_task_infos(root)
    for task_id, info in infos.items():
        try:
            parse_answer_key(read_answer_key_meta(root, task_id))
        except (OSError, ValueError) as exc:
            problems.append(f"{task_id}: answer key: {exc}")
        for variant in VARIANTS.values():
            if variant.excerpt_only and not info.excerpt_derivable:
                continue
            try:
                workspace_files(root, task_id, variant)
            except OSError as exc:
                problems.append(f"{task_id} [{variant.name}]: {exc}")
    return problems
