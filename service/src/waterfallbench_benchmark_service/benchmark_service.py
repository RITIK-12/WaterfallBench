"""WaterfallBench-Pilot benchmark service.

The agent gets ABS deal documents and a trustee report with the period's output values
removed, and writes the computed waterfall results to /workspace/answer.json. Grading reads
that file from the sandbox and compares it with the private answer key in meta/, which is
read only here in ``evaluate_instance`` and never enters the sandbox.

Environment:
    WFB_DATA_DIR                 private data root (tasks/ and meta/)
    WFB_SANDBOX_IMAGE            registry image built from sandbox-image/Dockerfile (ImageSource)
    WFB_SANDBOX_DOCKERFILE       absolute Dockerfile path, only for a Tracker on this machine
    WFB_AGENT_TIMEOUT_SECONDS    agent generation limit, default 3600
    WFB_SETUP_EGRESS / WFB_RUN_EGRESS / WFB_EVALUATION_EGRESS
                                 unset or "" blocks all traffic, "*" allows all, or a
                                 comma-separated allowlist of hosts / URLs / CIDRs
    WFB_SERVICE_TOKEN            bearer token checked when AUTH_REQUIRED=true
"""

import hmac
import logging
import os
from collections.abc import AsyncGenerator
from pathlib import Path
from typing import Any

from benchmark_service import BenchmarkService, DockerfileSource, ImageSource, Resources, Sandbox
from benchmark_service.schemas import (
    BenchmarkEgressPlan,
    EgressPolicy,
    EvaluateResponseRequest,
    FinalScoreResult,
    RetrieveTaskResponse,
    StreamChunk,
    StreamMessageChunk,
    StreamResultChunk,
)

from waterfallbench_benchmark_service.data import (
    ANSWER_PATH,
    DOCS_DIR,
    PROBLEM_PATH,
    REPORTS_DIR,
    WORKSPACE,
    TaskInfo,
    build_datasets,
    data_root,
    load_task_infos,
    problem_statement,
    read_answer_key_meta,
    read_instructions,
    resolve_variant,
    workspace_files,
)
from waterfallbench_benchmark_service.grading import MAX_ANSWER_BYTES, grade_answer
from waterfallbench_benchmark_service.scoring import final_score

logger = logging.getLogger(__name__)

DEFAULT_AGENT_TIMEOUT_SECONDS = 3600.0
SANDBOX_RESOURCES = Resources(vcpu=2, memory=4, disk=10)
_MISSING_MARKER = "__WFB_ANSWER_MISSING__"


def egress_from_env(name: str) -> EgressPolicy:
    """Unset or empty blocks everything; "*" is unrestricted; otherwise a comma-separated allowlist."""
    raw = os.environ.get(name, "").strip()
    if raw == "*":
        return "*"
    return [entry.strip() for entry in raw.split(",") if entry.strip()]


def agent_timeout_seconds() -> float:
    raw = os.environ.get("WFB_AGENT_TIMEOUT_SECONDS", "").strip()
    timeout = float(raw) if raw else DEFAULT_AGENT_TIMEOUT_SECONDS
    if not timeout > 0:
        raise ValueError("WFB_AGENT_TIMEOUT_SECONDS must be positive")
    return timeout


def sandbox_source() -> ImageSource | DockerfileSource:
    image = os.environ.get("WFB_SANDBOX_IMAGE", "").strip()
    if image:
        return ImageSource(image=image)
    dockerfile = os.environ.get("WFB_SANDBOX_DOCKERFILE", "").strip()
    if dockerfile:
        # Built by whichever machine creates the sandbox (the Tracker), so this only works
        # when the Tracker can read this path, i.e. a local Tracker on this machine.
        return DockerfileSource(dockerfile=dockerfile)
    raise ValueError(
        "Set WFB_SANDBOX_IMAGE to the registry image built from sandbox-image/Dockerfile "
        "(or WFB_SANDBOX_DOCKERFILE for a Tracker running on this machine)"
    )


async def read_answer_file(sandbox: Sandbox) -> tuple[bytes | None, int | None]:
    """(content, size) of the agent's answer. Content is None when the file is absent, or
    when it is too large to be worth downloading (size then says why)."""
    probe = await sandbox.exec(
        f"if [ -f {ANSWER_PATH} ]; then wc -c < {ANSWER_PATH}; else echo {_MISSING_MARKER}; fi",
        cwd=WORKSPACE,
        timeout=60,
    )
    output = probe.output.strip()
    if _MISSING_MARKER in output:
        return None, None
    try:
        size: int | None = int(output.split()[-1])
    except (IndexError, ValueError):
        size = None  # unexpected probe output: download and let the parser decide
    if size is not None and size > MAX_ANSWER_BYTES:
        return None, size
    return await sandbox.download_file(ANSWER_PATH), size


class WaterfallBench(BenchmarkService):
    """Serves the four WaterfallBench-Pilot variants and grades /workspace/answer.json."""

    @property
    def root(self) -> Path:
        return data_root()

    async def check_auth(self, headers: dict[str, str]) -> bool:
        """Only consulted when AUTH_REQUIRED=true; fails closed without WFB_SERVICE_TOKEN."""
        token = os.environ.get("WFB_SERVICE_TOKEN", "")
        if not token:
            return False
        return hmac.compare_digest(headers.get("authorization", "").encode(), f"Bearer {token}".encode())

    async def load_datasets(self) -> dict[str, dict[str, Any]]:
        infos, problems = load_task_infos(self.root)
        for problem in problems:
            logger.error("Skipping WaterfallBench task: %s", problem)
        datasets = build_datasets(infos)
        logger.info(
            "Loaded WaterfallBench from %s: %s",
            self.root,
            ", ".join(f"{name}={len(tasks)}" for name, tasks in datasets.items()),
        )
        return dict(datasets)

    def task_info(self, task_id: str, dataset: str | None) -> TaskInfo:
        tasks = self.get_dataset(dataset)
        if task_id not in tasks:
            raise ValueError(f"Task ID not found: {task_id}")
        return tasks[task_id]

    async def retrieve_task(
        self, task_id: str, skip_validation: bool = False, dataset: str | None = None
    ) -> RetrieveTaskResponse:
        if not skip_validation:
            await self.validate_task_ids([task_id], dataset=dataset)
        return RetrieveTaskResponse(
            source=sandbox_source(),
            problem_path=PROBLEM_PATH,
            cwd=WORKSPACE,
            agent_timeout=agent_timeout_seconds(),
            resources=SANDBOX_RESOURCES,
            egress=BenchmarkEgressPlan(
                setup_task=egress_from_env("WFB_SETUP_EGRESS"),
                run=egress_from_env("WFB_RUN_EGRESS"),
                evaluation=egress_from_env("WFB_EVALUATION_EGRESS"),
            ),
        )

    async def setup_task(
        self, task_id: str, sandbox: Sandbox, dataset: str | None = None
    ) -> AsyncGenerator[StreamChunk, None]:
        self.task_info(task_id, dataset)  # excerpt variants refuse non-derivable tasks here
        variant = resolve_variant(dataset)
        uploads = workspace_files(self.root, task_id, variant)
        statement = problem_statement(read_instructions(self.root, task_id), variant, uploads)

        yield StreamMessageChunk(type="message", data=f"Preparing {task_id} ({variant.name}): {len(uploads)} files")
        result = await sandbox.exec(f"mkdir -p {DOCS_DIR} {REPORTS_DIR}", cwd="/", timeout=60)
        if result.exit_code != 0:
            raise RuntimeError(f"Could not create {DOCS_DIR} and {REPORTS_DIR}: {result.output[-500:]}")
        for remote, local in uploads:
            await sandbox.upload_file(remote, local.read_bytes())
        await sandbox.upload_file(PROBLEM_PATH, statement.encode("utf-8"))

        yield StreamMessageChunk(type="message", data="Uploaded documents, reports, schema and problem statement")
        yield StreamResultChunk(type="result", data={"status": "ok"})

    async def evaluate_response(self, request: EvaluateResponseRequest, dataset: str | None = None) -> Any:
        raise ValueError("WaterfallBench grades /workspace/answer.json in the sandbox; use evaluate-instance")

    async def evaluate_instance(
        self, task_id: str, sandbox: Sandbox, dataset: str | None = None
    ) -> AsyncGenerator[StreamChunk, None]:
        self.task_info(task_id, dataset)
        yield StreamMessageChunk(type="message", data=f"Reading {ANSWER_PATH}")
        raw, size = await read_answer_file(sandbox)
        # The only place the private answer key is read.
        result = grade_answer(read_answer_key_meta(self.root, task_id), raw, size)
        summary = f"answer {result['answer_status']}: {result['n_correct']}/{result['n_fields']} fields correct"
        if result["error"]:
            summary += f" ({result['error']})"
        yield StreamMessageChunk(type="message", data=summary)
        yield StreamResultChunk(type="result", data=result)

    async def calculate_final_score(
        self, evaluation_results: dict[str, Any], dataset: str | None = None
    ) -> FinalScoreResult:
        variant = resolve_variant(dataset)
        score, metadata = final_score(evaluation_results, self.get_dataset(dataset), variant.name)
        return FinalScoreResult(score=score, metadata=metadata)
