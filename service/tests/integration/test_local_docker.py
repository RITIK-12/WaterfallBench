"""Real WebSocket setup / evaluate against a local Docker sandbox built from sandbox-image/.

Run with `make sandbox-image && make test-provider-integration`. Skipped when the image is
absent. Uses the FABRICATED fixture; no model calls and no network beyond the Docker daemon.
"""

import asyncio
import json
import os
import socket
import subprocess
import threading
import time
from collections.abc import Iterator
from typing import Any

import pytest
import uvicorn
from benchmark_service import BenchmarkServiceClient, DockerProviderConfig, ImageSource, Resources, SandboxCreateRequest

from ..conftest import C1, C2, C4, FIXTURE_ROOT, fixture_meta

IMAGE = os.environ.get("WFB_TEST_SANDBOX_IMAGE", "waterfallbench-sandbox:local")


def _image_available() -> bool:
    try:
        return subprocess.run(["docker", "image", "inspect", IMAGE], capture_output=True).returncode == 0
    except FileNotFoundError:
        return False


pytestmark = pytest.mark.skipif(not _image_available(), reason=f"Docker image {IMAGE} not built (make sandbox-image)")


@pytest.fixture
def service_url(monkeypatch: pytest.MonkeyPatch) -> Iterator[str]:
    monkeypatch.setenv("WFB_DATA_DIR", str(FIXTURE_ROOT))
    monkeypatch.setenv("WFB_SANDBOX_IMAGE", IMAGE)
    monkeypatch.setenv("CBS_DOCKER_ENABLED", "true")
    monkeypatch.delenv("AUTH_REQUIRED", raising=False)
    from main import app

    with socket.socket() as probe:
        probe.bind(("127.0.0.1", 0))
        port = probe.getsockname()[1]
    server = uvicorn.Server(uvicorn.Config(app, host="127.0.0.1", port=port, log_level="warning"))
    thread = threading.Thread(target=server.run, daemon=True)
    thread.start()
    deadline = time.monotonic() + 30
    while not server.started and time.monotonic() < deadline:
        time.sleep(0.05)
    assert server.started
    yield f"http://127.0.0.1:{port}"
    server.should_exit = True
    thread.join(timeout=10)


async def _scenario(url: str, task_id: str, dataset: str) -> dict[str, Any]:
    provider = DockerProviderConfig().create_provider()
    sandbox = await provider.create_sandbox(
        SandboxCreateRequest(
            source=ImageSource(image=IMAGE),
            resources=Resources(vcpu=1, memory=1, disk=5),
            name=f"wfb-it-{task_id}",
            labels={"Benchmark": "waterfallbench-integration"},
            env_vars={},
            auto_stop_interval=0,
            create_timeout=300,
        )
    )
    client = BenchmarkServiceClient(url=url, headers={})
    config = DockerProviderConfig()
    try:
        setup = await client.setup_task(task_id, sandbox.id, sandbox_provider=config, dataset=dataset)
        listing = await sandbox.exec("find /workspace /tmp/problem_statement.txt -type f | sort")
        missing = await client.evaluate_instance(task_id, sandbox.id, sandbox_provider=config, dataset=dataset)
        await sandbox.upload_file("/workspace/answer.json", json.dumps(fixture_meta(task_id)["answer"]).encode())
        solved = await client.evaluate_instance(task_id, sandbox.id, sandbox_provider=config, dataset=dataset)
        await sandbox.exec("ln -sf /dev/zero /workspace/answer.json")
        device = await client.evaluate_instance(task_id, sandbox.id, sandbox_provider=config, dataset=dataset)
        return {"setup": setup.status, "listing": listing.output.split(), "missing": missing, "solved": solved,
                "device": device}  # fmt: skip
    finally:
        await provider.delete_sandbox(sandbox.id)
        await provider.close()


@pytest.mark.parametrize(("task_id", "dataset"), [(C1, "full-md"), (C2, "full-pdf"), (C4, "excerpt-pdf")])
def test_setup_and_grade_in_real_sandbox(service_url: str, task_id: str, dataset: str) -> None:
    out = asyncio.run(_scenario(service_url, task_id, dataset))
    assert out["setup"] == "ok"
    extension = ".pdf" if dataset.endswith("pdf") else ".md"
    files = out["listing"]
    assert "/tmp/problem_statement.txt" in files and "/workspace/answer_schema.json" in files
    assert all(f.endswith(extension) for f in files if f.startswith(("/workspace/docs/", "/workspace/reports/")))
    assert not any("meta" in f or f.endswith("answer.json") for f in files)
    assert out["missing"]["answer_status"] == "missing"
    assert out["solved"]["fully_resolved"] is True
    assert out["device"]["answer_status"] == "missing"  # a symlink to a device is not a regular file
