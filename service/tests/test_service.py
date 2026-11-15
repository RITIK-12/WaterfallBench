"""Service tests with a fake recording Sandbox and the FABRICATED fixture; no network, no models."""

import json
import os
import shutil
from pathlib import Path
from typing import Any

import pytest
from benchmark_service import DockerfileSource, ImageSource
from benchmark_service.schemas import EvaluateResponseRequest, StreamResultChunk
from fastapi.testclient import TestClient

from waterfallbench_benchmark_service.benchmark_service import WaterfallBench
from waterfallbench_benchmark_service.data import ANSWER_PATH, PROBLEM_PATH, VARIANTS, validate_data_root

from .conftest import C1, C2, C4, FIXTURE_ROOT, FakeSandbox, collect, fixture_meta, make_service, run

ALL_TASKS = {C1, C2, C4}
ANSWER_NEEDLES = (b"1234567", b"987654", b"0.0012340", b"45678", b"0.1792480", b"48000000", b'"answer"')


def result_of(chunks: list[Any]) -> Any:
    results = [c for c in chunks if isinstance(c, StreamResultChunk)]
    assert len(results) == 1
    return results[0].data


# --------------------------------------------------------------------------- datasets


def test_datasets_and_excerpt_filtering(service: WaterfallBench) -> None:
    assert set(service.datasets) == {"full-md", "full-pdf", "excerpt-md", "excerpt-pdf", "default"}
    assert set(service.get_dataset("full-md")) == ALL_TASKS
    assert set(service.get_dataset("full-pdf")) == ALL_TASKS
    assert set(service.get_dataset("excerpt-md")) == {C1, C4}  # C2 is not excerpt-derivable
    assert set(service.get_dataset("excerpt-pdf")) == {C1, C4}
    assert service.get_dataset(None) is service.get_dataset("full-md")


def test_dataset_entries_hold_no_answers(service: WaterfallBench) -> None:
    for tasks in service.datasets.values():
        for info in tasks.values():
            assert not hasattr(info, "answer") and not hasattr(info, "fields")
            assert set(info.baselines) == {"copy_prior", "all_zeros"}


@pytest.mark.parametrize("make_root", ["empty", "missing", "meta_only"])
def test_zero_tasks(monkeypatch: pytest.MonkeyPatch, tmp_path: Path, make_root: str) -> None:
    root = tmp_path / "data"
    if make_root != "missing":
        root.mkdir()
    if make_root == "meta_only":
        (root / "meta").mkdir()
    monkeypatch.setenv("WFB_DATA_DIR", str(root))
    service = make_service()
    assert all(len(tasks) == 0 for tasks in service.datasets.values())
    final = run(service.calculate_final_score({}, dataset="full-md"))
    assert final.score == 0.0 and final.metadata["total_tasks"] == 0


def test_invalid_meta_is_skipped(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    root = tmp_path / "data"
    shutil.copytree(FIXTURE_ROOT, root)
    broken = fixture_meta(C1) | {"task_id": "c1-broken", "category": "C7"}
    (root / "meta" / "c1-broken.json").write_text(json.dumps(broken))
    (root / "meta" / "c1-renamed.json").write_text(json.dumps(fixture_meta(C1)))  # task_id != file name
    (root / "meta" / "c1-garbage.json").write_text("{nope")
    monkeypatch.setenv("WFB_DATA_DIR", str(root))
    assert set(make_service().get_dataset("full-md")) == ALL_TASKS
    assert len(validate_data_root(root)) == 3


def test_fixture_passes_data_validation() -> None:
    assert validate_data_root(FIXTURE_ROOT) == []


# --------------------------------------------------------------------------- retrieve_task


def test_retrieve_task_defaults(service: WaterfallBench) -> None:
    task = run(service.retrieve_task(C1, dataset="full-pdf"))
    assert task.source == ImageSource(image="registry.example.com/waterfallbench-sandbox:test")
    assert task.problem_path == "/tmp/problem_statement.txt"
    assert task.cwd == "/workspace"
    assert task.agent_timeout == 3600.0
    assert (task.resources.vcpu, task.resources.memory, task.resources.disk) == (2, 4, 10)
    assert (task.egress.setup_task, task.egress.run, task.egress.evaluation) == ([], [], [])


def test_retrieve_task_env_overrides(service: WaterfallBench, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("WFB_AGENT_TIMEOUT_SECONDS", "1800")
    monkeypatch.setenv("WFB_RUN_EGRESS", "api.anthropic.com, statsig.anthropic.com")
    monkeypatch.setenv("WFB_SETUP_EGRESS", "*")
    task = run(service.retrieve_task(C4, dataset="excerpt-md"))
    assert task.agent_timeout == 1800.0
    assert task.egress.run == ["api.anthropic.com", "statsig.anthropic.com"]
    assert task.egress.setup_task == "*" and task.egress.evaluation == []


def test_retrieve_task_image_sources(service: WaterfallBench, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("WFB_SANDBOX_IMAGE")
    with pytest.raises(ValueError, match="WFB_SANDBOX_IMAGE"):
        run(service.retrieve_task(C1))
    monkeypatch.setenv("WFB_SANDBOX_DOCKERFILE", "/opt/wfb/sandbox-image/Dockerfile")
    assert run(service.retrieve_task(C1)).source == DockerfileSource(dockerfile="/opt/wfb/sandbox-image/Dockerfile")


def test_retrieve_task_rejects_unknown_and_non_derivable(service: WaterfallBench) -> None:
    with pytest.raises(ValueError):
        run(service.retrieve_task("c1-does-not-exist"))
    with pytest.raises(ValueError):
        run(service.retrieve_task(C2, dataset="excerpt-md"))


# --------------------------------------------------------------------------- setup_task


def expected_uploads(task_id: str, dataset: str) -> set[str]:
    variant = VARIANTS[dataset]
    task_dir = FIXTURE_ROOT / "tasks" / task_id
    docs = {
        f"/workspace/docs/{p.name}" for p in (task_dir / "docs" / variant.docs_subdir).glob(f"*{variant.extension}")
    }
    reports = {f"/workspace/reports/{p.name}" for p in (task_dir / "reports").glob(f"*{variant.extension}")}
    return docs | reports | {"/workspace/answer_schema.json", PROBLEM_PATH}


@pytest.mark.parametrize("dataset", sorted(VARIANTS))
def test_setup_uploads_only_the_variant_files(service: WaterfallBench, dataset: str) -> None:
    for task_id in service.get_dataset(dataset):
        sandbox = FakeSandbox()
        chunks = collect(service.setup_task(task_id, sandbox, dataset=dataset))
        assert result_of(chunks) == {"status": "ok"}

        uploaded = [path for path, _ in sandbox.uploads]
        assert len(uploaded) == len(set(uploaded))
        assert set(uploaded) == expected_uploads(task_id, dataset)
        assert all("meta" not in path for path in uploaded)
        assert ANSWER_PATH not in uploaded
        other = ".pdf" if VARIANTS[dataset].extension == ".md" else ".md"
        assert not any(path.endswith(other) for path in uploaded)
        if VARIANTS[dataset].docs_subdir == "excerpt":
            assert all("excerpt" in path for path in uploaded if path.startswith("/workspace/docs/"))

        meta_bytes = (FIXTURE_ROOT / "meta" / f"{task_id}.json").read_bytes()
        for _, content in sandbox.uploads:
            assert content != meta_bytes
            assert not any(needle in content for needle in ANSWER_NEEDLES)

        statement = sandbox.files[PROBLEM_PATH].decode()
        instructions = (FIXTURE_ROOT / "tasks" / task_id / "instructions.md").read_text()
        assert statement.startswith(instructions.rstrip())
        assert f"({dataset})" in statement and "/workspace/answer.json" in statement


def test_setup_refuses_files_that_resolve_into_meta(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    root = tmp_path / "data"
    shutil.copytree(FIXTURE_ROOT, root)
    leak = root / "tasks" / C1 / "reports" / "zz_leak.md"
    os.symlink(root / "meta" / f"{C1}.json", leak)
    monkeypatch.setenv("WFB_DATA_DIR", str(root))
    service = make_service()
    sandbox = FakeSandbox()
    with pytest.raises(PermissionError):
        collect(service.setup_task(C1, sandbox, dataset="full-md"))
    assert sandbox.uploads == []


def test_setup_refuses_non_derivable_task_in_excerpt_variant(service: WaterfallBench) -> None:
    sandbox = FakeSandbox()
    with pytest.raises(ValueError, match="not found"):
        collect(service.setup_task(C2, sandbox, dataset="excerpt-pdf"))
    assert sandbox.uploads == []


# --------------------------------------------------------------------------- evaluate_instance


@pytest.mark.parametrize("task_id", sorted(ALL_TASKS))
def test_evaluate_instance_grades_answer_json(service: WaterfallBench, task_id: str) -> None:
    sandbox = FakeSandbox({ANSWER_PATH: json.dumps(fixture_meta(task_id)["answer"]).encode()})
    result = result_of(collect(service.evaluate_instance(task_id, sandbox, dataset="full-md")))
    assert result["fully_resolved"] is True and result["answer_status"] == "ok"
    assert sandbox.uploads == []  # grading never writes into the sandbox
    assert sandbox.downloads == [ANSWER_PATH]


def test_evaluate_instance_missing_answer(service: WaterfallBench) -> None:
    sandbox = FakeSandbox()
    result = result_of(collect(service.evaluate_instance(C1, sandbox)))
    assert result["answer_status"] == "missing" and result["fully_resolved"] is False
    assert result["line_item_accuracy"] == 0.0 and result["error"]
    assert sandbox.downloads == []


def test_evaluate_instance_malformed_answer(service: WaterfallBench) -> None:
    sandbox = FakeSandbox({ANSWER_PATH: b'{"corrections": [}'})
    result = result_of(collect(service.evaluate_instance(C4, sandbox, dataset="excerpt-md")))
    assert result["answer_status"] == "malformed" and result["f1"] == 0.0 and result["error"]


def test_evaluate_instance_oversized_answer_is_not_downloaded(service: WaterfallBench) -> None:
    sandbox = FakeSandbox({ANSWER_PATH: b"{}"}, reported_size=50 * 1024 * 1024)
    result = result_of(collect(service.evaluate_instance(C1, sandbox)))
    assert result["answer_status"] == "malformed" and "byte limit" in result["error"]
    assert sandbox.downloads == []


def test_evaluate_response_is_not_supported(service: WaterfallBench) -> None:
    with pytest.raises(ValueError, match="sandbox"):
        run(service.evaluate_response(EvaluateResponseRequest(task_id=C1, response="{}")))


# --------------------------------------------------------------------------- calculate_final_score


def graded(service: WaterfallBench, task_id: str, answer: bytes | None) -> dict[str, Any]:
    sandbox = FakeSandbox({ANSWER_PATH: answer} if answer is not None else {})
    return result_of(collect(service.evaluate_instance(task_id, sandbox)))


def test_final_score_with_none_result(service: WaterfallBench) -> None:
    results = {
        C1: graded(service, C1, json.dumps(fixture_meta(C1)["answer"]).encode()),
        C2: None,  # task never reached a verdict
        C4: graded(service, C4, None),
    }
    final = run(service.calculate_final_score(results, dataset="full-md"))
    meta = final.metadata
    assert final.score == pytest.approx(100 / 3, abs=1e-3)
    assert meta["total_tasks"] == 3 and meta["resolved_tasks"] == 1
    assert meta["tasks_without_result"] == 1
    assert meta["answer_status_counts"] == {"missing": 1, "no_result": 1, "ok": 1}
    assert meta["line_item_accuracy_pct"] == pytest.approx(100 / 3, abs=1e-3)
    assert meta["nontrivial_field_accuracy_pct"] == pytest.approx(100 / 3, abs=1e-3)
    assert meta["tolerance_1usd_accuracy_pct"] == pytest.approx(100 / 3, abs=1e-3)

    assert meta["by_category"]["C1"]["score"] == 100.0
    assert meta["by_category"]["C2"]["score"] == 0.0
    assert meta["by_category"]["C2"]["mean_consecutive_periods_correct"] == 0.0
    assert meta["by_category"]["C4"]["f1_pct"] == 0.0
    assert meta["by_asset_class"]["auto_loan"]["n_tasks"] == 2
    assert meta["by_family"]["fixture_card_master_trust"]["score"] == 0.0
    assert meta["by_window_tag"]["recent"]["score"] == 50.0
    assert meta["by_continuity_pending"]["True"]["n_tasks"] == 1

    assert sum(row["n_tasks"] for row in meta["allocation"]) == 3
    assert {"category": "C2", "asset_class": "auto_loan", "family": "fixture_auto_owner_trust",
            "window_tag": "historical", "n_tasks": 1} in meta["allocation"]  # fmt: skip

    copy_prior = meta["baselines"]["copy_prior"]
    assert copy_prior["n_tasks"] == 3 and copy_prior["score"] == 0.0
    assert copy_prior["line_item_accuracy_pct"] == pytest.approx(100 * (2 / 7 + 0.25 + 4 / 6) / 3, abs=1e-3)
    assert copy_prior["mean_consecutive_periods_correct"] == 0.0
    all_zeros = meta["baselines"]["all_zeros"]
    assert all_zeros["line_item_accuracy_pct"] == 0.0
    assert all_zeros["f1_pct"] == 50.0  # averaged over C4 tasks only


def test_final_score_all_none(service: WaterfallBench) -> None:
    final = run(service.calculate_final_score({C1: None, C4: None}, dataset="excerpt-md"))
    assert final.score == 0.0
    assert final.metadata["tasks_without_result"] == 2 and final.metadata["dataset"] == "excerpt-md"


# --------------------------------------------------------------------------- auth and HTTP wiring


def test_check_auth(service: WaterfallBench, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("WFB_SERVICE_TOKEN", raising=False)
    assert run(service.check_auth({"authorization": "Bearer anything"})) is False
    monkeypatch.setenv("WFB_SERVICE_TOKEN", "s3cret")
    assert run(service.check_auth({"authorization": "Bearer s3cret"})) is True
    assert run(service.check_auth({"authorization": "Bearer wrong"})) is False
    assert run(service.check_auth({})) is False


def test_http_routes(fixture_env: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("AUTH_REQUIRED", raising=False)
    from main import app

    with TestClient(app) as client:
        assert client.get("/health").status_code == 200
        assert client.get("/v1/datasets").json()["datasets"] == [
            "default",
            "excerpt-md",
            "excerpt-pdf",
            "full-md",
            "full-pdf",
        ]
        ids = client.get("/verify-task-ids", params={"dataset": "excerpt-pdf"}).json()["task_ids"]
        assert set(ids) == {C1, C4}
        task = client.get("/retrieve-task/", params={"task_id": C2, "dataset": "full-pdf"}).json()
        assert task["source"] == {"type": "image", "image": "registry.example.com/waterfallbench-sandbox:test"}
        assert task["egress"]["run"] == []
        final = client.post("/final-score/", json={"evaluation_results": {C1: None}, "dataset": "full-md"})
        assert final.status_code == 200 and final.json()["final_score"] == 0.0
        response = client.post("/evaluate-response/", json={"task_id": C1, "response": "{}", "dataset": "full-md"})
        assert response.status_code >= 400


def test_http_requires_token_when_auth_required(fixture_env: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("AUTH_REQUIRED", "true")
    monkeypatch.setenv("WFB_SERVICE_TOKEN", "s3cret")
    from main import app

    with TestClient(app) as client:
        assert client.get("/v1/datasets").status_code == 401
        ok = client.get("/v1/datasets", headers={"Authorization": "Bearer s3cret"})
        assert ok.status_code == 200
