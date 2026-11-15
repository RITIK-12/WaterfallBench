"""Contract family: Navient Student Loan Trust (FFELP), sponsor Navient Solutions / depositor Navient Funding, LLC.

Source of rules: prospectus supplement "Distributions from the Collection Account" (clauses (a)-(k)), glossary
("Principal Distribution Amount", "Specified Overcollateralization Amount", "Specified Reserve Account Balance",
"Adjusted Pool Balance", "Class A/B Noteholders' Interest/Principal Distribution Amount"), "Administration Fee",
"Compensation of the Servicer", "Floor Income Rebate Account", "Optional Purchase". The Monthly Servicing Report
(EX-99.1) prints: deal parameters (I), trust activity / Available Funds (II), statistics (III-V), the waterfall
(VI, with trigger tests), per-class distributions (VII) and reconciliations (VIII).

Balance identity (notes): ending principal balance = beginning balance - principal paid. FFELP notes in this family
have no loss allocation / write-down, write-up, capitalised (deferred) interest, cancellation or accretion terms
(documented zeros).

Sign convention: deductions the report prints in parentheses with the "(" and ")" in cells separate from the
number (e.g. "Less: Funds Previously Remitted", "E Less: Specified Reserve Account Balance", floor income rebate
"Release to Collection Account") parse as positive magnitudes; checks treat them as magnitudes.
"""

from __future__ import annotations

import re
from decimal import Decimal

FAMILY_ID = "navient_student_loan_trust"
NAME_PATTERN = "navient student loan trust <s>"
ASSET_CLASS = "student_loan"

# Section labels are mostly absent in this layout (only the "waterfall triggers" sub-table is detected and it
# propagates downward), so scope is decided on field names.
OUT_OF_SCOPE_SECTIONS: tuple = ()
OUT_OF_SCOPE_FIELDS = re.compile(
    r"^(?:"
    # III. portfolio characteristics by status (current and prior month)
    r"(?:interim_in_school|in_school|grace|interim_grace|deferment|repayment_current|current|\d+_\d+_days_delinquent|\d+_days_delinquent"
    r"|forbearance|claims_in_process|aged_claims_rejected|repayment_\w+|total)__\w+"
    # V. statistics by loan type and school type
    r"|(?:gsl_\w+|plus_\w+|sls_\w+|consolidation_loans|four_year|two_year|technical|other)(?:__\w+)?|total(?:__\d+)?"
    # IV. portfolio characteristics (cont'd) except unpaid fees / shortfalls / carryovers
    r"|pool_balance__date__[45]|outstanding_borrower_accrued_interest\w*|borrower_accrued_interest\w*|total_loans\w*|total_borrowers\w*"
    r"|weighted_average_coupon__date\w*|weighted_average_remaining_term\w*|non_reimbursable_losses__date\w*|cumulative_\w+"
    r"|since_issued_constant_prepayment_rate\w*|loan_substitutions\w*|rejected_claim_repurchases\w*|non_cash_principal_activity_capitalized_interest\w*"
    r"|borrower_interest_accrued\w*|interest_subsidy_payments_accrued\w*|special_allowance_payments_accrued\w*"
    # I.A pool statistics that the waterfall neither consumes nor computes
    r"|weighted_average_coupon_wac\w*|number_of_loans\w*|aggregate_outstanding_principal_balance_\w+"
    # II. memo items below Available Funds (statistics, not cash)
    r"|n_non_cash_principal_activity\w*|o_non_reimbursable_losses\w*|p_aggregate_purchased_amounts\w*|q_aggregate_loan_substitutions\w*"
    r")$")
ARTEFACT_FIELDS: tuple = ()

# Periods whose printed values were read while building the parser, label map and checks (before any split).
# Excluded from the test split and disclosed. (Aggregate surveys over all reports - pool-factor ranges, counts of
# principal-shortfall months - were also computed while scoping C3; no other individual values were read.)
DESIGN_EXPOSED_ACCESSIONS = {
    "0001140361-26-039059",  # 2014-1, Sep 2026 distribution: full report read to design the module
    "0001140361-25-044735",  # 2014-1, Nov 2025 distribution: receipts lines (negative reimbursement parsing)
    "0001140361-26-035740",  # 2014-4, Aug 2026 distribution: reconciliation tables (VIII)
    "0001140361-25-012519",  # 2014-4, Mar 2025 distribution: shifted floor income rebate rows
    "0001140361-24-045624",  # 2015-3, Oct 2024 distribution: waterfall with accelerated-principal steps
    "0001140361-25-021683",  # 2014-8, May 2025 distribution: receipts lines
    "0001140361-25-012524",  # 2015-1, Mar 2025 distribution: failing class B balance check detail
    "0001140361-26-024158",  # 2014-7, May 2026 distribution: failing sources=uses check detail
    "0001140361-26-035745",  # 2015-1, Aug 2026 distribution: failing reserve table check detail
    "0001140361-24-045619",  # 2014-6, Oct 2024 distribution: reconciliation tables (VIII)
    "0001140361-24-048624",  # 2014-6, Nov 2024 distribution: reconciliation tables (VIII)
    "0001140361-25-003357",  # 2014-6, Jan 2025 distribution: reconciliation tables (VIII)
}

BALANCE_IDENTITY = ("ending_principal_balance[c] = beginning_balance[c] - principal_paid[c]  "
                    "(loss allocation, write-down/up, capitalised interest, cancellation, accretion: documented zero)")

# decimals that are genuinely ratios/factors (everything else printed as d.dd without "$" is a dollar amount)
NON_MONEY_DECIMAL = re.compile(r"^(pool_factor|parity_ratio|daycount_fraction|accrued_interest_factor|paydown_factor|ending_balance_factor"
                               r"|weighted_average_remaining_term)\w*$")


STATS_SUFFIX = re.compile(r"__(wtd_avg_coupon|coupon|loans|principal|of_principal|weighted_average_coupon|amount)(__\d+)?$")


def in_scope(fs: dict) -> bool:
    f = fs["field"]
    return not (OUT_OF_SCOPE_FIELDS.match(f) or STATS_SUFFIX.search(f) or f.startswith("__total"))


# ---------------- parser hook (layout quirks of this report; the filed HTML itself is never modified) --------
PAREN_NUM = re.compile(r"^\(\s*(\d[\d,]*\.\d{2})\s*\)?$")


def parse_report(html: str):
    """grid.parse_report on a normalised in-memory copy of the report:
    - an amount printed as "(362.69)" or "$ | (41,061.80)" is a negative dollar amount; the shared parser reads the
      first as a non-value (and then mistakes the row for a header row) and the second as positive, so the cell text
      is rewritten to "$(362.69)" before parsing (same table/row/column positions);
    - the waterfall's second column is headed "Remaining Funds Balance" in most months and "Funds Balance" in a few.
    """
    from lxml import html as LH
    from .. import grid
    doc = LH.fromstring(html)
    for td in doc.xpath("//td|//th"):
        t = " ".join(td.text_content().replace("\xa0", " ").split())
        m = PAREN_NUM.match(t)
        if m:
            for ch in list(td):
                td.remove(ch)
            td.text = f"$({m.group(1)})"
    g = grid.parse_report(LH.tostring(doc, encoding="unicode"))
    for c in g.cells:
        if grid.norm(c.column) == "funds balance":
            c.column = "Remaining Funds Balance"
        # Sub-table headings ("Waterfall Triggers", "D Supplemental Purchase Account") are detected as sections only
        # in some months, which renames fields month to month; field names here rely on label + document order.
        c.section = ""
    # VIII sub-table heading rows never carry a value; one filing (2014-4, Mar 2025) prints its floor income rebate
    # rows shifted up by one, putting an amount on the heading. That cell is not mapped (the shifted period then fails
    # anchoring on its blank "Ending Balance" and is dropped), so it cannot rename fields for the deal's other months.
    g.cells = [c for c in g.cells if not SUBTABLE_HEADING.match(grid.norm(c.label))]
    return g


SUBTABLE_HEADING = re.compile(r"^[a-d] (principal distribution reconciliation|reserve account reconciliation|floor income rebate account|supplemental purchase account)$")


def kind_override(field: str, kind: str) -> str:
    if kind == "decimal" and not NON_MONEY_DECIMAL.match(field):
        return "money"
    return kind


# ---------------- class structure ----------------
DEBT_RX = re.compile(r"^([a-z](?:\d+)?)_([0-9a-z]{9})__date$")


def classes(v: dict) -> list[tuple[str, str]]:
    """[(class id, cusip)] in class-name order (A1 < A2 < ... < B), from the I.B Debt Securities table."""
    out = []
    for k in v:
        m = DEBT_RX.match(k)
        if m:
            out.append((m.group(1), m.group(2)))
    return sorted(set(out))


def _suffix(i: int) -> str:
    return "" if i == 0 else f"__{i + 1}"


def class_field(row: str, i: int) -> str:
    """Per-class field of the VII Distributions table, positional by class order."""
    return f"{row}__date{_suffix(i)}"


def _g(v: dict, k: str):
    if k not in v:
        raise KeyError(k)
    return v[k]


def _any(v: dict, *ks):
    for k in ks:
        if k in v:
            return v[k]
    raise KeyError("|".join(ks))


PRINCIPAL_RECEIPTS = ("borrower_principal", "guarantor_principal", "consolidation_activity_principal", "seller_principal_reimbursement",
                      "servicer_principal_reimbursement", "rejected_claim_repurchased_principal", "other_principal_deposits")
INTEREST_RECEIPTS = ("borrower_interest", "guarantor_interest", "consolidation_activity_interest", "special_allowance_payments",
                     "interest_subsidy_payments", "seller_interest_reimbursement", "servicer_interest_reimbursement",
                     "rejected_claim_repurchased_interest", "other_interest_deposits")
OTHER_SOURCES = ("c_reserves_in_excess_of_requirement", "d_investment_income", "e_funds_borrowed_from_next_collection_period",
                 "f_funds_repaid_from_prior_collection_period", "g_loan_sale_or_purchase_proceeds", "h_initial_deposits_to_collection_account",
                 "i_excess_transferred_from_other_accounts", "j_other_deposits", "k_funds_released_from_capitalized_interest_account")
LESS_REMITTED = ("servicing_fees_to_servicer", "consolidation_loan_rebate_fees_to_dept_of_education",
                 "floor_income_rebate_fees_to_dept_of_education", "funds_allocated_to_the_floor_income_rebate_account")
WATERFALL = ("a_trustee_fees", "b_primary_servicing_fee", "c_administration_fee", "d_class_a_noteholders_interest_distribution_amount",
             "e_class_b_noteholders_interest_distribution_amount", "f_reserve_account_reinstatement",
             "g_class_a_noteholders_principal_distribution_amount", "h_class_b_noteholders_principal_distribution_amount",
             "i_unpaid_expenses_of_the_trustees", "j_carryover_servicing_fee",
             "k_remaining_amounts_to_the_noteholders_after_the_first_auction_date", "l_excess_distribution_certificateholder")


def waterfall_steps(v: dict) -> list[str]:
    """Waterfall step stems present in this report (deals differ slightly in step lettering)."""
    return [k[: -len("__paid")] for k in v if k.endswith("__paid") and re.match(r"^[a-z]_", k)]


def checks(v: dict) -> list[tuple[str, str, bool, str]]:
    out = []

    def chk(group, name, fn):
        try:
            ok, detail = fn()
        except KeyError as e:
            ok, detail = False, f"missing field {e}"
        out.append((group, name, bool(ok), detail))

    cls = classes(v)
    if not cls:
        return [("anchoring", "classes_present", False, "no debt securities rows")]

    # 2. class balance identity (VII) and agreement with I.B Debt Securities
    for i, (c, cusip) in enumerate(cls):
        chk("balance_identity", f"class_{c}", lambda i=i, cusip=cusip: (
            _g(v, class_field("ending_principal_balance", i)) == _g(v, f"beginning_balance__{cusip}") - _g(v, class_field("principal_paid", i)),
            f"{_g(v, f'beginning_balance__{cusip}')} - {_g(v, class_field('principal_paid', i))} vs {_g(v, class_field('ending_principal_balance', i))}"))
        chk("totals", f"class_{c}_debt_table_beginning", lambda i=i, c=c, cusip=cusip: (
            _g(v, f"{c}_{cusip}__date") == _g(v, f"beginning_balance__{cusip}"), ""))
        chk("totals", f"class_{c}_debt_table_ending", lambda i=i, c=c, cusip=cusip: (
            _g(v, f"{c}_{cusip}__date__2") == _g(v, class_field("ending_principal_balance", i)), ""))
        chk("totals", f"class_{c}_interest_due", lambda i=i: (
            _g(v, class_field("total_interest_due", i)) == _g(v, class_field("current_interest_due", i))
            + _g(v, class_field("interest_shortfall_from_prior_period_plus_accrued_interest", i)), ""))
        chk("totals", f"class_{c}_interest_shortfall", lambda i=i: (
            _g(v, class_field("interest_shortfall", i)) == _g(v, class_field("total_interest_due", i)) - _g(v, class_field("interest_paid", i)), ""))

    a_idx = [i for i, (c, _) in enumerate(cls) if c.startswith("a")]
    b_idx = [i for i, (c, _) in enumerate(cls) if c.startswith("b")]

    # 6. totals: class interest / principal vs waterfall lines; principal receipts; interest receipts; notes
    chk("totals", "class_a_interest", lambda: (
        _g(v, "d_class_a_noteholders_interest_distribution_amount__paid") == sum(_g(v, class_field("interest_paid", i)) for i in a_idx), ""))
    chk("totals", "class_b_interest", lambda: (
        _g(v, "e_class_b_noteholders_interest_distribution_amount__paid") == sum(_g(v, class_field("interest_paid", i)) for i in b_idx), ""))
    chk("totals", "class_a_principal", lambda: (
        _g(v, "g_class_a_noteholders_principal_distribution_amount__paid") == sum(_g(v, class_field("principal_paid", i)) for i in a_idx), ""))
    chk("totals", "class_b_principal", lambda: (
        _g(v, "h_class_b_noteholders_principal_distribution_amount__paid") == sum(_g(v, class_field("principal_paid", i)) for i in b_idx), ""))
    chk("totals", "principal_receipts", lambda: (
        _g(v, "total_principal_receipts") == sum(_g(v, k) for k in PRINCIPAL_RECEIPTS), ""))
    chk("totals", "interest_receipts", lambda: (
        _g(v, "total_interest_receipts") == sum(_g(v, k) for k in INTEREST_RECEIPTS), ""))
    chk("totals", "notes_outstanding_before", lambda: (
        _g(v, "notes_outstanding_principal_balance") == sum(_g(v, f"beginning_balance__{cu}") for _, cu in cls)
        and _g(v, "total_notes__date") == _g(v, "notes_outstanding_principal_balance"), ""))
    chk("totals", "notes_outstanding_after", lambda: (
        _g(v, "total_notes__date__2") == sum(_g(v, class_field("ending_principal_balance", i)) for i in range(len(cls))), ""))
    chk("totals", "pda_paid", lambda: (
        _g(v, "principal_distribution_amount_paid") == _g(v, "g_class_a_noteholders_principal_distribution_amount__paid")
        + _g(v, "h_class_b_noteholders_principal_distribution_amount__paid"), ""))
    chk("totals", "difference", lambda: (
        _g(v, "difference__date__2") == _g(v, "adjusted_pool_balance_supplemental_loan_purchase__date__2") - _g(v, "total_notes__date__2")
        and _g(v, "difference__date") == _g(v, "adjusted_pool_balance_supplemental_loan_purchase__date") - _g(v, "total_notes__date"), ""))

    # 5. cash reconciliation: Available Funds composition and waterfall running balance (sources = uses).
    # "Less: Funds Previously Remitted" amounts are printed in parentheses and certified as negative numbers.
    def avail():
        src = (_g(v, "total_principal_receipts") + _g(v, "total_interest_receipts") + sum(_g(v, k) for k in OTHER_SOURCES)
               + sum(_g(v, k) for k in LESS_REMITTED))
        return src == _g(v, "m_available_funds"), f"{src} vs {_g(v, 'm_available_funds')}"
    chk("cash_reconciliation", "available_funds", avail)

    def running():
        bal = _g(v, "total_available_funds__remaining_funds_balance")
        if bal != _g(v, "m_available_funds"):
            return False, "total available funds != M"
        for s in waterfall_steps(v):
            bal -= _g(v, f"{s}__paid")
            if bal != _g(v, f"{s}__remaining_funds_balance"):
                return False, f"running balance breaks at {s}: {bal} vs {_g(v, f'{s}__remaining_funds_balance')}"
        return bal == 0, f"final remaining {bal}"
    chk("cash_reconciliation", "sources_equal_uses", running)

    # 4. account rollforwards
    # Withdrawals from accounts print either as "-"/0.00 or in parentheses; they are compared as magnitudes.
    chk("account_rollforward", "reserve_account", lambda: (
        _g(v, "ending_reserve_account_balance") == _g(v, "balance_available") - abs(_g(v, "release_to_collection_account"))
        and _g(v, "balance_available") == _g(v, "beginning_period_balance") - abs(_g(v, "reserve_funds_utilized")) + _g(v, "reserve_funds_reinstated"), ""))
    chk("account_rollforward", "reserve_account_table_IC", lambda: (
        _g(v, "reserve_account_balance__date") == _g(v, "beginning_period_balance")
        and _g(v, "reserve_account_balance__date__2") == _g(v, "ending_reserve_account_balance"), ""))
    chk("account_rollforward", "reserve_release_in_available_funds", lambda: (
        abs(_g(v, "release_to_collection_account")) == _g(v, "c_reserves_in_excess_of_requirement"), ""))
    chk("account_rollforward", "reserve_reinstatement_in_waterfall", lambda: (
        _g(v, "reserve_funds_reinstated") == _g(v, "f_reserve_account_reinstatement__paid"), ""))
    chk("account_rollforward", "floor_income_rebate_account", lambda: (
        _g(v, "ending_balance") == _g(v, "beginning_period_balance__2") + _g(v, "deposits_for_the_period") - abs(_g(v, "release_to_collection_account__2"))
        and _g(v, "floor_income_rebate_account__date") == _g(v, "beginning_period_balance__2")
        and _g(v, "floor_income_rebate_account__date__2") == _g(v, "ending_balance")
        and _g(v, "deposits_for_the_period") == -_g(v, "funds_allocated_to_the_floor_income_rebate_account"), ""))
    chk("account_rollforward", "supplemental_purchase_account", lambda: (
        _g(v, "ending_balance__2") == _g(v, "beginning_period_balance__3") - _g(v, "supplemental_loan_purchases") - _g(v, "transfers_to_collection_account")
        and _g(v, "supplemental_loan_purchase_account__date__2") == _g(v, "ending_balance__2"), ""))
    chk("account_rollforward", "capitalized_interest_account", lambda: (
        _g(v, "capitalized_interest_account_balance__date__2") == _g(v, "c_capitalized_interest_account_balance"), ""))

    # pool / trigger identities
    chk("totals", "pool_balance", lambda: (
        _g(v, "pool_balance__date__3") == _g(v, "principal_balance__date__3") + _g(v, "interest_to_be_capitalized_balance__date__3"), ""))
    chk("totals", "trigger_total", lambda: (
        _g(v, "f_total") == _g(v, "a_student_loan_principal_outstanding") + _g(v, "b_interest_to_be_capitalized")
        + _g(v, "c_capitalized_interest_account_balance") + _g(v, "d_reserve_account_balance_after_any_reinstatement")
        - abs(_g(v, "e_less_specified_reserve_account_balance")), ""))
    chk("totals", "trigger_class_a_after", lambda: (
        _g(v, "g_class_a_notes_outstanding_after_application_of_available_funds")
        == sum(_g(v, class_field("ending_principal_balance", i)) for i in a_idx), ""))
    chk("totals", "pda_identity", lambda: (
        _g(v, "principal_distribution_amount") == min(_g(v, "notes_outstanding_principal_balance"), max(0,
            _g(v, "notes_outstanding_principal_balance") - (_g(v, "adjusted_pool_balance") - _g(v, "overcollateralization_amount")))), ""))

    # 8. signs: only receipts adjustments, remitted deductions and account withdrawals may print negative
    neg = [k for k, x in v.items() if isinstance(x, int) and not isinstance(x, bool) and x < 0 and not NEG_OK.match(k)]
    out.append(("units_signs", "money_non_negative_except_deductions", not neg, ",".join(neg[:5])))
    return out


NEG_OK = re.compile(r"^(" + "|".join(PRINCIPAL_RECEIPTS + INTEREST_RECEIPTS + OTHER_SOURCES + LESS_REMITTED)
                    + r"|total_principal_receipts|total_interest_receipts|e_less_specified_reserve_account_balance"
                    r"|release_to_collection_account(__2)?|reserve_funds_utilized|transfers_to_collection_account)$")


def continuity_pairs(v: dict) -> list[tuple[str, str]]:
    """(field in period t, field in period t+1) that must be equal."""
    pairs = []
    for i, (c, cusip) in enumerate(classes(v)):
        pairs.append((class_field("ending_principal_balance", i), f"beginning_balance__{cusip}"))
        pairs.append((f"{c}_{cusip}__date__2", f"{c}_{cusip}__date"))
    pairs += [("ending_reserve_account_balance", "beginning_period_balance"),
              ("ending_balance", "beginning_period_balance__2"),
              ("ending_balance__2", "beginning_period_balance__3"),
              ("pool_balance__date__3", "pool_balance__date__2"),
              ("adjusted_pool_1__date__3", "adjusted_pool_1__date__2"),
              ("total_notes__date__2", "total_notes__date")]
    return pairs


def stress_signals(cur: dict, prev: dict, params: dict) -> list[str]:
    """C3 signals from certified values only (cur = graded period, prev = prior period, both complete).

    Plan signals: trigger status change; reserve withdrawal; interest shortfall; principal-payment mode change;
    pool factor at/below the optional-purchase (clean-up) threshold. The report's trigger statuses ("H Insolvency
    Event..." / "I Available Funds Applied to Class A ... (G>F or H=Y)") print as bare "N"/"Y" and are not parsed as
    cells, so the G>F condition is evaluated from the certified trigger-table amounts instead. Also returned (outside
    the plan's list, for the selector to decide): principal distribution shortfall and unpaid fees."""
    sig = []

    def class_a_first(v):
        g, f = v.get("g_class_a_notes_outstanding_after_application_of_available_funds"), v.get("f_total")
        return None if g is None or f is None else g > f

    ca, pa = class_a_first(cur), (class_a_first(prev) if prev else None)
    if ca is not None and pa is not None and ca != pa:
        sig += ["trigger_status_change", "principal_payment_mode_change"]
    if ca:
        sig.append("class_a_first_condition_in_effect")
    if cur.get("reserve_funds_utilized", 0):
        sig.append("reserve_withdrawal")
    sf = [k for k in cur if re.match(r"^interest_shortfall__date(__\d+)?$", k)]
    if any(cur[k] for k in sf) or cur.get("note_interest_shortfall__date", 0):
        sig.append("interest_shortfall")
    thr = params.get("optional_purchase_threshold_percent")
    pf = cur.get("pool_factor__date__2")
    if thr is not None and pf is not None and Decimal(str(pf)) <= Decimal(str(thr)) / 100:
        sig.append("pool_factor_at_or_below_cleanup_threshold")
    if cur.get("note_principal_shortfall__date", 0) or (
            "principal_distribution_amount" in cur and cur.get("principal_distribution_amount_paid") != cur["principal_distribution_amount"]):
        sig.append("principal_distribution_shortfall")
    if cur.get("unpaid_administration_fees__date", 0) or cur.get("unpaid_primary_servicing_fees__date", 0):
        sig.append("unpaid_fees")
    return sorted(set(sig))


def period_meta(html: str) -> dict:
    from .. import edgar
    t = edgar.html_to_text(html)[:4000]
    out = {}
    for key, pat in (("distribution_date", r"Distribution Date\s*\|?\s*(\d{1,2}/\d{1,2}/\d{4})"),
                     ("collection_period", r"Collection Period\s*\|?\s*(\d{1,2}/\d{1,2}/\d{4}\s*-\s*\d{1,2}/\d{1,2}/\d{4})")):
        m = re.search(pat, t)
        out[key] = m.group(1) if m else None
    return out


# ---------------- deal parameters (anchored in the final prospectus supplement) ----------------
Q = r"[“\"]\s*"
QE = r"\s*[”\"]"
PARAM_SPECS = [
    {"param": "administration_fee_per_collection_period", "unit": "usd", "label": r"administration fee in an amount equal to",
     "value": r"(\$\s*[\d,]+(?:\.\d{2})?)\s+per collection period", "window": 60},
    {"param": "specified_oc_percent_of_adjusted_pool", "unit": "pct", "label": Q + r"Specified Overcollateralization Amount" + QE + r"\s*means",
     "value": r"(\d+(?:\.\d+)?)\s*%\s+of\s+the\s+Adjusted\s+Pool\s+Balance", "window": 200},
    {"param": "specified_oc_floor", "unit": "usd", "label": Q + r"Specified Overcollateralization Amount" + QE + r"\s*means",
     "value": r"Adjusted\s+Pool\s+Balance[^$]{0,80}?(\$\s*[\d,]+(?:\.\d{2})?)", "window": 300},
    {"param": "specified_reserve_percent_of_pool", "unit": "pct", "label": Q + r"Specified Reserve Account Balance" + QE + r"\s*means",
     "value": r"on or after the [A-Za-z]+ \d{4} distribution date,\s+(\d+(?:\.\d+)?)\s*%\s+of\s+the\s+Pool\s+Balance", "window": 700},
    {"param": "specified_reserve_floor", "unit": "usd", "label": Q + r"Specified Reserve Account Balance" + QE + r"\s*means",
     "value": r"\(b\)\s*\|?\s*(\$\s*[\d,]+(?:\.\d{2})?)", "window": 900},
    {"param": "adjusted_pool_reserve_inclusion_percent", "unit": "pct", "label": Q + r"Adjusted Pool Balance" + QE + r"\s*means",
     "value": r"greater than\s+(\d+(?:\.\d+)?)\s*%\s+of\s+the\s+Initial\s+Pool\s+Balance", "window": 300},
    {"param": "optional_purchase_threshold_percent", "unit": "pct", "label": r"Optional Purchase",
     "value": r"pool balance is\s+(\d+(?:\.\d+)?)\s*%\s+or less of the initial pool balance", "window": 400},
]

PARAMS_SCHEMA = {"type": "object", "properties": {
    "administration_fee_per_collection_period": {"type": "string", "description": "Administration fee amount per collection period, exactly as printed (e.g. $6,667)"},
    "specified_oc_percent_of_adjusted_pool": {"type": "string", "description": "From THIS prospectus supplement's Glossary definition of \"Specified Overcollateralization Amount\" (\"the greater of (a) X% of the Adjusted Pool Balance ... and (b) $Y\"): the percentage X exactly as printed in this document, e.g. 1.00%. Copy it from this document only; if it is not visible, return null."},
    "specified_oc_floor": {"type": "string", "description": "From THIS prospectus supplement's Glossary definition of \"Specified Overcollateralization Amount\": the dollar amount in clause (b), exactly as printed in this document, e.g. $1,500,000. Copy it from this document only; if it is not visible, return null."},
    "specified_reserve_percent_of_pool": {"type": "string", "description": "From the Glossary definition of \"Specified Reserve Account Balance\": clause (a)(ii) gives the percentage of the Pool Balance for distribution dates occurring ON OR AFTER a stated month. Return ONLY that single (a)(ii) percentage, e.g. 0.25% - one number with %, no other text."},
    "specified_reserve_floor": {"type": "string", "description": "From THIS prospectus supplement's Glossary definition of \"Specified Reserve Account Balance\": the dollar amount in clause (b), exactly as printed in this document (e.g. $759,861). Copy it from this document only; if it is not visible, return null."},
    "adjusted_pool_reserve_inclusion_percent": {"type": "string", "description": "In the definition of Adjusted Pool Balance, the percentage of the Initial Pool Balance above which the Specified Reserve Account Balance is added to the Pool Balance (e.g. 40%)"},
    "optional_purchase_threshold_percent": {"type": "string", "description": "Optional purchase (clean-up) threshold: the pool balance as a percentage of the initial pool balance at or below which the servicer may purchase all remaining loans (e.g. 10%)"},
}}


def anchor_class_table(html: str) -> dict:
    """No class-level params are used: note rates (index + spread) and accrual fractions are printed in each report
    and consumed as period inputs. (The prospectus the shared selector returns for this shelf is the preliminary
    424B2, whose cover table prints "1-month LIBOR plus %" with the spread blank.)"""
    return {}
