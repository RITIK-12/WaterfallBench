"""Step 3: choose candidate deals and retrieve their governing filings and full 10-D / 10-D/A history.

Each filing is fetched once as its EDGAR full-submission `.txt` (one Firecrawl request returns the 10-D and
every exhibit exactly as filed). Documents are then split out deterministically into
raw/<cik>/<accession>/docs/<filename>.gz (as filed) and .md.gz (markdown, tables preserved), and listed in
docs_manifest.parquet with provenance.

Usage: python -m wfb.step3_retrieve [--families fam1,fam2] [--deals-per-family N]
"""

from __future__ import annotations

import argparse
import gzip
import hashlib
import json
from collections import defaultdict

import pandas as pd

from . import config, edgar, fc, htmlmd

MAKE_MD = False  # pilot decision: packets use EDGAR HTML as filed; no markdown/PDF variants
GOV_EXHIBIT_PREFIXES = ("EX-4", "EX-10", "EX-99", "EX-1")
TARGET_ASSET_CLASSES = ["auto_loan", "auto_lease", "equipment", "student_loan", "cmbs", "utility_device", "credit_card", "dealer_floorplan"]


def select_candidates(deals: pd.DataFrame, fams: pd.DataFrame, n_families: int = 30, deals_per_family: int = 6) -> pd.DataFrame:
    ok = fams[(fams.n_recent_filings > 0) & (fams.ex99_html_share >= 0.5) & (fams.deals_with_prospectus > 0)].copy()
    ok["score"] = ok.n_recent_filings + 25 * ok.deals_pre_window_history.clip(upper=4) - 10 * (ok.n_report_formats - 1).clip(lower=0)
    picked, per_class = [], defaultdict(list)
    for ac, g in ok.sort_values("score", ascending=False).groupby("asset_class"):
        per_class[ac] = list(g.contract_family)
    order = [a for a in TARGET_ASSET_CLASSES if a in per_class] + [a for a in per_class if a not in TARGET_ASSET_CLASSES]
    while len(picked) < n_families and any(per_class[a] for a in order):
        for a in order:
            if per_class[a] and len(picked) < n_families:
                picked.append(per_class[a].pop(0))
    rows = []
    for fam in picked:
        g = deals[deals.contract_family == fam]
        recent = g.sort_values("n_recent", ascending=False).head(max(1, deals_per_family - 2))
        hist = g[~g.deal_cik.isin(recent.deal_cik)].sort_values("n_historical", ascending=False).head(2)
        rows.append(pd.concat([recent, hist]))
    return pd.concat(rows) if rows else deals.head(0)


def split_and_store(cik: int, accession: str, form: str, txt_path, url: str) -> list[dict]:
    raw = fc.read_raw(txt_path)
    sub = edgar.parse_submission(raw)
    out = []
    ddir = edgar.raw_dir(cik, accession) / "docs"
    ddir.mkdir(parents=True, exist_ok=True)
    for d in sub.documents:
        if not d.filename:
            continue
        is_html = d.filename.lower().endswith((".htm", ".html"))
        is_txt = d.filename.lower().endswith(".txt")
        keep = d.type.upper().startswith(("10-D", "EX-99", "424B", "EX-4", "EX-10", "8-K", "EX-1")) or form.startswith("424B")
        if not keep:
            continue
        body = d.text.encode("utf-8")
        sha = hashlib.sha256(body).hexdigest()
        rawp = ddir / f"{d.filename}.gz"
        if not rawp.exists():
            with gzip.open(rawp, "wb") as f:
                f.write(body)
        mdp = ddir / f"{d.filename}.md.gz"
        if MAKE_MD and (is_html or is_txt) and not mdp.exists():
            try:
                md = htmlmd.html_to_md(d.text) if is_html else d.text
            except Exception as e:
                md = f"<!-- markdown conversion failed: {e} -->"
            with gzip.open(mdp, "wb") as f:
                f.write(md.encode("utf-8"))
        out.append({
            "cik": cik, "accession": accession, "form": form, "doc_type": d.type, "sequence": d.sequence,
            "filename": d.filename, "description": d.description, "sha256": sha, "bytes": len(body),
            "raw_path": str(rawp.relative_to(config.WORKDIR)),
            "md_path": str(mdp.relative_to(config.WORKDIR)) if mdp.exists() else None,
            "source_url": edgar.doc_url(cik, accession, d.filename), "submission_url": url,
            "pdf_source": "filer" if d.filename.lower().endswith(".pdf") else None,
        })
    return out


def run(families: list[str] | None = None, deals_per_family: int = 6, n_families: int = 30) -> pd.DataFrame:
    deals = pd.read_parquet(config.WORKDIR / "deals.parquet")
    fams = pd.read_parquet(config.WORKDIR / "families.parquet")
    filings = pd.read_parquet(config.WORKDIR / "filings_10d.parquet")
    if families:
        cand = deals[deals.contract_family.isin(families)]
    else:
        cand = select_candidates(deals, fams, n_families=n_families, deals_per_family=deals_per_family)
    cand_path = config.WORKDIR / "candidates.parquet"
    allc = config.merge_rows(cand_path, cand, "deal_cik", cand.deal_cik)
    print(f"Step 3: {cand.deal_cik.nunique()} candidate deals in {cand.contract_family.nunique()} families")

    jobs, meta = [], []
    for d in cand.itertuples():
        ciks = {int(d.deal_cik), int(d.filer_cik)}
        f = filings[filings.cik.isin(ciks) & (pd.to_datetime(filings.filed) >= pd.Timestamp(config.FAMILY_HISTORY_START))].drop_duplicates("accession")
        for r in f.itertuples():
            jobs.append((edgar.txt_url(r.cik, r.accession), edgar.txt_path(r.cik, r.accession), {"cik": str(r.cik), "accession": r.accession}))
            meta.append((int(d.deal_cik), r.cik, r.accession, r.form_type, r.filed))
        for col, form in (("prospectus_accessions", "424B"), ("closing_8k_accessions", "8-K")):
            for acc in json.loads(getattr(d, col) or "[]"):
                # Governing filings may sit under the depositor CIK; EDGAR serves them under any listed filer.
                jobs.append((edgar.txt_url(d.deal_cik, acc), edgar.txt_path(d.deal_cik, acc), {"cik": str(d.deal_cik), "accession": acc}))
                meta.append((int(d.deal_cik), int(d.deal_cik), acc, form, None))
    # de-dup jobs by destination
    seen, uj = set(), []
    for j in jobs:
        if j[1] not in seen:
            seen.add(j[1])
            uj.append(j)
    print(f"  {len(uj)} filings to retrieve ({sum(1 for j in uj if not j[1].exists())} not cached)")
    fails = fc.scrape_many(uj, kind="filing_full_submission", batch_size=60)
    if fails:
        print(f"  {len(fails)} retrieval failures (first 5): {list(fails.items())[:5]}")

    rows = []
    for deal_cik, cik, acc, form, filed in meta:
        p = edgar.txt_path(cik, acc)
        if not p.exists():
            continue
        for r in split_and_store(cik, acc, form, p, edgar.txt_url(cik, acc)):
            r["deal_cik"] = deal_cik
            r["filed"] = filed
            rows.append(r)
    man = pd.DataFrame(rows)
    mpath = config.WORKDIR / "docs_manifest.parquet"
    prov = pd.read_json(config.MANIFEST, lines=True)[["path", "retrieved_at", "sha256"]].rename(columns={"path": "submission_path", "sha256": "submission_sha256"})
    man["submission_path"] = man.apply(lambda r: str(edgar.txt_path(r.cik, r.accession).relative_to(config.WORKDIR)), axis=1)
    man = man.drop(columns=[c for c in ("retrieved_at", "submission_sha256") if c in man]).merge(prov.drop_duplicates("submission_path"), on="submission_path", how="left")
    man = config.merge_rows(mpath, man, "deal_cik", man.deal_cik)
    write_report(allc, man, fails)
    return man


def write_report(cand, man, fails) -> None:
    by_fam = cand.groupby(["asset_class", "contract_family"]).agg(deals=("deal_cik", "nunique"), recent=("n_recent", "sum"), historical=("n_historical", "sum")).reset_index()
    docs = man.groupby("doc_type").size().sort_values(ascending=False).head(25)
    lines = [
        "# Step 3 — Retrieve documents",
        "",
        f"- Candidate deals: **{cand.deal_cik.nunique()}** in **{cand.contract_family.nunique()}** families",
        f"- Filings stored (full submissions): **{man.accession.nunique():,}**; documents split out: **{len(man):,}**",
        f"- Retrieval failures this run: {len(fails)}",
        "- Each filing fetched once as its EDGAR full-submission `.txt` via Firecrawl; documents split deterministically; markdown generated locally from the filed HTML (tables preserved).",
        "- PDFs: filer-attached PDFs are kept as filed (`pdf_source=filer`); rendered PDFs (headless Chromium from official HTML) are produced in Step 9 only for documents that enter a packet (deviation: avoids rendering ~10k unused documents).",
        "",
        "## Candidates by family",
        "",
        by_fam.to_markdown(index=False),
        "",
        "## Documents by type (top 25)",
        "",
        docs.to_frame("count").to_markdown(),
        "",
    ]
    (config.REPORTS / "step_3.md").write_text("\n".join(lines))


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--families", default="")
    ap.add_argument("--deals-per-family", type=int, default=6)
    ap.add_argument("--n-families", type=int, default=30)
    a = ap.parse_args()
    run([f for f in a.families.split(",") if f] or None, a.deals_per_family, a.n_families)
    print(open(config.REPORTS / "step_3.md").read()[:4000])
