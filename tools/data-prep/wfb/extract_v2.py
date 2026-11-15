"""Step 4, pass v2: Firecrawl JSON candidates requested AS PRINTED, converted to the candidate format in code.

Pass v1 asked Firecrawl for money as integer cents; its conversions dropped digits and trailing ".00" on many
fields, so almost no period could pass the candidate-match check. Pass v2 asks for every field as the exact printed
string and converts it deterministically (money -> integer cents). The candidate is still only a candidate: Step 5
certifies the value read from the report cell and requires the converted candidate to equal it.

v2 replaces v1 for ALL of a family's reports in the 2-year window (no per-field choice). Raw v2 records are new files
(<accession>__<file>.v2.json.gz); v1 records are never overwritten. First developed in wfb/families/deere.py.

Usage: python -m wfb.extract_v2 --family carmax [--concurrency 20]
"""

from __future__ import annotations

import argparse
import gzip
import json
import re
import subprocess
import tempfile
from concurrent.futures import ThreadPoolExecutor
from decimal import Decimal
from pathlib import Path

import pandas as pd

from . import config, fc, grid, labels
from .step4_extract import family_module

EX = config.RAW / "extractions"


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
    """Deterministic conversion of a printed value to the candidate format (money -> integer cents)."""
    if s is None:
        return None
    t = str(s).strip()
    if kind == "status":
        return t
    if t in grid.DASHES or t.replace("$", "").strip() in ("-", "—", "–"):
        return "0"
    neg = (t.startswith("(") and t.endswith(")")) or t.startswith("-") or "$(" in t or t.startswith("$-")
    m = re.search(r"[\d,]*\.?\d+", t.replace(" ", ""))
    if not m:
        return None
    num = Decimal(m.group(0).replace(",", ""))
    if kind == "money":
        cents = int((num * 100).to_integral_value())
        return str(-cents if neg else cents)
    if kind == "int":
        return str(-int(num) if neg else int(num))
    return str(-num if neg else num)


def _reports(fam) -> pd.DataFrame:
    reps = pd.read_parquet(config.WORKDIR / f"reports_{fam.FAMILY_ID}.parquet")
    return reps[pd.to_datetime(reps.filed) >= pd.Timestamp(config.FAMILY_HISTORY_START)]


def _dest(r) -> Path:
    return EX / str(r.deal_cik) / f"{r.accession}__{r.filename}.v2.json.gz"


def extract(family: str, concurrency: int = 20) -> None:
    fam = family_module(family)
    reps = _reports(fam)
    todo = []
    for r in reps.itertuples():
        lm = json.loads((labels.LABEL_MAPS / fam.FAMILY_ID / r.report_format / f"{r.deal_cik}.json").read_text())
        sfile = EX / "_schemas" / fam.FAMILY_ID / r.report_format / f"{r.deal_cik}.v2.json"
        sfile.parent.mkdir(parents=True, exist_ok=True)
        sfile.write_text(json.dumps(schema_v2(lm)))
        if not _dest(r).exists():
            todo.append((r, _dest(r), sfile))
    print(f"v2 [{fam.FAMILY_ID}]: {len(reps)} reports in window, {len(todo)} to extract", flush=True)
    if not todo:
        return
    fc.check_budget(5 * len(todo))
    errs: list[str] = []
    blocked: list[Exception] = []

    def one(item):
        r, dest, sfile = item
        if blocked:
            return
        with tempfile.TemporaryDirectory() as td:
            out = Path(td) / "o.json"
            fc._rate_gate()
            p = subprocess.run(["firecrawl", "scrape", r.source_url, "--format", "json", "--schema-file", str(sfile),
                                "--json", "-o", str(out)], capture_output=True, text=True, timeout=900)
            if p.returncode != 0 or not out.exists():
                errs.append(f"{r.accession}: {(p.stderr or p.stdout)[-200:]}")
                return
            res = json.loads(out.read_text())
        md = res.get("metadata", {})
        fc._add_credits(md.get("creditsUsed") or 5)
        if md.get("statusCode") in (403, 429):
            blocked.append(fc.SecBlocked(f"{r.source_url}: {md.get('statusCode')}"))
            return
        dest.parent.mkdir(parents=True, exist_ok=True)
        with gzip.open(dest, "wt") as f:
            json.dump({"pass": "v2", "scrape_id": md.get("scrapeId"), "status_code": md.get("statusCode"), "url": r.source_url,
                       "schema": str(sfile.relative_to(config.WORKDIR)), "label_map_version": labels.LABEL_MAP_VERSION,
                       "json": res.get("json")}, f)

    with ThreadPoolExecutor(concurrency) as pool:
        list(pool.map(one, todo))
    if blocked:
        raise blocked[0]
    print(f"v2 [{fam.FAMILY_ID}]: extracted {len(todo) - len(errs)}/{len(todo)}; errors {errs[:3]}; credits {fc._credits_used()}", flush=True)


def candidates(family: str) -> pd.DataFrame:
    """Replace the family's rows in candidates_periods.parquet with pass-v2 candidates."""
    fam = family_module(family)
    rows = []
    for r in _reports(fam).itertuples():
        lm = json.loads((labels.LABEL_MAPS / fam.FAMILY_ID / r.report_format / f"{r.deal_cik}.json").read_text())
        if not _dest(r).exists():
            continue
        rec = json.load(gzip.open(_dest(r), "rt"))
        for f in lm["fields"]:
            raw = (rec.get("json") or {}).get(f["field"])
            rows.append({"family": fam.FAMILY_ID, "deal_cik": r.deal_cik, "accession": r.accession, "form": r.form,
                         "report_format": r.report_format, "field": f["field"], "kind": f["kind"],
                         "candidate": printed_to_candidate(f["kind"], raw), "printed": None if raw is None else str(raw),
                         "extraction_id": f"v2/{rec.get('scrape_id')}"})
    cand = pd.DataFrame(rows)
    config.merge_rows(config.WORKDIR / "candidates_periods.parquet", cand, "family", [fam.FAMILY_ID])
    print(f"v2 [{fam.FAMILY_ID}]: {cand.accession.nunique() if len(cand) else 0} reports, {len(cand)} candidate values", flush=True)
    return cand


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--family", required=True)
    ap.add_argument("--concurrency", type=int, default=20)
    a = ap.parse_args()
    extract(a.family, a.concurrency)
    candidates(a.family)
