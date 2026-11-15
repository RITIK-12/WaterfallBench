# WaterfallBench task `c1-nissanlease-2026-b-2026-09`

**Deal:** Nissan Auto Lease Trust 2026-B  
**Category:** C1 monthly_distribution

Compute every output field of ONE monthly distribution.

Files (all are SEC EDGAR HTML as filed):
- `/workspace/docs/`: the deal's governing documents (final prospectus; closing agreements where filed).
- `/workspace/reports/period_2026-08_opening_state.html`: the complete servicer report of the period before the first graded period.
- `/workspace/reports/period_2026-09_graded.html`: the servicer report for the distribution of 15-Oct-26, with every output value removed. Input values (collections, pool data, rates, beginning balances) remain.

Rules:
- Money: integer US cents, exactly to the cent as the trustee reports it (e.g. $1,234.56 -> 123456).
- Percentages and other decimals: the number as it would be printed, without a % sign.
- Statuses: one of the listed values.
- Apply the priority of payments and definitions in the governing documents; deal parameters come from those documents.

## Required output fields

| field | type | report line |
|---|---|---|
| `certificate_interest_on_interest_carryover_shortfall` | money_cents | Certificate Monthly Interest > Certificate Interest on Interest Carryover Shortfall |
| `certificate_monthly_available_interest_distribution_amount` | money_cents | Certificate Monthly Interest > Certificate Monthly Available Interest Distribution Amount |
| `certificate_monthly_interest_paid` | money_cents | Certificate Monthly Interest > Certificate Monthly Interest Paid |
| `certificates__ending_balance` | money_cents | SUMMARY > Certificates > Ending Balance |
| `certificates__interest_payment` | money_cents | SUMMARY > Certificates > Interest Payment |
| `certificates__interest_per_amt_face_amount` | decimal | SUMMARY > Certificates > Interest per $1000 Face Amount |
| `certificates__pool_factor` | decimal | SUMMARY > Certificates > Pool Factor |
| `certificates__principal_payment_due` | money_cents | SUMMARY > Certificates > Principal Payment Due |
| `certificates__principal_per_amt_face_amount` | decimal | SUMMARY > Certificates > Principal per $1000 Face Amount |
| `chg_in_certificate_int_carryover_shortfall` | money_cents | Certificate Monthly Interest > Chg in Certificate Int. Carryover Shortfall |
| `chg_in_class_a_1_notes_int_carryover_shortfall` | money_cents | Class A-1 Notes Monthly Interest > Chg in Class A-1 Notes Int. Carryover Shortfall |
| `chg_in_class_a_2a_notes_int_carryover_shortfall` | money_cents | Class A-2a Notes Monthly Interest > Chg in Class A-2a Notes Int. Carryover Shortfall |
| `chg_in_class_a_2b_notes_int_carryover_shortfall` | money_cents | Class A-2b Notes Monthly Interest > Chg in Class A-2b Notes Int. Carryover Shortfall |
| `chg_in_class_a_3_notes_int_carryover_shortfall` | money_cents | Class A-3 Notes Monthly Interest > Chg in Class A-3 Notes Int. Carryover Shortfall |
| `chg_in_class_a_4_notes_int_carryover_shortfall` | money_cents | Class A-4 Monthly Interest > Chg in Class A-4 Notes Int. Carryover Shortfall |
| `chg_in_class_b_notes_int_carryover_shortfall` | money_cents | Class B Monthly Interest > Chg in Class B Notes Int. Carryover Shortfall |
| `chg_in_class_c_notes_int_carryover_shortfall` | money_cents | Class C Monthly Interest > Chg in Class C Notes Int. Carryover Shortfall |
| `chg_in_total_certificateholders_principal_carryover_shortfall` | money_cents | Total Note and Certificate Monthly Interest > Chg in Total Certificateholders’ Principal Carryover Shortfall |
| `chg_in_total_note_and_certificate_int_carryover_shortfall` | money_cents | Total Note and Certificate Monthly Interest > Chg in Total Note and Certificate Int. Carryover Shortfall |
| `chg_in_total_noteholders_principal_carryover_shortfall` | money_cents | Total Note and Certificate Monthly Interest > Chg in Total Noteholders’ Principal Carryover Shortfall |
| `class_a_1_notes__ending_balance` | money_cents | SUMMARY > Class A-1 Notes > Ending Balance |
| `class_a_1_notes__interest_payment` | money_cents | SUMMARY > Class A-1 Notes > Interest Payment |
| `class_a_1_notes__interest_per_amt_face_amount` | decimal | SUMMARY > Class A-1 Notes > Interest per $1000 Face Amount |
| `class_a_1_notes__pool_factor` | decimal | SUMMARY > Class A-1 Notes > Pool Factor |
| `class_a_1_notes__principal_payment_due` | money_cents | SUMMARY > Class A-1 Notes > Principal Payment Due |
| `class_a_1_notes__principal_per_amt_face_amount` | decimal | SUMMARY > Class A-1 Notes > Principal per $1000 Face Amount |
| `class_a_1_notes_interest_on_interest_carryover_shortfall` | money_cents | Class A-1 Notes Monthly Interest > Class A-1 Notes Interest on Interest Carryover Shortfall |
| `class_a_1_notes_monthly_available_interest_distribution_amount` | money_cents | Class A-1 Notes Monthly Interest > Class A-1 Notes Monthly Available Interest Distribution Amount |
| `class_a_1_notes_monthly_interest_paid` | money_cents | Class A-1 Notes Monthly Interest > Class A-1 Notes Monthly Interest Paid |
| `class_a_2a_notes__ending_balance` | money_cents | SUMMARY > Class A-2a Notes > Ending Balance |
| `class_a_2a_notes__interest_payment` | money_cents | SUMMARY > Class A-2a Notes > Interest Payment |
| `class_a_2a_notes__interest_per_amt_face_amount` | decimal | SUMMARY > Class A-2a Notes > Interest per $1000 Face Amount |
| `class_a_2a_notes__pool_factor` | decimal | SUMMARY > Class A-2a Notes > Pool Factor |
| `class_a_2a_notes__principal_payment_due` | money_cents | SUMMARY > Class A-2a Notes > Principal Payment Due |
| `class_a_2a_notes__principal_per_amt_face_amount` | decimal | SUMMARY > Class A-2a Notes > Principal per $1000 Face Amount |
| `class_a_2a_notes_interest_on_interest_carryover_shortfall` | money_cents | Class A-2a Notes Monthly Interest > Class A-2a Notes Interest on Interest Carryover Shortfall |
| `class_a_2a_notes_monthly_available_interest_distribution_amount` | money_cents | Class A-2a Notes Monthly Interest > Class A-2a Notes Monthly Available Interest Distribution Amount |
| `class_a_2a_notes_monthly_interest_paid` | money_cents | Class A-2a Notes Monthly Interest > Class A-2a Notes Monthly Interest Paid |
| `class_a_2b_notes__ending_balance` | money_cents | SUMMARY > Class A-2b Notes > Ending Balance |
| `class_a_2b_notes__interest_payment` | money_cents | SUMMARY > Class A-2b Notes > Interest Payment |
| `class_a_2b_notes__interest_per_amt_face_amount` | decimal | SUMMARY > Class A-2b Notes > Interest per $1000 Face Amount |
| `class_a_2b_notes__pool_factor` | decimal | SUMMARY > Class A-2b Notes > Pool Factor |
| `class_a_2b_notes__principal_payment_due` | money_cents | SUMMARY > Class A-2b Notes > Principal Payment Due |
| `class_a_2b_notes__principal_per_amt_face_amount` | decimal | SUMMARY > Class A-2b Notes > Principal per $1000 Face Amount |
| `class_a_2b_notes_interest_on_interest_carryover_shortfall` | money_cents | Class A-2b Notes Monthly Interest > Class A-2b Notes Interest on Interest Carryover Shortfall |
| `class_a_2b_notes_monthly_available_interest_distribution_amount` | money_cents | Class A-2b Notes Monthly Interest > Class A-2b Notes Monthly Available Interest Distribution Amount |
| `class_a_2b_notes_monthly_interest_paid` | money_cents | Class A-2b Notes Monthly Interest > Class A-2b Notes Monthly Interest Paid |
| `class_a_3_notes__ending_balance` | money_cents | SUMMARY > Class A-3 Notes > Ending Balance |
| `class_a_3_notes__interest_payment` | money_cents | SUMMARY > Class A-3 Notes > Interest Payment |
| `class_a_3_notes__interest_per_amt_face_amount` | decimal | SUMMARY > Class A-3 Notes > Interest per $1000 Face Amount |
| `class_a_3_notes__pool_factor` | decimal | SUMMARY > Class A-3 Notes > Pool Factor |
| `class_a_3_notes__principal_payment_due` | money_cents | SUMMARY > Class A-3 Notes > Principal Payment Due |
| `class_a_3_notes__principal_per_amt_face_amount` | decimal | SUMMARY > Class A-3 Notes > Principal per $1000 Face Amount |
| `class_a_3_notes_interest_on_interest_carryover_shortfall` | money_cents | Class A-3 Notes Monthly Interest > Class A-3 Notes Interest on Interest Carryover Shortfall |
| `class_a_3_notes_monthly_available_interest_distribution_amount` | money_cents | Class A-3 Notes Monthly Interest > Class A-3 Notes Monthly Available Interest Distribution Amount |
| `class_a_3_notes_monthly_interest_paid` | money_cents | Class A-3 Notes Monthly Interest > Class A-3 Notes Monthly Interest Paid |
| `class_a_4_notes__ending_balance` | money_cents | SUMMARY > Class A-4 Notes > Ending Balance |
| `class_a_4_notes__interest_payment` | money_cents | SUMMARY > Class A-4 Notes > Interest Payment |
| `class_a_4_notes__interest_per_amt_face_amount` | decimal | SUMMARY > Class A-4 Notes > Interest per $1000 Face Amount |
| `class_a_4_notes__pool_factor` | decimal | SUMMARY > Class A-4 Notes > Pool Factor |
| `class_a_4_notes__principal_payment_due` | money_cents | SUMMARY > Class A-4 Notes > Principal Payment Due |
| `class_a_4_notes__principal_per_amt_face_amount` | decimal | SUMMARY > Class A-4 Notes > Principal per $1000 Face Amount |
| `class_a_4_notes_interest_on_interest_carryover_shortfall` | money_cents | Class A-4 Monthly Interest > Class A-4 Notes Interest on Interest Carryover Shortfall |
| `class_a_4_notes_monthly_available_interest_distribution_amount` | money_cents | Class A-4 Monthly Interest > Class A-4 Notes Monthly Available Interest Distribution Amount |
| `class_a_4_notes_monthly_interest_paid` | money_cents | Class A-4 Monthly Interest > Class A-4 Notes Monthly Interest Paid |
| `class_b_notes__ending_balance` | money_cents | SUMMARY > Class B Notes > Ending Balance |
| `class_b_notes__interest_payment` | money_cents | SUMMARY > Class B Notes > Interest Payment |
| `class_b_notes__interest_per_amt_face_amount` | decimal | SUMMARY > Class B Notes > Interest per $1000 Face Amount |
| `class_b_notes__pool_factor` | decimal | SUMMARY > Class B Notes > Pool Factor |
| `class_b_notes__principal_payment_due` | money_cents | SUMMARY > Class B Notes > Principal Payment Due |
| `class_b_notes__principal_per_amt_face_amount` | decimal | SUMMARY > Class B Notes > Principal per $1000 Face Amount |
| `class_b_notes_interest_on_interest_carryover_shortfall` | money_cents | Class B Monthly Interest > Class B Notes Interest on Interest Carryover Shortfall |
| `class_b_notes_monthly_available_interest_distribution_amount` | money_cents | Class B Monthly Interest > Class B Notes Monthly Available Interest Distribution Amount |
| `class_b_notes_monthly_interest_paid` | money_cents | Class B Monthly Interest > Class B Notes Monthly Interest Paid |
| `class_c_notes__ending_balance` | money_cents | SUMMARY > Class C Notes > Ending Balance |
| `class_c_notes__interest_payment` | money_cents | SUMMARY > Class C Notes > Interest Payment |
| `class_c_notes__interest_per_amt_face_amount` | decimal | SUMMARY > Class C Notes > Interest per $1000 Face Amount |
| `class_c_notes__pool_factor` | decimal | SUMMARY > Class C Notes > Pool Factor |
| `class_c_notes__principal_payment_due` | money_cents | SUMMARY > Class C Notes > Principal Payment Due |
| `class_c_notes__principal_per_amt_face_amount` | decimal | SUMMARY > Class C Notes > Principal per $1000 Face Amount |
| `class_c_notes_interest_on_interest_carryover_shortfall` | money_cents | Class C Monthly Interest > Class C Notes Interest on Interest Carryover Shortfall |
| `class_c_notes_monthly_available_interest_distribution_amount` | money_cents | Class C Monthly Interest > Class C Notes Monthly Available Interest Distribution Amount |
| `class_c_notes_monthly_interest_paid` | money_cents | Class C Monthly Interest > Class C Notes Monthly Interest Paid |
| `deposit_of_remaining_available_collections` | money_cents | IV. RESERVE ACCOUNT > Deposit of Remaining Available Collections |
| `ending_balance_of_payment_advance` | money_cents | VI. RECONCILIATION OF ADVANCES > Ending Balance of Payment Advance |
| `ending_balance_of_residual_advance` | money_cents | VI. RECONCILIATION OF ADVANCES > Ending Balance of Residual Advance |
| `gross_reserve_account_balance` | money_cents | IV. RESERVE ACCOUNT > Gross Reserve Account Balance |
| `remaining_available_collections` | money_cents | Total Note and Certificate Monthly Interest > Remaining Available Collections |
| `remaining_available_collections_released_to_seller` | money_cents | IV. RESERVE ACCOUNT > Remaining Available Collections Released to Seller |
| `required_reserve_account_amount` | money_cents | IV. RESERVE ACCOUNT > Required Reserve Account Amount |
| `reserve_amounts_available_for_distribution` | money_cents | III. DISTRIBUTIONS > Reserve Amounts Available for Distribution |
| `reserve_fund_available_for_distribution` | money_cents | IV. RESERVE ACCOUNT > Reserve Fund Available for Distribution |
| `reserve_fund_draw_amount` | money_cents | IV. RESERVE ACCOUNT > Reserve Fund Draw Amount |
| `servicing_fee_due` | money_cents | III. DISTRIBUTIONS > Servicing Fee Due |
| `servicing_fee_paid` | money_cents | III. DISTRIBUTIONS > Servicing Fee Paid |
| `servicing_fee_shortfall` | money_cents | III. DISTRIBUTIONS > Servicing Fee Shortfall |
| `total_available_for_distribution` | money_cents | III. DISTRIBUTIONS > Total Available for Distribution |
| `total_available_for_principal_distribution` | money_cents | Total Note and Certificate Monthly Interest > Total Available for Principal Distribution |
| `total_certificateholders_principal_distributable_amount` | money_cents | Total Note and Certificate Monthly Interest > Total Certificateholders’ Principal Distributable Amount |
| `total_ending_reserve_account_balance` | money_cents | IV. RESERVE ACCOUNT > Total Ending Reserve Account Balance |
| `total_monthly_principal_paid_on_the_certificates` | money_cents | Total Note and Certificate Monthly Interest > Total Monthly Principal Paid on the Certificates |
| `total_monthly_principal_paid_on_the_notes` | money_cents | Total Note and Certificate Monthly Interest > Total Monthly Principal Paid on the Notes |
| `total_note_and_certificate_monthly_interest_due` | money_cents | Total Note and Certificate Monthly Interest > Total Note and Certificate Monthly Interest Due |
| `total_note_and_certificate_monthly_interest_paid` | money_cents | Total Note and Certificate Monthly Interest > Total Note and Certificate Monthly Interest Paid |
| `total_noteholders_principal_distributable_amount` | money_cents | Total Note and Certificate Monthly Interest > Total Noteholders’ Principal Distributable Amount |
| `total_portfolio__pool_factor` | decimal | SUMMARY > Total Portfolio > Pool Factor |
| `total_securities__beginning_balance` | money_cents | SUMMARY > Total Securities > Beginning Balance |
| `total_securities__ending_balance` | money_cents | SUMMARY > Total Securities > Ending Balance |
| `total_securities__interest_payment` | money_cents | SUMMARY > Total Securities > Interest Payment |
| `total_securities__pool_factor` | decimal | SUMMARY > Total Securities > Pool Factor |
| `total_securities__principal_payment_due` | money_cents | SUMMARY > Total Securities > Principal Payment Due |
| `total_trustee_advances_and_servicing_fee_paid` | money_cents | III. DISTRIBUTIONS > Total Trustee, Advances and Servicing Fee Paid |

## Answer

Write `/workspace/answer.json` as {"<field>": <value>, ...}, matching `/workspace/answer_schema.json`.
