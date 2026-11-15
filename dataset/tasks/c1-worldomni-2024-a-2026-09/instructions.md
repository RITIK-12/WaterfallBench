# WaterfallBench task `c1-worldomni-2024-a-2026-09`

**Deal:** World Omni Auto Receivables Trust 2024-A  
**Category:** C1 monthly_distribution

Compute every output field of ONE monthly distribution.

Files (all are SEC EDGAR HTML as filed):
- `/workspace/docs/`: the deal's governing documents (final prospectus; closing agreements where filed).
- `/workspace/reports/period_2026-08_opening_state.html`: the complete servicer report of the period before the first graded period.
- `/workspace/reports/period_2026-09_graded.html`: the servicer report for the distribution of 2026-09-30, with every output value removed. Input values (collections, pool data, rates, beginning balances) remain.

Rules:
- Money: integer US cents, exactly to the cent as the trustee reports it (e.g. $1,234.56 -> 123456).
- Percentages and other decimals: the number as it would be printed, without a % sign.
- Statuses: one of the listed values.
- Apply the priority of payments and definitions in the governing documents; deal parameters come from those documents.

## Required output fields

| field | type | report line |
|---|---|---|
| `a_1_interest_carryover_shortfall__total` | decimal | Class C > A-1 Interest Carryover Shortfall > Total |
| `a_1_interest_distribution_amount__total` | decimal | Class C > A-1 Interest Distribution Amount > Total |
| `a_1_principal_distribution_amount__total` | decimal | Class C > A-1 Principal Distribution Amount > Total |
| `a_2a_interest_carryover_shortfall__total` | decimal | Class C > A-2a Interest Carryover Shortfall > Total |
| `a_2a_interest_distribution_amount__total` | decimal | Class C > A-2a Interest Distribution Amount > Total |
| `a_2a_principal_distribution_amount__total` | decimal | Class C > A-2a Principal Distribution Amount > Total |
| `a_2b_interest_carryover_shortfall__total` | decimal | Class C > A-2b Interest Carryover Shortfall > Total |
| `a_2b_interest_distribution_amount__total` | decimal | Class C > A-2b Interest Distribution Amount > Total |
| `a_2b_principal_distribution_amount__total` | decimal | Class C > A-2b Principal Distribution Amount > Total |
| `a_3_interest_carryover_shortfall__total` | decimal | Class C > A-3 Interest Carryover Shortfall > Total |
| `a_3_interest_distribution_amount__total` | decimal | Class C > A-3 Interest Distribution Amount > Total |
| `a_3_principal_distribution_amount__total` | decimal | Class C > A-3 Principal Distribution Amount > Total |
| `a_4_interest_carryover_shortfall__total` | decimal | Class C > A-4 Interest Carryover Shortfall > Total |
| `a_4_interest_distribution_amount__total` | decimal | Class C > A-4 Interest Distribution Amount > Total |
| `a_4_principal_distribution_amount__total` | decimal | Class C > A-4 Principal Distribution Amount > Total |
| `actual_overcollateralization` | money_cents | Ratio of Net Loss/(Gain) to the Receivables Balance as of beginning of Collection Period (Annualized) > Actual Overcollateralization |
| `asset_representation_reviewer_amounts_in_excess_of_1` | money_cents | Distributions of Available Funds > Asset Representation Reviewer Amounts (in excess of 1) |
| `asset_representation_reviewer_amounts_up_to_amt_per_year` | money_cents | Distributions of Available Funds > Asset Representation Reviewer Amounts (up to $150,000 per year) |
| `available_funds__amount` | money_cents | Ratio of Net Loss/(Gain) to the Receivables Balance as of beginning of Collection Period (Annualized) > Available Funds > $ Amount |
| `b_interest_carryover_shortfall__total` | decimal | Class C > B Interest Carryover Shortfall > Total |
| `b_interest_distribution_amount__total` | decimal | Class C > B Interest Distribution Amount > Total |
| `b_principal_distribution_amount__total` | decimal | Class C > B Principal Distribution Amount > Total |
| `balance_as_of_date__2` | money_cents | Reserve Account > Balance as of 10/15/26 |
| `c_interest_carryover_shortfall__total` | decimal | Class C > C Interest Carryover Shortfall > Total |
| `c_interest_distribution_amount__total` | decimal | Class C > C Interest Distribution Amount > Total |
| `c_principal_distribution_amount__total` | decimal | Class C > C Principal Distribution Amount > Total |
| `change` | money_cents | Reserve Account > Change |
| `change_in_amount_of_the_unpaid_servicing_fee_from_the_prior_period` | money_cents | Distributions of Available Funds > Change in amount of the unpaid servicing fee from the prior period |
| `class_a_1__coupon` | decimal | Class A-1 > Coupon |
| `class_a_1__interest_paid` | money_cents | Class A-1 > Interest Paid |
| `class_a_1__note_balance_date__2` | money_cents | Class A-1 > Note Balance @ 10/15/26 |
| `class_a_1__note_factor_date` | decimal | Class A-1 > Note Factor @ 10/15/26 |
| `class_a_1__principal_paid` | money_cents | Class A-1 > Principal Paid |
| `class_a_1__principal_paid__2` | money_cents | Class A-1 > Principal Paid |
| `class_a_2a__coupon` | decimal | Class A-2a > Coupon |
| `class_a_2a__interest_paid` | money_cents | Class A-2a > Interest Paid |
| `class_a_2a__note_balance_date__2` | money_cents | Class A-2a > Note Balance @ 10/15/26 |
| `class_a_2a__note_factor_date` | decimal | Class A-2a > Note Factor @ 10/15/26 |
| `class_a_2a__principal_paid` | money_cents | Class A-2a > Principal Paid |
| `class_a_2a__principal_paid__2` | money_cents | Class A-2a > Principal Paid |
| `class_a_2b__coupon` | decimal | Class A-2b > Coupon |
| `class_a_2b__interest_paid` | money_cents | Class A-2b > Interest Paid |
| `class_a_2b__note_balance_date__2` | money_cents | Class A-2b > Note Balance @ 10/15/26 |
| `class_a_2b__note_factor_date` | decimal | Class A-2b > Note Factor @ 10/15/26 |
| `class_a_2b__principal_paid` | money_cents | Class A-2b > Principal Paid |
| `class_a_2b__principal_paid__2` | money_cents | Class A-2b > Principal Paid |
| `class_a_3__coupon` | decimal | Class A-3 > Coupon |
| `class_a_3__interest_paid` | money_cents | Class A-3 > Interest Paid |
| `class_a_3__note_balance_date__2` | money_cents | Class A-3 > Note Balance @ 10/15/26 |
| `class_a_3__note_factor_date` | decimal | Class A-3 > Note Factor @ 10/15/26 |
| `class_a_3__principal_paid` | money_cents | Class A-3 > Principal Paid |
| `class_a_3__principal_paid__2` | money_cents | Class A-3 > Principal Paid |
| `class_a_4__coupon` | decimal | Class A-4 > Coupon |
| `class_a_4__interest_paid` | money_cents | Class A-4 > Interest Paid |
| `class_a_4__note_balance_date__2` | money_cents | Class A-4 > Note Balance @ 10/15/26 |
| `class_a_4__note_factor_date` | decimal | Class A-4 > Note Factor @ 10/15/26 |
| `class_a_4__principal_paid` | money_cents | Class A-4 > Principal Paid |
| `class_a_4__principal_paid__2` | money_cents | Class A-4 > Principal Paid |
| `class_a_interest` | money_cents | Distributions of Available Funds > Class A Interest |
| `class_b__coupon` | decimal | Class B > Coupon |
| `class_b__interest_paid` | money_cents | Class B > Interest Paid |
| `class_b__note_balance_date__2` | money_cents | Class B > Note Balance @ 10/15/26 |
| `class_b__note_factor_date` | decimal | Class B > Note Factor @ 10/15/26 |
| `class_b__principal_paid` | money_cents | Class B > Principal Paid |
| `class_b__principal_paid__2` | money_cents | Class B > Principal Paid |
| `class_b_interest` | money_cents | Distributions of Available Funds > Class B Interest |
| `class_c__coupon` | decimal | Class C > Coupon |
| `class_c__interest_paid` | money_cents | Class C > Interest Paid |
| `class_c__note_balance_date__2` | money_cents | Class C > Note Balance @ 10/15/26 |
| `class_c__note_factor_date` | decimal | Class C > Note Factor @ 10/15/26 |
| `class_c__principal_paid` | money_cents | Class C > Principal Paid |
| `class_c__principal_paid__2` | money_cents | Class C > Principal Paid |
| `class_c_interest` | money_cents | Distributions of Available Funds > Class C Interest |
| `deposit_withdrawal` | money_cents | Reserve Account > Deposit/(Withdrawal) |
| `distribution_to_certificateholders` | money_cents | Distributions of Available Funds > Distribution to Certificateholders |
| `investment_earnings_paid` | money_cents | Reserve Account > Investment Earnings Paid |
| `noteholders_first_priority_principal_distributable_amount` | money_cents | Distributions of Available Funds > Noteholders' First Priority Principal Distributable Amount |
| `noteholders_first_priority_principal_distributable_amount__total` | decimal | Class C > Noteholders' First Priority Principal Distributable Amount > Total |
| `noteholders_principal_distributable_amount` | money_cents | Distributions of Available Funds > Noteholders' Principal Distributable Amount |
| `noteholders_principal_distributable_amount__total` | decimal | Class C > Noteholders' Principal Distributable Amount > Total |
| `noteholders_second_priority_principal_distributable_amount` | money_cents | Distributions of Available Funds > Noteholders' Second Priority Principal Distributable Amount |
| `noteholders_second_priority_principal_distributable_amount__total` | decimal | Class C > Noteholders' Second Priority Principal Distributable Amount > Total |
| `noteholders_third_priority_principal_distributable_amount` | money_cents | Distributions of Available Funds > Noteholders' Third Priority Principal Distributable Amount |
| `noteholders_third_priority_principal_distributable_amount__total` | decimal | Class C > Noteholders' Third Priority Principal Distributable Amount > Total |
| `overcollateralization_target_amount` | money_cents | Ratio of Net Loss/(Gain) to the Receivables Balance as of beginning of Collection Period (Annualized) > Overcollateralization Target Amount |
| `pool_balance_at_date__amount` | money_cents | Dates Covered > Pool Balance at 08/31/26 > $ Amount |
| `pool_balance_at_date__amount__2` | money_cents | Dates Covered > Pool Balance at 09/30/26 > $ Amount |
| `required_reserve_account` | money_cents | Distributions of Available Funds > Required Reserve Account |
| `required_reserve_amount` | money_cents | Reserve Account > Required Reserve Amount |
| `servicing_fee` | money_cents | Distributions of Available Funds > Servicing Fee |
| `servicing_fee__amount` | money_cents | Ratio of Net Loss/(Gain) to the Receivables Balance as of beginning of Collection Period (Annualized) > Servicing Fee > $ Amount |
| `total_a_1_distribution_amount__total` | decimal | Class C > Total A-1 Distribution Amount > Total |
| `total_a_2a_distribution_amount__total` | decimal | Class C > Total A-2a Distribution Amount > Total |
| `total_a_2b_distribution_amount__total` | decimal | Class C > Total A-2b Distribution Amount > Total |
| `total_a_3_distribution_amount__total` | decimal | Class C > Total A-3 Distribution Amount > Total |
| `total_a_4_distribution_amount__total` | decimal | Class C > Total A-4 Distribution Amount > Total |
| `total_b_distribution_amount__total` | decimal | Class C > Total B Distribution Amount > Total |
| `total_c_distribution_amount__total` | decimal | Class C > Total C Distribution Amount > Total |
| `total_class_a_b_c__note_balance_date` | money_cents | Total Class A, B, & C > Note Balance @ 09/15/26 |
| `total_class_a_b_c__note_balance_date__2` | money_cents | Total Class A, B, & C > Note Balance @ 10/15/26 |
| `total_class_a_b_c__principal_paid` | money_cents | Total Class A, B, & C > Principal Paid |
| `total_distribution_amount__total` | decimal | Class C > Total Distribution Amount > Total |
| `total_distributions_of_available_funds` | money_cents | Distributions of Available Funds > Total Distributions of Available Funds |
| `total_interest_carryover_shortfall__total` | decimal | Class C > Total Interest Carryover Shortfall > Total |
| `total_interest_distribution_amount__total` | decimal | Class C > Total Interest Distribution Amount > Total |
| `total_interest_paid__amount` | money_cents | Class C > Total Interest Paid > $ Amount |
| `total_paid__amount` | money_cents | Class C > Total Paid > $ Amount |
| `total_paid_to_a_1_holders` | money_cents | Class A-1 > Total Paid to A-1 Holders |
| `total_paid_to_a_2a_holders` | money_cents | Class A-2a > Total Paid to A-2a Holders |
| `total_paid_to_a_2b_holders` | money_cents | Class A-2b > Total Paid to A-2b Holders |
| `total_paid_to_a_3_holders` | money_cents | Class A-3 > Total Paid to A-3 Holders |
| `total_paid_to_a_4_holders` | money_cents | Class A-4 > Total Paid to A-4 Holders |
| `total_paid_to_b_holders` | money_cents | Class B > Total Paid to B Holders |
| `total_paid_to_c_holders` | money_cents | Class C > Total Paid to C Holders |
| `total_principal_distribution_amount__total` | decimal | Class C > Total Principal Distribution Amount > Total |
| `total_principal_paid__amount` | money_cents | Class C > Total Principal Paid > $ Amount |
| `transfer_to_collection_account__amount` | money_cents | Ratio of Net Loss/(Gain) to the Receivables Balance as of beginning of Collection Period (Annualized) > Transfer to Collection Account > $ Amount |
| `unpaid_servicing_fee` | money_cents | Distributions of Available Funds > Unpaid Servicing Fee |

## Answer

Write `/workspace/answer.json` as {"<field>": <value>, ...}, matching `/workspace/answer_schema.json`.
