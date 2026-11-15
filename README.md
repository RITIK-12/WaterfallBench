# WaterfallBench-Pilot

**Can an agent execute an asset-backed-securities payment waterfall to the cent?**

Every month, ABS trusts pay bondholders according to the legal *priority of payments* in their prospectus and
transaction agreements, then file a Form 10-D on SEC EDGAR whose servicer report shows what was actually paid.
WaterfallBench gives an agent the governing documents and a month's **pre-distribution inputs** and asks it to
compute **every distribution result** — fees, interest and principal per class, account movements, overcollateralization,
ending balances. The answer key is what the trustee reported.

The benchmark measures waterfall *execution*, not answer *extraction*: every output is removed from the agent's copy of
the report, and every task was proven derivable from its packet by an independent, frozen reference implementation.

## The dataset

100 tasks from 5 contract families (SEC EDGAR filings, reports filed 2024-11 to 2026-11):

| Family | Asset class | C1 monthly distribution | C2 four-month roll-forward |
|---|---|---|---|
| CarMax Auto Owner Trust | auto loan | 15 | 5 |
| World Omni Auto Receivables Trust | auto loan | 15 | 5 |
| John Deere Owner Trust | equipment | 15 | 5 |
| Nissan Auto Lease Trust | auto lease | 15 | 5 |
| Navient Student Loan Trust | FFELP student loan | 15 | 5 |

- **C1 `monthly_distribution`** — compute every output field of one distribution period.
- **C2 `rollforward_4p`** — compute every output field of four consecutive periods from the opening state only
  (later periods' beginning balances and carryovers are removed too; the agent must carry its own results forward).

72 tasks are graded on reports filed between 2026-07-01 and 2026-11-14, after the published training cutoffs of the
evaluated models (no task is claimed to be unseen by any model). See [`DATASET_CARD.md`](DATASET_CARD.md) for window tags,
certification and reference pass rates, baselines, deviations and limitations.

## A task

```
dataset/tasks/<task_id>/
  docs/full/        final prospectus + closing agreements (SEC EDGAR HTML as filed)
  reports/          period_<YYYY-MM>_opening_state.html   complete report of the preceding period
                    period_<YYYY-MM>_graded.html          the graded period's report, every output removed
  instructions.md   deal, period(s), required output fields with their report line, rules
  answer_schema.json
```

The agent writes `/workspace/answer.json`: `{"<field>": <value>}` (C2: `{"period_1": {...}, ..., "period_4": {...}}`).
Money is integer US cents; percentages are the printed number; statuses come from the schema's enum.

Answer keys (`dataset/meta/`) are private to the grading service and are never committed or published.

## Scoring

Graded in the sandbox by the benchmark service ([`service/`](service/)):

- **Headline:** `fully_resolved` — every output field exact to the cent.
- Line-item accuracy, non-trivial-field accuracy (fields that are not zero and not unchanged from the prior report),
  ±$1 tolerance accuracy; C2 also reports the longest run of fully correct consecutive periods.
- Deterministic baselines: copying the prior report and answering all zeros both resolve 0/100 tasks.

## How the data was built

1. Enumerate every 10-D / 10-D/A on EDGAR and discover each trust's governing documents (Firecrawl is the retrieval
   engine for every SEC download, rate-limited under SEC fair-access rules).
2. Read every value from its exact cell in the filed HTML and **certify** each period deterministically: balance
   identity, account roll-forwards, sources = uses, totals, units/signs, and continuity with the next period.
3. Split each family into calibration / validation / test **before** writing reference code; write the family's
   reference waterfall from the prospectus using calibration/validation only; freeze it (SHA-256); run it **once** on
   the test split. Only test periods it reproduces exactly can become tasks.
4. Remove every output (the fields the reference computes) from the graded report, scan every agent-visible file for
   leaked values, and compute baselines with the service's own grader.

The pipeline code is in [`tools/data-prep/`](tools/data-prep/); its downloads, intermediate tables and the frozen
reference waterfalls stay local.

## Repository

| Path | What |
|---|---|
| `dataset/tasks/` | the 100 task packets |
| `DATASET_CARD.md` | composition, provenance, certification, pass rates, baselines, deviations, limitations |
| `service/` | Valkyrie benchmark service: sandbox setup, in-sandbox grading, scoring (`full-html` dataset) |
| `tools/data-prep/` | data pipeline code (EDGAR retrieval, certification, splits, packets, leakage tests) |
| `tools/harbor-smoke/` | Harbor quickstart smoke task used to check the Valkyrie setup |
