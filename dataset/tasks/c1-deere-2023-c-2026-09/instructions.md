# WaterfallBench task `c1-deere-2023-c-2026-09`

**Deal:** John Deere Owner Trust 2023-C  
**Category:** C1 monthly_distribution

Compute every output field of ONE monthly distribution.

Files (all are SEC EDGAR HTML as filed):
- `/workspace/docs/`: the deal's governing documents (final prospectus; closing agreements where filed).
- `/workspace/reports/period_2026-08_opening_state.html`: the complete servicer report of the period before the first graded period.
- `/workspace/reports/period_2026-09_graded.html`: the servicer report for the distribution of 2026-09-15, with every output value removed. Input values (collections, pool data, rates, beginning balances) remain.

Rules:
- Money: integer US cents, exactly to the cent as the trustee reports it (e.g. $1,234.56 -> 123456).
- Percentages and other decimals: the number as it would be printed, without a % sign.
- Statuses: one of the listed values.
- Apply the priority of payments and definitions in the governing documents; deal parameters come from those documents.

## Required output fields

| field | type | report line |
|---|---|---|
| `administration_fee` | money_cents | Administration Fee |
| `administration_fee_shortfall` | money_cents | Administration Fee Shortfall |
| `amount_of_overcollateralization_note_value_less_aggregate_principal_amount_of_notes` | money_cents | Amount of Overcollateralization (Note value less aggregate principal amount of Notes) |
| `amount_of_servicing_fee_earned` | money_cents | Amount of Servicing Fee earned |
| `amount_of_servicing_fee_paid` | money_cents | Amount of Servicing Fee paid |
| `amount_of_servicing_fee_shortfall` | money_cents | Amount of Servicing Fee Shortfall |
| `amount_paid_to_certificateholder` | money_cents | Amount Paid to Certificateholder |
| `amount_paid_to_indenture_trustee` | money_cents | Amount paid to Indenture Trustee |
| `amount_paid_to_owner_trustee` | money_cents | Amount paid to Owner Trustee |
| `amount_to_be_withdrawn_from_the_reserve_account_and_deposited_into_certificateholder_accou` | money_cents | Amount to be withdrawn from the Reserve Account and Deposited into Certificateholder Account (5.05(c)) |
| `amount_to_be_withdrawn_from_the_reserve_account_and_deposited_into_note_distribution_accou` | money_cents | Amount to be withdrawn from the Reserve Account and deposited into Note Distribution Account (5.05(e)) |
| `amount_to_increase_the_amount_on_deposit_in_the_reserve_account_to_the_specified_reserve_a` | money_cents | Amount to increase the amount on deposit in the Reserve Account to the Specified Reserve Account Balance |
| `class_a_1_note_pool_factor` | decimal | Class A-1 Note Pool Factor |
| `class_a_1_noteholders_monthly_principal_distributable_amount` | money_cents | Class A-1 Noteholders' Monthly Principal Distributable Amount |
| `class_a_1_noteholders_principal_carryover_shortfall` | money_cents | Class A-1 Noteholders' Principal Carryover Shortfall |
| `class_a_1_noteholders_principal_distributable_amount` | money_cents | Class A-1 Noteholders' Principal Distributable Amount |
| `class_a_2_note_pool_factor` | decimal | Class A-2 Note Pool Factor |
| `class_a_2_noteholders_monthly_principal_distributable_amount` | money_cents | Class A-2 Noteholders' Monthly Principal Distributable Amount |
| `class_a_2_noteholders_principal_carryover_shortfall` | money_cents | Class A-2 Noteholders' Principal Carryover Shortfall |
| `class_a_2_noteholders_principal_distributable_amount` | money_cents | Class A-2 Noteholders' Principal Distributable Amount |
| `class_a_3_note_pool_factor` | decimal | Class A-3 Note Pool Factor |
| `class_a_3_noteholders_monthly_principal_distributable_amount` | money_cents | Class A-3 Noteholders' Monthly Principal Distributable Amount |
| `class_a_3_noteholders_principal_carryover_shortfall` | money_cents | Class A-3 Noteholders' Principal Carryover Shortfall |
| `class_a_3_noteholders_principal_distributable_amount` | money_cents | Class A-3 Noteholders' Principal Distributable Amount |
| `class_a_4_note_pool_factor` | decimal | Class A-4 Note Pool Factor |
| `class_a_4_noteholders_monthly_principal_distributable_amount` | money_cents | Class A-4 Noteholders' Monthly Principal Distributable Amount |
| `class_a_4_noteholders_principal_carryover_shortfall` | money_cents | Class A-4 Noteholders' Principal Carryover Shortfall |
| `class_a_4_noteholders_principal_distributable_amount` | money_cents | Class A-4 Noteholders' Principal Distributable Amount |
| `ending_balance_after_giving_effect_to_all_distributions` | money_cents | Ending Balance (after giving effect to all distributions) |
| `interest_amount_included_above` | money_cents | Interest Amount included above |
| `noteholders_distributable_amount` | money_cents | Noteholders' Distributable Amount |
| `noteholders_interest_carryover_shortfall` | money_cents | Noteholders' Interest Carryover Shortfall |
| `noteholders_interest_carryover_shortfall_applicable_to_class_a_1_notes` | money_cents | Noteholders' Interest Carryover Shortfall applicable to Class A-1 Notes |
| `noteholders_interest_carryover_shortfall_applicable_to_class_a_2_notes` | money_cents | Noteholders' Interest Carryover Shortfall applicable to Class A-2 Notes |
| `noteholders_interest_carryover_shortfall_applicable_to_class_a_3_notes` | money_cents | Noteholders' Interest Carryover Shortfall applicable to Class A-3 Notes |
| `noteholders_interest_carryover_shortfall_applicable_to_class_a_4_notes` | money_cents | Noteholders' Interest Carryover Shortfall applicable to Class A-4 Notes |
| `noteholders_interest_distributable_amount_applicable_to_class_a_1_notes` | money_cents | Noteholders' Interest Distributable Amount applicable to Class A-1 Notes |
| `noteholders_interest_distributable_amount_applicable_to_class_a_2_notes` | money_cents | Noteholders' Interest Distributable Amount applicable to Class A-2 Notes |
| `noteholders_interest_distributable_amount_applicable_to_class_a_3_notes` | money_cents | Noteholders' Interest Distributable Amount applicable to Class A-3 Notes |
| `noteholders_interest_distributable_amount_applicable_to_class_a_4_notes` | money_cents | Noteholders' Interest Distributable Amount applicable to Class A-4 Notes |
| `noteholders_interest_distributable_amount_deposited_into_note_distribution_account` | money_cents | Noteholders' Interest Distributable Amount deposited into Note Distribution Account |
| `noteholders_principal_carryover_shortfall` | money_cents | Noteholders' Principal Carryover Shortfall |
| `noteholders_principal_distribution_amount_deposited_into_note_distribution_account` | money_cents | Noteholders' Principal Distribution Amount deposited into Note Distribution Account |
| `of_principal_distribution_amount_applicable_to_class_a_1_noteholders` | decimal | % of Principal Distribution Amount applicable to Class A-1 Noteholders |
| `of_principal_distribution_amount_applicable_to_class_a_2_noteholders` | decimal | % of Principal Distribution Amount applicable to Class A-2 Noteholders |
| `of_principal_distribution_amount_applicable_to_class_a_3_noteholders` | decimal | % of Principal Distribution Amount applicable to Class A-3 Noteholders |
| `of_principal_distribution_amount_applicable_to_class_a_4_noteholders` | decimal | % of Principal Distribution Amount applicable to Class A-4 Noteholders |
| `outstanding_principal_balance_of_class_a_1_notes` | money_cents | Outstanding Principal Balance of Class A-1 Notes |
| `outstanding_principal_balance_of_class_a_2_notes` | money_cents | Outstanding Principal Balance of Class A-2 Notes |
| `outstanding_principal_balance_of_class_a_3_notes` | money_cents | Outstanding Principal Balance of Class A-3 Notes |
| `outstanding_principal_balance_of_class_a_4_notes` | money_cents | Outstanding Principal Balance of Class A-4 Notes |
| `principal_amount_included_above` | money_cents | Principal Amount included above |
| `section_5_04_iii_asset_representations_review_fees` | money_cents | Section 5.04 (iii) - Asset Representations Review Fees |
| `section_5_04_ix_asset_representations_review_fees` | money_cents | Section 5.04 (ix) - Asset Representations Review Fees |
| `servicing_fee` | money_cents | Servicing Fee |
| `specified_reserve_account_balance` | money_cents | Specified Reserve Account Balance |

## Answer

Write `/workspace/answer.json` as {"<field>": <value>, ...}, matching `/workspace/answer_schema.json`.
