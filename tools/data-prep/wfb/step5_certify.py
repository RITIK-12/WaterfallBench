"""Step 5: certify the answer key deterministically (no model output is ever accepted as a value).

For every fetched period of a family:
 1. label-first source anchoring: each label-map field is read from its cell(s) in the official HTML;
    no cell, or mapped cells that disagree, fails; the Firecrawl candidate must equal the cell value.
 2./4./5./6./8. family checks (balance identity, account rollforwards, cash reconciliation, totals, signs).
 3. cross-filing continuity (period t ending == period t+1 beginning), on ORIGINAL filings in period order;
    the last period with no successor filing yet is tagged continuity_pending; a final (paid-off) period is
    tagged continuity_not_applicable.
 7. closing anchor: only when the deal's first report is in the fetched history (needs certified params).
Writes certified_periods.parquet (one row per filing, with every check result) and certified_values.parquet.

Usage: python -m wfb.step5_certify --family carmax
"""

from __future__ import annotations

import argparse
import json
from decimal import Decimal

import pandas as pd

from . import config, fc, grid, labels
from .step4_extract import family_module, parser

DESIGN_EXPOSED = {
    # Periods inspected while designing the parser/label maps/checks, before any split was assigned.
    # Family modules add their own via DESIGN_EXPOSED_ACCESSIONS = {...} and/or
    # DESIGN_EXPOSED_PERIODS = {(deal_cik, "YYYYMMDD"), ...}.
    # They are excluded from the test split (Step 7) and disclosed in the dataset card.
    ("0002003263-25-000037", "carmax_auto_owner_trust"),          # CarMax 2024-1, Jul 2025 distribution
    ("0001104659-26-119988", "world_omni_auto_receivables_trust"), # World Omni 2024-C, Oct 2026 distribution
}


def cand_equal(kind: str, cand: str | None, val) -> bool:
    if cand is None:
        return False
    try:
        if kind in ("money", "int"):
            return int(Decimal(cand.replace(",", ""))) == int(val) and Decimal(cand.replace(",", "")) == int(Decimal(cand.replace(",", "")))
        if kind in ("pct", "decimal"):
            return Decimal(cand.replace("%", "").replace(",", "").strip()) == Decimal(val)
        return cand.strip() == str(val).strip()
    except Exception:
        return False


def certify_report(g: grid.Grid, lm: dict, cands: dict[str, str | None]) -> tuple[dict, list[dict], list[tuple]]:
    values, locs, fails = {}, [], []
    for fs in lm["fields"]:
        cells = labels.locate(g, fs)
        if not cells:
            fails.append(("anchoring", fs["field"], "no cell maps to field"))
            continue
        vals = [labels.typed_value(c, fs["kind"]) for c in cells]
        if any(v is None for v in vals):
            fails.append(("anchoring", fs["field"], f"cell not parseable as {fs['kind']}: {[c.text for c in cells]}"))
            continue
        if len(set(map(str, vals))) > 1:
            fails.append(("anchoring", fs["field"], f"mapped cells disagree: {[c.text for c in cells]}"))
            continue
        v = vals[0]
        if any(x is not None for x in cands.values()) and not cand_equal(fs["kind"], cands.get(fs["field"]), v):
            fails.append(("candidate_match", fs["field"], f"firecrawl={cands.get(fs['field'])!r} cell={v}"))
        values[fs["field"]] = v
        locs.append({"field": fs["field"], "cells": [{"table": c.table, "row": c.row, "col": c.col, "text": c.text, "line": c.line} for c in cells]})
    return values, locs, fails


def run(family: str) -> pd.DataFrame:
    fam = family_module(family)
    reps = pd.read_parquet(config.WORKDIR / f"reports_{fam.FAMILY_ID}.parquet")
    reps = reps[pd.to_datetime(reps.filed) >= pd.Timestamp(config.FAMILY_HISTORY_START)]  # pilot: last ~2 years
    cand = pd.read_parquet(config.WORKDIR / "candidates_periods.parquet")
    cand = cand[cand.family == fam.FAMILY_ID]
    cmap = {(r.accession, r.field): r.candidate for r in cand.itertuples()}
    rows, vals_rows = [], []
    per_deal_values: dict[int, list] = {}
    for r in reps.itertuples():
        lm = json.loads((labels.LABEL_MAPS / fam.FAMILY_ID / r.report_format / f"{r.deal_cik}.json").read_text())
        raw_html = fc.read_raw(config.WORKDIR / r.raw_path)
        g = parser(fam)(raw_html)
        cands = {f["field"]: cmap.get((r.accession, f["field"])) for f in lm["fields"]}
        values, locs, fails = certify_report(g, lm, cands)
        fam_checks = fam.checks(values) if values else []
        scale_ok = all("thousand" not in s and "million" not in s for s in g.scale_notes)  # family reports in dollars
        rec = {
            "family": fam.FAMILY_ID, "deal_cik": r.deal_cik, "accession": r.accession, "form": r.form, "filed": r.filed,
            "period_of_report": r.period_of_report, "report_format": r.report_format, "n_fields": len(lm["fields"]),
            "anchoring_failures": json.dumps([f for f in fails if f[0] == "anchoring"]),
            "candidate_mismatches": json.dumps([f for f in fails if f[0] == "candidate_match"]),
            "family_checks": json.dumps(fam_checks),
            "check_anchoring": not any(f[0] == "anchoring" for f in fails),
            "check_candidate_match": not any(f[0] == "candidate_match" for f in fails),
            "check_units_signs": scale_ok and all(c[2] for c in fam_checks if c[0] == "units_signs"),
            "design_exposed": (r.accession, fam.FAMILY_ID) in DESIGN_EXPOSED
                              or r.accession in getattr(fam, "DESIGN_EXPOSED_ACCESSIONS", ())
                              or (int(r.deal_cik), str(r.period_of_report)) in getattr(fam, "DESIGN_EXPOSED_PERIODS", ()),
            "period_meta": json.dumps(fam.period_meta(raw_html)),
        }
        for grp in ("balance_identity", "account_rollforward", "cash_reconciliation", "totals"):
            rec[f"check_{grp}"] = bool(fam_checks) and all(c[2] for c in fam_checks if c[0] == grp)
        rows.append(rec)
        vals_rows.append({"accession": r.accession, "values": json.dumps({k: str(v) for k, v in values.items()}),
                          "cell_locations": json.dumps(locs)})
    cp = pd.DataFrame(rows)

    # 3. continuity on original filings, ordered by period
    vmap = {v["accession"]: json.loads(v["values"]) for v in vals_rows}
    cp["continuity"] = None
    for deal, g in cp[cp.form == "10-D"].sort_values("period_of_report").groupby("deal_cik"):
        accs = list(g.accession)
        pers = list(g.period_of_report)
        for i, acc in enumerate(accs):
            v = vmap[acc]
            if i + 1 < len(accs):
                nxt = vmap[accs[i + 1]]
                gap = _months_between(pers[i], pers[i + 1])
                if gap != 1:
                    status = f"fail:gap_{gap}_months"
                else:
                    bad = [(a, b) for a, b in fam.continuity_pairs(v) if a in v and b in nxt and v[a] != nxt[b]]
                    missing = [(a, b) for a, b in fam.continuity_pairs(v) if a not in v or b not in nxt]
                    status = "pass" if not bad and not missing else f"fail:{(bad or missing)[:3]}"
            else:
                ends = [x for x in v if x.endswith("_note_balance__end_of_period")]
                final = ends and all(Decimal(v[x]) == 0 for x in ends)
                status = "not_applicable_final_period" if final else "continuity_pending"
            cp.loc[cp.accession == acc, "continuity"] = status
    cp.loc[cp.form == "10-D/A", "continuity"] = "not_applicable_amendment"
    cp["continuity_pending"] = cp.continuity.eq("continuity_pending")
    cp["check_continuity"] = cp.continuity.isin(["pass", "continuity_pending", "not_applicable_final_period", "not_applicable_amendment"])
    cp["closing_anchor"] = "not_applicable"  # set by params anchoring when the deal's first report is in history

    checks = ["check_anchoring", "check_candidate_match", "check_balance_identity", "check_continuity",
              "check_account_rollforward", "check_cash_reconciliation", "check_totals", "check_units_signs"]
    gate = [c for c in checks if config.FIRECRAWL_AI_EXTRACTION or c != "check_candidate_match"]
    cp["firecrawl_gate"] = config.FIRECRAWL_AI_EXTRACTION
    cand_accs = set(cand.accession[cand.candidate.notna()])
    cp["candidate_agreement"] = [(1 - len(json.loads(m)) / max(1, n)) if a in cand_accs else None
                                 for a, m, n in zip(cp.accession, cp.candidate_mismatches, cp.n_fields)]
    cp["certified"] = cp[gate].all(axis=1)
    cp["drop_reason"] = cp.apply(lambda r: ",".join(c.removeprefix("check_") for c in gate if not r[c]) or None, axis=1)

    config.merge_rows(config.WORKDIR / "certified_periods.parquet", cp, "family", [fam.FAMILY_ID])
    vv = pd.DataFrame(vals_rows).assign(family=fam.FAMILY_ID)
    config.merge_rows(config.WORKDIR / "certified_values.parquet", vv, "family", [fam.FAMILY_ID])
    write_report(fam, cp, checks)
    return cp


def _months_between(a: str, b: str) -> int:
    ya, ma = int(a[:4]), int(a[4:6])
    yb, mb = int(b[:4]), int(b[4:6])
    return (yb - ya) * 12 + (mb - ma)


def write_report(fam, cp, checks) -> None:
    rates = {c.removeprefix("check_"): f"{cp[c].mean():.1%}" for c in checks}
    tag = cp.assign(tag=cp.filed.map(lambda d: config.window_tag(pd.Timestamp(d).date())))
    by = tag.groupby(["form", "tag"]).agg(periods=("accession", "count"), certified=("certified", "sum")).reset_index()
    reasons = cp.drop_reason.dropna().str.split(",").explode().value_counts()
    lines = [f"## {fam.FAMILY_ID}", "",
             f"- Balance identity: {fam.BALANCE_IDENTITY}",
             f"- Periods: {len(cp)}; certified: **{int(cp.certified.sum())}** ({cp.certified.mean():.1%}); continuity_pending: {int(cp.continuity_pending.sum())}; design-exposed: {int(cp.design_exposed.sum())}",
             "- Pass rate per check: " + ", ".join(f"{k} {v}" for k, v in rates.items()), "",
             by.to_markdown(index=False), "", "Drop reasons (a period can fail several):", "",
             reasons.to_frame("periods").to_markdown(), ""]
    config.update_report("step_5.md", fam.FAMILY_ID, "\n".join(lines), "# Step 5 — Certify the answer key")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--family", required=True)
    run(ap.parse_args().family)
