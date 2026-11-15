"""First-waterfall bench (dataset-fw/): 20 tasks, one FIXED output schema shared by every task.

Each task is a deal's FIRST distribution date. There is no prior servicer report: the agent gets the governing documents
(final prospectus + closing agreements) and this month's servicer report with every waterfall output removed. Opening
balances are the initial balances in the prospectus.

Every task uses the same answer_schema.json, byte for byte. The model lists the deal's note classes itself:

  {"servicing_fee_paid": int, "reserve_ending_balance": int, "released_to_residual": int,
   "classes": [{"class": "A-1", "interest_paid": int, "principal_paid": int, "ending_balance": int}, ...]}

The private meta keeps the key flat (`<CLASS>.<field>`) with answer_format "classes_array"; the service grader matches
listed classes to the key by name (grading.flatten_classes).

Candidates: the first 10-D of every deal in the pilot families whose report was parsed. Values come from the anchored
report cells (Step 5). Build-time checks, any failure drops the candidate:
  - the deal's classes in the report == the classes in the certified prospectus cover table (where certified);
  - per class: initial principal (prospectus, or the report's certified beginning balance) - principal == ending, to the cent;
  - class interest / principal add up to the report's own totals (where the report prints them);
  - no output value is left in the redacted report (value scan) or in the instructions / schema;
  - the gold answer, submitted in the fixed schema, grades fully resolved.

Usage: python -m wfb.step9b_first_waterfall
"""

from __future__ import annotations

import hashlib
import json
import re
import shutil
from decimal import Decimal

import pandas as pd

from . import config, fc, labels
from .step4_extract import family_module, parser
from .step8_select import series_of, window_of
from .step9_packets import Ctx, _governing_docs, _grader, _patterns, leakage_hits, sanitize

OUT = config.REPO / "dataset-fw"
N_TASKS = 20
MODULES = ["carmax", "worldomni", "deere", "nissanlease", "navient"]
# first reports left out on purpose (reason recorded in the build report)
EXCLUDE = {
    "0001558370-25-005506": "John Deere 2025: the report's own sources and uses differ by 1 cent",
}

MAP = {
    "carmax": {
        "classes": r"^note_balances__class_([a-d](?:_\d[a-z]?)?)(?:_floating_rate)?_note_balance__end_of_period$",
        "servicing_fee_paid": "servicing_fee__amount_paid",
        # total interest line if it carries the class's own name, else the class's monthly interest line (2026-3 labels
        # its A-2 total "A-2a"); the sum check ties the chosen lines to the report's interest totals
        "interest_paid": lambda c, v: next(k for k in (
            f"class_a_noteholder_interest_amounts__total_class_{c}_note_interest" if c.startswith("a") else f"class_{c}_noteholder_interest_amount__total_class_{c}_note_interest",
            f"class_a_noteholder_interest_amounts__class_{c}_monthly_interest" if c.startswith("a") else f"class_{c}_noteholder_interest_amount__class_{c}_monthly_interest") if k in v),
        "interest_total_fields": r"^class_[a-d]_noteholder_interest_amounts?__total_class_.*_note_interest$",
        "principal_paid": lambda c: f"deposits__class_{c}_principal_distribution",
        "ending_balance": lambda c, v: next(k for k in (f"note_balances__class_{c}_note_balance__end_of_period",
                                                        f"note_balances__class_{c}_floating_rate_note_balance__end_of_period") if k in v),
        "reserve_ending_balance": "ending_balance",
        "released_to_residual": "amount_to_be_paid_to_certificateholders_from_the_certificate_payment_account_with_respect",
    },
    "worldomni": {
        # first reports print ONE note-balance column (after this date's distributions); later reports print two
        # (date = beginning, an input; date__2 = ending). So on a first report the single column is an OUTPUT.
        "classes": r"^class_([a-d](?:_\d[a-z]?)?)__interest_paid$",
        "first_period_outputs": [r"^class_[a-z0-9_]+?__note_balance_date$"],
        "servicing_fee_paid": "servicing_fee",
        "interest_paid": lambda c, v: f"class_{c}__interest_paid",
        "interest_total": "total_interest_paid__amount",
        "principal_paid": lambda c: f"class_{c}__principal_paid",
        "principal_total": "total_principal_paid__amount",
        "ending_balance": lambda c, v: f"class_{c}__note_balance_date",
        "reserve_ending_balance": "balance_as_of_date__2",
        "released_to_residual": "distribution_to_certificateholders",
    },
    "deere": {
        "classes": r"^outstanding_principal_balance_of_class_([a-d](?:_\d[a-z]?)?)_notes$",
        "servicing_fee_paid": "amount_of_servicing_fee_paid",
        "interest_paid": lambda c, v: f"noteholders_interest_distributable_amount_applicable_to_class_{c}_notes",
        "principal_paid": lambda c: f"class_{c}_noteholders_principal_distributable_amount",
        "ending_balance": lambda c, v: f"outstanding_principal_balance_of_class_{c}_notes",
        "reserve_ending_balance": "ending_balance_after_giving_effect_to_all_distributions",
        "released_to_residual": "amount_paid_to_certificateholder",
        # Sale and Servicing Agreement s.4.08: the first fee = 1.00% p.a. of the pool balance at the cut-off date (first
        # month) + 1.00% p.a. of the pool balance at the end of the first month (second month). No document in the
        # packet - nor the original servicer report - prints that month-end pool balance, so these two values cannot
        # be derived to the cent. They stay in the schema (and in the meta for reference) but are not graded.
        "not_derivable": {
            "servicing_fee_paid": "first fee uses the pool balance at the end of the first month, which no document provides",
            "released_to_residual": "depends on the servicing fee, which cannot be derived (see servicing_fee_paid)",
        },
    },
    "nissanlease": {
        "classes": r"^class_([a-d](?:_\d[a-z]?)?)_notes__ending_balance$",
        "servicing_fee_paid": "servicing_fee_paid",
        "interest_paid": lambda c, v: f"class_{c}_notes_monthly_interest_paid",
        "principal_paid": lambda c: f"class_{c}_notes__principal_payment_due",
        "ending_balance": lambda c, v: f"class_{c}_notes__ending_balance",
        "reserve_ending_balance": "total_ending_reserve_account_balance",
        "released_to_residual": "remaining_available_collections_released_to_seller",
        "beginning": lambda c: f"class_{c}_notes__beginning_balance",   # certified input; no class params for this shelf
    },
}

CLASS_FIELDS = ("interest_paid", "principal_paid", "ending_balance")


def worldomni_fee_dependents(report_html: str, ans: dict) -> dict[str, str]:
    """World Omni s.4.08: the first fee 'shall be prorated to compensate for the length of the initial Collection Period
    being longer than one month' - no day count is given (30/360 is specified only for note interest). The servicer
    prorated by 30/360 days; prorating by actual days is an equally valid reading. Recompute the fee the actual-day
    way and return the graded fields whose value differs between the two readings (the extra or missing fee comes out
    of the residual first, then out of Class A-1 principal - the only class paid principal on the first date)."""
    from datetime import date
    t = " ".join(re.sub(r"<[^>]+>", " ", report_html).replace("&nbsp;", " ").replace("​", " ").split())
    m = re.search(r"Collections Period\D*?(\d\d)/(\d\d)/(\d\d) - (\d\d)/(\d\d)/(\d\d)", t)
    b = re.search(r"Aggregate Starting Principal Balance\D*?([\d,]+\.\d\d)", t)
    if not m or not b:
        raise Skip("World Omni: collection period or starting balance not found for the fee-proration check")
    m1, d1, y1, m2, d2, y2 = map(int, m.groups())
    days = (date(2000 + y2, m2, d2) - date(2000 + y1, m1, d1)).days + 1
    fee_actual = int((Decimal(b.group(1).replace(",", "")) * 100 * Decimal("0.01") * days / 360)
                     .quantize(Decimal("1"), rounding="ROUND_HALF_UP"))
    delta, res = fee_actual - ans["servicing_fee_paid"], ans["released_to_residual"]
    why = (f"the agreement prorates the first servicing fee without a day count; the servicer used 30/360 days, "
           f"actual days ({days}) give {fee_actual / 100:,.2f} instead of {ans['servicing_fee_paid'] / 100:,.2f}")
    dep = {"servicing_fee_paid": why}
    if delta != 0 and (delta < 0 or res > 0):
        dep["released_to_residual"] = why + "; the difference changes the residual"
    if (delta > 0 and delta > res) or (delta < 0 and res == 0):
        dep["A-1.principal_paid"] = dep["A-1.ending_balance"] = why + "; the difference changes Class A-1 principal"
    return dep

# report values that the governing documents cannot reproduce for one specific deal (found by auditing model runs);
# they stay in the meta for reference but are not graded
NOT_DERIVABLE_BY_ACCESSION = {
    "0002063979-25-000005": {   # CarMax 2025-2
        k: "the Sale and Servicing Agreement sets the overcollateralization target at 0.75% of the cutoff pool balance "
           "($10,579,345.66); the servicer report used $10,579,421.74 (the initial overcollateralization), $76.08 more, "
           "so the documented rule cannot reproduce the paid amount"
        for k in ("A-1.principal_paid", "A-1.ending_balance", "released_to_residual")},
}

SCHEMA = {
    "$schema": "https://json-schema.org/draft/2020-12/schema",
    "title": "WaterfallBench first-distribution answer",
    "type": "object",
    "additionalProperties": False,
    "required": ["servicing_fee_paid", "reserve_ending_balance", "released_to_residual", "classes"],
    "properties": {
        "servicing_fee_paid": {"type": "integer", "description": "US cents"},
        "reserve_ending_balance": {"type": "integer", "description": "US cents"},
        "released_to_residual": {"type": "integer", "description": "US cents"},
        "classes": {
            "type": "array", "minItems": 1, "description": "one entry per class of notes the trust issued",
            "items": {
                "type": "object", "additionalProperties": False,
                "required": ["class", "interest_paid", "principal_paid", "ending_balance"],
                "properties": {
                    "class": {"type": "string", "description": "the class name as the prospectus gives it, e.g. A-1"},
                    "interest_paid": {"type": "integer", "description": "US cents"},
                    "principal_paid": {"type": "integer", "description": "US cents"},
                    "ending_balance": {"type": "integer", "description": "US cents"},
                },
            },
        },
    },
}
SCHEMA_TEXT = json.dumps(SCHEMA, indent=1)


def instructions(task_id: str, deal_name: str, dist: str, gname: str) -> str:
    return "\n".join([
        f"# WaterfallBench first-distribution task `{task_id}`", "",
        f"**Deal:** {deal_name}  ", f"**Distribution:** the trust's first distribution date ({dist})", "",
        "This is the first payment date after the closing date, so there is no prior servicer report. Opening "
        "balances are the initial balances in the governing documents.", "",
        "Files (SEC EDGAR HTML as filed):",
        "- `/workspace/docs/`: the final prospectus and the closing agreements.",
        f"- `/workspace/reports/{gname}`: this distribution's servicer report with every waterfall result removed. "
        "Collections, pool data, rates and dates remain.", "",
        "Apply the priority of payments and the definitions in the governing documents and compute:", "",
        "| field | meaning |", "|---|---|",
        "| `servicing_fee_paid` | servicing fee paid on this distribution date |",
        "| `reserve_ending_balance` | reserve account balance after this date's deposits and withdrawals |",
        "| `released_to_residual` | amount released from available funds to the certificateholders / seller after all "
        "required payments (excluding any reserve account release) |",
        "| `classes` | one entry per class of notes the trust issued (certificates are not a note class) |",
        "| `classes[].class` | the class name as the prospectus gives it, e.g. `A-1` |",
        "| `classes[].interest_paid` | interest paid to the class on this date |",
        "| `classes[].principal_paid` | principal paid to the class on this date |",
        "| `classes[].ending_balance` | the class's outstanding principal balance after this date's distributions |", "",
        "Money is integer US cents (e.g. $1,234.56 -> 123456). Write `/workspace/answer.json` as one JSON object "
        "matching `/workspace/answer_schema.json`, listing every class of notes exactly once.", ""])


def class_name(c: str) -> str:
    return c.replace("_", "-").upper().replace("A-2A", "A-2a").replace("A-2B", "A-2b")


def norm_cls(s: str) -> str:
    return re.sub(r"[^a-z0-9]", "", s.lower().replace("class", ""))


def cents(s) -> int | None:
    t = re.sub(r"[^\d.]", "", str(s or ""))
    return int(Decimal(t) * 100) if t else None


def as_array(ans: dict, classes: list[str]) -> dict:
    out = {k: ans[k] for k in ("servicing_fee_paid", "reserve_ending_balance", "released_to_residual")}
    out["classes"] = [{"class": c, **{f: ans[f"{c}.{f}"] for f in CLASS_FIELDS}} for c in classes]
    return out


class Skip(Exception):
    pass


def build(ctx: Ctx, acc: str, params: pd.DataFrame) -> dict:
    """Build one task into OUT (raises Skip with the reason if any check fails)."""
    mp = MAP[ctx.module]
    deal = int(ctx.cp.loc[acc, "deal_cik"])
    per = ctx.cp.loc[acc, "period_of_report"]
    raw = ctx.vals[acc]
    deal_name = ctx.deals.loc[deal, "deal_name"]
    task_id = f"fw-{ctx.module}-{series_of(deal_name)}-{per[:4]}-{per[4:6]}"
    if not bool(ctx.cp.loc[acc, "check_anchoring"]):
        bad = json.loads(ctx.cp.loc[acc, "anchoring_failures"] or "[]")
        if any(f[1] in raw for f in bad):     # an unanchored field that carries a value could not be redacted
            raise Skip(f"{task_id}: unanchored fields with values {bad}")
    forced = [re.compile(p) for p in mp.get("first_period_outputs", [])]
    if forced and any(k.endswith("__note_balance_date__2") for k in raw):
        raise Skip(f"{task_id}: report has a prior balance column - not a first-report layout")

    def is_in(f: str) -> bool:
        return ctx.is_input(f) and not any(p.search(f) for p in forced)

    classes = sorted({m.group(1) for k in raw for m in [re.match(mp["classes"], k)] if m}, key=lambda c: (c[0], c))
    if not classes:
        raise Skip(f"{task_id}: no note classes found")
    ans, src = {}, {}

    def put(key, field):
        if field not in raw:
            raise Skip(f"{task_id}: mapped field {field!r} for {key} is not in the report")
        if is_in(field):
            raise Skip(f"{task_id}: {field!r} ({key}) is an INPUT in this report (visible)")
        ans[key], src[key] = int(Decimal(raw[field])), field

    put("servicing_fee_paid", mp["servicing_fee_paid"])
    for c in classes:
        cn = class_name(c)
        put(f"{cn}.interest_paid", mp["interest_paid"](c, raw))
        put(f"{cn}.principal_paid", mp["principal_paid"](c))
        put(f"{cn}.ending_balance", mp["ending_balance"](c, raw))
    put("reserve_ending_balance", mp["reserve_ending_balance"])
    put("released_to_residual", mp["released_to_residual"])
    names = [class_name(c) for c in classes]
    sums = []
    tot_i = (sum(int(Decimal(raw[k])) for k in raw if re.match(mp["interest_total_fields"], k)) if "interest_total_fields" in mp
             else int(Decimal(raw[mp["interest_total"]])) if mp.get("interest_total") in raw else None)
    if tot_i is not None:
        got = sum(ans[f"{n}.interest_paid"] for n in names)
        sums.append(("interest", got, tot_i))
        if got != tot_i:
            raise Skip(f"{task_id}: class interest {got} != report interest total {tot_i}")
    if mp.get("principal_total") in raw:
        tot_p, got = int(Decimal(raw[mp["principal_total"]])), sum(ans[f"{n}.principal_paid"] for n in names)
        sums.append(("principal", got, tot_p))
        if got != tot_p:
            raise Skip(f"{task_id}: class principal {got} != report principal total {tot_p}")
    # ---- classes and opening balances against the prospectus cover table
    pr = params[(params.family == ctx.fam.FAMILY_ID) & (params.deal_cik == deal) & params.param.str.endswith(".initial_principal")]
    init = {norm_cls(p.split(".")[1]): cents(v) for p, v in zip(pr.param, pr.value)}
    if init and set(init) != {norm_cls(c) for c in classes}:
        raise Skip(f"{task_id}: report classes {names} != prospectus classes {sorted(init)}")
    checks = []
    for c, cn in zip(classes, names):
        ib = init.get(norm_cls(c))
        if ib is None and "beginning" in mp and mp["beginning"](c) in raw:
            ib = int(Decimal(raw[mp["beginning"](c)]))
        ok = ib is not None and ib - ans[f"{cn}.principal_paid"] == ans[f"{cn}.ending_balance"]
        checks.append({"class": cn, "initial": ib, "principal_paid": ans[f"{cn}.principal_paid"],
                       "ending": ans[f"{cn}.ending_balance"], "ok": ok})
        if not ok:
            raise Skip(f"{task_id}: identity failed for {cn}: initial {ib} - principal {ans[f'{cn}.principal_paid']} "
                       f"!= ending {ans[f'{cn}.ending_balance']}")
    # ---- redacted report: every output cell removed, value scan for leaks
    lm = ctx.lm(acc)
    src_html = ctx.html(acc)
    g = parser(ctx.fam)(src_html)
    fs_by = {f["field"]: f for f in lm["fields"]}
    inputs = {k for k in raw if is_in(k)}
    removed = set(raw) - inputs
    from .step7_refs import _kinds, _typed
    kinds = _kinds(ctx.fam, deal)
    cur = _typed(raw, kinds)
    rm_cells, keep_cells, outvals = [], [], {}
    for f in raw:
        cells = labels.locate(g, fs_by[f]) if f in fs_by else []
        if f in removed:
            rm_cells += cells
            outvals[f] = (kinds.get(f, "money"), cur.get(f), cells[0].text if cells else "")
        else:
            keep_cells += cells
    for key, f in src.items():   # every graded value must sit in a located cell that is removed
        if f not in fs_by or not labels.locate(g, fs_by[f]):
            raise Skip(f"{task_id}: graded field {f} ({key}) has no located cell to remove")
    in_cents = {int(cur[k]) for k in inputs if kinds.get(k, "money") == "money" and cur.get(k) is not None}
    in_printed = {re.sub(r"[$%()\s]", "", c.text) for c in keep_cells}
    # opening class balances are public (prospectus cover; some reports print an unparsed "Original Note Balance"
    # row). An untouched class's ending balance equals its opening balance, so the value-scan pass must not blank
    # those opening-balance cells; the graded ending-balance cells themselves are still removed via rm_cells.
    public = in_cents | {ck["initial"] for ck in checks if ck["initial"] is not None}
    scan = {f: x for f, x in outvals.items() if not (x[0] == "money" and x[1] is not None and int(x[1]) in public)}
    clean, removed_rows = sanitize(src_html, ctx.fam, rm_cells, keep_cells, scan)
    hits = leakage_hits(clean, outvals, public, in_printed)
    gname = f"period_{per[:4]}-{per[4:6]}_graded.html"
    dd = json.loads(ctx.cp.loc[acc, "period_meta"]).get("distribution_date") if isinstance(ctx.cp.loc[acc, "period_meta"], str) else None
    instr = instructions(task_id, deal_name, dd or f"{per[:4]}-{per[4:6]}", gname)
    leaks = [f"report: {h}" for h in hits]
    for f, p in _patterns({k: ("money", v, "") for k, v in ans.items()}):
        if p.search(instr):
            leaks.append(f"instructions: {f}")
    if leaks:
        raise Skip(f"{task_id}: leakage {leaks[:3]}")
    # ---- write the task
    tdir = OUT / "tasks" / task_id
    if tdir.exists():
        shutil.rmtree(tdir)
    (tdir / "docs" / "full").mkdir(parents=True)
    (tdir / "reports").mkdir(parents=True)
    prov = []
    for r in _governing_docs(ctx, deal):
        kind = ("prospectus" if str(r.doc_type).upper().startswith("424B")
                else f"closing-8k-agreement_{str(r.doc_type).lower().replace('.', '-')}")
        name = f"{kind}__{r.filename.rsplit('.', 1)[0]}.html"
        (tdir / "docs" / "full" / name).write_text(fc.read_raw(config.WORKDIR / r.raw_path), encoding="utf-8")
        prov.append({"file": f"docs/full/{name}", "source_url": r.source_url, "accession": r.accession, "sha256": r.sha256})
    if not any(p["file"].startswith("docs/full/prospectus") for p in prov):
        shutil.rmtree(tdir)
        raise Skip(f"{task_id}: no final prospectus on file")
    (tdir / "reports" / gname).write_text(clean, encoding="utf-8")
    prov.append({"file": f"reports/{gname}", "source_url": ctx.reps.loc[acc, "source_url"], "accession": acc,
                 "derived": "original report with every waterfall output removed"})
    (tdir / "instructions.md").write_text(instr, encoding="utf-8")
    (tdir / "answer_schema.json").write_text(SCHEMA_TEXT, encoding="utf-8")
    initial = {ck["class"]: ck["initial"] for ck in checks}
    nd = {**mp.get("not_derivable", {}), **NOT_DERIVABLE_BY_ACCESSION.get(acc, {})}
    if ctx.module == "worldomni":
        nd.update(worldomni_fee_dependents(src_html, ans))
    ungraded = {k: {"value": ans[k], "source_field": src[k], "reason": nd[k]} for k in nd}
    full = ans
    ans = {k: v for k, v in full.items() if k not in nd}
    fields = {}
    for k, v in ans.items():
        cls, _, fld = k.partition(".")
        # trivial = zero, or unchanged from its opening balance (a class nobody paid; a reserve still at its closing
        # deposit, which the report prints as the beginning balance)
        trivial = (v == 0 or (fld == "ending_balance" and v == initial.get(cls))
                   or (k == "reserve_ending_balance" and v in in_cents))
        fields[k] = {"type": "money_cents", "trivial": trivial, "source_field": src[k]}
    meta = {"task_id": task_id, "category": "C1", "category_name": "first_distribution", "answer_format": "classes_array",
            "excerpt_derivable": False, "asset_class": ctx.deals.loc[deal, "asset_class"], "family": ctx.fam.FAMILY_ID,
            "deal": deal_name, "deal_cik": deal, "classes": names, "window_tag": window_of([ctx.cp.loc[acc, "filed"]]),
            "continuity_pending": False, "fields": fields, "answer": ans, "ungraded": ungraded,
            "answer_classes_array": as_array(full, names),
            "graded_periods": [{"accession": acc, "period_of_report": per, "filed": str(ctx.cp.loc[acc, "filed"]), "report": gname}],
            "mapping_checks": checks, "sum_checks": [{"what": w, "classes": a, "report_total": b} for w, a, b in sums],
            "checks_passed": {c: bool(ctx.cp.loc[acc, c]) for c in ctx.cp.columns if c.startswith("check_")},
            "removed_rows": len(removed_rows), "provenance": prov, "leakage": {"passed": True, "hits": []},
            "note": "First distribution date; no frozen reference run (references never covered first periods)."}
    gr = _grader()
    gold = as_array(full, names)
    assert gr.headline_metrics(gr.grade_submission(meta, gold))["fully_resolved"] is True
    variant = {**gold, "classes": [{**r, "class": f"Class {r['class'].upper()} Notes"} for r in reversed(gold["classes"])]}
    assert gr.headline_metrics(gr.grade_submission(meta, variant))["fully_resolved"] is True
    zeros = {k: 0 for k in ("servicing_fee_paid", "reserve_ending_balance", "released_to_residual")}
    zeros["classes"] = [{"class": n, **{f: 0 for f in CLASS_FIELDS}} for n in names]
    meta["baselines"] = {"all_zeros": gr.headline_metrics(gr.grade_submission(meta, zeros))}
    (OUT / "meta").mkdir(parents=True, exist_ok=True)
    (OUT / "meta" / f"{task_id}.json").write_text(json.dumps(meta, indent=1, default=str), encoding="utf-8")
    nt = sum(1 for f in fields.values() if not f["trivial"])
    print(f"  OK {task_id:34} classes={len(names)} fields={len(fields):2} non-trivial={nt:2} removed rows={len(removed_rows)}")
    return {"task_id": task_id, "module": ctx.module, "deal": deal_name, "accession": acc,
            "filed": str(ctx.cp.loc[acc, "filed"])[:10], "classes": len(names), "fields": len(fields), "nontrivial": nt}


def candidates() -> list[tuple[str, str, str]]:
    """(module, accession, deal_name) of each deal's first 10-D whose report was parsed, newest first."""
    deals = pd.read_parquet(config.WORKDIR / "deals.parquet")
    f = pd.read_parquet(config.WORKDIR / "filings_10d.parquet")
    first = f[f.form_type == "10-D"].sort_values("filed").groupby("cik").first()
    cp = pd.read_parquet(config.WORKDIR / "certified_periods.parquet").set_index("accession")
    out = []
    for module in MODULES:
        ctx_fid = family_module(module).FAMILY_ID
        for r in deals[deals.contract_family.notna()].itertuples():
            if r.deal_cik not in first.index:
                continue
            acc = first.loc[r.deal_cik].accession
            if acc in cp.index and cp.loc[acc, "family"] == ctx_fid:
                out.append((module, acc, r.deal_name, str(first.loc[r.deal_cik].filed)[:10]))
    return sorted(out, key=lambda x: x[3], reverse=True)


def main() -> None:
    for d in ("tasks", "meta"):
        if (OUT / d).exists():
            shutil.rmtree(OUT / d)
    params = pd.read_parquet(config.WORKDIR / "params_certified.parquet")
    params = params[params.certified]
    ctxs: dict[str, Ctx] = {}
    built, skipped = [], []
    for module, acc, deal_name, filed in candidates():
        if acc in EXCLUDE:
            skipped.append((deal_name, acc, EXCLUDE[acc]))
            continue
        if module not in MAP:
            skipped.append((deal_name, acc, f"no first-waterfall mapping for {module}"))
            continue
        if len(built) >= N_TASKS:
            skipped.append((deal_name, acc, "older than the 20 newest"))
            continue
        ctx = ctxs.setdefault(module, Ctx(module))
        try:
            built.append(build(ctx, acc, params))
        except Skip as e:
            skipped.append((deal_name, acc, str(e)))
    bt = pd.DataFrame(built)
    print(f"\nbuilt {len(bt)} tasks:", bt.groupby("module").size().to_dict() if len(bt) else {})
    print("not used:")
    for d, a, why in skipped:
        print(f"  {d:42} {a}  {why}")
    schemas = {hashlib.sha256((OUT / "tasks" / t / "answer_schema.json").read_bytes()).hexdigest() for t in bt.task_id}
    print(f"distinct answer_schema.json files: {len(schemas)}")
    bt.to_csv(OUT / "meta" / "_build.csv", index=False)


if __name__ == "__main__":
    main()
