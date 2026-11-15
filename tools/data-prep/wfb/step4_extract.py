"""Step 4: candidate extraction for one contract family.

1. Collect every 10-D / 10-D/A servicer report (EX-99 HTML) of the family's candidate deals.
2. Group reports into formats by their actual table structure (class-abstracted label sets, Jaccard >= 0.85).
3. Build a versioned label map per (format, deal) over the family's in-scope fields.
4. Extract every in-scope field from every report with Firecrawl JSON extraction (rate-gated scrapes, schema per
   deal), storing the raw extraction and its run ID. These are candidates only (Step 5 certifies).

Usage: python -m wfb.step4_extract --family carmax
"""

from __future__ import annotations

import argparse
import gzip
import importlib
import json
import subprocess
import tempfile
from collections import defaultdict
from pathlib import Path

import pandas as pd

from . import config, edgar, fc, grid, labels

EXTRACT_DIR = config.RAW / "extractions"


def family_module(name: str):
    return importlib.import_module(f"wfb.families.{name}")


def parser(fam):
    """Family modules may define parse_report(html) -> grid.Grid to handle their own layout quirks."""
    return getattr(fam, "parse_report", grid.parse_report)


def family_deals(fam) -> pd.DataFrame:
    deals = pd.read_parquet(config.WORKDIR / "deals.parquet")
    cand = pd.read_parquet(config.WORKDIR / "candidates.parquet") if (config.WORKDIR / "candidates.parquet").exists() else deals
    # A family module may list several EDGAR name patterns for one shelf (e.g. "John Deere Owner Trust 2024"
    # and "John Deere Owner Trust 2024-B" are the same contract family).
    pats = getattr(fam, "NAME_PATTERNS", [fam.NAME_PATTERN])
    d = deals[deals.name_pattern.isin(pats)]
    return d[d.deal_cik.isin(cand.deal_cik)]


def family_reports(fam) -> pd.DataFrame:
    """One row per (filing, servicer-report document): the EX-99 HTML with the most in-scope value cells."""
    man = pd.read_parquet(config.WORKDIR / "docs_manifest.parquet")
    deals = family_deals(fam)
    m = man[man.deal_cik.isin(deals.deal_cik) & man.form.isin(config.TEN_D_FORMS)
            & man.doc_type.str.upper().str.startswith("EX-99") & man.filename.str.lower().str.endswith((".htm", ".html"))]
    rows = []
    for (deal, acc), g in m.groupby(["deal_cik", "accession"]):
        best = None
        for r in g.itertuples():
            gr = parser(fam)(fc.read_raw(config.WORKDIR / r.raw_path))
            n = len(gr.cells)
            if best is None or n > best[0]:
                best = (n, r, gr)
        n, r, gr = best
        sub = edgar.parse_submission(fc.read_raw(edgar.txt_path(r.cik, acc)))
        rows.append({"deal_cik": int(deal), "cik": int(r.cik), "accession": acc, "form": r.form, "filed": r.filed,
                     "filename": r.filename, "doc_type": r.doc_type, "raw_path": r.raw_path, "source_url": r.source_url,
                     "period_of_report": sub.h("CONFORMED PERIOD OF REPORT"), "n_cells": n,
                     "keys": json.dumps(sorted(labels.class_abstract_keys(gr.cells)))})
    return pd.DataFrame(rows).sort_values(["filed", "accession"]).reset_index(drop=True)


def assign_formats(reps: pd.DataFrame, family_id: str) -> pd.DataFrame:
    reps = reps.copy()
    reps_keys = [frozenset(json.loads(k)) for k in reps["keys"]]
    centers: list[frozenset] = []
    ids = []
    for ks in reps_keys:
        for i, c in enumerate(centers):
            if labels.jaccard(ks, c) >= labels.FORMAT_JACCARD:
                ids.append(f"{family_id}-f{i+1}")
                break
        else:
            centers.append(ks)
            ids.append(f"{family_id}-f{len(centers)}")
    reps["report_format"] = ids
    return reps


def run(family: str, extract: bool = True) -> pd.DataFrame:
    fam = family_module(family)
    reps = family_reports(fam)
    reps = assign_formats(reps, fam.FAMILY_ID)
    print(f"Step 4 [{fam.FAMILY_ID}]: {len(reps)} reports, {reps.deal_cik.nunique()} deals, formats: {reps.report_format.value_counts().to_dict()}")

    # label maps per (format, deal), in-scope fields only
    lms = {}
    for (fmt, deal), g in reps.groupby(["report_format", "deal_cik"]):
        grids = [parser(fam)(fc.read_raw(config.WORKDIR / p)) for p in g.raw_path]
        lm = labels.build_label_map(fam.FAMILY_ID, fmt, deal, grids)
        lm["fields"] = [f for f in lm["fields"] if fam.in_scope(f)]
        if hasattr(fam, "kind_override"):
            for f in lm["fields"]:
                f["kind"] = fam.kind_override(f["field"], f["kind"])
        (labels.LABEL_MAPS / fam.FAMILY_ID / fmt / f"{deal}.json").write_text(json.dumps(lm, indent=1))
        lms[(fmt, deal)] = lm
    reps.drop(columns=["keys"]).to_parquet(config.WORKDIR / f"reports_{fam.FAMILY_ID}.parquet", index=False)
    if not extract or not config.FIRECRAWL_AI_EXTRACTION:
        return reps

    # One rate-gated pool over every report of the family (each extraction takes ~60-90 s).
    todo = []
    for (fmt, deal), g in reps.groupby(["report_format", "deal_cik"]):
        sfile = EXTRACT_DIR / "_schemas" / fam.FAMILY_ID / fmt / f"{deal}.json"
        sfile.parent.mkdir(parents=True, exist_ok=True)
        sfile.write_text(json.dumps(labels.schema_for(lms[(fmt, deal)])))
        for r in g.itertuples():
            dest = EXTRACT_DIR / str(deal) / f"{r.accession}__{r.filename}.json.gz"
            if not dest.exists():
                todo.append((r, dest, sfile, fmt, deal))
    if todo:
        fc.check_budget(5 * len(todo))
        done = [0]

        def _extract(item):
            r, dest, sfile, fmt, deal = item
            with tempfile.TemporaryDirectory() as td:
                out = Path(td) / "o.json"
                fc._rate_gate()
                p = subprocess.run(["firecrawl", "scrape", r.source_url, "--format", "json", "--schema-file", str(sfile), "--json", "-o", str(out)],
                                   capture_output=True, text=True, timeout=900)
                if p.returncode != 0 or not out.exists():
                    return f"{r.accession}: {(p.stderr or p.stdout)[-300:]}"
                res = json.loads(out.read_text())
            md = res.get("metadata", {})
            fc._add_credits(md.get("creditsUsed") or 5)
            if md.get("statusCode") in (403, 429):
                raise fc.SecBlocked(f"{r.source_url}: {md.get('statusCode')}")
            dest.parent.mkdir(parents=True, exist_ok=True)
            rec = {"batch_id": None, "scrape_id": md.get("scrapeId"), "status_code": md.get("statusCode"), "url": r.source_url,
                   "label_map": f"{fmt}/{deal}.json", "label_map_version": labels.LABEL_MAP_VERSION, "json": res.get("json")}
            with gzip.open(dest, "wt") as f:
                json.dump(rec, f)
            done[0] += 1
            if done[0] % 50 == 0:
                print(f"  extracted {done[0]}/{len(todo)}; credits {fc._credits_used()}", flush=True)
            return None

        from concurrent.futures import ThreadPoolExecutor
        with ThreadPoolExecutor(config.FC_MAX_CONCURRENCY) as ex:
            errs = [e for e in ex.map(_extract, todo) if e]
        print(f"  extracted {len(todo) - len(errs)}/{len(todo)}; credits {fc._credits_used()}" + (f"; errors ({len(errs)}): {errs[:2]}" if errs else ""), flush=True)

    rows = []
    for (fmt, deal), g in reps.groupby(["report_format", "deal_cik"]):
        lm = lms[(fmt, deal)]
        for r in g.itertuples():
            dest = EXTRACT_DIR / str(deal) / f"{r.accession}__{r.filename}.json.gz"
            if not dest.exists():
                continue
            rec = json.load(gzip.open(dest, "rt"))
            for f in lm["fields"]:
                val = (rec.get("json") or {}).get(f["field"])
                rows.append({"family": fam.FAMILY_ID, "deal_cik": deal, "accession": r.accession, "form": r.form,
                             "report_format": fmt, "field": f["field"], "kind": f["kind"],
                             "candidate": None if val is None else str(val),
                             "extraction_id": f"{rec.get('batch_id')}/{rec.get('scrape_id')}"})
    cand = pd.DataFrame(rows)
    cand = config.merge_rows(config.WORKDIR / "candidates_periods.parquet", cand, "family", [fam.FAMILY_ID])
    write_report(fam, reps, lms, cand[cand.family == fam.FAMILY_ID])
    return reps


def write_report(fam, reps, lms, cand) -> None:
    fmt = reps.groupby("report_format").agg(reports=("accession", "count"), deals=("deal_cik", "nunique"),
                                            first=("filed", "min"), last=("filed", "max")).reset_index()
    nf = {f"{k[0]}/{k[1]}": len(v["fields"]) for k, v in lms.items()}
    lines = [f"## {fam.FAMILY_ID}", "",
             f"- Reports: {len(reps)} ({(reps.form=='10-D').sum()} 10-D, {(reps.form=='10-D/A').sum()} 10-D/A) across {reps.deal_cik.nunique()} deals",
             f"- Formats (table-structure clusters, Jaccard >= {labels.FORMAT_JACCARD}):", "", fmt.to_markdown(index=False), "",
             f"- Label maps (`label_maps/{fam.FAMILY_ID}/<format>/<deal>.json`, version {labels.LABEL_MAP_VERSION}); in-scope fields per map: "
             f"min {min(nf.values()) if nf else 0}, max {max(nf.values()) if nf else 0}",
             f"- Firecrawl JSON candidates: {cand.candidate.notna().sum():,} values over {cand.accession.nunique()} reports; "
             f"missing candidate values: {cand.candidate.isna().sum():,}",
             f"- Out-of-scope (statistics) sections: {', '.join(fam.OUT_OF_SCOPE_SECTIONS)}; artefact fields: {', '.join(fam.ARTEFACT_FIELDS)}", ""]
    config.update_report("step_4.md", fam.FAMILY_ID, "\n".join(lines), "# Step 4 — Candidate extraction (Firecrawl JSON)")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--family", required=True)
    ap.add_argument("--no-extract", action="store_true")
    a = ap.parse_args()
    run(a.family, extract=not a.no_extract)
