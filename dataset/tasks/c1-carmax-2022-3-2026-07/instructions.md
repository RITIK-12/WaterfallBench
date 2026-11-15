# WaterfallBench task `c1-carmax-2022-3-2026-07`

**Deal:** CarMax Auto Owner Trust 2022-3  
**Category:** C1 monthly_distribution

Compute every output field of ONE monthly distribution.

Files (all are SEC EDGAR HTML as filed):
- `/workspace/docs/`: the deal's governing documents (final prospectus; closing agreements where filed).
- `/workspace/reports/period_2026-06_opening_state.html`: the complete servicer report of the period before the first graded period.
- `/workspace/reports/period_2026-07_graded.html`: the servicer report for the distribution of 8/17/2026, with every output value removed. Input values (collections, pool data, rates, beginning balances) remain.

Rules:
- Money: integer US cents, exactly to the cent as the trustee reports it (e.g. $1,234.56 -> 123456).
- Percentages and other decimals: the number as it would be printed, without a % sign.
- Statuses: one of the listed values.
- Apply the priority of payments and definitions in the governing documents; deal parameters come from those documents.

## Required output fields

| field | type | report line |
|---|---|---|
| `amount_to_be_deposited_from_the_collection_account_into_the_certificate_payment_account` | money_cents | Instructions to the Trustee > Amount to be deposited from the Collection Account into the Certificate Payment Account |
| `amount_to_be_deposited_from_the_collection_account_into_the_note_payment_account` | money_cents | Instructions to the Trustee > Amount to be deposited from the Collection Account into the Note Payment Account |
| `amount_to_be_deposited_from_the_collection_account_into_the_reserve_account` | money_cents | Instructions to the Trustee > Amount to be deposited from the Collection Account into the Reserve Account |
| `amount_to_be_deposited_from_the_reserve_account_if_reserve_account_balance_exceeds_require__the_depositor_if_no_unfunded_regular_principal_distributable_amount_exists` | money_cents | Instructions to the Trustee > Amount to be deposited from the Reserve Account, if Reserve Account Balance exceeds Required Reserve Account Amount, into > the Depositor, if no unfunded Regular Principal distributable amount exists |
| `amount_to_be_deposited_from_the_reserve_account_if_reserve_account_balance_exceeds_require__the_note_payment_account_for_any_unfunded_regular_principal_distributable_amount` | money_cents | Instructions to the Trustee > Amount to be deposited from the Reserve Account, if Reserve Account Balance exceeds Required Reserve Account Amount, into > the Note Payment Account for any unfunded Regular Principal Distributable Amount |
| `amount_to_be_deposited_from_the_reserve_account_into_the_collection_account` | money_cents | Instructions to the Trustee > Amount to be deposited from the Reserve Account into the Collection Account |
| `amount_to_be_paid_to_certificateholders_from_the_certificate_payment_account_with_respect` | money_cents | Instructions to the Trustee > Amount to be paid to Certificateholders from the Certificate Payment Account with respect to Excess Collections |
| `amount_to_be_paid_to_class_a_1_noteholders_from_the_note_payment_account` | money_cents | Instructions to the Trustee > Amount to be paid to Class A-1 Noteholders from the Note Payment Account |
| `amount_to_be_paid_to_class_a_2a_noteholders_from_the_note_payment_account` | money_cents | Instructions to the Trustee > Amount to be paid to Class A-2a Noteholders from the Note Payment Account |
| `amount_to_be_paid_to_class_a_2b_noteholders_from_the_note_payment_account` | money_cents | Instructions to the Trustee > Amount to be paid to Class A-2b Noteholders from the Note Payment Account |
| `amount_to_be_paid_to_class_a_3_noteholders_from_the_note_payment_account` | money_cents | Instructions to the Trustee > Amount to be paid to Class A-3 Noteholders from the Note Payment Account |
| `amount_to_be_paid_to_class_a_4_noteholders_from_the_note_payment_account` | money_cents | Instructions to the Trustee > Amount to be paid to Class A-4 Noteholders from the Note Payment Account |
| `amount_to_be_paid_to_class_b_noteholders_from_the_note_payment_account` | money_cents | Instructions to the Trustee > Amount to be paid to Class B Noteholders from the Note Payment Account |
| `amount_to_be_paid_to_class_c_noteholders_from_the_note_payment_account` | money_cents | Instructions to the Trustee > Amount to be paid to Class C Noteholders from the Note Payment Account |
| `amount_to_be_paid_to_class_d_noteholders_from_the_note_payment_account` | money_cents | Instructions to the Trustee > Amount to be paid to Class D Noteholders from the Note Payment Account |
| `amount_to_be_paid_to_servicer_from_the_collection_account` | money_cents | Instructions to the Trustee > Amount to be paid to Servicer from the Collection Account |
| `application_of_available_funds__reserve_account_deficiency` | money_cents | Application of Available Funds > Reserve Account Deficiency |
| `available_funds` | money_cents | Available Funds > Available Funds |
| `available_funds__available_collections` | money_cents | Available Funds > Available Collections |
| `available_funds__reserve_account_draw_amount` | money_cents | Available Funds > Reserve Account Draw Amount |
| `class_a_noteholder_interest_amounts__additional_note_interest_related_to_class_a_4_monthly_interest__2` | money_cents | Application of Available Funds > Class A Noteholder Interest Amounts > Additional Note Interest related to Class A-4 Monthly Interest |
| `class_a_noteholder_interest_amounts__class_a_1_monthly_interest` | money_cents | Application of Available Funds > Class A Noteholder Interest Amounts > Class A-1 Monthly Interest |
| `class_a_noteholder_interest_amounts__class_a_2a_monthly_interest` | money_cents | Application of Available Funds > Class A Noteholder Interest Amounts > Class A-2a Monthly Interest |
| `class_a_noteholder_interest_amounts__class_a_2b_monthly_interest` | money_cents | Application of Available Funds > Class A Noteholder Interest Amounts > Class A-2b Monthly Interest |
| `class_a_noteholder_interest_amounts__class_a_3_monthly_interest` | money_cents | Application of Available Funds > Class A Noteholder Interest Amounts > Class A-3 Monthly Interest |
| `class_a_noteholder_interest_amounts__class_a_4_monthly_interest` | money_cents | Application of Available Funds > Class A Noteholder Interest Amounts > Class A-4 Monthly Interest |
| `class_a_noteholder_interest_amounts__interest_due_on_additional_note_interest_related_to_class_a_1_monthly_interest` | money_cents | Application of Available Funds > Class A Noteholder Interest Amounts > Interest Due on Additional Note Interest related to Class A-1 Monthly Interest |
| `class_a_noteholder_interest_amounts__interest_due_on_additional_note_interest_related_to_class_a_2a_monthly_interest` | money_cents | Application of Available Funds > Class A Noteholder Interest Amounts > Interest Due on Additional Note Interest related to Class A-2a Monthly Interest |
| `class_a_noteholder_interest_amounts__interest_due_on_additional_note_interest_related_to_class_a_2b_monthly_interest` | money_cents | Application of Available Funds > Class A Noteholder Interest Amounts > Interest Due on Additional Note Interest related to Class A-2b Monthly Interest |
| `class_a_noteholder_interest_amounts__interest_due_on_additional_note_interest_related_to_class_a_3_monthly_interest` | money_cents | Application of Available Funds > Class A Noteholder Interest Amounts > Interest Due on Additional Note Interest related to Class A-3 Monthly Interest |
| `class_a_noteholder_interest_amounts__total_class_a_1_note_interest` | money_cents | Application of Available Funds > Class A Noteholder Interest Amounts > Total Class A-1 Note Interest (sum a - c) |
| `class_a_noteholder_interest_amounts__total_class_a_2a_note_interest` | money_cents | Application of Available Funds > Class A Noteholder Interest Amounts > Total Class A-2a Note Interest (sum e - g) |
| `class_a_noteholder_interest_amounts__total_class_a_2b_note_interest` | money_cents | Application of Available Funds > Class A Noteholder Interest Amounts > Total Class A-2b Note Interest (sum i - k) |
| `class_a_noteholder_interest_amounts__total_class_a_3_note_interest` | money_cents | Application of Available Funds > Class A Noteholder Interest Amounts > Total Class A-3 Note Interest (sum m - o) |
| `class_a_noteholder_interest_amounts__total_class_a_4_note_interest` | money_cents | Application of Available Funds > Class A Noteholder Interest Amounts > Total Class A-4 Note Interest (sum q - s) |
| `class_b_noteholder_interest_amount__class_b_monthly_interest` | money_cents | Application of Available Funds > Class B Noteholder Interest Amount > Class B Monthly Interest |
| `class_b_noteholder_interest_amount__interest_due_on_additional_note_interest_related_to_class_b_monthly_interest` | money_cents | Application of Available Funds > Class B Noteholder Interest Amount > Interest Due on Additional Note Interest related to Class B Monthly Interest |
| `class_b_noteholder_interest_amount__total_class_b_note_interest` | money_cents | Application of Available Funds > Class B Noteholder Interest Amount > Total Class B Note Interest (sum a - c) |
| `class_c_noteholder_interest_amount__class_c_monthly_interest` | money_cents | Application of Available Funds > Class C Noteholder Interest Amount > Class C Monthly Interest |
| `class_c_noteholder_interest_amount__interest_due_on_additional_note_interest_related_to_class_c_monthly_interest` | money_cents | Application of Available Funds > Class C Noteholder Interest Amount > Interest Due on Additional Note Interest related to Class C Monthly Interest |
| `class_c_noteholder_interest_amount__total_class_c_note_interest` | money_cents | Application of Available Funds > Class C Noteholder Interest Amount > Total Class C Note Interest (sum a - c) |
| `class_d_noteholder_interest_amount__class_d_monthly_interest` | money_cents | Application of Available Funds > Class D Noteholder Interest Amount > Class D Monthly Interest |
| `class_d_noteholder_interest_amount__interest_due_on_additional_note_interest_related_to_class_d_monthly_interest` | money_cents | Application of Available Funds > Class D Noteholder Interest Amount > Interest Due on Additional Note Interest related to Class D Monthly Interest |
| `class_d_noteholder_interest_amount__total_class_d_note_interest` | money_cents | Application of Available Funds > Class D Noteholder Interest Amount > Total Class D Note Interest (sum a - c) |
| `current_overcollateralization_amount_pool_balance_note_balance__end_of_period` | money_cents | Pool Balance > Current overcollateralization amount (Pool Balance - Note Balance) > End of Period |
| `deposit_from_available_funds` | money_cents | Reserve Account Reconciliation > Deposit from Available Funds (Ln 44d) |
| `deposits__class_a_1_interest_distribution` | money_cents | Note Payment Account Activity > Deposits > Class A-1 Interest Distribution |
| `deposits__class_a_1_principal_distribution` | money_cents | Note Payment Account Activity > Deposits > Class A-1 Principal Distribution |
| `deposits__class_a_2a_interest_distribution` | money_cents | Note Payment Account Activity > Deposits > Class A-2a Interest Distribution |
| `deposits__class_a_2a_principal_distribution` | money_cents | Note Payment Account Activity > Deposits > Class A-2a Principal Distribution |
| `deposits__class_a_2b_interest_distribution` | money_cents | Note Payment Account Activity > Deposits > Class A-2b Interest Distribution |
| `deposits__class_a_2b_principal_distribution` | money_cents | Note Payment Account Activity > Deposits > Class A-2b Principal Distribution |
| `deposits__class_a_3_interest_distribution` | money_cents | Note Payment Account Activity > Deposits > Class A-3 Interest Distribution |
| `deposits__class_a_3_principal_distribution` | money_cents | Note Payment Account Activity > Deposits > Class A-3 Principal Distribution |
| `deposits__class_a_4_interest_distribution` | money_cents | Note Payment Account Activity > Deposits > Class A-4 Interest Distribution |
| `deposits__class_a_4_principal_distribution` | money_cents | Note Payment Account Activity > Deposits > Class A-4 Principal Distribution |
| `deposits__class_b_interest_distribution` | money_cents | Note Payment Account Activity > Deposits > Class B Interest Distribution |
| `deposits__class_b_principal_distribution` | money_cents | Note Payment Account Activity > Deposits > Class B Principal Distribution |
| `deposits__class_c_interest_distribution` | money_cents | Note Payment Account Activity > Deposits > Class C Interest Distribution |
| `deposits__class_c_principal_distribution` | money_cents | Note Payment Account Activity > Deposits > Class C Principal Distribution |
| `deposits__class_d_interest_distribution` | money_cents | Note Payment Account Activity > Deposits > Class D Interest Distribution |
| `deposits__class_d_principal_distribution` | money_cents | Note Payment Account Activity > Deposits > Class D Principal Distribution |
| `deposits__interest_income` | money_cents | Application of Available Funds > Deposits > Interest Income |
| `deposits__total_daily_deposits_of_finance_charge_collections` | money_cents | Application of Available Funds > Deposits > Total Daily Deposits of Finance Charge Collections |
| `deposits__total_daily_deposits_of_principal_collections` | money_cents | Application of Available Funds > Deposits > Total Daily Deposits of Principal Collections |
| `deposits__total_deposits_to_collection_account` | money_cents | Application of Available Funds > Deposits > Total Deposits to Collection Account (sum a - d) |
| `deposits__total_deposits_to_note_payment_account` | money_cents | Note Payment Account Activity > Deposits > Total Deposits to Note Payment Account (sum a - p) |
| `deposits__withdrawal_from_reserve_account` | money_cents | Application of Available Funds > Deposits > Withdrawal from Reserve Account |
| `deposits_to_certificate_payment_account_from_excess_collections` | money_cents | Certificate Payment Account Activity > Deposits to Certificate Payment Account from Excess Collections |
| `ending_balance` | money_cents | Reserve Account Reconciliation > Ending Balance (Ln53 + Ln54 - Ln55 - Ln56) |
| `if_reserve_account_balance_exceeds_required_reserve_account_amount_payment_to__any_successor_servicer_for_the_payment_of_any_unfunded_transition_costs_and_additional_ser` | money_cents | Reserve Account Reconciliation > If Reserve Account Balance exceeds Required Reserve Account Amount, payment to > any Successor Servicer for the payment of any unfunded Transition Costs and Additional Servicing Fee |
| `if_reserve_account_balance_exceeds_required_reserve_account_amount_payment_to__the_note_payment_account_for_the_payment_of_principal_to_the_extent_of_any_unfunded_regula` | money_cents | Reserve Account Reconciliation > If Reserve Account Balance exceeds Required Reserve Account Amount, payment to > the Note Payment Account for the payment of principal to the extent of any unfunded Regular Principal Distribution Amount; and |
| `note_balances__class_a_1_note_balance__end_of_period` | money_cents | Pool Balance > Note Balances > Class A-1 Note Balance > End of Period |
| `note_balances__class_a_2a_note_balance__end_of_period` | money_cents | Pool Balance > Note Balances > Class A-2a Note Balance > End of Period |
| `note_balances__class_a_2b_floating_rate_note_balance__end_of_period` | money_cents | Pool Balance > Note Balances > Class A-2b Floating Rate Note Balance > End of Period |
| `note_balances__class_a_3_note_balance__end_of_period` | money_cents | Pool Balance > Note Balances > Class A-3 Note Balance > End of Period |
| `note_balances__class_a_4_note_balance__end_of_period` | money_cents | Pool Balance > Note Balances > Class A-4 Note Balance > End of Period |
| `note_balances__class_b_note_balance__end_of_period` | money_cents | Pool Balance > Note Balances > Class B Note Balance > End of Period |
| `note_balances__class_c_note_balance__end_of_period` | money_cents | Pool Balance > Note Balances > Class C Note Balance > End of Period |
| `note_balances__class_d_note_balance__end_of_period` | money_cents | Pool Balance > Note Balances > Class D Note Balance > End of Period |
| `note_balances__note_balance__end_of_period` | money_cents | Pool Balance > Note Balances > Note Balance (sum a - h) > End of Period |
| `overcollateralization_target_amount__end_of_period` | money_cents | Pool Balance > Overcollateralization Target Amount > End of Period |
| `payment_to_depositor_if_reserve_account_balance_exceeds_required_reserve_account_amount_an` | money_cents | Reserve Account Reconciliation > Payment to Depositor if Reserve Account Balance exceeds Required Reserve Account Amount and to the extent no unfunded amounts described in Ln 55 exist |
| `pool_factors__class_a_1_note_pool_factor__end_of_period` | decimal | Pool Balance > Pool Factors > Class A-1 Note Pool Factor > End of Period |
| `pool_factors__class_a_2a_note_pool_factor__end_of_period` | decimal | Pool Balance > Pool Factors > Class A-2a Note Pool Factor > End of Period |
| `pool_factors__class_a_2b_floating_rate_note_pool_factor__end_of_period` | decimal | Pool Balance > Pool Factors > Class A-2b Floating Rate Note Pool Factor > End of Period |
| `pool_factors__class_a_3_note_pool_factor__end_of_period` | decimal | Pool Balance > Pool Factors > Class A-3 Note Pool Factor > End of Period |
| `pool_factors__class_a_4_note_pool_factor__end_of_period` | decimal | Pool Balance > Pool Factors > Class A-4 Note Pool Factor > End of Period |
| `pool_factors__class_b_note_pool_factor__end_of_period` | decimal | Pool Balance > Pool Factors > Class B Note Pool Factor > End of Period |
| `pool_factors__class_c_note_pool_factor__end_of_period` | decimal | Pool Balance > Pool Factors > Class C Note Pool Factor > End of Period |
| `pool_factors__class_d_note_pool_factor__end_of_period` | decimal | Pool Balance > Pool Factors > Class D Note Pool Factor > End of Period |
| `pool_factors__note_pool_factor__end_of_period` | decimal | Pool Balance > Pool Factors > Note Pool Factor > End of Period |
| `priority_principal_distributable_amount` | money_cents | Application of Available Funds > Priority Principal Distributable Amount |
| `quaternary_principal_distributable_amount` | money_cents | Application of Available Funds > Quaternary Principal Distributable Amount |
| `regular_principal_distributable_amount` | money_cents | Application of Available Funds > Regular Principal Distributable Amount |
| `required_payment_amount` | money_cents | Application of Available Funds > Required Payment Amount (Ln 26 + Ln 28 + (sum of Ln 29 through Ln 36)) |
| `required_reserve_account_amount_pct_of_initial_pool_balance` | money_cents | Certificate Payment Account Activity > Required Reserve Account Amount (1.00% of Initial Pool Balance) |
| `reserve_account_amount` | money_cents | Reserve Account Reconciliation > Reserve Account Amount (Ln 50 + Ln 51 - Ln 52) |
| `reserve_account_reconciliation__reserve_account_deficiency` | money_cents | Reserve Account Reconciliation > Reserve Account Deficiency (Ln50 - Ln57) |
| `reserve_account_reconciliation__reserve_account_draw_amount` | money_cents | Reserve Account Reconciliation > Reserve Account Draw Amount |
| `secondary_principal_distributable_amount` | money_cents | Application of Available Funds > Secondary Principal Distributable Amount |
| `servicing_fee__amount_paid` | money_cents | Application of Available Funds > Servicing Fee > Amount Paid |
| `servicing_fee__monthly_servicing_fee` | money_cents | Application of Available Funds > Servicing Fee > Monthly Servicing Fee |
| `servicing_fee__shortfall_amount_a_b_c` | money_cents | Application of Available Funds > Servicing Fee > Shortfall Amount (a + b - c) |
| `successor_servicer_and_asset_representations_reviewer_unpaid_expenses_and_indemnity_amount__asset_representations_reviewer_amount_paid` | money_cents | Application of Available Funds > Successor Servicer and Asset Representations Reviewer Unpaid Expenses and Indemnity Amounts > Asset Representations Reviewer Amount Paid |
| `successor_servicer_and_asset_representations_reviewer_unpaid_expenses_and_indemnity_amount__asset_representations_reviewer_shortfall_amount_d_e` | money_cents | Application of Available Funds > Successor Servicer and Asset Representations Reviewer Unpaid Expenses and Indemnity Amounts > Asset Representations Reviewer Shortfall Amount (d - e) |
| `successor_servicer_and_asset_representations_reviewer_unpaid_expenses_and_indemnity_amount__successor_servicer_amount_paid` | money_cents | Application of Available Funds > Successor Servicer and Asset Representations Reviewer Unpaid Expenses and Indemnity Amounts > Successor Servicer Amount Paid |
| `successor_servicer_and_asset_representations_reviewer_unpaid_expenses_and_indemnity_amount__successor_servicer_shortfall_amount_a_b` | money_cents | Application of Available Funds > Successor Servicer and Asset Representations Reviewer Unpaid Expenses and Indemnity Amounts > Successor Servicer Shortfall Amount (a - b) |
| `tertiary_principal_distributable_amount` | money_cents | Application of Available Funds > Tertiary Principal Distributable Amount |
| `withdrawals__class_a_1_distribution` | money_cents | Note Payment Account Activity > Withdrawals > Class A-1 Distribution |
| `withdrawals__class_a_2a_distribution` | money_cents | Note Payment Account Activity > Withdrawals > Class A-2a Distribution |
| `withdrawals__class_a_2b_distribution` | money_cents | Note Payment Account Activity > Withdrawals > Class A-2b Distribution |
| `withdrawals__class_a_3_distribution` | money_cents | Note Payment Account Activity > Withdrawals > Class A-3 Distribution |
| `withdrawals__class_a_4_distribution` | money_cents | Note Payment Account Activity > Withdrawals > Class A-4 Distribution |
| `withdrawals__class_b_distribution` | money_cents | Note Payment Account Activity > Withdrawals > Class B Distribution |
| `withdrawals__class_c_distribution` | money_cents | Note Payment Account Activity > Withdrawals > Class C Distribution |
| `withdrawals__class_d_distribution` | money_cents | Note Payment Account Activity > Withdrawals > Class D Distribution |
| `withdrawals__deposit_to_note_payment_account_for_monthly_note_interest_principal` | money_cents | Application of Available Funds > Withdrawals > Deposit to Note Payment Account for Monthly Note Interest/Principal |
| `withdrawals__deposit_to_reserve_account` | money_cents | Application of Available Funds > Withdrawals > Deposit to Reserve Account |
| `withdrawals__excess_collections_deposit_to_certificate_payment_account_for_payment_to_certificateholder` | money_cents | Application of Available Funds > Withdrawals > Excess Collections (Deposit to Certificate Payment Account for payment to Certificateholder) |
| `withdrawals__servicing_fee_and_unreimbursed_servicer_advances` | money_cents | Application of Available Funds > Withdrawals > Servicing Fee and Unreimbursed Servicer Advances |
| `withdrawals__successor_servicer_transition_expenses_and_indemnity_amounts` | money_cents | Application of Available Funds > Withdrawals > Successor Servicer Transition Expenses and Indemnity Amounts |
| `withdrawals__total_withdrawals_from_collection_account` | money_cents | Application of Available Funds > Withdrawals > Total Withdrawals from Collection Account (sum a - e) |
| `withdrawals__total_withdrawals_from_note_payment_account` | money_cents | Note Payment Account Activity > Withdrawals > Total Withdrawals from Note Payment Account (sum a - h) |
| `withdrawals_from_certificate_payment_account_for_certificateholder_distribution` | money_cents | Certificate Payment Account Activity > Withdrawals from Certificate Payment Account for Certificateholder Distribution |

## Answer

Write `/workspace/answer.json` as {"<field>": <value>, ...}, matching `/workspace/answer_schema.json`.
