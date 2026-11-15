"""Contract family: John Deere Owner Trust (sponsor John Deere Capital Corporation; equipment receivables).

Source of rules: final prospectus (424B5) "Summary — Principal Payments / Priority of Payments", "Description of the
Transfer and Servicing Agreements — Distributions" and "Credit and Cash Flow Enhancement — Reserve Account".

Each 10-D carries three exhibits restating one payment date: EX-99.1 Statement to Noteholders, EX-99.2 Statement to
Certificateholders and EX-99.3 Servicer's Certificate. The Servicer's Certificate is the most complete (sources,
every waterfall step, reserve account, pool and note balances) and is the family's certified report; the other two
exhibits only restate its outputs (they must never be placed in a graded-period packet).

Balance identity (notes): ending = beginning - principal paid. Equipment notes in this family have no loss
allocation / write-down, write-up, capitalised interest, cancellation or accretion terms (documented zeros).
"""

from __future__ import annotations

import re
from decimal import Decimal

FAMILY_ID = "john_deere_owner_trust"
# EDGAR names some deals "John Deere Owner Trust 2024" (no -A/-B suffix); one shelf, one contract family.
NAME_PATTERNS = ["john deere owner trust <s>", "john deere owner trust 2023", "john deere owner trust 2024",
                 "john deere owner trust 2025", "john deere owner trust 2026"]
NAME_PATTERN = NAME_PATTERNS[0]
ASSET_CLASS = "equipment"

# Periods whose values were inspected while designing this module's parser/checks (before splits): excluded from test.
DESIGN_EXPOSED_ACCESSIONS = {"0001104659-26-118325"}                  # JDOT 2024-B, payment date 15-Oct-26
DESIGN_EXPOSED_PERIODS = {(2013096, "20241115"), (1934741, "20260415")}  # JDOT 2024 Nov-24; JDOT 2022-B Apr-26

# Reg AB / asset-review statistics printed after the waterfall: neither consumed nor computed by the reference.
OUT_OF_SCOPE_SECTIONS = ("repurchase demand activity (15Ga-1)", "net losses", "60+ day delinquency",
                         "collateral composition", "delinquency trigger (asset representations review)")
ARTEFACT_FIELDS = ()

BALANCE_IDENTITY = ("end_balance[c] = beginning_balance[c] - principal_distributable[c]  (beginning = prior period's "
                    "ending; loss allocation, write-up, capitalised interest, cancellation: documented zero)")

# ---------------------------------------------------------------- parsing hook
_SUB = re.compile(r"^(?:\(\s*(?:[a-z]{1,2}|[ivxl]{1,5})\s*\)\s*)+", re.I)
_DATE_COL = re.compile(r"^\d{1,2}-[A-Za-z]{3}-\d{2,4}$")
_TITLE = re.compile(r"servicer.s\s+certificate", re.I)


def parse_report(html: str):
    """Servicer's Certificate only (other exhibits -> empty grid, so the shared report picker selects EX-99.3).

    The certificate prints sub-item markers "(a)", "(i)" in their own cells; they are blanked (and leading markers
    stripped from label cells) before the shared grid parser runs, so field names carry the printed label only and
    stay stable when a deal has fewer classes. Value cells are untouched, so every cell keeps its (table, row,
    column) location in the official HTML. Header rows that print the payment/collection dates ("15-Oct-26") are
    not column headers of the values below them; such date "columns" are dropped from cell paths. Cover-line rows
    ("$270,000,000 Class A-2A ... Notes") are deal-specific titles, not sections."""
    from lxml import html as LH

    from .. import grid
    doc = LH.fromstring(html)
    head = " ".join(doc.text_content()[:4000].split())
    if not _TITLE.search(head):
        return grid.Grid()
    for td in doc.xpath("//td|//th"):
        t = grid.clean(td.text_content())
        if not t or grid.parse_value(t) is not None or t in grid.GLUE or t in grid.DASHES:
            continue
        if re.match(r"^\(\s*\d{1,3}\s*\)$", t):  # numbered line "(12)": keep
            continue
        new = _SUB.sub("", t).strip()
        if new != t:
            for ch in list(td):
                td.remove(ch)
            td.text = new
    g = grid.parse_report(LH.tostring(doc, encoding="unicode"))
    for c in g.cells:
        if _DATE_COL.match(c.column or ""):
            c.column = ""
        if re.match(r"^\$\s*[\d,]+", c.section or "") or "Check for Error" in (c.section or ""):
            c.section = ""
    return g


# ---------------------------------------------------------------- scope
_OUT = re.compile(
    r"(repurchase|aggregate_principal_balance_of_(purchased_|related_)?receivables|of_pool_balance|net_losses|"
    r"cumulative_net_loss|past_due|number_of_loans|remaining_term|prepayment_amount|weighted_average_apr|"
    r"(^|__)pool_factor$|delinquency_trigger|number_of_accounts|number_of_receivables)")


def in_scope(fs: dict) -> bool:
    """The total distribution amount (collections + net investment earnings, no account withdrawals) is the
    waterfall's source and an input; its collection-detail line "administrative repurchases" is out of scope
    (the Firecrawl schema of label map lm-2 was built without it; the other detail lines are kept for checks)."""
    return not _OUT.search(fs["field"])


# ---------------------------------------------------------------- field helpers
END_BAL = re.compile(r"(?:^|__)outstanding_principal_balance_of_class_(.+?)_notes$")


def classes(v: dict) -> list[str]:
    """Class ids in waterfall order as used in labels, e.g. ['a_1', 'a_2a', 'a_2b', 'a_3', 'a_4']."""
    out = []
    for k in v:
        m = END_BAL.search(k)
        if m:
            out.append(m.group(1))
    return out


def _find(v: dict, pattern: str):
    rx = re.compile(pattern)
    ks = [k for k in v if rx.search(k)]
    if len(ks) != 1:
        raise KeyError(f"{pattern}: {ks}")
    return v[ks[0]]


def key(v: dict, pattern: str) -> str:
    rx = re.compile(pattern)
    ks = [k for k in v if rx.search(k)]
    if len(ks) != 1:
        raise KeyError(f"{pattern}: {ks}")
    return ks[0]


F = {  # canonical role -> field regex (searched within one period's certified values)
    "total_distribution_amount": r"(^|__)total_distribution_amount$",
    "cash_receipts": r"total_cash_receipts_during_the_month$",
    "admin_repurchases": r"administrative_repurchases_during_the_month$",
    "investment_earnings": r"investment_earnings_on_cash_accounts$",
    "buyback": r"payment_from_deere_to_buy_back_the_deal$",
    "admin_fee": r"(^|__)administration_fee$",
    "admin_fee_shortfall": r"administration_fee_shortfall$",
    "interest_total": r"noteholders_interest_distributable_amount_deposited_into_note_distribution_account$",
    "interest_carryover_total": r"(^|__)noteholders_interest_carryover_shortfall$",
    "principal_total": r"noteholders_principal_distribution_amount_deposited_into_note_distribution_account$",
    "principal_carryover_total": r"(^|__)noteholders_principal_carryover_shortfall$",
    "noteholders_distributable": r"(^|__)noteholders_distributable_amount$",
    "reserve_begin": r"(^|__)beginning_balance$",
    "reserve_deposit": r"amount_to_increase_the_amount_on_deposit_in_the_reserve_account",
    "reserve_draw_notes": r"amount_to_be_withdrawn_from_the_reserve_account_and_deposited_into_note_distribution",
    "reserve_draw_interest": r"(^|__)interest_amount_included_above$",
    "reserve_draw_principal": r"(^|__)principal_amount_included_above$",
    "reserve_release": r"amount_to_be_withdrawn_from_the_reserve_account_and_deposited_into_certificateholder",
    "reserve_end": r"ending_balance_after_giving_effect_to_all_distributions$",
    "reserve_specified": r"(^|__)specified_reserve_account_balance$",
    "servicing_fee": r"(^|__)servicing_fee$",
    "servicing_fee_earned": r"amount_of_servicing_fee_earned$",
    "servicing_fee_paid": r"amount_of_servicing_fee_paid$",
    "servicing_fee_shortfall": r"amount_of_servicing_fee_shortfall$",
    "indenture_trustee": r"amount_paid_to_indenture_trustee$",
    "owner_trustee": r"amount_paid_to_owner_trustee$",
    "arr_iii": r"section_5_04_iii_asset_representations_review_fees$",
    "arr_ix": r"section_5_04_ix_asset_representations_review_fees$",
    "certificateholder": r"amount_paid_to_certificateholder$",
    "pool_balance_end": r"pool_balance_excluding_accrued_interest_as_of_close_of_business",
    "note_value_end": r"note_value_as_of_the_end_of_the_related_collection_period$",
    "oc_amount": r"amount_of_overcollateralization",
}


def g(v: dict, role: str):
    return _find(v, F[role])


def cf(cid: str) -> dict:
    """Per-class field regexes."""
    c = re.escape(cid)
    return {
        "int": rf"noteholders_interest_distributable_amount_applicable_to_class_{c}_notes$",
        "int_short": rf"noteholders_interest_carryover_shortfall_applicable_to_class_{c}_notes$",
        "prin_monthly": rf"class_{c}_noteholders_monthly_principal_distributable_amount$",
        "prin_pct": rf"of_principal_distribution_amount_applicable_to_class_{c}_noteholders$",
        "prin_short": rf"class_{c}_noteholders_principal_carryover_shortfall$",
        "prin": rf"class_{c}_noteholders_principal_distributable_amount$",
        "end": rf"(^|__)outstanding_principal_balance_of_class_{c}_notes$",
        "factor": rf"(^|__)class_{c}_note_pool_factor$",
    }


# ---------------------------------------------------------------- within-period checks
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
        out.append(("anchoring", "classes_present", False, "no class balance rows"))
        return out

    # 2. class balance identity cannot be closed within one certificate (beginning balances are the prior
    # period's ending balances; checked across filings by continuity); within-period: ending = beginning - paid is
    # verified in the cross-period identity check below via continuity_pairs + identity_pairs.
    for c in cls:
        def f(c=c):
            end = _find(v, cf(c)["end"])
            return end >= 0, f"ending {end}"
        chk("balance_identity", f"class_{c}_non_negative", f)

    # 4. account rollforward: reserve account
    def reserve():
        b, dep = g(v, "reserve_begin"), g(v, "reserve_deposit")
        dn, dc, e = g(v, "reserve_draw_notes"), g(v, "reserve_release"), g(v, "reserve_end")
        return b + dep - dn - dc == e, f"{b} + {dep} - {dn} - {dc} vs {e}"
    chk("account_rollforward", "reserve_account", reserve)
    chk("account_rollforward", "reserve_draw_split", lambda: (
        g(v, "reserve_draw_notes") == g(v, "reserve_draw_interest") + g(v, "reserve_draw_principal"), ""))

    # 5. full cash reconciliation: total distribution amount + reserve draws to notes = all uses
    def cash():
        src = g(v, "total_distribution_amount") + g(v, "reserve_draw_notes") + g(v, "reserve_release")
        uses = (g(v, "admin_fee") + g(v, "arr_iii") + g(v, "interest_total") + g(v, "principal_total")
                + g(v, "reserve_deposit") + g(v, "servicing_fee_paid") + g(v, "indenture_trustee")
                + g(v, "owner_trustee") + g(v, "arr_ix") + g(v, "certificateholder"))
        return src == uses, f"sources {src} vs uses {uses}"
    chk("cash_reconciliation", "sources_equal_uses", cash)
    # total distribution amount = cash receipts + administrative repurchases (>= 0, out of scope) + earnings + buy-back
    chk("cash_reconciliation", "total_distribution_amount", lambda: (
        g(v, "total_distribution_amount") >= g(v, "cash_receipts") + g(v, "investment_earnings") + g(v, "buyback"), ""))

    # 6. totals
    chk("totals", "interest_total", lambda: (
        g(v, "interest_total") == sum(_find(v, cf(c)["int"]) for c in cls), ""))
    chk("totals", "principal_total", lambda: (
        g(v, "principal_total") == sum(_find(v, cf(c)["prin"]) for c in cls), ""))
    chk("totals", "noteholders_distributable", lambda: (
        g(v, "noteholders_distributable") == g(v, "interest_total") + g(v, "principal_total"), ""))
    chk("totals", "servicing_fee", lambda: (
        g(v, "servicing_fee") == g(v, "servicing_fee_earned") and g(v, "servicing_fee_earned") == g(v, "servicing_fee_paid") + g(v, "servicing_fee_shortfall"), ""))
    for c in cls:
        chk("totals", f"class_{c}_principal", lambda c=c: (
            _find(v, cf(c)["prin"]) == _find(v, cf(c)["prin_monthly"]) + _find(v, cf(c)["prin_short"]), ""))
    # The certificate prints the deal's initial overcollateralization (initial note value less initial note
    # principal, whole dollars); while the notes amortise normally it equals note value less notes, to the dollar.
    # In the final (buy-back) period the notes are redeemed in full and the line still prints the initial amount.
    def oc():
        notes = sum(_find(v, cf(c)["end"]) for c in cls)
        if notes == 0:
            return g(v, "oc_amount") % 100 == 0, "final period: initial OC, whole dollars"
        return abs(g(v, "oc_amount") - (g(v, "note_value_end") - notes)) <= 50, "OC printed rounded to whole dollars"
    chk("totals", "overcollateralization", oc)
    # principal shares printed per class add up to 100% whenever principal is paid (2-dp rounding tolerance)
    def shares():
        tot = sum(_find(v, cf(c)["prin_pct"]) for c in cls)
        paid = g(v, "principal_total")
        return (tot == 0) if paid == 0 else abs(tot - 100) <= Decimal("0.02") * len(cls), f"sum {tot}"
    chk("totals", "principal_shares", shares)

    # 8. signs
    neg = [k for k, x in v.items() if isinstance(x, int) and not isinstance(x, bool) and x < 0]
    out.append(("units_signs", "money_non_negative", not neg, ",".join(neg[:5])))
    return out


def continuity_pairs(v: dict) -> list[tuple[str, str]]:
    """(field in period t, field in period t+1) that must be equal."""
    return [(key(v, F["reserve_end"]), key(v, F["reserve_begin"]))]


def period_meta(html: str) -> dict:
    from .. import edgar
    t = " ".join(edgar.html_to_text(html)[:6000].replace("|", " ").replace("​", " ").split())
    out = {}
    for k, pat in (("payment_date", r"Actual Payment Date \(A/360\)\s*(\d{1,2}-[A-Za-z]{3}-\d{2})"),
                   ("scheduled_payment_date", r"Scheduled Payment Date \(30/360\)\s*(\d{1,2}-[A-Za-z]{3}-\d{2})"),
                   ("collection_period_begin", r"Collection Period Begin Date\s*(\d{1,2}-[A-Za-z]{3}-\d{2})"),
                   ("collection_period_end", r"Collection Period End Date\s*(\d{1,2}-[A-Za-z]{3}-\d{2})")):
        m = re.search(pat, t)
        out[k] = m.group(1) if m else None
    return out


# ---------------------------------------------------------------- C3 stress signals
def stress_signals(cur: dict, prev: dict, params: dict) -> list[str]:
    """Which C3 signals fire for a period, from certified values (cur, prev) and certified params only."""
    sig = []
    try:
        if g(cur, "reserve_draw_notes") > 0:
            sig.append("reserve_withdrawal")
    except KeyError:
        pass
    try:
        if g(cur, "interest_carryover_total") > 0 or any(_find(cur, cf(c)["int_short"]) > 0 for c in classes(cur)):
            sig.append("interest_shortfall")
    except KeyError:
        pass
    try:  # principal mode: which classes receive principal (sequential -> A-2A/A-2B ratable, or new class reached)
        paid = lambda v: tuple(c for c in classes(v) if _find(v, cf(c)["prin"]) > 0)
        if prev and paid(prev) and paid(cur) and paid(prev) != paid(cur):
            sig.append("principal_payment_mode_change")
    except KeyError:
        pass
    try:  # clean-up call: note value at or below 10% of the initial note value
        thr = Decimal(params["initial_note_value"]) * Decimal(params["optional_redemption_percent"]) / 100
        if Decimal(g(cur, "note_value_end")) / 100 <= thr:
            sig.append("note_value_at_or_below_cleanup_threshold")
    except (KeyError, TypeError):
        pass
    return sig


# ---------------------------------------------------------------- deal parameters (anchored in the final prospectus)
Q = r"[“\"]\s*"
QE = r"\s*[”\"]"
PARAM_SPECS = [
    {"param": "servicing_fee_rate", "unit": "pct", "label": r"(?i)servicing fee for each collection period in an amount\s+(?:\d+\s+)?equal to",
     "value": r"(\d+\.\d+)\s*%\s+per annum of the pool balance as of the first day", "window": 80},
    {"param": "administration_fee", "unit": "usd", "label": r"(?i)Administration fee\s*\|", "value": r"(\$\s*[\d,]+)\s+per month", "window": 40},
    {"param": "initial_note_value", "unit": "usd", "label": r"(?i)the\s+[“\"]?\s*initial note value\s*[”\"]?\s+is", "value": r"(\$\s*[\d,]+\.\d{2})", "window": 40},
    {"param": "reserve_specified_percent", "unit": "pct", "label": r"(?i)specified reserve account balance\s*[”\"]?\s+for the reserve account on any payment date means an amount not less than",
     "value": r"(\d+\.\d+)\s*%\s+of the initial note value", "window": 60},
    {"param": "optional_redemption_percent", "unit": "pct", "label": r"(?i)becomes equal to or less than",
     "value": r"(\d+(?:\.\d+)?)\s*%\s+of the initial note value", "window": 30},
]
# Not a parameter: the initial overcollateralization printed on each certificate equals initial note value less the
# initial principal of the notes, rounded to whole dollars (both certified above). The extraction schema also asked for
# it, but its description carried an example amount that Firecrawl copied for two deals; it is not used.

PARAMS_SCHEMA = {"type": "object", "properties": {
    "classes": {"type": "array", "description": "Every class of notes listed in the prospectus cover table", "items": {"type": "object", "properties": {
        "class_name": {"type": "string", "description": "e.g. A-1, A-2A, A-2B, A-3, A-4"},
        "initial_principal_amount": {"type": "string", "description": "Initial principal amount exactly as printed, e.g. $388,000,000"},
        "interest_rate": {"type": "string", "description": "Interest rate exactly as printed in the summary table of the notes (Class of Notes / Aggregate Principal Amount / Interest Rate), e.g. 5.42% or Benchmark + 0.37%"}}}},
    "servicing_fee_rate": {"type": "string", "description": "Annual servicing fee rate (percent per annum of the pool balance as of the first day of the collection period), exactly as printed (e.g. 1.00%)"},
    "administration_fee": {"type": "string", "description": "Administration fee amount per month from the fee and expense table, exactly as printed (e.g. $100)"},
    "initial_note_value": {"type": "string", "description": "The initial note value of the receivables as of the cut-off date, exactly as printed (dollars and cents)"},
    "reserve_specified_percent": {"type": "string", "description": "Percentage of the initial note value that defines the specified reserve account balance, exactly as printed (e.g. 1.00%)"},
    "optional_redemption_percent": {"type": "string", "description": "Percentage of the initial note value at or below which the servicer may purchase the remaining receivables (optional redemption / clean-up call), exactly as printed (e.g. 10%)"},
    "initial_overcollateralization": {"type": "string", "description": "Amount shown for the Certificate/Overcollateralization in the capitalization table of the trust, exactly as printed (e.g. 39,062,743)"},
}}


def anchor_class_table(html: str) -> dict:
    """Prospectus cover table "Aggregate Principal Amount | Class of Notes": rows "$388,000,000 | Class A-1 |
    5.510% Asset Backed Notes". {class: {initial_principal, interest_rate, cell_*}} anchored to (table, row).
    The floating-rate class prints "Floating Rate Asset Backed Notes" here (its coupon for each period is printed
    in the servicer's certificate and is a period input)."""
    from lxml import html as LH
    doc = LH.fromstring(html)
    out = {}
    for ti, t in enumerate(doc.xpath("//table")):
        txt = " ".join(t.text_content().replace("\u200b", " ").split())
        if not ("Aggregate Principal Amount" in txt and "Class of Notes" in txt) or "Interest Rate" in txt:
            continue
        for ri, tr in enumerate(t.xpath(".//tr")):
            cells = [" ".join(td.text_content().replace("\xa0", " ").replace("\u200b", " ").replace("\u200c", " ").split()) for td in tr.xpath("./td|./th")]
            cells = [c for c in cells if c]
            merged = []
            for c in cells:
                if merged and merged[-1] == "$":
                    merged[-1] = "$" + c
                else:
                    merged.append(c)
            if len(merged) < 3:
                continue
            m = re.match(r"^Class\s+(A-\d+[A-Za-z]?)$", merged[1])
            if m and merged[0].startswith("$"):
                out[m.group(1)] = {"initial_principal": merged[0], "interest_rate": merged[2],
                                   "cell_initial_principal": {"table": ti, "row": ri, "text": merged[0]},
                                   "cell_interest_rate": {"table": ti, "row": ri, "text": merged[2]}}
        if out:
            break
    return out


# ---------------------------------------------------------------- candidate extraction, pass v2
# Pass v1 (shared step 4: money requested as integer cents) mis-converted many amounts on this certificate
# (trailing ".00" dropped, digits lost). Pass v2 re-extracts EVERY report of the family uniformly, asking Firecrawl
# for each value exactly as printed; the printed text is converted to integer cents deterministically. v2 replaces
# v1 as the candidate source for all reports (no per-field or per-report selection). Raw v2 records are new files
# (raw/extractions/<deal>/<accession>__<file>.v2.json.gz); v1 records are kept untouched.
def schema_v2(lm: dict) -> dict:
    props = {}
    for f in lm["fields"]:
        where = " > ".join(x for x in (f["section"], f["parent"], f["label"], f["column"]) if x)
        props[f["field"]] = {"type": "string", "description": (
            f"The value printed in the row '{where}', copied exactly as printed, character for character, "
            "including any '$', commas, decimal point, digits after the decimal point, '%' and parentheses. "
            "Do not convert, round or reformat.")}
    return {"type": "object", "properties": props}


def printed_to_candidate(kind: str, s):
    """Deterministic conversion of a printed value to the shared candidate format (money -> integer cents)."""
    if s is None:
        return None
    t = str(s).strip()
    neg = t.startswith("(") and t.endswith(")") or t.startswith("-") or "$(" in t
    m = re.search(r"[\d,]*\.?\d+", t.replace(" ", ""))
    if not m:
        return None
    num = Decimal(m.group(0).replace(",", ""))
    if kind == "money":
        cents = int((num * 100).to_integral_value())
        return str(-cents if neg else cents)
    if kind == "int":
        return str(int(num))
    return str(-num if neg else num)


def extract_v2(concurrency: int = 20) -> None:
    import gzip
    import json
    import subprocess
    import tempfile
    from concurrent.futures import ThreadPoolExecutor
    from pathlib import Path

    import pandas as pd

    from .. import config, fc, labels
    reps = pd.read_parquet(config.WORKDIR / f"reports_{FAMILY_ID}.parquet")
    ex = config.RAW / "extractions"
    todo = []
    for r in reps.itertuples():
        lm = json.loads((labels.LABEL_MAPS / FAMILY_ID / r.report_format / f"{r.deal_cik}.json").read_text())
        sfile = ex / "_schemas" / FAMILY_ID / r.report_format / f"{r.deal_cik}.v2.json"
        sfile.parent.mkdir(parents=True, exist_ok=True)
        sfile.write_text(json.dumps(schema_v2(lm)))
        dest = ex / str(r.deal_cik) / f"{r.accession}__{r.filename}.v2.json.gz"
        if not dest.exists():
            todo.append((r, dest, sfile))
    fc.check_budget(5 * len(todo))
    errs = []

    def one(item):
        r, dest, sfile = item
        with tempfile.TemporaryDirectory() as td:
            out = Path(td) / "o.json"
            fc._rate_gate()
            p = subprocess.run(["firecrawl", "scrape", r.source_url, "--format", "json", "--schema-file", str(sfile), "--json", "-o", str(out)],
                               capture_output=True, text=True, timeout=900)
            if p.returncode != 0 or not out.exists():
                errs.append(f"{r.accession}: {(p.stderr or p.stdout)[-200:]}")
                return
            res = json.loads(out.read_text())
        md = res.get("metadata", {})
        fc._add_credits(md.get("creditsUsed") or 5)
        if md.get("statusCode") in (403, 429):
            raise fc.SecBlocked(f"{r.source_url}: {md.get('statusCode')}")
        dest.parent.mkdir(parents=True, exist_ok=True)
        with gzip.open(dest, "wt") as f:
            json.dump({"pass": "v2", "scrape_id": md.get("scrapeId"), "status_code": md.get("statusCode"), "url": r.source_url,
                       "schema": str(sfile.relative_to(config.WORKDIR)), "label_map_version": labels.LABEL_MAP_VERSION,
                       "json": res.get("json")}, f)

    with ThreadPoolExecutor(concurrency) as pool:
        list(pool.map(one, todo))
    print(f"v2 extracted {len(todo) - len(errs)}/{len(todo)}; errors {errs[:3]}; credits {fc._credits_used()}", flush=True)


def candidates_v2() -> "object":
    """Candidate rows for the family from pass v2 (replacing the family's v1 rows in candidates_periods)."""
    import gzip
    import json

    import pandas as pd

    from .. import config, labels
    reps = pd.read_parquet(config.WORKDIR / f"reports_{FAMILY_ID}.parquet")
    ex = config.RAW / "extractions"
    rows = []
    for r in reps.itertuples():
        lm = json.loads((labels.LABEL_MAPS / FAMILY_ID / r.report_format / f"{r.deal_cik}.json").read_text())
        dest = ex / str(r.deal_cik) / f"{r.accession}__{r.filename}.v2.json.gz"
        if not dest.exists():
            continue
        rec = json.load(gzip.open(dest, "rt"))
        for f in lm["fields"]:
            raw = (rec.get("json") or {}).get(f["field"])
            rows.append({"family": FAMILY_ID, "deal_cik": r.deal_cik, "accession": r.accession, "form": r.form,
                         "report_format": r.report_format, "field": f["field"], "kind": f["kind"],
                         "candidate": printed_to_candidate(f["kind"], raw), "extraction_id": f"v2/{rec.get('scrape_id')}"})
    cand = pd.DataFrame(rows)
    return config.merge_rows(config.WORKDIR / "candidates_periods.parquet", cand, "family", [FAMILY_ID])
