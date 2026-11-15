"""Shared helpers. tests/fixtures/fabricated_data holds FABRICATED unit-test data only."""

import asyncio
import json
import os

# The fabricated fixtures carry the markdown/PDF variants; production defaults to full-html.
os.environ.setdefault("WFB_VARIANTS", "full-md,full-pdf,excerpt-md,excerpt-pdf")
from collections.abc import AsyncGenerator, Mapping
from pathlib import Path
from typing import Any

import pytest
from benchmark_service import ExecResult, Sandbox

from waterfallbench_benchmark_service.benchmark_service import WaterfallBench
from waterfallbench_benchmark_service.data import ANSWER_PATH

FIXTURE_ROOT = Path(__file__).parent / "fixtures" / "fabricated_data"
C1 = "c1-fixture-auto-001"
C2 = "c2-fixture-auto-002"  # excerpt_derivable = false
C4 = "c4-fixture-cards-003"


def fixture_meta(task_id: str) -> dict[str, Any]:
    return json.loads((FIXTURE_ROOT / "meta" / f"{task_id}.json").read_text())


class FakeSandbox(Sandbox):
    """Records every upload and command; serves files it holds for download."""

    def __init__(self, files: Mapping[str, bytes] | None = None, reported_size: int | None = None) -> None:
        self.files: dict[str, bytes] = dict(files or {})
        self.uploads: list[tuple[str, bytes]] = []
        self.commands: list[str] = []
        self.downloads: list[str] = []
        self.reported_size = reported_size

    @property
    def id(self) -> str:
        return "fake-sandbox"

    @property
    def name(self) -> str:
        return "fake-sandbox"

    @property
    def state(self) -> str:
        return "started"

    async def exec(self, command: str, *, cwd: str | None = None, timeout: float | None = None) -> ExecResult:
        self.commands.append(command)
        if "wc -c" in command and ANSWER_PATH in command:
            if ANSWER_PATH not in self.files:
                return ExecResult(exit_code=0, output="__WFB_ANSWER_MISSING__\n")
            size = self.reported_size if self.reported_size is not None else len(self.files[ANSWER_PATH])
            return ExecResult(exit_code=0, output=f"{size}\n")
        return ExecResult(exit_code=0, output="")

    async def command(
        self,
        command: str,
        *,
        cwd: str | None = None,
        timeout: float | None = None,
        env_vars: Mapping[str, str] | None = None,
    ) -> AsyncGenerator[str, None]:
        self.commands.append(command)
        if False:  # pragma: no cover - makes this an async generator
            yield ""

    async def upload_file(self, remote_path: str, content: bytes) -> None:
        self.uploads.append((remote_path, content))
        self.files[remote_path] = content

    async def download_file(self, remote_path: str) -> bytes:
        self.downloads.append(remote_path)
        if remote_path not in self.files:
            raise FileNotFoundError(remote_path)
        return self.files[remote_path]


def run(coro: Any) -> Any:
    return asyncio.run(coro)


async def _collect(stream: AsyncGenerator[Any, None]) -> list[Any]:
    return [chunk async for chunk in stream]


def collect(stream: AsyncGenerator[Any, None]) -> list[Any]:
    return run(_collect(stream))


def make_service() -> WaterfallBench:
    """Builds the service the way the app does; reads WFB_DATA_DIR from the environment."""
    return run(WaterfallBench.create())


@pytest.fixture
def fixture_env(monkeypatch: pytest.MonkeyPatch) -> Path:
    monkeypatch.setenv("WFB_DATA_DIR", str(FIXTURE_ROOT))
    monkeypatch.setenv("WFB_SANDBOX_IMAGE", "registry.example.com/waterfallbench-sandbox:test")
    for name in ("WFB_AGENT_TIMEOUT_SECONDS", "WFB_SETUP_EGRESS", "WFB_RUN_EGRESS", "WFB_EVALUATION_EGRESS"):
        monkeypatch.delenv(name, raising=False)
    return FIXTURE_ROOT


@pytest.fixture
def service(fixture_env: Path) -> WaterfallBench:
    return make_service()
