"""Pure grading logic for WaterfallBench-Pilot.

Nothing here touches a sandbox, the network, or the filesystem: every function takes the
task's private meta (answer key) and the agent's answer as arguments. ``benchmark_service.py``
reads the answer key from disk only inside ``evaluate_instance`` and passes it here.

The pipeline computes ``meta["baselines"]`` with :func:`grade_submission` and
:func:`headline_metrics`, so baseline numbers and run numbers come from the same code.
"""

from __future__ import annotations

import json
import math
import re
from collections.abc import Mapping
from dataclasses import dataclass
from decimal import Decimal, InvalidOperation
from typing import Any, cast

CATEGORY_NAMES: dict[str, str] = {
    "C1": "monthly_distribution",
    "C2": "rollforward_4p",
    "C3": "stress_events",
    "C4": "amendment_audit",
    "C5": "master_trust_allocation",
}
FIELD_TYPES = frozenset({"money_cents", "status", "int", "decimal"})
MONEY_TOLERANCE_CENTS = 100
MAX_ANSWER_BYTES = 5 * 1024 * 1024
_PERIOD_KEY = re.compile(r"^period_([1-9][0-9]*)$")

# Keys a baseline entry in meta and a per-task result share; calculate_final_score
# aggregates these, so the pipeline must record at least these for every baseline.
HEADLINE_KEYS: tuple[str, ...] = (
    "fully_resolved",
    "line_item_accuracy",
    "nontrivial_accuracy",
    "tolerance_accuracy",
)
C2_HEADLINE_KEYS: tuple[str, ...] = ("consecutive_periods_correct",)
C4_HEADLINE_KEYS: tuple[str, ...] = ("precision", "recall", "f1", "value_accuracy")


def as_object(value: object) -> Mapping[str, Any] | None:
    """``value`` as a string-keyed mapping when it is one (parsed JSON objects always are)."""
    return cast("Mapping[str, Any]", value) if isinstance(value, Mapping) else None


def as_list(value: object) -> list[Any] | None:
    return cast("list[Any]", value) if isinstance(value, list) else None


class MetaError(ValueError):
    """The private meta / answer key does not follow the data contract."""


@dataclass(frozen=True)
class FieldSpec:
    type: str
    trivial: bool = False
    enum: tuple[str, ...] | None = None


@dataclass(frozen=True)
class AnswerKey:
    """A validated answer key. Never serialised into results or uploaded anywhere."""

    category: str
    # C2: {"period_1": {...}, ...}; every other category: {"": {...}} (one unnamed group).
    groups: dict[str, dict[str, FieldSpec]]
    # C1/C2/C3/C5: expected value per group and field; C4: misstated field -> correct value.
    expected: dict[str, dict[str, Any]]


# --------------------------------------------------------------------------- meta parsing


def _field_specs(raw: Any, where: str) -> dict[str, FieldSpec]:
    fields = as_object(raw)
    if not fields:
        raise MetaError(f"{where}: 'fields' must be a non-empty object")
    specs: dict[str, FieldSpec] = {}
    for name, value in fields.items():
        spec = as_object(value)
        if not name:
            raise MetaError(f"{where}: field names must be non-empty strings")
        if spec is None or spec.get("type") not in FIELD_TYPES:
            raise MetaError(f"{where}.{name}: 'type' must be one of {sorted(FIELD_TYPES)}")
        enum = as_list(spec.get("enum")) if spec.get("enum") is not None else None
        if spec.get("enum") is not None and (enum is None or not all(isinstance(v, str) for v in enum)):
            raise MetaError(f"{where}.{name}: 'enum' must be a list of strings")
        trivial = spec.get("trivial", False)
        if not isinstance(trivial, bool):
            raise MetaError(f"{where}.{name}: 'trivial' must be a boolean")
        specs[name] = FieldSpec(type=spec["type"], trivial=trivial, enum=tuple(enum) if enum is not None else None)
    return specs


def period_keys(keys: Any) -> list[str]:
    """C2 period keys sorted by number; they must be period_1..period_N with no gaps."""
    numbered: list[tuple[int, str]] = []
    for key in keys:
        match = _PERIOD_KEY.match(key) if isinstance(key, str) else None
        if match is None:
            raise MetaError(f"C2 period key {key!r} is not of the form period_<n>")
        numbered.append((int(match.group(1)), key))
    numbered.sort()
    if not numbered or [n for n, _ in numbered] != list(range(1, len(numbered) + 1)):
        raise MetaError("C2 periods must be period_1..period_N with no gaps")
    return [key for _, key in numbered]


def field_groups(meta: Mapping[str, Any]) -> dict[str, dict[str, FieldSpec]]:
    """Validate ``meta['category']`` and ``meta['fields']``; no answer values are read."""
    category = meta.get("category")
    if category not in CATEGORY_NAMES:
        raise MetaError(f"'category' must be one of {sorted(CATEGORY_NAMES)}, got {category!r}")
    fields = meta.get("fields")
    if category == "C2":
        if not isinstance(fields, Mapping):
            raise MetaError("C2 'fields' must be an object keyed by period")
        return {period: _field_specs(fields[period], f"fields.{period}") for period in period_keys(fields.keys())}
    return {"": _field_specs(fields, "fields")}


def _check_expected(spec: FieldSpec, value: Any, where: str) -> None:
    ok = {
        "money_cents": _as_exact_int(value) is not None,
        "int": _as_exact_int(value) is not None,
        "status": isinstance(value, str),
        "decimal": _as_decimal(value) is not None,
    }[spec.type]
    if not ok:
        raise MetaError(f"{where}: expected value is not a valid {spec.type}")


def parse_answer_key(meta: Mapping[str, Any]) -> AnswerKey:
    """Validate the whole answer key (fields + answer). Raises MetaError on contract violations."""
    groups = field_groups(meta)
    category: str = meta["category"]
    answer = as_object(meta.get("answer"))
    if answer is None:
        raise MetaError("'answer' must be an object")

    if category == "C4":
        specs = groups[""]
        corrections = as_list(answer.get("corrections"))
        if corrections is None:
            raise MetaError("C4 'answer.corrections' must be a list")
        expected: dict[str, Any] = {}
        for i, item in enumerate(corrections):
            where = f"answer.corrections[{i}]"
            entry = as_object(item)
            if entry is None or "correct_value" not in entry:
                raise MetaError(f"{where}: needs 'field' and 'correct_value'")
            name = entry.get("field")
            if not isinstance(name, str) or name not in specs:
                raise MetaError(f"{where}: field {name!r} is not listed in 'fields'")
            if name in expected:
                raise MetaError(f"{where}: field {name!r} is listed twice")
            _check_expected(specs[name], entry["correct_value"], where)
            expected[name] = entry["correct_value"]
        return AnswerKey(category=category, groups=groups, expected={"": expected})

    expected_groups: dict[str, dict[str, Any]] = {}
    for group, specs in groups.items():
        values = answer if group == "" else as_object(answer.get(group))
        if values is None:
            raise MetaError(f"answer.{group}: must be an object")
        if set(values) != set(specs):
            raise MetaError(f"answer{'.' + group if group else ''}: keys must match 'fields' exactly")
        for name, spec in specs.items():
            _check_expected(spec, values[name], f"answer.{group + '.' if group else ''}{name}")
        expected_groups[group] = dict(values)
    if category == "C2" and set(answer) != set(groups):
        raise MetaError("C2 'answer' periods must match 'fields' periods")
    return AnswerKey(category=category, groups=groups, expected=expected_groups)


# --------------------------------------------------------------------------- value comparison


def _as_exact_int(value: Any) -> int | None:
    """JSON ints, or floats that are exactly integral. Booleans and strings are not numbers."""
    if isinstance(value, bool):
        return None
    if isinstance(value, int):
        return value
    if isinstance(value, float) and math.isfinite(value) and value.is_integer():
        return int(value)
    return None


def _as_decimal(value: Any) -> Decimal | None:
    """``Decimal(str(value))`` for finite numbers and numeric strings; None otherwise."""
    if isinstance(value, bool) or not isinstance(value, (int, float, str)):
        return None
    try:
        number = Decimal(str(value))
    except InvalidOperation:
        return None
    return number if number.is_finite() else None


def value_correct(spec: FieldSpec, expected: Any, submitted: Any) -> bool:
    if spec.type in ("money_cents", "int"):
        got, want = _as_exact_int(submitted), _as_exact_int(expected)
        return got is not None and want is not None and got == want
    if spec.type == "status":
        return isinstance(submitted, str) and isinstance(expected, str) and submitted == expected
    if spec.type == "decimal":
        got_d, want_d = _as_decimal(submitted), _as_decimal(expected)
        return got_d is not None and want_d is not None and got_d == want_d
    raise MetaError(f"unknown field type {spec.type!r}")


def value_within_tolerance(spec: FieldSpec, expected: Any, submitted: Any) -> bool:
    """Money fields pass within ±$1 (100 cents) of the answer; other types must be exact."""
    if spec.type != "money_cents":
        return value_correct(spec, expected, submitted)
    if isinstance(submitted, bool) or not isinstance(submitted, (int, float)):
        return False
    if isinstance(submitted, float) and not math.isfinite(submitted):
        return False
    want = _as_exact_int(expected)
    return want is not None and abs(Decimal(str(submitted)) - want) <= MONEY_TOLERANCE_CENTS


# --------------------------------------------------------------------------- answer parsing


class AnswerError(ValueError):
    def __init__(self, status: str, message: str) -> None:
        self.status = status
        super().__init__(message)


def _reject_constant(name: str) -> Any:
    raise ValueError(f"non-standard JSON constant {name}")


def parse_answer(raw: bytes | None, size: int | None = None) -> dict[str, Any]:
    """Parse ``/workspace/answer.json``. Raises AnswerError('missing'|'malformed', reason).

    ``size`` is the file size the sandbox reported, so an oversized file is rejected
    without downloading it (``raw`` is then None).
    """
    size = len(raw) if raw is not None else size
    if size is not None and size > MAX_ANSWER_BYTES:
        raise AnswerError("malformed", f"answer.json is {size} bytes, over the {MAX_ANSWER_BYTES}-byte limit")
    if raw is None:
        raise AnswerError("missing", "/workspace/answer.json was not found")
    try:
        parsed = json.loads(raw.decode("utf-8-sig"), parse_constant=_reject_constant)
    except (UnicodeDecodeError, ValueError, RecursionError) as exc:
        raise AnswerError("malformed", f"answer.json is not valid JSON: {exc}") from None
    answer = as_object(parsed)
    if answer is None:
        raise AnswerError("malformed", f"answer.json must be a JSON object, got {type(parsed).__name__}")
    return dict(answer)


# --------------------------------------------------------------------------- grading


def _field_result(correct: bool, within_tolerance: bool, trivial: bool, answered: bool) -> dict[str, bool]:
    return {"correct": correct, "within_tolerance": within_tolerance, "trivial": trivial, "answered": answered}


def _qualified(group: str, name: str) -> str:
    return f"{group}.{name}" if group else name


def _accuracy_block(per_field: Mapping[str, Mapping[str, bool]]) -> dict[str, Any]:
    n = len(per_field)
    correct = sum(1 for r in per_field.values() if r["correct"])
    tolerant = sum(1 for r in per_field.values() if r["within_tolerance"])
    nontrivial = [r for r in per_field.values() if not r["trivial"]]
    nontrivial_correct = sum(1 for r in nontrivial if r["correct"])
    return {
        "n_fields": n,
        "n_correct": correct,
        "line_item_accuracy": correct / n if n else 0.0,
        "n_nontrivial_fields": len(nontrivial),
        "n_nontrivial_correct": nontrivial_correct,
        "nontrivial_accuracy": nontrivial_correct / len(nontrivial) if nontrivial else None,
        "n_within_tolerance": tolerant,
        "tolerance_accuracy": tolerant / n if n else 0.0,
    }


def _grade_fields(key: AnswerKey, submission: Mapping[str, Any]) -> tuple[dict[str, dict[str, bool]], dict[str, Any]]:
    per_field: dict[str, dict[str, bool]] = {}
    for group, specs in key.groups.items():
        values = (submission if group == "" else as_object(submission.get(group))) or {}
        for name, spec in specs.items():
            expected = key.expected[group][name]
            answered = name in values
            got = values.get(name)
            per_field[_qualified(group, name)] = _field_result(
                correct=answered and value_correct(spec, expected, got),
                within_tolerance=answered and value_within_tolerance(spec, expected, got),
                trivial=spec.trivial,
                answered=answered,
            )
    extra: dict[str, Any] = {}
    if key.category == "C2":
        periods = list(key.groups)
        full = {p: all(per_field[_qualified(p, f)]["correct"] for f in key.groups[p]) for p in periods}
        extra["n_periods"] = len(periods)
        extra["periods_fully_correct"] = full
        extra["consecutive_periods_correct"] = consecutive_correct([full[p] for p in periods])
    return per_field, extra


def consecutive_correct(period_flags: list[bool]) -> int:
    """Length of the run of fully-correct periods starting at period_1."""
    run = 0
    for ok in period_flags:
        if not ok:
            break
        run += 1
    return run


def prf(n_true_positive: int, n_predicted: int, n_actual: int) -> tuple[float, float, float]:
    """Precision, recall, F1 for set prediction.

    Conventions: nothing predicted and nothing to find is perfect (1, 1, 1); an empty
    prediction against a non-empty truth, or any prediction against an empty truth, is 0.
    """
    if n_predicted == 0 and n_actual == 0:
        return 1.0, 1.0, 1.0
    precision = n_true_positive / n_predicted if n_predicted else 0.0
    recall = n_true_positive / n_actual if n_actual else 0.0
    f1 = 2 * precision * recall / (precision + recall) if precision + recall else 0.0
    return precision, recall, f1


def _grade_c4(key: AnswerKey, submission: Mapping[str, Any]) -> tuple[dict[str, dict[str, bool]], dict[str, Any]]:
    corrections = as_list(submission.get("corrections"))
    if corrections is None:
        raise AnswerError("malformed", "C4 answer must be an object with a 'corrections' list")
    specs = key.groups[""]
    truth = key.expected[""]

    claims: dict[str, list[Any]] = {}
    invalid_entries = 0
    for item in corrections:
        entry = as_object(item)
        name = entry.get("field") if entry is not None else None
        if entry is None or not isinstance(name, str) or "correct_value" not in entry:
            invalid_entries += 1  # an entry the grader cannot read is a wrong claim
            continue
        claims.setdefault(name, []).append(entry["correct_value"])

    predicted = set(claims)
    true_positive = predicted & truth.keys()
    false_positive = predicted - truth.keys()  # includes field names not in the report
    false_negative = truth.keys() - predicted
    # A field claimed more than once counts as right only if every claimed value is right.
    exact = {f: all(value_correct(specs[f], truth[f], v) for v in claims[f]) for f in true_positive}
    tolerant = {f: all(value_within_tolerance(specs[f], truth[f], v) for v in claims[f]) for f in true_positive}

    per_field: dict[str, dict[str, bool]] = {}
    for name, spec in specs.items():
        flagged = name in claims
        if name in truth:  # misstated: must be flagged with the correct value
            per_field[name] = _field_result(flagged and exact[name], flagged and tolerant[name], spec.trivial, flagged)
        else:  # asserted correct: must not be flagged
            per_field[name] = _field_result(not flagged, not flagged, spec.trivial, flagged)

    n_predicted = len(predicted) + invalid_entries
    precision, recall, f1 = prf(len(true_positive), n_predicted, len(truth))
    n_value_correct = sum(1 for ok in exact.values() if ok)
    extra = {
        "precision": precision,
        "recall": recall,
        "f1": f1,
        "n_predicted": n_predicted,
        "n_misstated": len(truth),
        "n_true_positive": len(true_positive),
        "n_false_positive": len(false_positive) + invalid_entries,
        "n_false_negative": len(false_negative),
        "unknown_fields": sorted(predicted - specs.keys()),
        "invalid_entries": invalid_entries,
        "n_value_correct": n_value_correct,
        "value_accuracy": n_value_correct / len(true_positive) if true_positive else None,
        "set_match": predicted == truth.keys() and invalid_entries == 0,
    }
    return per_field, extra


CLASS_FIELDS: tuple[str, ...] = ("interest_paid", "principal_paid", "ending_balance")


def class_token(name: Any) -> str | None:
    """'Class A-2a Notes', 'A-2A' and 'a2a' all become 'a2a' (how a listed class is matched to the answer key)."""
    if not isinstance(name, str):
        return None
    t = name.lower()
    for word in ("classes", "class", "notes", "note"):
        t = t.replace(word, "")
    t = re.sub(r"[^a-z0-9]", "", t)
    return t or None


def flatten_classes(specs: Mapping[str, FieldSpec], submission: Mapping[str, Any]) -> dict[str, Any]:
    """A fixed-schema answer {..., "classes": [{"class": "A-1", "interest_paid": ..}, ..]} as the answer key's flat
    ``<CLASS>.<field>`` keys. Classes match by name ignoring case, spaces, hyphens and the words class/notes; a class
    listed more than once is ambiguous and counts as unanswered; classes the deal does not have are ignored."""
    flat = {k: v for k, v in submission.items() if k != "classes"}
    want = {class_token(n.split(".", 1)[0]): n.split(".", 1)[0] for n in specs if "." in n}
    listed: dict[str, list[Mapping[str, Any]]] = {}
    for item in as_list(submission.get("classes")) or []:
        row = as_object(item)
        token = class_token(row.get("class")) if row is not None else None
        if row is not None and token in want:
            listed.setdefault(token, []).append(row)
    for token, rows in listed.items():
        if len(rows) == 1:
            for field in CLASS_FIELDS:
                if field in rows[0]:
                    flat[f"{want[token]}.{field}"] = rows[0][field]
    return flat


def task_labels(meta: Mapping[str, Any]) -> dict[str, Any]:
    """Non-secret descriptive metadata copied into every result."""
    category = meta.get("category")
    return {
        "task_id": meta.get("task_id"),
        "category": category,
        "category_name": CATEGORY_NAMES.get(category) if isinstance(category, str) else None,
        "asset_class": meta.get("asset_class"),
        "family": meta.get("family"),
        "deal": meta.get("deal"),
        "window_tag": meta.get("window_tag"),
        "continuity_pending": meta.get("continuity_pending"),
    }


def _zero_result(key: AnswerKey, status: str, error: str) -> dict[str, Any]:
    per_field = {
        _qualified(group, name): _field_result(False, False, spec.trivial, False)
        for group, specs in key.groups.items()
        for name, spec in specs.items()
    }
    result: dict[str, Any] = {"answer_status": status, "error": error, "fields": per_field}
    result.update(_accuracy_block(per_field))
    result["fully_resolved"] = False
    if key.category == "C2":
        result["n_periods"] = len(key.groups)
        result["periods_fully_correct"] = {p: False for p in key.groups}
        result["consecutive_periods_correct"] = 0
    if key.category == "C4":
        n_true = len(key.expected[""])
        result.update(
            {
                "precision": 0.0,
                "recall": 0.0,
                "f1": 0.0,
                "n_predicted": 0,
                "n_misstated": n_true,
                "n_true_positive": 0,
                "n_false_positive": 0,
                "n_false_negative": n_true,
                "unknown_fields": [],
                "invalid_entries": 0,
                "n_value_correct": 0,
                "value_accuracy": None,
                "set_match": False,
            }
        )
    return result


def grade_submission(meta: Mapping[str, Any], submission: Any) -> dict[str, Any]:
    """Grade an already-parsed answer object against the private meta."""
    key = parse_answer_key(meta)
    labels = task_labels(meta)
    answer = as_object(submission)
    if answer is None:
        return {**labels, **_zero_result(key, "malformed", "answer must be a JSON object")}
    if meta.get("answer_format") == "classes_array":
        answer = flatten_classes(key.groups[""], answer)
    try:
        if key.category == "C4":
            per_field, extra = _grade_c4(key, answer)
            fully_resolved = bool(extra["set_match"]) and extra["n_value_correct"] == extra["n_true_positive"]
        else:
            per_field, extra = _grade_fields(key, answer)
            fully_resolved = all(r["correct"] for r in per_field.values())
    except AnswerError as exc:
        return {**labels, **_zero_result(key, exc.status, str(exc))}
    result: dict[str, Any] = {**labels, "answer_status": "ok", "error": None, "fields": per_field}
    result.update(_accuracy_block(per_field))
    result["fully_resolved"] = fully_resolved
    result.update(extra)
    return result


def grade_answer(meta: Mapping[str, Any], raw: bytes | None, size: int | None = None) -> dict[str, Any]:
    """Grade the raw bytes of /workspace/answer.json (None when absent or not downloaded)."""
    key = parse_answer_key(meta)  # a broken answer key is a service error, not a zero
    try:
        submission = parse_answer(raw, size)
    except AnswerError as exc:
        return {**task_labels(meta), **_zero_result(key, exc.status, str(exc))}
    return grade_submission(meta, submission)


def headline_metrics(result: Mapping[str, Any]) -> dict[str, Any]:
    """The subset of a result that baselines record and the final score aggregates."""
    keys = list(HEADLINE_KEYS)
    if result.get("category") == "C2":
        keys += C2_HEADLINE_KEYS
    if result.get("category") == "C4":
        keys += C4_HEADLINE_KEYS
    return {k: result.get(k) for k in keys}
