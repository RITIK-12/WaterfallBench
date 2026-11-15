"""Deal parameters: Firecrawl JSON candidates (Step 4.3) + deterministic anchoring (Step 5).

Every parameter is anchored to (document, section label, exact text span or table cell) in the deal's final
prospectus. The Firecrawl candidate must equal the anchored value; otherwise the parameter (and the deal) is
not certified. The reference reads deal-specific values ONLY from params_certified.parquet.

Usage: python -m wfb.params --family carmax
"""

from __future__ import annotations

import argparse
import gzip
import json
import re
import subprocess
import tempfile
from decimal import Decimal
from pathlib import Path

import pandas as pd

from . import config, fc, grid, htmlmd
from .step4_extract import family_deals, family_module

PARAM_DIR = config.RAW / "extractions" / "params"


def norm_num(s: str | None) -> Decimal | None:
    if s is None:
        return None
    m = re.search(r"-?[\d,]*\.?\d+", str(s))
    return Decimal(m.group(0).replace(",", "")) if m else None


def rate_key(s: str):
    """Printed interest rate -> comparable key: footnote markers dropped, numbers compared numerically,
    index names normalised ('SOFR Rate + 0.62%' == 'SOFR Rate plus 0.620%')."""
    t = re.sub(r"\(\d\)", "", s).replace("plus", "+").lower()
    nums = tuple(Decimal(x) for x in re.findall(r"\d+\.?\d*", t))
    idx = "sofr" if "sofr" in t else ("libor" if "libor" in t else "")
    return (idx, nums)


def daycount_norm(s: str) -> str | None:
    t = s.lower()
    if "actual" in t and "360" in t:
        return "actual/360"
    if "30/360" in t or ("360" in t and "30-day" in t):
        return "30/360"
    return None


def _filing_dates(ciks) -> dict[str, "object"]:
    """accession -> filing date from the cached EDGAR submissions JSON of the given CIKs (no network)."""
    from .step2_discover import load_submissions, submissions_frame
    out = {}
    for c in ciks:
        try:
            sub = load_submissions(int(c))
        except Exception:
            sub = None
        if sub:
            sf = submissions_frame(sub)
            out.update(dict(zip(sf.accessionNumber, sf.filingDate)))
    return out


def prospectus_for(deal_cik: int) -> pd.Series | None:
    """The deal's FINAL prospectus: among its 424B HTML filings, the latest one filed within 60 days of the first
    (a preliminary 424B2/424B3 precedes the final 424B5/424B2; a 424B filed months later belongs to something
    else). Filing dates come from the cached submissions JSON; accession order breaks ties / fills gaps."""
    man = pd.read_parquet(config.WORKDIR / "docs_manifest.parquet")
    p = man[(man.deal_cik == deal_cik) & man.doc_type.str.upper().str.startswith("424B") & man.filename.str.lower().str.endswith((".htm", ".html"))]
    if p.empty:
        return None
    deals = pd.read_parquet(config.WORKDIR / "deals.parquet").set_index("deal_cik")
    ciks = [deal_cik] + ([int(deals.loc[deal_cik, "depositor_cik"])] if deal_cik in deals.index and pd.notna(deals.loc[deal_cik, "depositor_cik"]) else [])
    dates = _filing_dates(ciks)
    p = p.assign(_date=p.accession.map(lambda a: dates.get(a)),
                 _ord=p.accession.str.split("-").map(lambda x: (x[1], x[2]) if len(x) == 3 else ("", "")))
    if p._date.notna().any():
        first = pd.to_datetime(p._date).min()
        p = p[p._date.isna() | (pd.to_datetime(p._date) <= first + pd.Timedelta(days=60))]
    return p.sort_values(["_date", "_ord"], na_position="first").iloc[-1]


def anchor_spans(text: str, specs: list[dict]) -> dict:
    out = {}
    for sp in specs:
        res = None
        for m in re.finditer(sp["label"], text):
            win = text[m.end(): m.end() + sp.get("window", 600)]
            v = re.search(sp["value"], win)
            if v:
                a = m.end() + v.start(1)
                res = {"value": v.group(1), "offset": a, "section": m.group(0)[:80],
                       "span": text[max(0, m.start()): m.end() + v.end()][:400]}
                break
        out[sp["param"]] = res
    return out


def _candidate(fam, deal_cik: int, url: str) -> None:
    dest = PARAM_DIR / f"{int(deal_cik)}.json.gz"
    if dest.exists():
        prev = json.load(gzip.open(dest, "rt"))
        if prev.get("json"):
            return
        # Empty extraction (Firecrawl returned nothing): retried once; the empty attempt is kept for provenance.
        if prev.get("retry_of"):
            return
        dest.rename(dest.with_name(dest.name.replace(".json.gz", ".empty1.json.gz")))
    with tempfile.TemporaryDirectory() as td:
        sf = Path(td) / "s.json"
        sf.write_text(json.dumps(fam.PARAMS_SCHEMA))
        out = Path(td) / "o.json"
        fc._rate_gate()
        subprocess.run(["firecrawl", "scrape", url, "--format", "json", "--schema-file", str(sf), "--json", "-o", str(out)],
                       check=True, capture_output=True, text=True, timeout=900)
        res = json.loads(out.read_text())
    fc._add_credits(res.get("metadata", {}).get("creditsUsed") or 5)
    dest.parent.mkdir(parents=True, exist_ok=True)
    with gzip.open(dest, "wt") as f:
        json.dump({"scrape_id": res.get("metadata", {}).get("scrapeId"), "url": url, "json": res.get("json"),
                   "retry_of": (dest.with_name(dest.name.replace(".json.gz", ".empty1.json.gz")).name
                                if dest.with_name(dest.name.replace(".json.gz", ".empty1.json.gz")).exists() else None)}, f)


def run(family: str) -> pd.DataFrame:
    fam = family_module(family)
    deals = family_deals(fam)
    from concurrent.futures import ThreadPoolExecutor
    jobs = [(int(d.deal_cik), prospectus_for(int(d.deal_cik))) for d in deals.itertuples()]
    if config.FIRECRAWL_AI_EXTRACTION:
        fc.check_budget(5 * len(jobs))
        with ThreadPoolExecutor(4) as ex:
            list(ex.map(lambda j: _candidate(fam, j[0], j[1].source_url) if j[1] is not None else None, jobs))
    rows = []
    for d in deals.itertuples():
        pr = prospectus_for(int(d.deal_cik))
        if pr is None:
            rows.append({"family": fam.FAMILY_ID, "deal_cik": int(d.deal_cik), "param": "_prospectus", "certified": False, "reason": "no 424B prospectus HTML retrieved"})
            continue
        html = fc.read_raw(config.WORKDIR / pr.raw_path)
        text = fc.read_raw(config.WORKDIR / pr.md_path) if isinstance(pr.md_path, str) and pr.md_path else htmlmd.html_to_md(html)
        anchors = anchor_spans(text, fam.PARAM_SPECS)
        table = fam.anchor_class_table(html)
        # Firecrawl candidate extraction on the prospectus URL
        dest = PARAM_DIR / f"{int(d.deal_cik)}.json.gz"
        if not dest.exists() and config.FIRECRAWL_AI_EXTRACTION:
            fc.check_budget(5)
            with tempfile.TemporaryDirectory() as td:
                sf = Path(td) / "s.json"
                sf.write_text(json.dumps(fam.PARAMS_SCHEMA))
                out = Path(td) / "o.json"
                subprocess.run(["firecrawl", "scrape", pr.source_url, "--format", "json", "--schema-file", str(sf), "--json", "-o", str(out)],
                               check=True, capture_output=True, text=True, timeout=900)
                res = json.loads(out.read_text())
                fc._add_credits(res.get("metadata", {}).get("creditsUsed") or 5)
                dest.parent.mkdir(parents=True, exist_ok=True)
                with gzip.open(dest, "wt") as f:
                    json.dump({"scrape_id": res.get("metadata", {}).get("scrapeId"), "url": pr.source_url, "json": res.get("json")}, f)
        cand = json.load(gzip.open(dest, "rt")) if dest.exists() else {}
        cj = cand.get("json") or {}
        gate = config.FIRECRAWL_AI_EXTRACTION
        base = {"family": fam.FAMILY_ID, "deal_cik": int(d.deal_cik), "prospectus_accession": pr.accession,
                "prospectus_url": pr.source_url, "extraction_id": cand.get("scrape_id")}
        # scalar params
        for sp in fam.PARAM_SPECS:
            a = anchors.get(sp["param"])
            c = cj.get(sp["param"])
            if sp["unit"] == "daycount":
                av = daycount_norm(a["value"]) if a else None
                agree = c is not None and av == daycount_norm(str(c))
                ok = a is not None and av is not None and (agree or not gate)
            elif sp["unit"] == "text":
                av = a["value"] if a else None
                agree = c is not None and av is not None and re.sub(r"\W", "", av).lower() == re.sub(r"\W", "", str(c)).lower()
                ok = a is not None and av is not None and (agree or not gate)
            else:
                av, cv = (norm_num(a["value"]) if a else None), norm_num(c)
                agree = av is not None and av == cv
                ok = a is not None and av is not None and (agree or not gate)
            rows.append({**base, "param": sp["param"], "value": str(av) if av is not None else None, "unit": sp["unit"],
                         "candidate": c, "anchor_section": a and a["section"], "anchor_offset": a and a["offset"],
                         "anchor_span": a and a["span"], "certified": ok, "candidate_agrees": agree if c is not None else None,
                         "reason": None if ok else ("not anchored" if a is None or av is None else f"candidate {c!r} != anchored {a['value']!r}")})
        # class table params (cell-anchored)
        cc = {str(x.get("class_name", "")).replace("Class ", "").strip(): x for x in (cj.get("classes") or [])}
        for cls, cell in table.items():
            x = cc.get(cls, {})
            for field, key, unit in (("initial_principal", "initial_principal_amount", "usd"), ("interest_rate", "interest_rate", "rate_text")):
                av = cell[field]
                cv = x.get(key)
                if unit == "usd":
                    agree = norm_num(av) is not None and norm_num(av) == norm_num(cv)
                    ok = norm_num(av) is not None and (agree or not gate)
                else:
                    agree = cv is not None and rate_key(av) == rate_key(str(cv))
                    ok = bool(av) and bool(rate_key(av)) and (agree or not gate)
                rows.append({**base, "param": f"class.{cls}.{field}", "value": av, "unit": unit, "candidate": cv,
                             "anchor_section": "prospectus cover table", "anchor_offset": None,
                             "anchor_span": json.dumps(cell["cell_" + field]), "certified": ok, "candidate_agrees": agree if cv is not None else None,
                             "reason": None if ok else f"not anchored / candidate {cv!r} != anchored {av!r}"})
        missing = (set(cc) - set(table)) if gate else set()
        for m in missing:
            rows.append({**base, "param": f"class.{m}", "certified": False, "reason": "class in candidate but not anchored in cover table"})
    df = pd.DataFrame(rows)
    df = config.merge_rows(config.WORKDIR / "params_certified.parquet", df, "family", [fam.FAMILY_ID])
    fam_rows = df[df.family == fam.FAMILY_ID]
    ok = fam_rows.groupby("deal_cik").certified.all()
    print(f"params [{fam.FAMILY_ID}]: {int(ok.sum())}/{len(ok)} deals fully certified; failing params:")
    print(fam_rows[~fam_rows.certified][["deal_cik", "param", "candidate", "value", "reason"]].to_string()[:3000])
    return df


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--family", required=True)
    run(ap.parse_args().family)
