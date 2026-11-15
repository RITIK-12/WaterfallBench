"""Grader unit tests on the FABRICATED fixture metas; no sandbox, no network."""

import copy
import json
import math
from collections.abc import Callable
from typing import Any

import pytest

from waterfallbench_benchmark_service.grading import (
    MAX_ANSWER_BYTES,
    MetaError,
    consecutive_correct,
    grade_answer,
    grade_submission,
    headline_metrics,
    parse_answer_key,
    prf,
)

from .conftest import C1, C2, C4, fixture_meta


def as_bytes(obj: Any) -> bytes:
    return json.dumps(obj).encode()


def assert_metrics_equal(got: dict[str, Any], want: dict[str, Any]) -> None:
    assert set(got) == set(want), (got, want)
    for key, value in want.items():
        if isinstance(value, float):
            assert got[key] is not None and math.isclose(got[key], value, rel_tol=0, abs_tol=1e-12), (key, got, want)
        else:
            assert got[key] == value, (key, got, want)


# --------------------------------------------------------------------------- answer keys score 100%


@pytest.mark.parametrize("task_id", [C1, C2, C4])
def test_answer_key_is_fully_resolved(task_id: str) -> None:
    meta = fixture_meta(task_id)
    result = grade_answer(meta, as_bytes(meta["answer"]))
    assert result["answer_status"] == "ok" and result["error"] is None
    assert result["fully_resolved"] is True
    assert result["line_item_accuracy"] == 1.0
    assert result["nontrivial_accuracy"] == 1.0
    assert result["tolerance_accuracy"] == 1.0
    assert all(f["correct"] for f in result["fields"].values())
    assert result["category"] == meta["category"] and result["family"] == meta["family"]
    assert result["window_tag"] == meta["window_tag"] and result["continuity_pending"] == meta["continuity_pending"]
    if task_id == C2:
        assert result["consecutive_periods_correct"] == 4
        assert result["n_fields"] == 12
    if task_id == C4:
        assert (result["precision"], result["recall"], result["f1"], result["value_accuracy"]) == (1.0, 1.0, 1.0, 1.0)


@pytest.mark.parametrize("task_id", [C1, C2, C4])
def test_results_never_contain_answer_values(task_id: str) -> None:
    meta = fixture_meta(task_id)
    text = json.dumps(grade_answer(meta, as_bytes(meta["answer"])))
    for needle in ("1234567", "987654", "0.0012340", "45678", "0.1792480", "48000000"):
        assert needle not in text


# --------------------------------------------------------------------------- baselines


def copy_prior_answer(task_id: str) -> dict[str, Any]:
    if task_id == C1:  # the opening-state report's values carried forward
        return {
            "available_funds": 1200000,
            "servicing_fee": 10050,  # 50 cents off: within ±$1
            "class_a2_principal": 990000,
            "reserve_account_balance": 500000,
            "cumulative_net_loss_ratio": "0.0011000",
            "cnl_trigger_status": "pass",
            "delinquent_60_plus_count": 40,
        }
    if task_id == C2:  # each period repeats the previous period (period_1 the opening state)
        answer = fixture_meta(C2)["answer"]
        opening = {"available_funds": 1980000, "note_balance_end": 52000000, "trigger_status": "pass"}
        return {
            "period_1": opening,
            "period_2": answer["period_1"],
            "period_3": answer["period_2"],
            "period_4": answer["period_3"],
        }
    return {"corrections": []}  # C4: assert the report is right everywhere


def all_zeros_answer(task_id: str) -> dict[str, Any]:
    meta = fixture_meta(task_id)

    def zero(spec: dict[str, Any]) -> Any:
        return "" if spec["type"] == "status" else 0

    if task_id == C2:
        return {p: {f: zero(s) for f, s in fields.items()} for p, fields in meta["fields"].items()}
    if task_id == C4:
        return {"corrections": [{"field": f, "correct_value": zero(s)} for f, s in meta["fields"].items()]}
    return {f: zero(s) for f, s in meta["fields"].items()}


@pytest.mark.parametrize("task_id", [C1, C2, C4])
@pytest.mark.parametrize("baseline", ["copy_prior", "all_zeros"])
def test_recomputed_baselines_match_meta(task_id: str, baseline: str) -> None:
    meta = fixture_meta(task_id)
    answer = copy_prior_answer(task_id) if baseline == "copy_prior" else all_zeros_answer(task_id)
    result = grade_answer(meta, as_bytes(answer))
    assert result["answer_status"] == "ok"
    assert_metrics_equal(headline_metrics(result), meta["baselines"][baseline])


def test_c1_copy_prior_details() -> None:
    result = grade_submission(fixture_meta(C1), copy_prior_answer(C1))
    fields = result["fields"]
    assert fields["servicing_fee"] == {"correct": False, "within_tolerance": True, "trivial": True, "answered": True}
    assert fields["reserve_account_balance"]["correct"] is True
    assert (result["n_correct"], result["n_within_tolerance"], result["n_nontrivial_correct"]) == (2, 3, 0)


# --------------------------------------------------------------------------- value comparison


def c1_with(**overrides: Any) -> dict[str, Any]:
    answer = dict(fixture_meta(C1)["answer"])
    answer.update(overrides)
    return grade_submission(fixture_meta(C1), answer)["fields"]


def test_money_accepts_ints_and_integral_floats_only() -> None:
    assert c1_with(available_funds=1234567.0)["available_funds"]["correct"] is True
    assert c1_with(available_funds="1234567")["available_funds"]["correct"] is False
    assert c1_with(available_funds=1234567.5)["available_funds"]["correct"] is False
    assert c1_with(available_funds=True)["available_funds"]["correct"] is False
    assert c1_with(available_funds=None)["available_funds"]["correct"] is False


def test_money_tolerance_is_one_dollar() -> None:
    near = c1_with(available_funds=1234667)["available_funds"]
    assert near == {"correct": False, "within_tolerance": True, "trivial": False, "answered": True}
    assert c1_with(available_funds=1234467.0)["available_funds"]["within_tolerance"] is True
    assert c1_with(available_funds=1234668)["available_funds"]["within_tolerance"] is False
    assert c1_with(available_funds="1234567")["available_funds"]["within_tolerance"] is False


def test_decimal_compares_numerically() -> None:
    assert c1_with(cumulative_net_loss_ratio=0.001234)["cumulative_net_loss_ratio"]["correct"] is True
    assert c1_with(cumulative_net_loss_ratio="0.001234")["cumulative_net_loss_ratio"]["correct"] is True
    assert c1_with(cumulative_net_loss_ratio=0.0012341)["cumulative_net_loss_ratio"]["correct"] is False
    assert c1_with(cumulative_net_loss_ratio="sNaN")["cumulative_net_loss_ratio"]["correct"] is False
    assert c1_with(cumulative_net_loss_ratio=[0.001234])["cumulative_net_loss_ratio"]["correct"] is False


def test_status_and_int_are_exact() -> None:
    assert c1_with(cnl_trigger_status="Pass")["cnl_trigger_status"]["correct"] is False
    assert c1_with(cnl_trigger_status=" pass")["cnl_trigger_status"]["correct"] is False
    assert c1_with(delinquent_60_plus_count=42.0)["delinquent_60_plus_count"]["correct"] is True
    assert c1_with(delinquent_60_plus_count="42")["delinquent_60_plus_count"]["correct"] is False
    assert c1_with(delinquent_60_plus_count=43)["delinquent_60_plus_count"]["within_tolerance"] is False


def test_missing_field_and_extra_fields() -> None:
    answer = dict(fixture_meta(C1)["answer"])
    del answer["servicing_fee"]
    answer["not_a_field"] = 1
    result = grade_submission(fixture_meta(C1), answer)
    assert result["fields"]["servicing_fee"] == {
        "correct": False,
        "within_tolerance": False,
        "trivial": True,
        "answered": False,
    }
    assert "not_a_field" not in result["fields"]
    assert result["fully_resolved"] is False and result["n_correct"] == 6


# --------------------------------------------------------------------------- missing / malformed


@pytest.mark.parametrize("task_id", [C1, C2, C4])
def test_missing_answer_scores_zero(task_id: str) -> None:
    result = grade_answer(fixture_meta(task_id), None)
    assert result["answer_status"] == "missing"
    assert "not found" in result["error"]
    assert result["fully_resolved"] is False
    assert result["line_item_accuracy"] == 0.0 and result["tolerance_accuracy"] == 0.0
    assert result["nontrivial_accuracy"] == 0.0
    assert not any(f["correct"] for f in result["fields"].values())


@pytest.mark.parametrize(
    "raw",
    [b"", b"{not json", b"[1, 2]", b'"answer"', b"NaN", b'{"available_funds": NaN}', b"\xff\xfe", b"[" * 100000],
)
@pytest.mark.parametrize("task_id", [C1, C2, C4])
def test_malformed_answer_scores_zero(task_id: str, raw: bytes) -> None:
    result = grade_answer(fixture_meta(task_id), raw)
    assert result["answer_status"] == "malformed"
    assert result["error"]
    assert result["fully_resolved"] is False and result["line_item_accuracy"] == 0.0


def test_oversized_answer_is_malformed_without_content() -> None:
    result = grade_answer(fixture_meta(C1), None, size=MAX_ANSWER_BYTES + 1)
    assert result["answer_status"] == "malformed" and "byte limit" in result["error"]


def test_c4_without_corrections_list_is_malformed() -> None:
    for answer in ({}, {"corrections": "class_b_interest"}, {"corrections": {"field": "x"}}):
        result = grade_submission(fixture_meta(C4), answer)
        assert result["answer_status"] == "malformed" and result["f1"] == 0.0


# --------------------------------------------------------------------------- C2 run length


def c2_answer_with_wrong_periods(*wrong: str) -> dict[str, Any]:
    answer = copy.deepcopy(fixture_meta(C2)["answer"])
    for period in wrong:
        answer[period]["available_funds"] += 1
    return answer


@pytest.mark.parametrize(
    ("wrong", "run_length"),
    [((), 4), (("period_4",), 3), (("period_3",), 2), (("period_2", "period_4"), 1), (("period_1",), 0)],
)
def test_c2_consecutive_periods(wrong: tuple[str, ...], run_length: int) -> None:
    result = grade_submission(fixture_meta(C2), c2_answer_with_wrong_periods(*wrong))
    assert result["consecutive_periods_correct"] == run_length
    assert result["periods_fully_correct"] == {f"period_{i}": f"period_{i}" not in wrong for i in range(1, 5)}
    assert result["fully_resolved"] is (not wrong)


def test_c2_missing_or_non_object_period() -> None:
    answer = copy.deepcopy(fixture_meta(C2)["answer"])
    del answer["period_1"]
    answer["period_3"] = [1, 2, 3]
    result = grade_submission(fixture_meta(C2), answer)
    assert result["consecutive_periods_correct"] == 0
    assert result["periods_fully_correct"] == {
        "period_1": False,
        "period_2": True,
        "period_3": False,
        "period_4": True,
    }
    assert result["n_correct"] == 6


def test_consecutive_correct_helper() -> None:
    assert consecutive_correct([]) == 0
    assert consecutive_correct([True, True, False, True]) == 2


# --------------------------------------------------------------------------- C4 precision / recall / F1


def c4_meta_with(corrections: list[dict[str, Any]]) -> dict[str, Any]:
    meta = fixture_meta(C4)
    meta["answer"] = {"corrections": corrections}
    return meta


def c4(meta: dict[str, Any], *claims: tuple[Any, Any]) -> dict[str, Any]:
    return grade_submission(meta, {"corrections": [{"field": f, "correct_value": v} for f, v in claims]})


def test_c4_nothing_misstated_nothing_flagged_is_perfect() -> None:
    result = c4(c4_meta_with([]))
    assert (result["precision"], result["recall"], result["f1"]) == (1.0, 1.0, 1.0)
    assert result["value_accuracy"] is None
    assert result["fully_resolved"] is True and result["line_item_accuracy"] == 1.0


def test_c4_flagging_when_nothing_misstated_scores_zero() -> None:
    result = c4(c4_meta_with([]), ("reserve_draw", 0))
    assert (result["precision"], result["recall"], result["f1"]) == (0.0, 0.0, 0.0)
    assert result["fully_resolved"] is False
    assert result["fields"]["reserve_draw"]["correct"] is False
    assert result["n_correct"] == 5


def test_c4_flagging_nothing_when_misstated_scores_zero() -> None:
    result = c4(fixture_meta(C4))
    assert (result["precision"], result["recall"], result["f1"]) == (0.0, 0.0, 0.0)
    assert result["n_false_negative"] == 2 and result["fully_resolved"] is False


def test_c4_unknown_field_is_a_false_positive() -> None:
    result = c4(
        fixture_meta(C4),
        ("class_b_interest", 45678),
        ("overcollateralization_pct", 0.179248),  # 0.179248 == "0.1792480"
        ("made_up_field", 5),
    )
    assert result["unknown_fields"] == ["made_up_field"]
    assert result["n_false_positive"] == 1
    assert result["precision"] == pytest.approx(2 / 3) and result["recall"] == 1.0
    assert result["f1"] == pytest.approx(0.8)
    assert result["value_accuracy"] == 1.0
    assert result["fully_resolved"] is False  # the set does not match exactly
    assert result["line_item_accuracy"] == 1.0  # every report field has the right verdict


def test_c4_right_field_wrong_value() -> None:
    result = c4(fixture_meta(C4), ("class_b_interest", 45679), ("overcollateralization_pct", "0.1792480"))
    assert (result["precision"], result["recall"], result["f1"]) == (1.0, 1.0, 1.0)
    assert result["value_accuracy"] == 0.5 and result["set_match"] is True
    assert result["fully_resolved"] is False
    assert result["fields"]["class_b_interest"] == {
        "correct": False,
        "within_tolerance": True,
        "trivial": False,
        "answered": True,
    }


def test_c4_partial_recall() -> None:
    result = c4(fixture_meta(C4), ("class_b_interest", 45678))
    assert (result["precision"], result["recall"]) == (1.0, 0.5)
    assert result["f1"] == pytest.approx(2 / 3)
    assert result["value_accuracy"] == 1.0 and result["fully_resolved"] is False


def test_c4_conflicting_duplicate_claims_are_wrong() -> None:
    result = c4(
        fixture_meta(C4),
        ("class_b_interest", 45678),
        ("class_b_interest", 99999),
        ("overcollateralization_pct", "0.1792480"),
    )
    assert result["precision"] == 1.0 and result["recall"] == 1.0
    assert result["value_accuracy"] == 0.5 and result["fully_resolved"] is False


def test_c4_unreadable_entries_count_as_false_positives() -> None:
    meta = fixture_meta(C4)
    answer = {
        "corrections": [
            {"field": "class_b_interest", "correct_value": 45678},
            {"field": "overcollateralization_pct", "correct_value": "0.1792480"},
            {"field": "reserve_draw"},  # no correct_value
            "class_a_interest",
        ]
    }
    result = grade_submission(meta, answer)
    assert result["invalid_entries"] == 2 and result["n_false_positive"] == 2
    assert result["precision"] == 0.5 and result["recall"] == 1.0
    assert result["fully_resolved"] is False


def test_prf_conventions() -> None:
    assert prf(0, 0, 0) == (1.0, 1.0, 1.0)
    assert prf(0, 3, 0) == (0.0, 0.0, 0.0)
    assert prf(0, 0, 3) == (0.0, 0.0, 0.0)
    assert prf(1, 2, 4) == (0.5, 0.25, pytest.approx(1 / 3))


# --------------------------------------------------------------------------- answer-key validation


BAD_C1_KEYS: list[Callable[[dict[str, Any]], object]] = [
    lambda m: m.update(category="C9"),
    lambda m: m.update(fields={}),
    lambda m: m["fields"]["available_funds"].update(type="currency"),
    lambda m: m["answer"].pop("servicing_fee"),
    lambda m: m["answer"].update(available_funds="12.34"),
    lambda m: m.update(answer=[]),
]


@pytest.mark.parametrize("mutate", BAD_C1_KEYS)
def test_bad_c1_answer_key_is_rejected(mutate: Callable[[dict[str, Any]], object]) -> None:
    meta = fixture_meta(C1)
    mutate(meta)
    with pytest.raises(MetaError):
        parse_answer_key(meta)


def test_bad_c2_and_c4_answer_keys_are_rejected() -> None:
    gap = fixture_meta(C2)
    gap["fields"]["period_5"] = gap["fields"].pop("period_4")
    gap["answer"]["period_5"] = gap["answer"].pop("period_4")
    with pytest.raises(MetaError, match="no gaps"):
        parse_answer_key(gap)
    unknown = c4_meta_with([{"field": "nope", "correct_value": 1}])
    with pytest.raises(MetaError, match="not listed"):
        parse_answer_key(unknown)
    twice = c4_meta_with([{"field": "reserve_draw", "correct_value": 1}] * 2)
    with pytest.raises(MetaError, match="twice"):
        parse_answer_key(twice)
