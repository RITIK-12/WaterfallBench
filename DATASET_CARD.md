# WaterfallBench-Pilot — dataset card

ABS waterfall execution from SEC EDGAR Form 10-D servicer reports. Each task gives an agent the deal's governing documents, the complete servicer report of the preceding period, and the graded period's report with every output value removed; the agent must compute every output (money to the cent). The answer key is the amount the trustee reported.

## Task window

- Graded periods tagged `recent` were filed between 2026-07-01 and 2026-11-14, after the published training cutoffs of the evaluated models (fill in the table below). No task is claimed to be unseen by any model.
- `fallback`: all graded periods filed on/after 2026-01-01, at least one before 2026-07-01; `historical`: any earlier.

## Final allocation

- Tasks: **100**; window tags: {'fallback': 24, 'recent': 72, 'historical': 4}; `continuity_pending`: 41

|                                                    |   C1 |   C2 |
|:---------------------------------------------------|-----:|-----:|
| ('carmax_auto_owner_trust', 'auto_loan')           |   15 |    5 |
| ('john_deere_owner_trust', 'equipment')            |   15 |    5 |
| ('navient_student_loan_trust', 'student_loan')     |   15 |    5 |
| ('nissan_auto_lease_trust', 'auto_lease')          |   15 |    5 |
| ('world_omni_auto_receivables_trust', 'auto_loan') |   15 |    5 |

By category x window:

| category   |   fallback |   historical |   recent |
|:-----------|-----------:|-------------:|---------:|
| C1         |          3 |            0 |       72 |
| C2         |         21 |            4 |        0 |

## Baselines (deterministic, graded by the service's grader)

- copy-prior: fully resolved 0/100; mean line-item accuracy 64.3%
- all-zeros: fully resolved 0/100; mean line-item accuracy 44.8%
- Output fields per task: median 118, min 56, max 500; every graded period has >= 5 non-trivial fields.

## Leakage tests

- All final tasks passed: removed label paths absent; output-value scan; filenames; period limit (100/100).
- Packets built: 121; dropped by a gate: 0.

## Sources and crawl

- SEC EDGAR full-index/daily-index, 10-D/10-D/A full submissions, EDGAR submissions JSON, final prospectuses (424B) and closing 8-K agreement exhibits.
- Retrieved 2026-11-15 00:24 to 2026-11-15 03:06 UTC; 2,397 raw files with URL, accession, timestamp and SHA-256 in `provenance.jsonl`; raw downloads never overwritten.
- Firecrawl features used: `scrape` (rawHtml) for every sec.gov fetch, rate-gated to <= 8 request starts/second across all processes; JSON extraction (first passes only; see deviations). No other model API was called.

## Certification (Step 5), 2-year window

| family | periods | certified | anchoring | balance_identity | continuity | account_rollforward | cash_reconciliation | totals | units_signs | Firecrawl agreement (cross-check) |
|---|---|---|---|---|---|---|---|---|---|---|
| carmax_auto_owner_trust | 359 | 359 (100%) | 100% | 100% | 100% | 100% | 100% | 100% | 100% | 74.5% |
| john_deere_owner_trust | 226 | 224 (99%) | 100% | 100% | 100% | 100% | 100% | 100% | 100% | 99.7% |
| navient_student_loan_trust | 275 | 263 (96%) | 99% | 100% | 97% | 99% | 99% | 99% | 100% | n/a |
| nissan_auto_lease_trust | 93 | 79 (85%) | 99% | 98% | 98% | 100% | 90% | 87% | 100% | 77.0% |
| world_omni_auto_receivables_trust | 333 | 300 (90%) | 92% | 98% | 98% | 98% | 100% | 97% | 99% | 82.7% |

Balance identities:

- **carmax_auto_owner_trust**: end_balance[c] = beginning_balance[c] - principal_distribution[c]  (loss allocation, write-up, capitalised interest, cancellation: documented zero)
- **world_omni_auto_receivables_trust**: note_balance_after[c] = note_balance_before[c] - principal_paid[c]  (loss allocation, write-up, capitalised interest, cancellation: documented zero)
- **john_deere_owner_trust**: end_balance[c] = beginning_balance[c] - principal_distributable[c]  (beginning = prior period's ending; loss allocation, write-up, capitalised interest, cancellation: documented zero)
- **nissan_auto_lease_trust**: end_balance[c] = beginning_balance[c] - principal_payment[c]  (loss allocation, write-up, capitalised interest, cancellation: documented zero; certificates not reduced while notes are outstanding)
- **navient_student_loan_trust**: ending_principal_balance[c] = beginning_balance[c] - principal_paid[c]  (loss allocation, write-down/up, capitalised interest, cancellation, accretion: documented zero)

Deal parameters certified (all parameters of the deal anchored): carmax_auto_owner_trust 19/19, john_deere_owner_trust 12/12, navient_student_loan_trust 11/11, nissan_auto_lease_trust 6/6, world_omni_auto_receivables_trust 18/18

## Splits, references and the derivability filter (Step 7)

| family | split mode | calibration | validation | test | cal pass | val pass | test pass (single run) | eligible recent / fallback / historical | frozen SHA-256 |
|---|---|---|---|---|---|---|---|---|---|
| carmax_auto_owner_trust | default | 6 | 6 | 320 | 83.3% | 100.0% | 71.9% | 50 / 69 / 111 | `2494a0f03c5d430d…` |
| john_deere_owner_trust | default | 6 | 6 | 210 | 100.0% | 100.0% | 84.3% | 31 / 39 / 107 | `07d0740f59f4a4d4…` |
| navient_student_loan_trust | default | 6 | 6 | 247 | 83.3% | 100.0% | 68.4% | 35 / 38 / 96 | `6af085379695cd3a…` |
| nissan_auto_lease_trust | default | 6 | 6 | 67 | 100.0% | 100.0% | 68.7% | 12 / 9 / 25 | `063b1da262f4c090…` |
| world_omni_auto_receivables_trust | default | 6 | 6 | 285 | 100.0% | 100.0% | 70.2% | 45 / 57 / 98 | `bd865190b7e0b3bf…` |

Derivability selection effect: only test-split periods that the frozen family reference reproduced exactly (every output to the cent, from the packet's inputs) could become tasks. Periods the reference cannot handle (e.g. pro-rata rounding edge cases, first reports with no opening state) are excluded, so the benchmark measures periods a deterministic implementation of the documents can solve. Calibration and validation periods never become tasks. No family was withdrawn.

## Gates

- C3 stress_events, C4 amendment_audit and C5 master_trust_allocation: not built (scope decisions).
- C1 is recent-window only in the plan. Nissan Auto Lease Trust filed only 20 reports in the recent window and its frozen reference reproduces 12, so 3 of its C1 tasks come from the fallback window (Jan-Jun 2026) and are tagged `fallback` (deviation, user decision).

## Deviations from the plan

- **Scope: C1-C2 only.** C3 (stress events), C4 (amendment audit) and C5 (master trusts) dropped by the user. The plan's stress signals were rare in these families in the window; recent-window 10-D/A filings are almost all CMBS; C5 needs ~7 separate master-trust families. Target per family: 15 C1 + 5 C2.
- **Families.** 5 contract families x 20 tasks (user decision), not the plan's asset-class spread; no CMBS, credit card, dealer floorplan or utility/device families.
- **Per-family cap.** Up to 15 tasks per family per category (plan: 3); C2/C3 shortfalls go to C1 per the plan's allocation rule 3, and a family's own shortfall is covered by other families' passing reserves.
- **History window.** Reports from 2024-11-01 onward (~2 years) instead of 2016-01-01: enough for calibration/validation and every allowed task window.
- **Format.** Packets are SEC EDGAR HTML as filed: no markdown/PDF conversion and no excerpt variant (single dataset variant `full-html`; excerpt_derivable=false).
- **Firecrawl AI extraction.** Firecrawl is the retrieval engine for every SEC download. Its JSON extraction was run, then switched off (user decision): exact candidate agreement blocked certification for formatting reasons. The answer key never came from Firecrawl; certification uses the deterministic checks plus the frozen reference's exact recomputation; agreement statistics are kept below as a cross-check.
- **Parameter certification.** Deal parameters are certified from deterministic anchors in the final prospectus (text span or cover-table cell) without a Firecrawl candidate match.
- **Leakage scan scope.** The value scan covers graded-period reports, instructions, schema and filenames. The opening-state report is the complete prior-period report by design, so it is not scanned (prior outputs that repeat unchanged are marked trivial instead).
- **C3 signals.** Only the plan's five stress signals count. Family diagnostics outside that list (e.g. Navient principal-distribution shortfall) do not select C3 tasks.

## Known limitations

- Five contract families (2 prime auto loan, 1 equipment, 1 auto lease, 1 FFELP student loan): scores are clustered by family.
- Many output lines are zero or unchanged month to month (marked `trivial`); the headline metric is `fully_resolved` (every field exact).
- 1,669/17,006 (9.8%) of output fields equal an input amount printed in the same graded report (e.g. available funds = available collections). Under the plan's rule they are outputs (the reference computes them) and the value scan allows them because they sit in input cells, but they can be copied rather than computed.
- `continuity_pending` tasks: the next period's report did not exist at the snapshot, so cross-filing continuity is re-checked later.
- Prospectus parameters for some deals sit in closing agreements rather than the prospectus; references read such values from the prior period's report in the packet where the documents allow.

## Evaluated models' published training cutoffs (fill in at evaluation time)

| model | published training cutoff | all recent tasks filed after cutoff? |
|---|---|---|
| | | |
