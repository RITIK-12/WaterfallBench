"""Contract family: World Omni Auto Receivables Trust (sponsor World Omni Financial Corp.).

Source of rules: prospectus "Priority of Payments", "Overcollateralization Target Amount", "Required Reserve
Amount", "Pool Balance" (receivables less YSOC Amount). The Monthly Servicer Certificate prints a flow of funds
(Collections + Investment Earnings - Servicing Fee + Transfer to Collection Account = Available Funds) and the
11-step distribution of Available Funds.

Balance identity (notes): note balance after = note balance before - principal paid. No loss allocation,
write-down/up, capitalised interest, cancellation or accretion terms exist for these notes (documented zeros).
Pool identity: pool end = receivables begin - principal payments - defaulted - repurchased - YSOC end.
"""

from __future__ import annotations

import re
from decimal import Decimal

FAMILY_ID = "world_omni_auto_receivables_trust"
NAME_PATTERN = "world omni auto receivables trust <s>"
ASSET_CLASS = "auto_loan"

# Statistics (delinquency, loss ratios, pool statistics) are neither consumed nor computed by the waterfall.
OUT_OF_SCOPE_SECTIONS = ("delinquent receivables", "ratio of net loss gain to the receivables balance as of beginning of collection period annualized")
OUT_OF_SCOPE_FIELDS = re.compile(r"^(pool_factor__amount|prepayment_abs_speed__amount|.*__of_accounts(__\d+)?|current_net_losses|prior_net_losses|second_prior|third_prior|four_month_average|cumulative_net_loss|weighted_average_.*|recoveries|aggregate_net_losses.*|total_\d+_delinquent.*|delinquency_trigger_occurred|past_due_.*|total(__2)?)$")
IN_SCOPE_FROM_STATS = re.compile(r"^(overcollateralization_target_amount|actual_overcollateralization|collections__amount|investment_earnings_on_cash_accounts__amount|servicing_fee__amount|transfer_to_collection_account__amount|available_funds__amount|reserve_fund_balance__amount|aggregate_purchase_amount__amount)$")
ARTEFACT_FIELDS: tuple = ()
# Static deal information (original balances, risk-retention fair-value table) and parser artefacts (labels that
# embed a printed amount, e.g. "balance_as_of_date__243_33") are neither consumed nor computed by the waterfall;
# they stay in the packet unredacted.
STATIC_FIELDS = re.compile(r"^(.*original_note_balance|original_pool_balance__amount|original_yield_supplement_overcollateralization_amount__amount|"
                           r"original_class_[a-z0-9_]+__amount|aggregate_starting_principal_balance.*|certificates(__\d+)?|class_[a-z]_notes(__\d+)?|"
                           r"class_of_securities__total(__\d+)?|fair_value_of_.*|reserve_account(__\d+)?|account(__\d+)?|"
                           r"collection_account_redeposits|.*__\d+_\d+(__\d+)?|.*__\d+_pct(__\d+)?)$")

# Periods whose report values were inspected while building checks, parser rules or extraction-schema tests.
# They are excluded from the test split.
DESIGN_EXPOSED_ACCESSIONS = {
    "0001104659-26-119988",  # 2024-C, period 2026-09-30: layout study + v1/v2 schema experiments
    "0001104659-26-119978",  # 2022-C, period 2026-09-30: clean-up purchase inspected while building cash check
    "0001104659-26-111681",  # 2025-B, period 2026-08-31: different layout inspected
    "0001104659-26-119991",  # 2025-B, period 2026-09-30: different layout inspected
}

BALANCE_IDENTITY ="note_balance_after[c] = note_balance_before[c] - principal_paid[c]  (loss allocation, write-up, capitalised interest, cancellation: documented zero)"


def in_scope(fs: dict) -> bool:
    f = fs["field"]
    if IN_SCOPE_FROM_STATS.match(f):
        return True
    if fs["section"] in OUT_OF_SCOPE_SECTIONS or OUT_OF_SCOPE_FIELDS.match(f) or STATIC_FIELDS.match(f):
        return False
    return True


def kind_override(field: str, kind: str) -> str:
    """Dollar columns print zero as '0.00' (no thousands separator): those fields are money. Per-$1,000
    amounts and percentages keep their decimal/pct kinds."""
    if kind == "decimal" and not field.endswith("__total") and not field.endswith(("_days__date_date",)):
        return "money"
    return kind


CLASS_RX = re.compile(r"^class_(a_\d+[a-z]?|[b-z])__note_balance_date$")


def classes(v: dict) -> list[str]:
    return [m.group(1) for k in v for m in [CLASS_RX.match(k)] if m]


def _g(v, k):
    if k not in v:
        raise KeyError(k)
    return v[k]


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
        return [("anchoring", "classes_present", False, "no class balance rows")]
    for c in cls:
        chk("balance_identity", f"class_{c}", lambda c=c: (
            _g(v, f"class_{c}__note_balance_date__2") == _g(v, f"class_{c}__note_balance_date") - _g(v, f"class_{c}__principal_paid"), ""))
        chk("totals", f"class_{c}_principal_consistent", lambda c=c: (_g(v, f"class_{c}__principal_paid") == _g(v, f"class_{c}__principal_paid__2"), ""))
        chk("totals", f"class_{c}_total_paid", lambda c=c: (
            _g(v, f"total_paid_to_{c}_holders") == _g(v, f"class_{c}__interest_paid") + _g(v, f"class_{c}__principal_paid__2"), ""))
    chk("totals", "note_balance_before", lambda: (_g(v, "total_class_a_b_c__note_balance_date") == sum(_g(v, f"class_{c}__note_balance_date") for c in cls), ""))
    chk("totals", "note_balance_after", lambda: (_g(v, "total_class_a_b_c__note_balance_date__2") == sum(_g(v, f"class_{c}__note_balance_date__2") for c in cls), ""))
    chk("totals", "principal_paid", lambda: (_g(v, "total_class_a_b_c__principal_paid") == sum(_g(v, f"class_{c}__principal_paid") for c in cls), ""))
    chk("totals", "interest_paid", lambda: (_g(v, "total_interest_paid__amount") == sum(_g(v, f"class_{c}__interest_paid") for c in cls), ""))
    chk("totals", "principal_paid_2", lambda: (_g(v, "total_principal_paid__amount") == sum(_g(v, f"class_{c}__principal_paid__2") for c in cls), ""))
    chk("totals", "total_paid", lambda: (_g(v, "total_paid__amount") == _g(v, "total_interest_paid__amount") + _g(v, "total_principal_paid__amount"), ""))
    chk("totals", "class_a_interest", lambda: (_g(v, "class_a_interest") == sum(_g(v, f"class_{c}__interest_paid") for c in cls if c.startswith("a_")), ""))
    chk("totals", "class_b_interest", lambda: (_g(v, "class_b_interest") == _g(v, "class_b__interest_paid"), ""))
    if "c" in cls:
        chk("totals", "class_c_interest", lambda: (_g(v, "class_c_interest") == _g(v, "class_c__interest_paid"), ""))
    dist = ["asset_representation_reviewer_amounts_up_to_amt_per_year", "class_a_interest", "noteholders_first_priority_principal_distributable_amount",
            "class_b_interest", "noteholders_second_priority_principal_distributable_amount", "class_c_interest",
            "noteholders_third_priority_principal_distributable_amount", "required_reserve_account", "noteholders_principal_distributable_amount",
            "asset_representation_reviewer_amounts_in_excess_of_1", "distribution_to_certificateholders"]
    dist = [d for d in dist if d in v or d not in ("class_c_interest", "noteholders_third_priority_principal_distributable_amount")]
    chk("totals", "distributions_sum", lambda: (_g(v, "total_distributions_of_available_funds") == sum(_g(v, d) for d in dist), ""))
    chk("totals", "principal_from_waterfall", lambda: (
        _g(v, "total_principal_paid__amount") == sum(_g(v, d) for d in dist if "principal_distributable" in d), ""))
    # On an optional-purchase (clean-up) Payment Date the certificate adds the reserve fund balance and the
    # Aggregate Purchase Amount to Available Funds; both lines are absent otherwise (documented zero).
    extra = lambda: v.get("reserve_fund_balance__amount", 0) + v.get("aggregate_purchase_amount__amount", 0)
    chk("cash_reconciliation", "available_funds", lambda: (
        _g(v, "available_funds__amount") == _g(v, "collections__amount") + _g(v, "investment_earnings_on_cash_accounts__amount")
        + _g(v, "servicing_fee__amount") + _g(v, "transfer_to_collection_account__amount") + extra(), "servicing fee printed negative"))
    chk("cash_reconciliation", "sources_equal_uses", lambda: (
        _g(v, "collections__amount") + _g(v, "investment_earnings_on_cash_accounts__amount") + _g(v, "transfer_to_collection_account__amount") + extra()
        == -_g(v, "servicing_fee__amount") + _g(v, "total_distributions_of_available_funds"), ""))
    chk("cash_reconciliation", "servicing_fee_paid", lambda: (_g(v, "servicing_fee") == -_g(v, "servicing_fee__amount"), ""))
    chk("account_rollforward", "reserve_account", lambda: (
        _g(v, "balance_as_of_date__2") == _g(v, "balance_as_of_date") + _g(v, "investment_earnings") + _g(v, "investment_earnings_paid") + _g(v, "deposit_withdrawal"), ""))
    chk("account_rollforward", "reserve_change", lambda: (_g(v, "change") == _g(v, "balance_as_of_date__2") - _g(v, "balance_as_of_date"), ""))
    chk("account_rollforward", "pool_begin", lambda: (
        _g(v, "pool_balance_at_date__amount") == _g(v, "receivables_balance_date__amount") - _g(v, "yield_supplement_overcollateralization_amount_date__amount"), ""))
    chk("account_rollforward", "pool_end", lambda: (
        _g(v, "pool_balance_at_date__amount__2") == _g(v, "receivables_balance_date__amount") - _g(v, "principal_payments__amount")
        - _g(v, "defaulted_receivables__amount") - _g(v, "repurchased_accounts__amount") - _g(v, "yield_supplement_overcollateralization_amount_at_date__amount"), ""))
    chk("totals", "actual_oc", lambda: (_g(v, "actual_overcollateralization") == _g(v, "pool_balance_at_date__amount__2") - _g(v, "total_class_a_b_c__note_balance_date__2"), ""))
    signed_ok = {"servicing_fee__amount", "investment_earnings_paid", "deposit_withdrawal", "change", "transfer_to_collection_account__amount"}
    neg = [k for k, x in v.items() if isinstance(x, int) and not isinstance(x, bool) and x < 0 and k not in signed_ok]
    out.append(("units_signs", "money_non_negative", not neg, ",".join(neg[:5])))
    return out


def continuity_pairs(v: dict) -> list[tuple[str, str]]:
    pairs = [(f"class_{c}__note_balance_date__2", f"class_{c}__note_balance_date") for c in classes(v)]
    pairs += [("balance_as_of_date__2", "balance_as_of_date"),
              ("pool_balance_at_date__amount__2", "pool_balance_at_date__amount"),
              ("yield_supplement_overcollateralization_amount_at_date__amount", "yield_supplement_overcollateralization_amount_date__amount")]
    return pairs


def period_meta(html: str) -> dict:
    from .. import edgar
    t = edgar.html_to_text(html)[:3000]
    out = {}
    for key, pat in (("distribution_date", r"Distribution Date\s*\|?\s*(\d{2}/\d{2}/\d{2})"),
                     ("collection_period", r"Collections Period\s*\|?\s*(\d{2}/\d{2}/\d{2}\s*-\s*\d{2}/\d{2}/\d{2})"),
                     ("interest_accrual_period", r"Interest Accrual Period\s*\|?\s*(\d{2}/\d{2}/\d{2}\s*-\s*\d{2}/\d{2}/\d{2})")):
        m = re.search(pat, t)
        out[key] = m.group(1) if m else None
    return out


def stress_signals(cur: dict, prev: dict | None, params: dict) -> list[str]:
    """C3 signals that fire in this period, computed from certified field values and certified params only."""
    sig = []
    if cur.get("deposit_withdrawal", 0) < 0:
        sig.append("reserve_withdrawal")
    if any(v > 0 for k, v in cur.items() if "interest_carryover_shortfall" in k and isinstance(v, (int, Decimal))):
        sig.append("interest_shortfall")
    if prev is not None:
        for k, v in cur.items():
            if "trigger" in k and k in prev and prev[k] != v:
                sig.append("trigger_status_change")
                break
    try:
        start = Decimal(str(params["aggregate_starting_principal_balance"])) * 100  # cents
        pct = Decimal(str(params["optional_purchase_percent"])) / 100
        recv_end = cur["pool_balance_at_date__amount__2"] + cur["yield_supplement_overcollateralization_amount_at_date__amount"]
        if recv_end <= pct * start:
            sig.append("pool_at_or_below_cleanup_threshold")
    except (KeyError, TypeError, ArithmeticError):
        pass
    if cur.get("aggregate_purchase_amount__amount", 0) > 0:
        sig.append("optional_purchase_exercised")
    return sig


# ---------------- deal parameters (anchored in the final prospectus) ----------------
PARAM_SPECS = [
    {"param": "servicing_fee_rate", "unit": "pct", "label": r"Servicing Compensation", "value": r"1/12\s*th\s+of\s+(\d+\.\d+)\s*%", "window": 400},
    {"param": "overcollateralization_target_percent", "unit": "pct", "label": r"[“\"]\s*Overcollateralization Target Amount\s*[”\"]\s*means", "value": r"(?i)equal to (\d+\.\d+)\s*% of the aggregate principal balance of the Receivables as of the end", "window": 300},
    {"param": "overcollateralization_floor_percent", "unit": "pct", "label": r"[“\"]\s*Overcollateralization Target Amount\s*[”\"]\s*means", "value": r"(?i)but not less than (\d+\.\d+)\s*% of the aggregate starting", "window": 500},
    {"param": "required_reserve_percent", "unit": "pct", "label": r"[“\"]\s*Required Reserve Amount\s*[”\"]\s*means", "value": r"(\d+\.\d+)\s*%", "window": 120},
    {"param": "aggregate_starting_principal_balance", "unit": "usd", "label": r"(?i)the aggregate starting principal balance of the receivables (?:is|included in the pool will be)", "value": r"(\$\s*[\d,]+\.\d{2})", "window": 40},
    {"param": "ysoc_amount_closing_date", "unit": "usd", "label": r"\|\s*Closing Date\s*\|", "value": r"(\$\s*[\d,]+\.\d{2})", "window": 40},
    {"param": "asset_representations_reviewer_cap", "unit": "usd", "label": r"(?i)to the Asset Representations Reviewer, all fees, expenses and indemnities due", "value": r"(?i)up to a maximum (?:amount )?of (\$\s*[\d,]+) per (?:calendar )?year", "window": 300},
    {"param": "day_count_class_a1_and_floating", "unit": "daycount", "label": r"(?i)Interest on the Class A-1 Notes(?: and the Class A-2b Notes)? will be calculated on the basis of", "value": r"(the actual number of days[^.]{0,400}?360-day year)", "window": 600},
    {"param": "day_count_fixed_rate_other", "unit": "daycount", "label": r"(?i)Interest (?:for a related period )?on (?:the other classes of Notes|each (?:other )?class of the(?: Class A)? Notes(?:, other than the Class A-1 Notes(?: and the Class A-2b Notes)?,)?) will be calculated on the basis of", "value": r"(a 360-day year (?:consisting )?of twelve 30-day months)", "window": 80},
    {"param": "optional_purchase_percent", "unit": "pct", "label": r"Redemption Upon Optional Purchase", "value": r"(?i)aggregate principal balance of the Receivables is (\d+\.\d+)\s*% or less of the aggregate starting principal balance", "window": 400},
]

PARAMS_SCHEMA = {"type": "object", "properties": {
    "classes": {"type": "array", "description": "Every class of notes in the prospectus cover table (Principal Amount and Interest Rate rows)", "items": {"type": "object", "properties": {
        "class_name": {"type": "string", "description": "e.g. A-1, A-2a, A-2b, A-3, A-4, B, C"},
        "initial_principal_amount": {"type": "string", "description": "Principal Amount exactly as printed, e.g. $225,500,000"},
        "interest_rate": {"type": "string", "description": "Interest Rate exactly as printed, e.g. 5.369% or SOFR Rate plus 0.47%"}}}},
    "servicing_fee_rate": {"type": "string", "description": "Annual rate in the servicing fee (1/12th of X% of the receivables balance), exactly as printed"},
    "overcollateralization_target_percent": {"type": "string", "description": "Percentage of the current receivables balance less YSOC in the Overcollateralization Target Amount definition"},
    "overcollateralization_floor_percent": {"type": "string", "description": "Floor percentage ('but not less than X%') of the starting receivables balance less YSOC in the Overcollateralization Target Amount definition"},
    "required_reserve_percent": {"type": "string", "description": "Percentage in the Required Reserve Amount definition"},
    "aggregate_starting_principal_balance": {"type": "string", "description": "Aggregate starting principal balance of the Receivables, exactly as printed"},
    "ysoc_amount_closing_date": {"type": "string", "description": "From the Yield Supplement Overcollateralization Amount schedule table: the 'Closing Date' row value in the FIRST Required Rate column (the Required Rate that applies on the Cutoff Date and before the Class A-2 Notes are paid in full), exactly as printed"},
    "asset_representations_reviewer_cap": {"type": "string", "description": "Maximum amount per calendar year paid to the Asset Representations Reviewer in priority (1), exactly as printed"},
    "day_count_class_a1_and_floating": {"type": "string", "description": "Day-count convention stated in the sentence 'Interest on the Class A-1 Notes ... will be calculated on the basis of ...' (Actual/360 if it says the actual number of days and a 360-day year; 30/360 if it says twelve 30-day months)"},
    "day_count_fixed_rate_other": {"type": "string", "description": "Day-count convention stated for the other (fixed rate) classes of Notes (Actual/360 if it says the actual number of days and a 360-day year; 30/360 if it says twelve 30-day months)"},
    "optional_purchase_percent": {"type": "string", "description": "Percentage in 'Redemption Upon Optional Purchase': the servicer may purchase the receivables when their aggregate principal balance is X% or less of the aggregate starting principal balance; X exactly as printed"},
}}


def anchor_class_table(html: str) -> dict:
    """Transposed cover table: header row of 'Class X Notes', rows 'Principal Amount' / 'Interest Rate'."""
    from lxml import html as LH
    doc = LH.fromstring(html)
    for ti, t in enumerate(doc.xpath("//table")):
        rows = []
        for ri, tr in enumerate(t.xpath(".//tr")):
            cells = [" ".join(td.text_content().replace("\xa0", " ").split()) for td in tr.xpath("./td|./th")]
            merged = []
            for c in cells:
                if not c:
                    continue
                if merged and merged[-1] == "$":
                    merged[-1] = "$" + c
                else:
                    merged.append(c)
            rows.append((ri, merged))
        hdr = next(((ri, m) for ri, m in rows if sum(1 for x in m if re.match(r"^Class\s+[A-Z](-\d+[a-z]?)?\s+Notes", x)) >= 2), None)
        pa = next(((ri, m) for ri, m in rows if m and m[0].startswith("Principal Amount")), None)
        ir = next(((ri, m) for ri, m in rows if m and m[0].startswith("Interest Rate")), None)
        if not (hdr and pa and ir):
            continue
        names = [re.match(r"^Class\s+([A-Z](?:-\d+[a-z]?)?)", x).group(1) for x in hdr[1] if re.match(r"^Class\s+[A-Z]", x)]
        pas, irs = pa[1][1:], ir[1][1:]
        if len(names) != len(pas) or len(names) != len(irs):
            continue
        out = {}
        for i, cls in enumerate(names):
            rate = re.sub(r"\(\d\)$", "", irs[i]).strip()
            out[cls] = {"initial_principal": pas[i], "interest_rate": rate,
                        "cell_initial_principal": {"table": ti, "row": pa[0], "col": i + 1, "text": pas[i]},
                        "cell_interest_rate": {"table": ti, "row": ir[0], "col": i + 1, "text": irs[i]}}
        return out
    return {}
