"""Contract family: Nissan Auto Lease Trust (sponsor Nissan Motor Acceptance Company LLC, NMAC).

Source of rules: final prospectus (424B5) "Distributions on the Notes — Determination of Available Funds",
"— Deposits to the Distribution Accounts; Priority of Payments", "The Notes — Principal" (Optimal Principal
Distributable Amount, Principal Carryover Shortfall), "Security for the Notes — The Reserve Account" (Reserve
Account Requirement) and "Description of the Servicing Agreement" (Servicing Fee). The monthly Servicer Report
(EX-99.1) is a fixed seven-table layout shared by every deal of the shelf.

Balance identity (notes): ending = beginning - principal paid. Lease notes in this family have no loss
allocation / write-down, write-up, capitalised interest, cancellation or accretion terms (documented zeros).
The certificates (initial overcollateralisation) are not reduced while notes are outstanding.
"""

from __future__ import annotations

import re

FAMILY_ID = "nissan_auto_lease_trust"
NAME_PATTERN = "nissan auto lease trust <s>"
ASSET_CLASS = "auto_lease"

# Statistics: not part of the waterfall (neither consumed nor computed by the reference).
OUT_OF_SCOPE_SECTIONS = ("v pool statistics", "units", "net loss ratio", "delinquent receivables",
                         "61 days delinquencies as percentage of receivables", "aggregate sales performance of auctioned vehicles",
                         "cumulative sales performance of auctioned vehicles")
# Vehicle-disposition activity table (counts and proceeds by termination type; informational breakdown of the
# Vehicle Disposition Proceeds already reported as collections) and the narrative Statements to Noteholders.
ARTEFACT_FIELDS = ()
OUT_OF_SCOPE_FIELD = re.compile(
    r"^(early_termination|involuntary_repossession|voluntary_repossession|full_termination|bankrupt\w*|insurance_payoff|"
    r"customer_payoff|grounding_dealer_payoff|dealer_purchase|total)__(reallocation\w*|net_insurance\w*|lease_payoffs|count)$"
    r"|^vii_statements_to_noteholders|^have_there_been_any|^has_there_been_any"
    r"|^securitization_value_of_defaulted|^recoveries_of_defaulted|^aggregate_defaulted|^pool_balance_at_beginning_of_collection_period$"
    r"|^weighted_average_remaining|^monthly_prepayment|^lifetime_prepayment|^cumulative_net_losses|^net_loss_ratio"
    r"|^remaining_available_collections_released_to_seller__2$")  # printed twice only on a deal's first report
# Reconciliation of advances (section VI) is an account roll-forward of servicer advances: in scope.
IN_SCOPE_FROM_STATS = re.compile(r"(beginning_balance_of|reimbursement_of_outstanding|additional\w*advances_for_current_period|ending_balance_of)_?\w*advance")

# Periods whose values were inspected while building the parser, label map and checks (excluded from test).
DESIGN_EXPOSED_PERIODS = {
    (1999583, "20260531"),  # 2024-A, Jun-2026 distribution: full report read to design the module
    (1999583, "20241130"),  # 2024-A, Dec-2024: principal totals printed while diagnosing A-2 pro rata rounding
    (1999583, "20250331"),  # 2024-A, Apr-2025: class balances seen in a failing balance-identity check
    (1999583, "20251031"),  # 2024-A, Nov-2025: values seen in a candidate-mismatch sample
    (1999583, "20260630"),  # 2024-A, Jul-2026: certificate balances seen in a failing balance-identity check
}

BALANCE_IDENTITY = ("end_balance[c] = beginning_balance[c] - principal_payment[c]  (loss allocation, write-up, capitalised "
                    "interest, cancellation: documented zero; certificates not reduced while notes are outstanding)")

# Day-month-year dates printed inside labels/headers (e.g. "31-May-26") and statistic counts glued to labels
# (e.g. "Principal Amount of Gross Losses (31)") change every period; they are not part of a field's identity.
DMY = re.compile(r"\b\d{1,2}-[A-Za-z]{3}-\d{2,4}\b")
COUNT_SUFFIX = re.compile(r"\s*\(\s*[\d,]+\s*\)\s*$")
# Header cells sometimes lose the line-break space ("PrincipalPayment Due", "$1000Face Amount", "SecuritizationValue").
GLUED_WORDS = re.compile(r"(?<=[a-z0-9])(?=[A-Z][a-z])")
# Zero amounts printed as negatives without "$" or thousands separator: "(0.00)" / "(0.0000000)".
PAREN_DEC = re.compile(r"^\((\d[\d,]*\.\d+)\)$")
_PARSE_LOCK = __import__("threading").Lock()


def parse_report(html: str):
    from decimal import Decimal

    from .. import grid as _grid
    orig = _grid.parse_value

    def parse_value(t, scale=1):
        r = orig(t, scale)
        if r is None:
            m = PAREN_DEC.match(t.strip())
            if m:
                d = Decimal(m.group(1).replace(",", ""))
                return ("decimal", -d if d else abs(d))
        return r

    with _PARSE_LOCK:  # grid.parse_report looks parse_value up at module level; restore it afterwards
        _grid.parse_value = parse_value
        try:
            g = _grid.parse_report(html)
        finally:
            _grid.parse_value = orig
    for c in g.cells:
        for attr in ("section", "parent", "label", "column"):
            t = GLUED_WORDS.sub(" ", DMY.sub(" ", getattr(c, attr)))
            if attr == "label":
                t = COUNT_SUFFIX.sub("", t)
            setattr(c, attr, " ".join(t.split()))
    return g


def in_scope(fs: dict) -> bool:
    f, sec = fs["field"], fs["section"]
    if OUT_OF_SCOPE_FIELD.search(f):
        return False
    if sec in OUT_OF_SCOPE_SECTIONS or sec.startswith("v pool statistics"):
        return bool(IN_SCOPE_FROM_STATS.search(f))
    return True


def kind_override(field: str, kind: str) -> str:
    """Dollar columns print zero (and small amounts) as '0.00' without a thousands separator: those fields are
    money. Pool factors and per-$1,000 amounts (7 decimals) keep the decimal kind; rates keep pct."""
    if kind == "decimal" and not field.endswith(("pool_factor", "per_amt_face_amount")):
        return "money"
    return kind


CLASS_ROW = re.compile(r"^(class_[a-z](?:_\d+[a-z]?)?_notes|certificates)__beginning_balance$")


def classes(v: dict) -> list[str]:
    """Security stems in report order of the SUMMARY table, e.g. class_a_1_notes, ..., certificates."""
    return [m.group(1) for k in v for m in [CLASS_ROW.match(k)] if m]


def note_classes(v: dict) -> list[str]:
    return [c for c in classes(v) if c != "certificates"]


def interest_stem(c: str) -> str:
    """Interest-section stem: class_a_4_notes -> class_a_4_notes (the A-4 section header drops 'Notes' but the row
    labels keep it), certificates -> certificate."""
    return "certificate" if c == "certificates" else c


def _g(v: dict, k: str):
    if k not in v:
        raise KeyError(k)
    return v[k]


# Deals with only Class A notes print "...on the Class A Notes" / "Class A Noteholders'"; deals with Class B/C notes
# print "...on the Notes" / "Noteholders'".
NOTE_PRINCIPAL_PAID = ("total_monthly_principal_paid_on_the_notes", "total_monthly_principal_paid_on_the_class_a_notes")
NOTE_PRINCIPAL_CARRYOVER = ("total_noteholders_principal_carryover_shortfall", "total_class_a_noteholders_principal_carryover_shortfall")
NOTE_PRINCIPAL_DISTRIBUTABLE = ("total_noteholders_principal_distributable_amount", "total_class_a_noteholders_principal_distributable_amount")
NOTE_PRINCIPAL_CHG = ("chg_in_total_noteholders_principal_carryover_shortfall", "chg_in_total_class_a_noteholders_principal_carryover_shortfall")


def pick(v: dict, names: tuple[str, ...]) -> str:
    """The variant of a field name present in this report."""
    for n in names:
        if n in v:
            return n
    raise KeyError(names[0])


def checks(v: dict) -> list[tuple[str, str, bool, str]]:
    out = []

    def chk(group, name, fn):
        try:
            ok, detail = fn()
        except KeyError as e:
            ok, detail = False, f"missing field {e}"
        out.append((group, name, bool(ok), detail))

    cls = classes(v)
    notes = note_classes(v)
    if not notes:
        out.append(("anchoring", "classes_present", False, "no class rows"))
        return out

    # 2. class balance identity (notes and certificates)
    for c in cls:
        chk("balance_identity", c, lambda c=c: (
            _g(v, f"{c}__ending_balance") == _g(v, f"{c}__beginning_balance") - _g(v, f"{c}__principal_payment_due"),
            f"{_g(v, f'{c}__beginning_balance')} - {_g(v, f'{c}__principal_payment_due')} vs {_g(v, f'{c}__ending_balance')}"))

    # 4. account roll-forwards: reserve account, servicer advances (residual/sales-proceeds and monthly payment)
    def reserve():
        avail = _g(v, "reserve_fund_available_for_distribution")
        ok1 = avail == _g(v, "beginning_reserve_account_balance") + _g(v, "additional_cash_infusion") + _g(v, "reinvestment_income_for_the_period")
        gross = _g(v, "gross_reserve_account_balance")
        ok2 = gross == avail - _g(v, "reserve_fund_draw_amount") + _g(v, "deposit_of_remaining_available_collections")
        end = _g(v, "total_ending_reserve_account_balance")
        ok3 = end == gross - _g(v, "remaining_available_collections_released_to_seller")
        return ok1 and ok2 and ok3, f"avail {avail} gross {gross} end {end}"
    chk("account_rollforward", "reserve_account", reserve)
    chk("account_rollforward", "sales_proceeds_advance", lambda: (
        _g(v, "ending_balance_of_residual_advance") == _g(v, "beginning_balance_of_residual_advance")
        - _g(v, "reimbursement_of_outstanding_advance") + _g(v, "additional_advances_for_current_period"), ""))
    chk("account_rollforward", "payment_advance", lambda: (
        _g(v, "ending_balance_of_payment_advance") == _g(v, "beginning_balance_of_payment_advance")
        - _g(v, "reimbursement_of_outstanding_payment_advance") + _g(v, "additional_payment_advances_for_current_period"), ""))
    chk("account_rollforward", "advance_reimbursements_agree", lambda: (
        _g(v, "reimbursement_of_outstanding_advance") == _g(v, "reimbursement_of_sales_proceeds_advance")
        and _g(v, "reimbursement_of_outstanding_payment_advance") == _g(v, "reimbursement_of_payment_advance")
        and _g(v, "additional_advances_for_current_period") == _g(v, "aggregate_sales_proceeds_advance")
        and _g(v, "additional_payment_advances_for_current_period") == _g(v, "aggregate_monthly_payment_advances"), ""))

    # 5. full cash reconciliation: sources (collections incl. advances + reserve draw) = uses
    def cash():
        src = _g(v, "total_available_for_distribution")
        interest = _g(v, "total_note_and_certificate_monthly_interest_paid")
        principal = _g(v, pick(v, NOTE_PRINCIPAL_PAID)) + _g(v, "total_monthly_principal_paid_on_the_certificates")
        uses = (_g(v, "total_trustee_advances_and_servicing_fee_paid") + interest + principal
                + _g(v, "remaining_available_collections"))
        return src == uses, f"sources {src} vs uses {uses}"
    chk("cash_reconciliation", "sources_equal_uses", cash)
    chk("cash_reconciliation", "available_for_distribution", lambda: (
        _g(v, "total_available_for_distribution") == _g(v, "iii_distributions__total_collections") + _g(v, "reserve_amounts_available_for_distribution"), ""))
    chk("cash_reconciliation", "available_for_principal", lambda: (
        _g(v, "total_available_for_principal_distribution") == _g(v, "total_available_for_distribution")
        - _g(v, "total_trustee_advances_and_servicing_fee_paid") - _g(v, "total_note_and_certificate_monthly_interest_paid"), ""))
    chk("cash_reconciliation", "remaining_collections_to_reserve", lambda: (
        _g(v, "deposit_of_remaining_available_collections") == _g(v, "remaining_available_collections"), ""))

    # 6. totals
    chk("totals", "collections", lambda: (
        _g(v, "vehicle_disposition_proceeds__total_collections") == _g(v, "total_monthly_payments") + _g(v, "interest_rate_cap_payments")
        + _g(v, "total_advances") + _g(v, "repurchase_payments") + _g(v, "recoveries")
        + _g(v, "net_liquidation_proceeds_includes_reallocation_payments_and_net_auction_proceeds")
        + _g(v, "excess_wear_and_tear_and_excess_mileage") + _g(v, "remaining_payoffs") + _g(v, "net_insurance_proceeds")
        + _g(v, "residual_value_surplus"), ""))
    chk("totals", "collections_carried", lambda: (_g(v, "iii_distributions__total_collections") == _g(v, "vehicle_disposition_proceeds__total_collections"), ""))
    chk("totals", "monthly_payments", lambda: (_g(v, "total_monthly_payments") == _g(v, "monthly_principal") + _g(v, "monthly_interest"), ""))
    chk("totals", "advances", lambda: (_g(v, "total_advances") == _g(v, "aggregate_monthly_payment_advances") + _g(v, "aggregate_sales_proceeds_advance"), ""))
    chk("totals", "trustee_advances_servicing", lambda: (
        _g(v, "total_trustee_advances_and_servicing_fee_paid") == _g(v, "amounts_due_indenture_trustee_as_compensation_or_indemnity")
        + _g(v, "reimbursement_of_payment_advance") + _g(v, "reimbursement_of_sales_proceeds_advance") + _g(v, "servicing_fee_paid"), ""))
    chk("totals", "servicing_fee_shortfall", lambda: (_g(v, "servicing_fee_shortfall") == _g(v, "servicing_fee_due") - _g(v, "servicing_fee_paid"), ""))
    for pos in ("beginning_balance", "ending_balance", "initial_balance"):
        chk("totals", f"securities_{pos}", lambda pos=pos: (_g(v, f"total_securities__{pos}") == sum(_g(v, f"{c}__{pos}") for c in cls), ""))
    chk("totals", "securities_principal", lambda: (_g(v, "total_securities__principal_payment_due") == sum(_g(v, f"{c}__principal_payment_due") for c in cls), ""))
    chk("totals", "securities_interest", lambda: (_g(v, "total_securities__interest_payment") == sum(_g(v, f"{c}__interest_payment") for c in cls), ""))
    chk("totals", "interest_paid_by_class", lambda: (all(
        _g(v, f"{c}__interest_payment") == _g(v, f"{interest_stem(c)}_monthly_interest_paid") for c in cls), ""))
    chk("totals", "interest_paid_total", lambda: (
        _g(v, "total_note_and_certificate_monthly_interest_paid") == sum(_g(v, f"{interest_stem(c)}_monthly_interest_paid") for c in cls), ""))
    chk("totals", "interest_due_total", lambda: (
        _g(v, "total_note_and_certificate_monthly_interest_due") == sum(_g(v, f"{interest_stem(c)}_monthly_available_interest_distribution_amount") for c in cls), ""))
    chk("totals", "note_principal_total", lambda: (
        _g(v, pick(v, NOTE_PRINCIPAL_PAID)) == sum(_g(v, f"{c}__principal_payment_due") for c in notes), ""))
    chk("totals", "pool_securitization_value_rollforward", lambda: (
        _g(v, "pool_balance_end_of_period__securitization_value") == _g(v, "pool_balance_beginning_of_period__securitization_value")
        + _g(v, "total_depreciation_received__securitization_value") + _g(v, "principal_amount_of_gross_losses__securitization_value")
        + _g(v, "repurchase_reallocation__securitization_value") + _g(v, "early_terminations__securitization_value")
        + _g(v, "scheduled_terminations__securitization_value"), ""))
    chk("totals", "portfolio_equals_pool", lambda: (
        _g(v, "total_portfolio__ending_balance") == _g(v, "pool_balance_end_of_period__securitization_value")
        and _g(v, "total_portfolio__beginning_balance") == _g(v, "pool_balance_beginning_of_period__securitization_value"), ""))

    # 8. signs: every money field non-negative except the pool roll-forward reductions (printed in parentheses)
    neg = [k for k, x in v.items() if isinstance(x, int) and not isinstance(x, bool) and x < 0
           and not k.startswith(("total_depreciation_received", "principal_amount_of_gross_losses", "repurchase_reallocation",
                                 "early_terminations", "scheduled_terminations"))]
    out.append(("units_signs", "money_non_negative", not neg, ",".join(neg[:5])))
    return out


def continuity_pairs(v: dict) -> list[tuple[str, str]]:
    pairs = [(f"{c}__ending_balance", f"{c}__beginning_balance") for c in classes(v)]
    pairs += [("total_ending_reserve_account_balance", "beginning_reserve_account_balance"),
              ("pool_balance_end_of_period__securitization_value", "pool_balance_beginning_of_period__securitization_value"),
              ("ending_balance_of_residual_advance", "beginning_balance_of_residual_advance"),
              ("ending_balance_of_payment_advance", "beginning_balance_of_payment_advance")]
    return pairs


def stress_signals(cur: dict, prev: dict, params: dict) -> list[str]:
    """C3 signals from certified values only."""
    out = []
    if cur.get("reserve_fund_draw_amount", 0) or cur.get("reserve_amounts_available_for_distribution", 0):
        out.append("reserve_withdrawal")
    shortfall = [k for k, x in cur.items() if re.search(r"(interest_carryover_shortfall|chg_in_\w*int_carryover_shortfall)$", k) and x]
    if shortfall or cur.get("total_note_and_certificate_interest_carryover_shortfall", 0):
        out.append("interest_shortfall")
    if cur.get("servicing_fee_shortfall", 0):
        out.append("servicing_fee_shortfall")
    if any(cur.get(n, 0) for n in NOTE_PRINCIPAL_CARRYOVER + NOTE_PRINCIPAL_CHG):
        out.append("principal_shortfall")
    # principal-payment mode: sequential by class pre-acceleration; a payment to more than one non-A-2 class at once
    # (other than the final class retiring) would indicate the post-acceleration pro rata mode.
    paid = [c for c in note_classes(cur) if cur.get(f"{c}__principal_payment_due", 0)]
    prev_paid = [c for c in note_classes(prev or {}) if (prev or {}).get(f"{c}__principal_payment_due", 0)]
    def _mode(p):
        groups = {re.sub(r"(a_2)[ab]", r"\1", c) for c in p}
        return "pro_rata" if len(groups) > 2 else "sequential"
    if prev and paid and prev_paid and _mode(paid) != _mode(prev_paid):
        out.append("principal_mode_change")
    init = cur.get("total_portfolio__initial_balance")
    end = cur.get("pool_balance_end_of_period__securitization_value")
    if init and end is not None and end * 10 <= init:  # Optional Purchase threshold: 10% of cutoff Securitization Value
        out.append("pool_factor_at_or_below_cleanup_threshold")
    return out


# ---------------- deal parameters (anchored in the final prospectus) ----------------
Q = r"[“\"]\s*"
QE = r"\s*[”\"]"
PARAM_SPECS = [
    {"param": "servicing_fee_rate", "unit": "pct",
     "label": r"entitled to receive a fee in respect of the \d{4}-[A-Z] Series Assets equal to",
     "value": r"one-twelfth of the product of \(a\)\s*(\d+\.\d+)\s*%", "window": 200},
    {"param": "reserve_requirement_pct_through_a2_payoff", "unit": "pct",
     "label": Q + r"Reserve Account Requirement" + QE + r"\s*will be",
     "value": r"on or prior to the payment in full of the Class A-2 notes, at least (\d+\.\d+)\s*%", "window": 300},
    {"param": "reserve_requirement_pct_after_a2_payoff", "unit": "pct",
     "label": Q + r"Reserve Account Requirement" + QE + r"\s*will be",
     "value": r"following the payment in full of the Class A-2 notes, at least (\d+\.\d+)\s*%", "window": 500},
]

PARAMS_SCHEMA = {"type": "object", "properties": {
    "servicing_fee_rate": {"type": "string", "description": "Annual rate in the Servicing Fee definition (the fee is one-twelfth of this percentage times the aggregate Securitization Value at the start of the Collection Period), exactly as printed, e.g. 1.00%"},
    "reserve_requirement_pct_through_a2_payoff": {"type": "string", "description": "Reserve Account Requirement percentage of the cutoff-date aggregate Securitization Value that applies on each payment date on or prior to the payment in full of the Class A-2 notes, exactly as printed"},
    "reserve_requirement_pct_after_a2_payoff": {"type": "string", "description": "Reserve Account Requirement percentage of the cutoff-date aggregate Securitization Value that applies on each payment date following the payment in full of the Class A-2 notes, exactly as printed"},
}}


def anchor_class_table(html: str) -> dict:
    """Class rates and balances are printed in every Servicer Report (inputs); no cover-table parameters are used."""
    return {}


MON = {m: i for i, m in enumerate(["jan", "feb", "mar", "apr", "may", "jun", "jul", "aug", "sep", "oct", "nov", "dec"], 1)}


def period_meta(html: str) -> dict:
    """Header dates and day counts printed on the Servicer Report (kept in sanitized reports; not outputs)."""
    from .. import edgar
    t = " ".join(edgar.html_to_text(html)[:4000].replace("|", " ").split())
    out = {}
    for key, pat in (("collection_period_start", r"Collection Period Start\s+(\d{1,2}-[A-Za-z]{3}-\d{2})"),
                     ("collection_period_end", r"Collection Period End\s+(\d{1,2}-[A-Za-z]{3}-\d{2})"),
                     ("distribution_date", r"Distribution Date\s+(\d{1,2}-[A-Za-z]{3}-\d{2})"),
                     ("interest_period_begin", r"Beg\. of Interest Period\s+(\d{1,2}-[A-Za-z]{3}-\d{2})"),
                     ("interest_period_end", r"End of Interest Period\s+(\d{1,2}-[A-Za-z]{3}-\d{2})"),
                     ("days_30_360", r"30/360 Days\s+(\d+)"),
                     ("days_actual_360", r"Actual/360 Days\s+(\d+)")):
        m = re.search(pat, t)
        out[key] = m.group(1) if m else None
    return out
