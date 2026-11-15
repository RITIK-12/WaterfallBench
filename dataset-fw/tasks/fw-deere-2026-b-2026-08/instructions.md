# WaterfallBench first-distribution task `fw-deere-2026-b-2026-08`

**Deal:** John Deere Owner Trust 2026-B  
**Distribution:** the trust's first distribution date (2026-08)

This is the first payment date after the closing date, so there is no prior servicer report. Opening balances are the initial balances in the governing documents.

Files (SEC EDGAR HTML as filed):
- `/workspace/docs/`: the final prospectus and the closing agreements.
- `/workspace/reports/period_2026-08_graded.html`: this distribution's servicer report with every waterfall result removed. Collections, pool data, rates and dates remain.

Apply the priority of payments and the definitions in the governing documents and compute:

| field | meaning |
|---|---|
| `servicing_fee_paid` | servicing fee paid on this distribution date |
| `reserve_ending_balance` | reserve account balance after this date's deposits and withdrawals |
| `released_to_residual` | amount released from available funds to the certificateholders / seller after all required payments (excluding any reserve account release) |
| `classes` | one entry per class of notes the trust issued (certificates are not a note class) |
| `classes[].class` | the class name as the prospectus gives it, e.g. `A-1` |
| `classes[].interest_paid` | interest paid to the class on this date |
| `classes[].principal_paid` | principal paid to the class on this date |
| `classes[].ending_balance` | the class's outstanding principal balance after this date's distributions |

Money is integer US cents (e.g. $1,234.56 -> 123456). Write `/workspace/answer.json` as one JSON object matching `/workspace/answer_schema.json`, listing every class of notes exactly once.
