"""Contract family: CarMax Auto Owner Trust (sponsor CarMax Business Services, LLC).

Source of rules: prospectus "Application of Available Funds — Priority of Distributions (Pre-Acceleration)"
and "Description of the Notes — Payments of Principal"; the Monthly Servicer's Certificate (EX-99.1) prints
the formulas for its own sub-totals (e.g. "Ln 50 + Ln 51 - Ln 52").

Balance identity (notes): ending = beginning - principal paid. Auto-loan notes in this family have no loss
allocation / write-down, write-up, capitalised interest, cancellation or accretion terms (documented zeros).
"""

from __future__ import annotations

import re

FAMILY_ID = "carmax_auto_owner_trust"
NAME_PATTERN = "carmax auto owner trust <s>"
ASSET_CLASS = "auto_loan"

# Statistics sections are not part of the waterfall: neither consumed nor computed by the reference.
OUT_OF_SCOPE_SECTIONS = ("delinquency activity", "loss activity", "cumulative loss activity", "other servicing information")
# Presentation artefacts: a "0.15%" printed beside three section headings, unrelated to the deal's fee/reserve terms.
ARTEFACT_FIELDS = ("collection_account_activity", "required_reserve_account_amount", "servicing_fee")

BALANCE_IDENTITY = "end_balance[c] = beginning_balance[c] - principal_distribution[c]  (loss allocation, write-up, capitalised interest, cancellation: documented zero)"


# The Class A-2(b) note rate (Ln 16) prints "N/A" once the floating tranche is retired; it is a derived display
# value (SOFR + spread from the prospectus), so it is kept out of scope rather than certified period by period.
OUT_OF_SCOPE_FIELD_RX = re.compile(r"^note_rate_applicable_to_the_class_")


def _strip_digits(t: str) -> str:
    return re.sub(r"\d+$", "", (t or "").strip()).strip()


def in_scope(fs: dict) -> bool:
    for part in (fs["section"], fs.get("parent", "")):
        if any(_strip_digits(part).startswith(s) for s in OUT_OF_SCOPE_SECTIONS):
            return False
    if fs["field"] in ARTEFACT_FIELDS or OUT_OF_SCOPE_FIELD_RX.match(fs["field"]):
        return False
    return True


_ORPHAN_TOTAL = re.compile(r"^total class ([a-z])(?: \d+[a-z]?)? note interest$", re.I)


def parse_report(html: str):
    """grid.parse_report plus one layout repair: when a page break splits the "Class X Noteholder Interest
    Amount(s)" block, its "Total Class X Note Interest" row loses its parent heading. The parent is restored from
    the class letter so the row keeps one field name across reports (no value is touched)."""
    from .. import grid, labels
    g = grid.parse_report(html)
    for c in g.cells:
        m = _ORPHAN_TOTAL.match(labels.match_norm(c.label))
        if m and not c.parent:
            x = m.group(1).upper()
            c.parent = "Class A Noteholder Interest Amounts" if x == "A" else f"Class {x} Noteholder Interest Amount"
            if not c.section:
                c.section = "Application of Available Funds"
    return g


CLASS_BAL = re.compile(r"^note_balances__class_(.+?)_note_balance__beginning_of_period$")


def classes(v: dict) -> list[tuple[str, str]]:
    """[(class id as used in other labels, balance-label stem)] e.g. ("a_2b", "a_2b_floating_rate")."""
    out = []
    for k in v:
        m = CLASS_BAL.match(k)
        if m:
            stem = m.group(1)
            cid = stem.replace("_floating_rate", "").replace("_fixed_rate", "")
            out.append((cid, stem))
    return out


def _g(v: dict, k: str):
    if k not in v:
        raise KeyError(k)
    return v[k]


def _find(v: dict, pattern: str):
    rx = re.compile(pattern)
    ks = [k for k in v if rx.search(k)]
    if len(ks) != 1:
        raise KeyError(f"{pattern}: {ks}")
    return v[ks[0]]


def checks(v: dict) -> list[tuple[str, str, bool, str]]:
    """Within-period checks. Returns (check_group, name, passed, detail). Missing field -> failed check."""
    out = []

    def chk(group, name, fn):
        try:
            ok, detail = fn()
        except KeyError as e:
            ok, detail = False, f"missing field {e}"
        out.append((group, name, bool(ok), detail))

    cls = classes(v)
    if not cls:
        out.append(("anchoring", "classes_present", False, "no class balance rows"))
        return out

    # 2. class balance identity
    for cid, stem in cls:
        def f(cid=cid, stem=stem):
            beg = _g(v, f"note_balances__class_{stem}_note_balance__beginning_of_period")
            end = _g(v, f"note_balances__class_{stem}_note_balance__end_of_period")
            prin = _g(v, f"deposits__class_{cid}_principal_distribution")
            return end == beg - prin, f"{beg} - {prin} vs {end}"
        chk("balance_identity", f"class_{cid}", f)

    # 4. account rollforwards (every account the deal maintains)
    def reserve():
        b = _find(v, r"^beginning_balance_as_of_end_of_preceding_distribution_date$")
        e = _find(v, r"^ending_balance$")
        moves = (_find(v, r"^investment_earnings$") - _find(v, r"^reserve_account_reconciliation__reserve_account_draw_amount$")
                 + _find(v, r"^deposit_from_available_funds$")
                 - _find(v, r"payment_to__the_note_payment_account_for_the_payment_of_principal")
                 - _find(v, r"payment_to__any_successor_servicer_for_the_payment")
                 - _find(v, r"^payment_to_depositor_if_reserve_account_balance_exceeds"))
        return b + moves == e, f"{b} + {moves} vs {e}"
    chk("account_rollforward", "reserve_account", reserve)
    chk("account_rollforward", "reserve_account_amount_line53", lambda: (
        _find(v, r"^reserve_account_amount$") == _find(v, r"^beginning_balance_as_of_end_of_preceding_distribution_date$") + _find(v, r"^investment_earnings$") - _find(v, r"^reserve_account_reconciliation__reserve_account_draw_amount$"), ""))
    chk("account_rollforward", "collection_account_swept", lambda: (
        _g(v, "deposits__total_deposits_to_collection_account") == _g(v, "withdrawals__total_withdrawals_from_collection_account"), "beginning 0 + deposits - withdrawals = ending 0"))
    chk("account_rollforward", "note_payment_account_swept", lambda: (
        _g(v, "deposits__total_deposits_to_note_payment_account") == _g(v, "withdrawals__total_withdrawals_from_note_payment_account"), ""))
    chk("account_rollforward", "certificate_payment_account_swept", lambda: (
        _g(v, "deposits_to_certificate_payment_account_from_excess_collections") == _g(v, "withdrawals_from_certificate_payment_account_for_certificateholder_distribution"), ""))

    # 5. full cash reconciliation (sources = uses)
    def cash():
        # Reserve-account excess released to the Note Payment Account for an unfunded Regular Principal
        # Distributable Amount (Ln 55a) is a source: it reaches noteholders without passing the Collection Account.
        src = (_g(v, "finance_charges__available_finance_charge_collections") + _g(v, "principal__available_principal_collections")
               + _g(v, "interest_income_from_collection_account") + _g(v, "simple_interest_advances")
               + _g(v, "available_funds__reserve_account_draw_amount")
               + _find(v, r"payment_to__the_note_payment_account_for_the_payment_of_principal"))
        interest = sum(_g(v, f"deposits__class_{cid}_interest_distribution") for cid, _ in cls)
        principal = sum(_g(v, f"deposits__class_{cid}_principal_distribution") for cid, _ in cls)
        uses = (_g(v, "servicing_fee__amount_paid") + _g(v, "unreimbursed_servicer_advances")
                + _find(v, r"__successor_servicer_amount_paid$") + _find(v, r"__asset_representations_reviewer_amount_paid$")
                + interest + principal + _g(v, "withdrawals__deposit_to_reserve_account")
                + _find(v, r"^withdrawals__excess_collections"))
        return src == uses, f"sources {src} vs uses {uses}"
    chk("cash_reconciliation", "sources_equal_uses", cash)
    chk("account_rollforward", "note_payment_account_funding", lambda: (
        _g(v, "deposits__total_deposits_to_note_payment_account") ==
        _g(v, "withdrawals__deposit_to_note_payment_account_for_monthly_note_interest_principal")
        + _find(v, r"payment_to__the_note_payment_account_for_the_payment_of_principal"), "Ln 45q = Ln 44c + Ln 55a"))
    chk("cash_reconciliation", "available_funds", lambda: (
        _g(v, "available_funds") == _g(v, "available_funds__available_collections") + _g(v, "available_funds__reserve_account_draw_amount"), ""))

    # 6. totals
    for pos in ("beginning_of_period", "end_of_period"):
        chk("totals", f"note_balance_{pos}", lambda pos=pos: (
            _find(v, rf"^note_balances__note_balance__{pos}$") == sum(_g(v, f"note_balances__class_{s}_note_balance__{pos}") for _, s in cls), ""))
    chk("totals", "note_payment_deposits", lambda: (
        _g(v, "deposits__total_deposits_to_note_payment_account") == sum(_g(v, f"deposits__class_{c}_interest_distribution") + _g(v, f"deposits__class_{c}_principal_distribution") for c, _ in cls), ""))
    chk("totals", "note_payment_withdrawals", lambda: (
        _g(v, "withdrawals__total_withdrawals_from_note_payment_account") == sum(_g(v, f"withdrawals__class_{c}_distribution") for c, _ in cls), ""))
    for c, _ in cls:
        chk("totals", f"class_{c}_distribution", lambda c=c: (
            _g(v, f"withdrawals__class_{c}_distribution") == _g(v, f"deposits__class_{c}_interest_distribution") + _g(v, f"deposits__class_{c}_principal_distribution"), ""))
    chk("totals", "finance_charge_collections", lambda: (
        _g(v, "finance_charges__available_finance_charge_collections") == _g(v, "finance_charges__collections_allocable_to_finance_charge") + _g(v, "finance_charges__liquidation_proceeds_allocable_to_finance_charge") + _g(v, "finance_charges__purchase_amount_allocable_to_finance_charge"), ""))
    chk("totals", "principal_collections", lambda: (
        _g(v, "principal__available_principal_collections") == _g(v, "principal__collections_allocable_to_principal") + _g(v, "principal__liquidation_proceeds_allocable_to_principal") + _g(v, "principal__purchase_amount_allocable_to_principal"), ""))
    chk("totals", "collection_deposits", lambda: (
        _g(v, "deposits__total_deposits_to_collection_account") == sum(_find(v, rf"^deposits__{x}") for x in ("total_daily_deposits_of_finance_charge", "total_daily_deposits_of_principal", "withdrawal_from_reserve_account", "interest_income$")), ""))
    chk("totals", "pool_balance_rollforward", lambda: (
        _find(v, r"^pool_balance_on_the_close_of_the_last_day_of_the_related_collection_period$") ==
        _find(v, r"^(pool_balance__)?pool_balance_on_the_close_of_the_last_day_of_the_preceding_collection_period$") - _g(v, "collections_allocable_to_principal") - _g(v, "purchase_amount_allocable_to_principal") - _g(v, "defaulted_receivables"), "Ln1 - Ln2 - Ln3 - Ln4"))

    # 8. signs: every money field non-negative
    neg = [k for k, x in v.items() if isinstance(x, int) and not isinstance(x, bool) and x < 0]
    out.append(("units_signs", "money_non_negative", not neg, ",".join(neg[:5])))
    return out


# Clean-up call: "Optional Purchase Right" means the Servicer's right to purchase all outstanding Receivables ...
# as of which the Pool Balance is equal to or less than 10% of the Pool Balance as of the Cutoff Date.
# Verified identical (10%) in all 19 CarMax prospectuses of this family; used only for C3 mining, not by the reference.
CLEANUP_THRESHOLD = 0.10


def stress_signals(cur: dict, prev: dict | None, params: dict) -> list[str]:
    """C3 signals that fire in a period, from certified field values only (money in cents).

    - reserve_withdrawal: nonzero Reserve Account Draw Amount (Ln 24 / Ln 52)
    - interest_shortfall: nonzero Additional Note Interest (unpaid interest carried from a prior period) for any
      class, or interest due on it, or a nonzero servicing-fee shortfall
    - cleanup_threshold: ending Pool Balance <= 10% of the Pool Balance as of the Cutoff Date
    Not available in this family's certified fields: trigger statuses (the only trigger printed, the Delinquency
    Trigger, sits in the out-of-scope statistics section and is not certified) and principal-payment mode changes
    (pre-acceleration principal is always sequential; acceleration is never reported in these certificates).
    """
    from decimal import Decimal
    out = []
    draw = [cur.get(k) for k in ("available_funds__reserve_account_draw_amount", "reserve_account_reconciliation__reserve_account_draw_amount")]
    if any(isinstance(x, int) and x > 0 for x in draw):
        out.append("reserve_withdrawal")
    short = [x for k, x in cur.items() if ("additional_note_interest_related_to" in k or k == "servicing_fee__shortfall_amount_a_b_c")]
    if any(isinstance(x, int) and x > 0 for x in short):
        out.append("interest_shortfall")
    end = cur.get("pool_balance_on_the_close_of_the_last_day_of_the_related_collection_period")
    cutoff = params.get("pool_balance_as_of_cutoff_date")
    if isinstance(end, int) and cutoff:
        if Decimal(end) <= Decimal(str(cutoff)) * 100 * Decimal(str(CLEANUP_THRESHOLD)):
            out.append("cleanup_threshold")
    return out


def continuity_pairs(v: dict) -> list[tuple[str, str]]:
    """(field in period t, field in period t+1) that must be equal."""
    pairs = [(f"note_balances__class_{s}_note_balance__end_of_period", f"note_balances__class_{s}_note_balance__beginning_of_period") for _, s in classes(v)]
    pairs.append(("ending_balance", "beginning_balance_as_of_end_of_preceding_distribution_date"))
    pairs.append(("pool_balance_on_the_close_of_the_last_day_of_the_related_collection_period",
                  "pool_balance__pool_balance_on_the_close_of_the_last_day_of_the_preceding_collection_period"))
    return pairs


# ---------------- deal parameters (anchored in the final prospectus) ----------------
Q = r"[“\"]\s*"
QE = r"\s*[”\"]"
PARAM_SPECS = [
    {"param": "servicing_fee_rate", "unit": "pct", "label": Q + r"Servicing Fee" + QE + r"\s*means", "value": r"(?:1\s*/\s*12|one-twelfth)\s+of\s+(\d+\.\d+)\s*%", "window": 400},
    {"param": "required_reserve_account_amount", "unit": "usd", "label": Q + r"Required Reserve Account Amount" + QE + r"\s*means", "value": r"(\$\s*[\d,]+\.\d{2})", "window": 300},
    {"param": "overcollateralization_target_percent", "unit": "pct", "label": Q + r"Overcollateralization Target Amount" + QE + r"\s*means", "value": r"(\d+\.\d+)\s*%\s+of\s+the\s+Pool\s+Balance\s+as\s+of\s+the\s+Cutoff\s+Date", "window": 300},
    {"param": "pool_balance_as_of_cutoff_date", "unit": "usd", "label": r"(?i)will have (?:a|an aggregate) (?:pool balance|principal balance) of", "value": r"(\$\s*[\d,]+\.\d{2})\s+as of the cutoff date", "window": 80},
    # asset_representations_reviewer_cap is not certified: the reference does not use it (clause (2) amounts are
    # reported already capped), and an uncertified unused param would void the whole deal (step7._params).
    {"param": "day_count_class_a1_and_floating", "unit": "text", "label": r"Interest Accrual\s+Class A-1 Notes(?: and Floating Rate Notes)?", "value": r"[“\"]\s*(Actual/360)", "window": 60},
    {"param": "day_count_fixed_rate_other", "unit": "text", "label": r"(?:Fixed Rate )?Notes Other Than Class A-1 Notes", "value": r"[“\"]\s*(30/360)", "window": 60},
]

PARAMS_SCHEMA = {"type": "object", "properties": {
    "classes": {"type": "array", "description": "Every class of notes listed on the prospectus cover table", "items": {"type": "object", "properties": {
        "class_name": {"type": "string", "description": "e.g. A-1, A-2a, A-2b, A-3, A-4, B, C, D"},
        "initial_principal_amount": {"type": "string", "description": "Initial principal amount exactly as printed, e.g. $275,100,000"},
        "interest_rate": {"type": "string", "description": "Interest rate exactly as printed on the cover, e.g. 5.511% or SOFR Rate + 0.62%"}}}},
    "servicing_fee_rate": {"type": "string", "description": "Annual servicing fee rate used to compute the monthly Servicing Fee, exactly as printed (e.g. 1.00%)"},
    "required_reserve_account_amount": {"type": "string", "description": "The Required Reserve Account Amount from its definition, exactly as printed (dollar amount)"},
    "overcollateralization_target_percent": {"type": "string", "description": "Percentage of the Pool Balance as of the Cutoff Date that defines the Overcollateralization Target Amount, exactly as printed"},
    "pool_balance_as_of_cutoff_date": {"type": "string", "description": "Pool balance of the receivables as of the cutoff date, exactly as printed"},
    "asset_representations_reviewer_cap": {"type": "string", "description": "Annual cap on Asset Representations Reviewer fees/expenses/indemnities paid in the pre-acceleration priority of payments, exactly as printed"},
    "day_count_class_a1_and_floating": {"type": "string", "description": "Interest accrual day-count convention for the Class A-1 Notes and floating rate notes, exactly as printed (e.g. Actual/360)"},
    "day_count_fixed_rate_other": {"type": "string", "description": "Interest accrual day-count convention for fixed rate notes other than Class A-1, exactly as printed (e.g. 30/360)"},
}}


def anchor_class_table(html: str) -> dict:
    """Cover-page table: {class: {initial_principal, interest_rate, cell_*}} anchored to table/row/col."""
    from lxml import html as LH
    doc = LH.fromstring(html)
    out = {}
    for ti, t in enumerate(doc.xpath("//table")):
        txt = " ".join(t.text_content().split())
        if "Interest Rate" not in txt or "Asset" not in txt:
            continue
        for ri, tr in enumerate(t.xpath(".//tr")):
            cells = [" ".join(td.text_content().replace("\xa0", " ").split()) for td in tr.xpath("./td|./th")]
            cells = [c for c in cells if c]
            merged = []
            for c in cells:
                if merged and merged[-1] == "$":
                    merged[-1] = "$" + c
                elif c in ("%",) and merged:
                    merged[-1] += c
                else:
                    merged.append(c)
            if not merged:
                continue
            m = re.match(r"^Class\s+([A-Z](?:-\d+[a-z]?)?)\s+Asset", merged[0])
            if m and len(merged) >= 3 and merged[1].startswith("$"):
                cls = m.group(1)
                out[cls] = {"initial_principal": merged[1], "interest_rate": merged[2],
                            "cell_initial_principal": {"table": ti, "row": ri, "text": merged[1]},
                            "cell_interest_rate": {"table": ti, "row": ri, "text": merged[2]}}
        if out:
            break
    return out


def period_meta(html: str) -> dict:
    """Header dates printed on the certificate (kept in sanitized reports; they are not waterfall outputs)."""
    from .. import edgar
    t = edgar.html_to_text(html)[:3000]
    out = {}
    for key, pat in (("distribution_date", r"Distribution Date[\s|]*(\d{1,2}/\d{1,2}/\d{4})"),
                     ("determination_date", r"Determination Date[\s|]*(\d{1,2}/\d{1,2}/\d{4})"),
                     ("collection_period", r"Collection Period[\s|]*(\d{2}/\d{2}/\d{2}\s*-\s*\d{2}/\d{2}/\d{2})")):
        m = re.search(pat, t)
        out[key] = m.group(1) if m else None
    return out

# Periods whose certified values were printed while debugging the parser, Firecrawl candidates and the cash
# check (2026-11-14, before splits). step5 marks them design_exposed; the split code keeps them out of test.
DESIGN_EXPOSED_ACCESSIONS = {
    # first-mismatch examples printed per field (Firecrawl candidate diagnostics)
    "0001899236-24-000058", "0001921745-24-000058", "0001934479-24-000058", "0001946521-24-000058",
    "0001959426-24-000058", "0001969339-24-000059", "0001995430-24-000063", "0002003263-24-000054",
    "0002016948-24-000036", "0002029255-24-000021", "0002074530-26-000052",
    # "as printed" extraction sample (5 reports)
    "0002089777-25-000005", "0001980857-24-000058",
    # cash-reconciliation failures whose source/use totals were printed (Ln 55a fix)
    "0001946521-25-000020", "0001946521-25-000043", "0001946521-25-000048", "0001946521-25-000053",
    "0001946521-25-000058", "0001946521-25-000063", "0001946521-26-000005", "0001959426-26-000005",
    "0001946521-26-000010", "0001946521-26-000015", "0001946521-26-000037", "0001946521-26-000042",
    "0001946521-26-000047",
}
