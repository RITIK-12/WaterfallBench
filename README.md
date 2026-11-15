# WaterfallBench

[![Hugging Face](https://img.shields.io/badge/%F0%9F%A4%97%20Hugging%20Face-Dataset-FFD21E)](https://huggingface.co/datasets/ritik12/WaterfallBench) [![Leaderboard](https://img.shields.io/badge/Leaderboard-live-2f7d3c)](https://ritik-12.github.io/WaterfallBench/) [![License](https://img.shields.io/badge/data-CC%20BY%204.0-lightgrey)](https://creativecommons.org/licenses/by/4.0/)

**Can a model execute an asset-backed securities waterfall to the cent, from the deal documents alone?**

📊 **[Leaderboard & methodology →](https://ritik-12.github.io/WaterfallBench/)** · 🤗 **[Dataset on Hugging Face →](https://huggingface.co/datasets/ritik12/WaterfallBench)**

An asset-backed security turns thousands of car loans or leases into bonds sold in classes, senior (A) to junior
(B, C). Every month the collections are paid out in a fixed order, the **waterfall**: servicing fee, interest, principal
(senior first), reserve top-up, then the residual. The rules sit in hundreds of pages of legal documents, and an error
moves cash between investors. The 20 deals here issued $23.5B of notes.

Each task is a deal's **first distribution date**. The model gets the final prospectus, the closing agreements and that
month's servicer report with every waterfall result removed: no prior report, no worked example. It must return the
servicing fee, each class's interest, principal and ending balance, the reserve balance and the residual, in exact
cents. The answer key is what the trustee actually paid, as filed on SEC EDGAR.

## Leaderboard

One API call per task, identical prompt and documents, reasoning effort `high`, 20 tasks.

| # | Model | Fully resolved | Field accuracy | Cost / task |
|---|---|---|---|---|
| 1 | GPT-6 Astra | **95.0%** ±4.9 | 99.2% | $8.33 |
| 1 | Claude Fable 5.2 | **95.0%** ±4.9 | 99.1% | $5.18 |
| 3 | GPT-6 Luna | **90.0%** ±6.7 | 99.2% | $0.09 |
| 4 | GLM 5.3 | **75.0%** ±9.7 | 95.7% | $0.68 |
| 5 | MiniMax M3.1 Flash | **50.0%** ±11.2 | 89.0% | $0.07 |
| 6 | Kimi K3.1 Pro | **45.0%** ±11.1 | 92.3% | $0.89 |
| 7 | Claude Haiku 5.5 | **40.0%** ±11.0 | 85.8% | $0.34 |

Anthropic and OpenAI models via their own APIs; GLM, MiniMax and Kimi via Fireworks serverless. See [Scoring](#scoring) for
the metrics; ± is one standard error. A reply with no JSON answer scores 0 (MiniMax returned one empty reply).

## A task

```
dataset-fw/tasks/fw-carmax-2026-3-2026-07/
├── instructions.md          # the task statement
├── answer_schema.json       # identical for every task
├── docs/full/               # final prospectus + closing agreements (EDGAR HTML as filed)
└── reports/period_*.html    # this month's servicer report, waterfall results removed
```

Every task uses the same output schema; the model lists the deal's note classes itself:

```json
{
  "servicing_fee_paid": 0, "reserve_ending_balance": 0, "released_to_residual": 0,
  "classes": [{"class": "A-1", "interest_paid": 0, "principal_paid": 0, "ending_balance": 0}]
}
```

Money is integer US cents. Classes are matched by name (`A-2A`, `Class A-2a Notes` and `a2a` are the same class).

## Run it with Valkyrie

```bash
# 1. API keys (stored as Valkyrie secrets; prompts for the value)
valkyrie secret set anthropic-api-key
valkyrie secret set openai-api-key
valkyrie secret set fireworks-api-key

# 2. The single-call harness
valkyrie agent push agents/waterfallbench-direct

# 3. Run a model on all 20 tasks, 5 at a time
valkyrie run start --benchmark waterfallbench --dataset full-html \
  --agent waterfallbench-direct --model anthropic/claude-haiku-5-5 -k effort high \
  -s ANTHROPIC_API_KEY anthropic-api-key --provider modal --concurrency 5

#    OpenAI models:    --model openai/gpt-6-luna -s OPENAI_API_KEY openai-api-key
#    Fireworks models: --model fireworks/kimi-k3p1-pro -s FIREWORKS_API_KEY fireworks-api-key

# 4. Leaderboard from one or more runs
python tools/eval/leaderboard.py <RUN_ID> [<RUN_ID> ...]
```

Add `--task-ids fw-deere-2026-b-2026-08` to try a single task first. Effort can be `low` to `max`;
`-k max_input_tokens N` caps the prompt (default 1M; no task needs truncation).

**Grading service.** Runs are graded by the WaterfallBench benchmark service in [`service/`](service/). It holds the
answer keys, which are not in this repo. To host your own copy you need the keys (`dataset-fw/meta/`); then:

```bash
cd service && WFB_DATA_DIR=../dataset-fw WFB_SANDBOX_IMAGE=docker.io/ritik12/waterfallbench-sandbox:v2 \
  uv run fastapi run main.py --port 8001
valkyrie benchmark service set waterfallbench https://<your-public-url>
```

## Run it without Valkyrie

The harness runs on any task folder. It needs `pip install anthropic openai` and an `ANTHROPIC_API_KEY`,
`OPENAI_API_KEY` or `FIREWORKS_API_KEY` in your environment:

```bash
T=dataset-fw/tasks/fw-deere-2026-b-2026-08; W=$(mktemp -d)
mkdir -p $W/docs && cp $T/docs/full/*.html $W/docs/ && cp -r $T/reports $T/answer_schema.json $W/
WFB_WORKSPACE=$W python3 agents/waterfallbench-direct/direct.py \
  --problem $T/instructions.md --task-id $(basename $T) --model anthropic/claude-haiku-5-5
cat $W/answer.json
```

Add `--dry-run` to build the prompt without calling a model.

## Dataset

| Issuer | Deals | First distributions | Note classes | Documents / task | Prompt tokens | Graded fields |
|---|---|---|---|---|---|---|
| CarMax Auto Owner Trust | 6 | May 2025 – Aug 2026 | 7–8 | 8–9 | 634K | 156 |
| World Omni Auto Receivables Trust | 7 | Feb 2025 – Sep 2026 | 7 | 8 | 629K | 149 |
| John Deere Owner Trust | 3 | Aug 2025 – Aug 2026 | 5 | 7–8 | 509K | 48 |
| Nissan Auto Lease Trust | 4 | Feb 2025 – Aug 2026 | 7 | 11 | 727K | 96 |

Each task is a trust's first Form 10-D. Prompt tokens are the mean per task (Claude tokenizer); no task needs
truncation. Every task was checked before release:

- the report's classes match the prospectus cover table;
- per class, opening balance − principal paid = ending balance, to the cent;
- class interest and principal sum to the report's totals, and each report passes its own cash reconciliation;
- a value scan finds no graded answer left in the redacted report or the instructions;
- the true answer grades 100%, and an all-zeros answer resolves nothing.

**Not graded (28 of 477 fields, 11 tasks).** Auditing the model runs turned up three places where the documents cannot
determine a value: John Deere's first fee needs a mid-period pool balance no document provides; CarMax 2025-2's report
departs from its own agreement's overcollateralization target; World Omni's agreement prorates the first fee without a
day count. The filed values are kept in the keys; those fields just aren't scored.

## Scoring

The reply is parsed, its classes are matched to the deal's by name, and every graded field is compared with the filed
value, exactly.

| Metric | Definition |
|---|---|
| **Fully resolved** (primary) | 1 if every graded field is exact to the cent, else 0 |
| **Field accuracy** | share of non-trivial fields exactly right (trivial = zero, or an opening balance left untouched) |
| All fields / within $1 | share of all graded fields exact / within one dollar (rounding slips vs logic errors) |

Scores are means over the 20 tasks. Grading is deterministic, with no LLM judge. Cost uses each provider's list price.

## Repository

```
dataset-fw/tasks/          the 20 first-distribution tasks (this benchmark)
agents/waterfallbench-direct/   single-call harness (Anthropic, OpenAI, Fireworks) and Valkyrie contract
service/                   grading service (Valkyrie benchmark service)
tools/eval/                leaderboard + site data
tools/data-prep/wfb/       pipeline that built the tasks from SEC EDGAR
site/                      the leaderboard page (deployed by GitHub Actions)
hf/                        Hugging Face release: build script, dataset card, submission helper
dataset/tasks/             WaterfallBench-Pilot: 100 monthly tasks with the prior report given (see DATASET_CARD.md)
```

Data: SEC EDGAR public filings, retrieved with Firecrawl. Code: Apache 2.0.
