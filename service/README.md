# WaterfallBench benchmark service

Valkyrie benchmark service for **WaterfallBench-Pilot**. An agent reads ABS deal documents and
a trustee report with the period's output values removed, computes the waterfall results, and
writes them to `/workspace/answer.json`. The service serves the tasks, sets up each sandbox, and
grades the answer against a private answer key that never enters the sandbox.

Generated with `create-benchmark-service` (framework `v0.74.0`).

| Path | Contents |
| - | - |
| `src/waterfallbench_benchmark_service/benchmark_service.py` | `WaterfallBench`, the `BenchmarkService` subclass |
| `src/waterfallbench_benchmark_service/grading.py` | Pure per-task grader (no sandbox, no I/O) |
| `src/waterfallbench_benchmark_service/scoring.py` | Pure aggregation for `calculate_final_score` |
| `src/waterfallbench_benchmark_service/data.py` | Data-root reading, variant file selection, answer-key reader |
| `sandbox-image/Dockerfile` | The agent's sandbox image (Python 3.12, poppler-utils, pypdf, pdfplumber, pandas) |
| `noop-agent/` | A model-free Valkyrie agent for smoke runs |
| `tests/fixtures/fabricated_data/` | FABRICATED unit-test data (one C1, C2, C4 task) |

## Datasets

| Dataset | Documents uploaded to `/workspace/docs/` | Reports in `/workspace/reports/` | Tasks |
| - | - | - | - |
| `full-html` (also `default`) | `docs/full/*.html` | `reports/*.html` | all (pilot: EDGAR HTML as filed) |
| `full-md` | `docs/full/*.md` | `reports/*.md` | all (only when enabled via `WFB_VARIANTS`) |
| `full-pdf` | `docs/full/*.pdf` | `reports/*.pdf` | all |
| `excerpt-md` | `docs/excerpt/*.md` | `reports/*.md` | `excerpt_derivable: true` only |
| `excerpt-pdf` | `docs/excerpt/*.pdf` | `reports/*.pdf` | `excerpt_derivable: true` only |

Every task also gets `/workspace/answer_schema.json`, and `instructions.md` (plus a listing of
the uploaded files) at `/tmp/problem_statement.txt`. Nothing from `meta/` is uploaded; files
that resolve outside the task folder (for example through a symlink) are refused.

## Configuration

| Variable | Default | Meaning |
| - | - | - |
| `WFB_DATA_DIR` | `<repo>/dataset` | Data root with `tasks/` (published) and `meta/` (private answer keys) |
| `WFB_SANDBOX_IMAGE` | none (required for runs) | Registry image built from `sandbox-image/Dockerfile` |
| `WFB_SANDBOX_DOCKERFILE` | none | Absolute Dockerfile path; only for a Tracker on this machine |
| `WFB_AGENT_TIMEOUT_SECONDS` | `3600` | Agent generation limit |
| `WFB_SETUP_EGRESS`, `WFB_RUN_EGRESS`, `WFB_EVALUATION_EGRESS` | empty: block all | `*`, or comma-separated hosts / URLs / CIDRs |
| `AUTH_REQUIRED` + `WFB_SERVICE_TOKEN` | off | Require `Authorization: Bearer <token>` |

The run stage blocks all egress by default. An agent that calls a model API from the sandbox
must have its host allowed, either in its contract (`egress_allowlist: [api.anthropic.com]`,
which Valkyrie adds to the benchmark's run allowlist) or here with
`WFB_RUN_EGRESS=api.anthropic.com`. Local Docker sandboxes accept only `*` for every stage.

## Grading

Per task, `evaluate_instance` downloads `/workspace/answer.json` (missing, oversized over 5 MB,
or invalid JSON scores 0 with the reason in `error`) and compares each field exactly:

* `money_cents`: JSON integer, or a float that is exactly integral; strings are wrong.
* `int`: same rule. `status`: exact string. `decimal`: `Decimal(str(value)) == Decimal(expected)`.
* ±$1 tolerance: money fields within 100 cents count; other types must be exact.

The result holds per-field correctness, line-item, non-trivial-field and ±$1 accuracy,
`fully_resolved`, and the task's category, asset class, family, window tag and continuity flag.
C2 adds `consecutive_periods_correct` (fully-correct periods from `period_1`). C4 adds precision,
recall and F1 over the set of misstated fields (unknown or unreadable entries are false
positives; nothing to find and nothing flagged is 1/1/1), plus `value_accuracy` on the fields it
found; a field claimed twice must have every claimed value right. No expected values appear in
results.

`calculate_final_score` scores tasks with a `None` result as 0. The headline score is the
percentage of tasks fully resolved; metadata adds the accuracies, breakdowns by category, asset
class, family, window tag and continuity flag, the task allocation, and the baselines from meta.

The pipeline should compute `meta.baselines.<name>` with
`grading.headline_metrics(grading.grade_submission(meta, baseline_answer))`.

## Develop and test

```bash
make install
make test                         # unit tests, no network, no models
make validate-data                # check WFB_DATA_DIR against the data contract
make sandbox-image                # build the sandbox image locally (linux/amd64)
make test-provider-integration    # real WebSocket setup/grading in a local Docker sandbox
WFB_SANDBOX_IMAGE=REGISTRY/waterfallbench-sandbox:v1 make dev
```

## Run on Valkyrie

1. Push the sandbox image to a registry your sandbox provider can pull, and set `WFB_SANDBOX_IMAGE`.
2. Serve the service at a public HTTPS URL (`make docker-build && make docker-run` behind a
   tunnel or a host), ideally with `AUTH_REQUIRED=true` and `WFB_SERVICE_TOKEN`.
3. `valkyrie benchmark service set waterfallbench URL [--auth-secret SECRET]`.
4. `valkyrie agent push ./noop-agent`, then
   `valkyrie run start --benchmark waterfallbench --dataset full-html --agent waterfallbench-noop --slice 0:1`.
