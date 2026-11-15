# WaterfallBench task `c2-navient-2014-4-2026-03`

**Deal:** Navient Student Loan Trust 2014-4  
**Category:** C2 rollforward_4p

Compute every output field of FOUR consecutive monthly distributions, starting from the opening state only.

Files (all are SEC EDGAR HTML as filed):
- `/workspace/docs/`: the deal's governing documents (final prospectus; closing agreements where filed).
- `/workspace/reports/period_2026-02_opening_state.html`: the complete servicer report of the period before the first graded period.
- `/workspace/reports/period_2026-03_graded.html`: the servicer report for the distribution of 04/27/2026, with every output value removed. Input values (collections, pool data, rates, beginning balances) remain.
- `/workspace/reports/period_2026-04_graded.html`: the servicer report for the distribution of 05/26/2026, with every output value removed. Input values (collections, pool data, rates, beginning balances) remain. Beginning balances and carryovers are also removed: they equal your results for the previous period.
- `/workspace/reports/period_2026-05_graded.html`: the servicer report for the distribution of 06/25/2026, with every output value removed. Input values (collections, pool data, rates, beginning balances) remain. Beginning balances and carryovers are also removed: they equal your results for the previous period.
- `/workspace/reports/period_2026-06_graded.html`: the servicer report for the distribution of 07/27/2026, with every output value removed. Input values (collections, pool data, rates, beginning balances) remain. Beginning balances and carryovers are also removed: they equal your results for the previous period.

Rules:
- Money: integer US cents, exactly to the cent as the trustee reports it (e.g. $1,234.56 -> 123456).
- Percentages and other decimals: the number as it would be printed, without a % sign.
- Statuses: one of the listed values.
- Apply the priority of payments and definitions in the governing documents; deal parameters come from those documents.

## Required output fields — period_1

| field | type | report line |
|---|---|---|
| `a_63938qaa5__date__2` | money_cents | A 63938QAA5 > 04/27/2026 |
| `a_trustee_fees__remaining_funds_balance` | money_cents | A Trustee Fees > Remaining Funds Balance |
| `accrued_interest_factor__date` | decimal | Accrued Interest Factor > 4/27/2026 |
| `accrued_interest_factor__date__2` | decimal | Accrued Interest Factor > 4/27/2026 |
| `adjusted_pool_1__date__3` | money_cents | Adjusted Pool (1) > 03/31/2026 |
| `adjusted_pool_balance` | money_cents | Adjusted Pool Balance |
| `adjusted_pool_balance_supplemental_loan_purchase__date__2` | money_cents | Adjusted Pool Balance + Supplemental Loan Purchase > 04/27/2026 |
| `b_63938qab3__date__2` | money_cents | B 63938QAB3 > 04/27/2026 |
| `b_primary_servicing_fee__remaining_funds_balance` | money_cents | B Primary Servicing Fee > Remaining Funds Balance |
| `balance_available` | money_cents | Balance Available |
| `c_administration_fee__paid` | money_cents | C Administration Fee > Paid |
| `c_administration_fee__remaining_funds_balance` | money_cents | C Administration Fee > Remaining Funds Balance |
| `c_reserves_in_excess_of_requirement` | money_cents | C Reserves in Excess of Requirement |
| `capitalized_interest_account_balance__date__2` | money_cents | Capitalized Interest Account Balance > 04/27/2026 |
| `current_interest_due__date` | money_cents | Current Interest Due > 4/27/2026 |
| `current_interest_due__date__2` | money_cents | Current Interest Due > 4/27/2026 |
| `d_class_a_noteholders_interest_distribution_amount__paid` | money_cents | D Class A Noteholders' Interest Distribution Amount > Paid |
| `d_class_a_noteholders_interest_distribution_amount__remaining_funds_balance` | money_cents | D Class A Noteholders' Interest Distribution Amount > Remaining Funds Balance |
| `d_reserve_account_balance_after_any_reinstatement` | money_cents | D Reserve Account Balance (after any reinstatement) |
| `difference__date__2` | money_cents | Difference > 04/27/2026 |
| `e_class_b_noteholders_interest_distribution_amount__paid` | money_cents | E Class B Noteholders' Interest Distribution Amount > Paid |
| `e_class_b_noteholders_interest_distribution_amount__remaining_funds_balance` | money_cents | E Class B Noteholders' Interest Distribution Amount > Remaining Funds Balance |
| `e_less_specified_reserve_account_balance` | money_cents | E Less: Specified Reserve Account Balance |
| `ending_balance` | money_cents | Ending Balance |
| `ending_balance__2` | money_cents | Ending Balance |
| `ending_principal_balance__date` | money_cents | Ending Principal Balance > 4/27/2026 |
| `ending_principal_balance__date__2` | money_cents | Ending Principal Balance > 4/27/2026 |
| `ending_reserve_account_balance` | money_cents | Ending Reserve Account Balance |
| `f_reserve_account_reinstatement__paid` | money_cents | F Reserve Account Reinstatement > Paid |
| `f_reserve_account_reinstatement__remaining_funds_balance` | money_cents | F Reserve Account Reinstatement > Remaining Funds Balance |
| `f_total` | money_cents | F Total |
| `floor_income_rebate_account__date__2` | money_cents | Floor Income Rebate Account > 04/27/2026 |
| `g_class_a_noteholders_principal_distribution_amount__paid` | money_cents | G Class A Noteholders' Principal Distribution Amount > Paid |
| `g_class_a_noteholders_principal_distribution_amount__remaining_funds_balance` | money_cents | G Class A Noteholders' Principal Distribution Amount > Remaining Funds Balance |
| `g_class_a_notes_outstanding_after_application_of_available_funds` | money_cents | G Class A Notes Outstanding (after application of available funds) |
| `h_class_b_noteholders_principal_distribution_amount__paid` | money_cents | H Class B Noteholders' Principal Distribution Amount > Paid |
| `h_class_b_noteholders_principal_distribution_amount__remaining_funds_balance` | money_cents | H Class B Noteholders' Principal Distribution Amount > Remaining Funds Balance |
| `i_unpaid_expenses_of_the_trustees__remaining_funds_balance` | money_cents | I Unpaid Expenses of The Trustees > Remaining Funds Balance |
| `interest_paid__date` | money_cents | Interest Paid > 4/27/2026 |
| `interest_paid__date__2` | money_cents | Interest Paid > 4/27/2026 |
| `interest_shortfall__date` | money_cents | Interest Shortfall > 4/27/2026 |
| `interest_shortfall__date__2` | money_cents | Interest Shortfall > 4/27/2026 |
| `j_carryover_servicing_fee__remaining_funds_balance` | money_cents | J Carryover Servicing Fee > Remaining Funds Balance |
| `k_remaining_amounts_to_the_noteholders_after_the_first_auction_date__paid` | money_cents | K Remaining Amounts to the Noteholders after the first auction date > Paid |
| `k_remaining_amounts_to_the_noteholders_after_the_first_auction_date__remaining_funds_balance` | money_cents | K Remaining Amounts to the Noteholders after the first auction date > Remaining Funds Balance |
| `l_excess_distribution_certificateholder__paid` | money_cents | L Excess Distribution Certificateholder > Paid |
| `l_excess_distribution_certificateholder__remaining_funds_balance` | money_cents | L Excess Distribution Certificateholder > Remaining Funds Balance |
| `m_available_funds` | money_cents | M AVAILABLE FUNDS |
| `note_interest_shortfall__date` | money_cents | Note Interest Shortfall > 03/31/2026 |
| `note_principal_shortfall__date` | money_cents | Note Principal Shortfall > 03/31/2026 |
| `notes_outstanding_principal_balance` | money_cents | Notes Outstanding Principal Balance |
| `overcollateralization_amount` | money_cents | Overcollateralization Amount |
| `parity_ratio__date__2` | decimal | Parity Ratio > 04/27/2026 |
| `principal_distribution_amount` | money_cents | Principal Distribution Amount |
| `principal_distribution_amount_paid` | money_cents | Principal Distribution Amount Paid |
| `principal_paid__date` | money_cents | Principal Paid > 4/27/2026 |
| `principal_paid__date__2` | money_cents | Principal Paid > 4/27/2026 |
| `release_to_collection_account` | money_cents | Release to Collection Account |
| `release_to_collection_account__2` | money_cents | Release to Collection Account |
| `required_reserve_acct_balance` | money_cents | Required Reserve Acct Balance |
| `reserve_account_balance__date__2` | money_cents | Reserve Account Balance > 04/27/2026 |
| `reserve_funds_reinstated` | money_cents | Reserve Funds Reinstated |
| `reserve_funds_utilized` | money_cents | Reserve Funds Utilized |
| `supplemental_loan_purchase_account__date__2` | money_cents | Supplemental Loan Purchase Account > 04/27/2026 |
| `supplemental_loan_purchases` | money_cents | Supplemental Loan Purchases |
| `total_available_funds__remaining_funds_balance` | money_cents | Total Available Funds > Remaining Funds Balance |
| `total_interest_due__date` | money_cents | Total Interest Due > 4/27/2026 |
| `total_interest_due__date__2` | money_cents | Total Interest Due > 4/27/2026 |
| `total_interest_receipts` | money_cents | Total Interest Receipts |
| `total_notes__date__2` | money_cents | Total Notes > 04/27/2026 |
| `total_principal_receipts` | money_cents | Total Principal Receipts |
| `transfers_to_collection_account` | money_cents | Transfers to Collection Account |
| `unpaid_administration_fees__date` | money_cents | Unpaid Administration Fees > 03/31/2026 |

## Required output fields — period_2

| field | type | report line |
|---|---|---|
| `a_63938qaa5__date__2` | money_cents | A 63938QAA5 > 05/26/2026 |
| `a_trustee_fees__remaining_funds_balance` | money_cents | A Trustee Fees > Remaining Funds Balance |
| `accrued_interest_factor__date` | decimal | Accrued Interest Factor > 5/26/2026 |
| `accrued_interest_factor__date__2` | decimal | Accrued Interest Factor > 5/26/2026 |
| `adjusted_pool_1__date__3` | money_cents | Adjusted Pool (1) > 04/30/2026 |
| `adjusted_pool_balance` | money_cents | Adjusted Pool Balance |
| `adjusted_pool_balance_supplemental_loan_purchase__date__2` | money_cents | Adjusted Pool Balance + Supplemental Loan Purchase > 05/26/2026 |
| `b_63938qab3__date__2` | money_cents | B 63938QAB3 > 05/26/2026 |
| `b_primary_servicing_fee__remaining_funds_balance` | money_cents | B Primary Servicing Fee > Remaining Funds Balance |
| `balance_available` | money_cents | Balance Available |
| `c_administration_fee__paid` | money_cents | C Administration Fee > Paid |
| `c_administration_fee__remaining_funds_balance` | money_cents | C Administration Fee > Remaining Funds Balance |
| `c_reserves_in_excess_of_requirement` | money_cents | C Reserves in Excess of Requirement |
| `capitalized_interest_account_balance__date__2` | money_cents | Capitalized Interest Account Balance > 05/26/2026 |
| `current_interest_due__date` | money_cents | Current Interest Due > 5/26/2026 |
| `current_interest_due__date__2` | money_cents | Current Interest Due > 5/26/2026 |
| `d_class_a_noteholders_interest_distribution_amount__paid` | money_cents | D Class A Noteholders' Interest Distribution Amount > Paid |
| `d_class_a_noteholders_interest_distribution_amount__remaining_funds_balance` | money_cents | D Class A Noteholders' Interest Distribution Amount > Remaining Funds Balance |
| `d_reserve_account_balance_after_any_reinstatement` | money_cents | D Reserve Account Balance (after any reinstatement) |
| `difference__date__2` | money_cents | Difference > 05/26/2026 |
| `e_class_b_noteholders_interest_distribution_amount__paid` | money_cents | E Class B Noteholders' Interest Distribution Amount > Paid |
| `e_class_b_noteholders_interest_distribution_amount__remaining_funds_balance` | money_cents | E Class B Noteholders' Interest Distribution Amount > Remaining Funds Balance |
| `e_less_specified_reserve_account_balance` | money_cents | E Less: Specified Reserve Account Balance |
| `ending_balance` | money_cents | Ending Balance |
| `ending_balance__2` | money_cents | Ending Balance |
| `ending_principal_balance__date` | money_cents | Ending Principal Balance > 5/26/2026 |
| `ending_principal_balance__date__2` | money_cents | Ending Principal Balance > 5/26/2026 |
| `ending_reserve_account_balance` | money_cents | Ending Reserve Account Balance |
| `f_reserve_account_reinstatement__paid` | money_cents | F Reserve Account Reinstatement > Paid |
| `f_reserve_account_reinstatement__remaining_funds_balance` | money_cents | F Reserve Account Reinstatement > Remaining Funds Balance |
| `f_total` | money_cents | F Total |
| `floor_income_rebate_account__date__2` | money_cents | Floor Income Rebate Account > 05/26/2026 |
| `g_class_a_noteholders_principal_distribution_amount__paid` | money_cents | G Class A Noteholders' Principal Distribution Amount > Paid |
| `g_class_a_noteholders_principal_distribution_amount__remaining_funds_balance` | money_cents | G Class A Noteholders' Principal Distribution Amount > Remaining Funds Balance |
| `g_class_a_notes_outstanding_after_application_of_available_funds` | money_cents | G Class A Notes Outstanding (after application of available funds) |
| `h_class_b_noteholders_principal_distribution_amount__paid` | money_cents | H Class B Noteholders' Principal Distribution Amount > Paid |
| `h_class_b_noteholders_principal_distribution_amount__remaining_funds_balance` | money_cents | H Class B Noteholders' Principal Distribution Amount > Remaining Funds Balance |
| `i_unpaid_expenses_of_the_trustees__remaining_funds_balance` | money_cents | I Unpaid Expenses of The Trustees > Remaining Funds Balance |
| `interest_paid__date` | money_cents | Interest Paid > 5/26/2026 |
| `interest_paid__date__2` | money_cents | Interest Paid > 5/26/2026 |
| `interest_shortfall__date` | money_cents | Interest Shortfall > 5/26/2026 |
| `interest_shortfall__date__2` | money_cents | Interest Shortfall > 5/26/2026 |
| `j_carryover_servicing_fee__remaining_funds_balance` | money_cents | J Carryover Servicing Fee > Remaining Funds Balance |
| `k_remaining_amounts_to_the_noteholders_after_the_first_auction_date__paid` | money_cents | K Remaining Amounts to the Noteholders after the first auction date > Paid |
| `k_remaining_amounts_to_the_noteholders_after_the_first_auction_date__remaining_funds_balance` | money_cents | K Remaining Amounts to the Noteholders after the first auction date > Remaining Funds Balance |
| `l_excess_distribution_certificateholder__paid` | money_cents | L Excess Distribution Certificateholder > Paid |
| `l_excess_distribution_certificateholder__remaining_funds_balance` | money_cents | L Excess Distribution Certificateholder > Remaining Funds Balance |
| `m_available_funds` | money_cents | M AVAILABLE FUNDS |
| `note_interest_shortfall__date` | money_cents | Note Interest Shortfall > 04/30/2026 |
| `note_principal_shortfall__date` | money_cents | Note Principal Shortfall > 04/30/2026 |
| `notes_outstanding_principal_balance` | money_cents | Notes Outstanding Principal Balance |
| `overcollateralization_amount` | money_cents | Overcollateralization Amount |
| `parity_ratio__date__2` | decimal | Parity Ratio > 05/26/2026 |
| `principal_distribution_amount` | money_cents | Principal Distribution Amount |
| `principal_distribution_amount_paid` | money_cents | Principal Distribution Amount Paid |
| `principal_paid__date` | money_cents | Principal Paid > 5/26/2026 |
| `principal_paid__date__2` | money_cents | Principal Paid > 5/26/2026 |
| `release_to_collection_account` | money_cents | Release to Collection Account |
| `release_to_collection_account__2` | money_cents | Release to Collection Account |
| `required_reserve_acct_balance` | money_cents | Required Reserve Acct Balance |
| `reserve_account_balance__date__2` | money_cents | Reserve Account Balance > 05/26/2026 |
| `reserve_funds_reinstated` | money_cents | Reserve Funds Reinstated |
| `reserve_funds_utilized` | money_cents | Reserve Funds Utilized |
| `supplemental_loan_purchase_account__date__2` | money_cents | Supplemental Loan Purchase Account > 05/26/2026 |
| `supplemental_loan_purchases` | money_cents | Supplemental Loan Purchases |
| `total_available_funds__remaining_funds_balance` | money_cents | Total Available Funds > Remaining Funds Balance |
| `total_interest_due__date` | money_cents | Total Interest Due > 5/26/2026 |
| `total_interest_due__date__2` | money_cents | Total Interest Due > 5/26/2026 |
| `total_interest_receipts` | money_cents | Total Interest Receipts |
| `total_notes__date__2` | money_cents | Total Notes > 05/26/2026 |
| `total_principal_receipts` | money_cents | Total Principal Receipts |
| `transfers_to_collection_account` | money_cents | Transfers to Collection Account |
| `unpaid_administration_fees__date` | money_cents | Unpaid Administration Fees > 04/30/2026 |

## Required output fields — period_3

| field | type | report line |
|---|---|---|
| `a_63938qaa5__date__2` | money_cents | A 63938QAA5 > 06/25/2026 |
| `a_trustee_fees__remaining_funds_balance` | money_cents | A Trustee Fees > Remaining Funds Balance |
| `accrued_interest_factor__date` | decimal | Accrued Interest Factor > 6/25/2026 |
| `accrued_interest_factor__date__2` | decimal | Accrued Interest Factor > 6/25/2026 |
| `adjusted_pool_1__date__3` | money_cents | Adjusted Pool (1) > 05/31/2026 |
| `adjusted_pool_balance` | money_cents | Adjusted Pool Balance |
| `adjusted_pool_balance_supplemental_loan_purchase__date__2` | money_cents | Adjusted Pool Balance + Supplemental Loan Purchase > 06/25/2026 |
| `b_63938qab3__date__2` | money_cents | B 63938QAB3 > 06/25/2026 |
| `b_primary_servicing_fee__remaining_funds_balance` | money_cents | B Primary Servicing Fee > Remaining Funds Balance |
| `balance_available` | money_cents | Balance Available |
| `c_administration_fee__paid` | money_cents | C Administration Fee > Paid |
| `c_administration_fee__remaining_funds_balance` | money_cents | C Administration Fee > Remaining Funds Balance |
| `c_reserves_in_excess_of_requirement` | money_cents | C Reserves in Excess of Requirement |
| `capitalized_interest_account_balance__date__2` | money_cents | Capitalized Interest Account Balance > 06/25/2026 |
| `current_interest_due__date` | money_cents | Current Interest Due > 6/25/2026 |
| `current_interest_due__date__2` | money_cents | Current Interest Due > 6/25/2026 |
| `d_class_a_noteholders_interest_distribution_amount__paid` | money_cents | D Class A Noteholders’ Interest Distribution Amount > Paid |
| `d_class_a_noteholders_interest_distribution_amount__remaining_funds_balance` | money_cents | D Class A Noteholders’ Interest Distribution Amount > Remaining Funds Balance |
| `d_reserve_account_balance_after_any_reinstatement` | money_cents | D Reserve Account Balance (after any reinstatement) |
| `difference__date__2` | money_cents | Difference > 06/25/2026 |
| `e_class_b_noteholders_interest_distribution_amount__paid` | money_cents | E Class B Noteholders’ Interest Distribution Amount > Paid |
| `e_class_b_noteholders_interest_distribution_amount__remaining_funds_balance` | money_cents | E Class B Noteholders’ Interest Distribution Amount > Remaining Funds Balance |
| `e_less_specified_reserve_account_balance` | money_cents | E Less: Specified Reserve Account Balance |
| `ending_balance` | money_cents | Ending Balance |
| `ending_balance__2` | money_cents | Ending Balance |
| `ending_principal_balance__date` | money_cents | Ending Principal Balance > 6/25/2026 |
| `ending_principal_balance__date__2` | money_cents | Ending Principal Balance > 6/25/2026 |
| `ending_reserve_account_balance` | money_cents | Ending Reserve Account Balance |
| `f_reserve_account_reinstatement__paid` | money_cents | F Reserve Account Reinstatement > Paid |
| `f_reserve_account_reinstatement__remaining_funds_balance` | money_cents | F Reserve Account Reinstatement > Remaining Funds Balance |
| `f_total` | money_cents | F Total |
| `floor_income_rebate_account__date__2` | money_cents | Floor Income Rebate Account > 06/25/2026 |
| `g_class_a_noteholders_principal_distribution_amount__paid` | money_cents | G Class A Noteholders’ Principal Distribution Amount > Paid |
| `g_class_a_noteholders_principal_distribution_amount__remaining_funds_balance` | money_cents | G Class A Noteholders’ Principal Distribution Amount > Remaining Funds Balance |
| `g_class_a_notes_outstanding_after_application_of_available_funds` | money_cents | G Class A Notes Outstanding (after application of available funds) |
| `h_class_b_noteholders_principal_distribution_amount__paid` | money_cents | H Class B Noteholders’ Principal Distribution Amount > Paid |
| `h_class_b_noteholders_principal_distribution_amount__remaining_funds_balance` | money_cents | H Class B Noteholders’ Principal Distribution Amount > Remaining Funds Balance |
| `i_unpaid_expenses_of_the_trustees__remaining_funds_balance` | money_cents | I Unpaid Expenses of The Trustees > Remaining Funds Balance |
| `interest_paid__date` | money_cents | Interest Paid > 6/25/2026 |
| `interest_paid__date__2` | money_cents | Interest Paid > 6/25/2026 |
| `interest_shortfall__date` | money_cents | Interest Shortfall > 6/25/2026 |
| `interest_shortfall__date__2` | money_cents | Interest Shortfall > 6/25/2026 |
| `j_carryover_servicing_fee__remaining_funds_balance` | money_cents | J Carryover Servicing Fee > Remaining Funds Balance |
| `k_remaining_amounts_to_the_noteholders_after_the_first_auction_date__paid` | money_cents | K Remaining Amounts to the Noteholders after the first auction date > Paid |
| `k_remaining_amounts_to_the_noteholders_after_the_first_auction_date__remaining_funds_balance` | money_cents | K Remaining Amounts to the Noteholders after the first auction date > Remaining Funds Balance |
| `l_excess_distribution_certificateholder__paid` | money_cents | L Excess Distribution Certificateholder > Paid |
| `l_excess_distribution_certificateholder__remaining_funds_balance` | money_cents | L Excess Distribution Certificateholder > Remaining Funds Balance |
| `m_available_funds` | money_cents | M AVAILABLE FUNDS |
| `note_interest_shortfall__date` | money_cents | Note Interest Shortfall > 05/31/2026 |
| `note_principal_shortfall__date` | money_cents | Note Principal Shortfall > 05/31/2026 |
| `notes_outstanding_principal_balance` | money_cents | Notes Outstanding Principal Balance |
| `overcollateralization_amount` | money_cents | Overcollateralization Amount |
| `parity_ratio__date__2` | decimal | Parity Ratio > 06/25/2026 |
| `principal_distribution_amount` | money_cents | Principal Distribution Amount |
| `principal_distribution_amount_paid` | money_cents | Principal Distribution Amount Paid |
| `principal_paid__date` | money_cents | Principal Paid > 6/25/2026 |
| `principal_paid__date__2` | money_cents | Principal Paid > 6/25/2026 |
| `release_to_collection_account` | money_cents | Release to Collection Account |
| `release_to_collection_account__2` | money_cents | Release to Collection Account |
| `required_reserve_acct_balance` | money_cents | Required Reserve Acct Balance |
| `reserve_account_balance__date__2` | money_cents | Reserve Account Balance > 06/25/2026 |
| `reserve_funds_reinstated` | money_cents | Reserve Funds Reinstated |
| `reserve_funds_utilized` | money_cents | Reserve Funds Utilized |
| `supplemental_loan_purchase_account__date__2` | money_cents | Supplemental Loan Purchase Account > 06/25/2026 |
| `supplemental_loan_purchases` | money_cents | Supplemental Loan Purchases |
| `total_available_funds__remaining_funds_balance` | money_cents | Total Available Funds > Remaining Funds Balance |
| `total_interest_due__date` | money_cents | Total Interest Due > 6/25/2026 |
| `total_interest_due__date__2` | money_cents | Total Interest Due > 6/25/2026 |
| `total_interest_receipts` | money_cents | Total Interest Receipts |
| `total_notes__date__2` | money_cents | Total Notes > 06/25/2026 |
| `total_principal_receipts` | money_cents | Total Principal Receipts |
| `transfers_to_collection_account` | money_cents | Transfers to Collection Account |
| `unpaid_administration_fees__date` | money_cents | Unpaid Administration Fees > 05/31/2026 |

## Required output fields — period_4

| field | type | report line |
|---|---|---|
| `a_63938qaa5__date__2` | money_cents | A 63938QAA5 > 07/27/2026 |
| `a_trustee_fees__remaining_funds_balance` | money_cents | A Trustee Fees > Remaining Funds Balance |
| `accrued_interest_factor__date` | decimal | Accrued Interest Factor > 7/27/2026 |
| `accrued_interest_factor__date__2` | decimal | Accrued Interest Factor > 7/27/2026 |
| `adjusted_pool_1__date__3` | money_cents | Adjusted Pool (1) > 06/30/2026 |
| `adjusted_pool_balance` | money_cents | Adjusted Pool Balance |
| `adjusted_pool_balance_supplemental_loan_purchase__date__2` | money_cents | Adjusted Pool Balance + Supplemental Loan Purchase > 07/27/2026 |
| `b_63938qab3__date__2` | money_cents | B 63938QAB3 > 07/27/2026 |
| `b_primary_servicing_fee__remaining_funds_balance` | money_cents | B Primary Servicing Fee > Remaining Funds Balance |
| `balance_available` | money_cents | Balance Available |
| `c_administration_fee__paid` | money_cents | C Administration Fee > Paid |
| `c_administration_fee__remaining_funds_balance` | money_cents | C Administration Fee > Remaining Funds Balance |
| `c_reserves_in_excess_of_requirement` | money_cents | C Reserves in Excess of Requirement |
| `capitalized_interest_account_balance__date__2` | money_cents | Capitalized Interest Account Balance > 07/27/2026 |
| `current_interest_due__date` | money_cents | Current Interest Due > 7/27/2026 |
| `current_interest_due__date__2` | money_cents | Current Interest Due > 7/27/2026 |
| `d_class_a_noteholders_interest_distribution_amount__paid` | money_cents | D Class A Noteholders’ Interest Distribution Amount > Paid |
| `d_class_a_noteholders_interest_distribution_amount__remaining_funds_balance` | money_cents | D Class A Noteholders’ Interest Distribution Amount > Remaining Funds Balance |
| `d_reserve_account_balance_after_any_reinstatement` | money_cents | D Reserve Account Balance (after any reinstatement) |
| `difference__date__2` | money_cents | Difference > 07/27/2026 |
| `e_class_b_noteholders_interest_distribution_amount__paid` | money_cents | E Class B Noteholders’ Interest Distribution Amount > Paid |
| `e_class_b_noteholders_interest_distribution_amount__remaining_funds_balance` | money_cents | E Class B Noteholders’ Interest Distribution Amount > Remaining Funds Balance |
| `e_less_specified_reserve_account_balance` | money_cents | E Less: Specified Reserve Account Balance |
| `ending_balance` | money_cents | Ending Balance |
| `ending_balance__2` | money_cents | Ending Balance |
| `ending_principal_balance__date` | money_cents | Ending Principal Balance > 7/27/2026 |
| `ending_principal_balance__date__2` | money_cents | Ending Principal Balance > 7/27/2026 |
| `ending_reserve_account_balance` | money_cents | Ending Reserve Account Balance |
| `f_reserve_account_reinstatement__paid` | money_cents | F Reserve Account Reinstatement > Paid |
| `f_reserve_account_reinstatement__remaining_funds_balance` | money_cents | F Reserve Account Reinstatement > Remaining Funds Balance |
| `f_total` | money_cents | F Total |
| `floor_income_rebate_account__date__2` | money_cents | Floor Income Rebate Account > 07/27/2026 |
| `g_class_a_noteholders_principal_distribution_amount__paid` | money_cents | G Class A Noteholders’ Principal Distribution Amount > Paid |
| `g_class_a_noteholders_principal_distribution_amount__remaining_funds_balance` | money_cents | G Class A Noteholders’ Principal Distribution Amount > Remaining Funds Balance |
| `g_class_a_notes_outstanding_after_application_of_available_funds` | money_cents | G Class A Notes Outstanding (after application of available funds) |
| `h_class_b_noteholders_principal_distribution_amount__paid` | money_cents | H Class B Noteholders’ Principal Distribution Amount > Paid |
| `h_class_b_noteholders_principal_distribution_amount__remaining_funds_balance` | money_cents | H Class B Noteholders’ Principal Distribution Amount > Remaining Funds Balance |
| `i_unpaid_expenses_of_the_trustees__remaining_funds_balance` | money_cents | I Unpaid Expenses of The Trustees > Remaining Funds Balance |
| `interest_paid__date` | money_cents | Interest Paid > 7/27/2026 |
| `interest_paid__date__2` | money_cents | Interest Paid > 7/27/2026 |
| `interest_shortfall__date` | money_cents | Interest Shortfall > 7/27/2026 |
| `interest_shortfall__date__2` | money_cents | Interest Shortfall > 7/27/2026 |
| `j_carryover_servicing_fee__remaining_funds_balance` | money_cents | J Carryover Servicing Fee > Remaining Funds Balance |
| `k_remaining_amounts_to_the_noteholders_after_the_first_auction_date__paid` | money_cents | K Remaining Amounts to the Noteholders after the first auction date > Paid |
| `k_remaining_amounts_to_the_noteholders_after_the_first_auction_date__remaining_funds_balance` | money_cents | K Remaining Amounts to the Noteholders after the first auction date > Remaining Funds Balance |
| `l_excess_distribution_certificateholder__paid` | money_cents | L Excess Distribution Certificateholder > Paid |
| `l_excess_distribution_certificateholder__remaining_funds_balance` | money_cents | L Excess Distribution Certificateholder > Remaining Funds Balance |
| `m_available_funds` | money_cents | M AVAILABLE FUNDS |
| `note_interest_shortfall__date` | money_cents | Note Interest Shortfall > 06/30/2026 |
| `note_principal_shortfall__date` | money_cents | Note Principal Shortfall > 06/30/2026 |
| `notes_outstanding_principal_balance` | money_cents | Notes Outstanding Principal Balance |
| `overcollateralization_amount` | money_cents | Overcollateralization Amount |
| `parity_ratio__date__2` | decimal | Parity Ratio > 07/27/2026 |
| `principal_distribution_amount` | money_cents | Principal Distribution Amount |
| `principal_distribution_amount_paid` | money_cents | Principal Distribution Amount Paid |
| `principal_paid__date` | money_cents | Principal Paid > 7/27/2026 |
| `principal_paid__date__2` | money_cents | Principal Paid > 7/27/2026 |
| `release_to_collection_account` | money_cents | Release to Collection Account |
| `release_to_collection_account__2` | money_cents | Release to Collection Account |
| `required_reserve_acct_balance` | money_cents | Required Reserve Acct Balance |
| `reserve_account_balance__date__2` | money_cents | Reserve Account Balance > 07/27/2026 |
| `reserve_funds_reinstated` | money_cents | Reserve Funds Reinstated |
| `reserve_funds_utilized` | money_cents | Reserve Funds Utilized |
| `supplemental_loan_purchase_account__date__2` | money_cents | Supplemental Loan Purchase Account > 07/27/2026 |
| `supplemental_loan_purchases` | money_cents | Supplemental Loan Purchases |
| `total_available_funds__remaining_funds_balance` | money_cents | Total Available Funds > Remaining Funds Balance |
| `total_interest_due__date` | money_cents | Total Interest Due > 7/27/2026 |
| `total_interest_due__date__2` | money_cents | Total Interest Due > 7/27/2026 |
| `total_interest_receipts` | money_cents | Total Interest Receipts |
| `total_notes__date__2` | money_cents | Total Notes > 07/27/2026 |
| `total_principal_receipts` | money_cents | Total Principal Receipts |
| `transfers_to_collection_account` | money_cents | Transfers to Collection Account |
| `unpaid_administration_fees__date` | money_cents | Unpaid Administration Fees > 06/30/2026 |

## Answer

Write `/workspace/answer.json` as {"period_1": {"<field>": <value>, ...}, "period_2": {...}, "period_3": {...}, "period_4": {...}}, matching `/workspace/answer_schema.json`.
