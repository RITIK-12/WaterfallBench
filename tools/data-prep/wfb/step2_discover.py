"""Step 2 (phase A): discover deals active since FALLBACK_WINDOW_START, parse their parties, list governing
filings, assign provisional contract families, and fingerprint each deal's report format.

Phase B (MinHash confirmation of families on the priority-of-payments text) runs in step2b_families.py
after governing documents are retrieved for candidate families.
"""

from __future__ import annotations

import gzip
import hashlib
import json
import re
from collections import Counter, defaultdict
from datetime import date, timedelta

import pandas as pd
from lxml import html as lxml_html

from . import config, edgar, fc

SERIES_RE = re.compile(r"\b(19|20)\d{2}\s*-\s*[A-Z0-9]{1,8}\b|\b(19|20)\d{2}[A-Z]{1,3}\d{0,3}\b|\bSERIES\s+(19|20)\d{2}-?[A-Z0-9]*\b", re.I)
PROSPECTUS_FORMS = ("424B1", "424B2", "424B3", "424B4", "424B5", "424B7", "424B8")

ASSET_CLASS_MAP = {
    "auto loans": "auto_loan", "auto leases": "auto_lease", "equipment": "equipment",
    "student loans": "student_loan", "commercial mortgages": "cmbs", "credit card": "credit_card",
    "credit cards": "credit_card", "floorplan": "dealer_floorplan", "dealer floorplan": "dealer_floorplan",
    "residential mortgages": "rmbs", "debt securities": "resecuritization", "other": "other",
}


def family_pattern(name: str) -> str:
    n = SERIES_RE.sub("<S>", name)
    n = re.sub(r"[,.]", " ", n)
    n = re.sub(r"\s+", " ", n).strip().lower()
    return n


def norm_asset_class(raw: str | None, name: str) -> str:
    if raw:
        k = raw.strip().lower()
        for key, v in ASSET_CLASS_MAP.items():
            if k.startswith(key):
                return v
        return k.replace(" ", "_")
    n = name.lower()
    if "lease" in n and "auto" in n:
        return "auto_lease"
    if "student" in n:
        return "student_loan"
    if "mortgage" in n:
        return "cmbs"
    return "unknown"


# ---------- report-format fingerprint ----------
LABEL_CLEAN = re.compile(r"[^a-z ]+")


def table_row_labels(html_text: str) -> list[str]:
    try:
        doc = lxml_html.fromstring(html_text)
    except Exception:
        return []
    labels = []
    for tr in doc.xpath("//tr"):
        for td in tr.xpath("./td|./th"):
            t = " ".join(td.text_content().split())
            if re.search(r"[A-Za-z]{3,}", t):
                lab = LABEL_CLEAN.sub(" ", t.lower())
                lab = re.sub(r"\b(class|classes|a|b|c|d|e|f)\b", " ", lab)
                lab = " ".join(w for w in lab.split() if len(w) > 2)[:80]
                if lab:
                    labels.append(lab)
                break
    return labels


def format_fingerprint(labels: list[str]) -> tuple[str, frozenset]:
    s = frozenset(labels)
    return hashlib.sha1("\n".join(sorted(s)).encode()).hexdigest()[:12], s


def jaccard(a: frozenset, b: frozenset) -> float:
    return len(a & b) / max(1, len(a | b))


def cluster_formats(sets: dict[str, frozenset], thr: float = 0.8) -> dict[str, int]:
    """Greedy single-link clustering of report label sets; returns key -> format cluster id within the group."""
    reps: list[frozenset] = []
    out = {}
    for k, s in sets.items():
        for i, r in enumerate(reps):
            if jaccard(s, r) >= thr:
                out[k] = i
                break
        else:
            reps.append(s)
            out[k] = len(reps) - 1
    return out


def load_submissions(cik: int) -> dict | None:
    dest = config.RAW / "submissions" / f"CIK{int(cik):010d}.json.gz"
    try:
        f = fc.scrape_one(edgar.submissions_url(cik), dest, kind="submissions_json", max_age=0)
    except FileNotFoundError:
        return None
    return json.loads(f.text)


def submissions_frame(sub: dict) -> pd.DataFrame:
    r = sub["filings"]["recent"]
    df = pd.DataFrame({k: r.get(k, []) for k in ("accessionNumber", "filingDate", "form", "primaryDocument", "fileNumber")})
    extra = sub["filings"].get("files") or []
    frames = [df]
    for ef in extra:
        name = ef["name"]
        dest = config.RAW / "submissions" / name.replace(".json", ".json.gz")
        try:
            f = fc.scrape_one(f"{config.SEC_DATA}/submissions/{name}", dest, kind="submissions_json", max_age=0)
            e = json.loads(f.text)
            frames.append(pd.DataFrame({k: e.get(k, []) for k in ("accessionNumber", "filingDate", "form", "primaryDocument", "fileNumber")}))
        except FileNotFoundError:
            pass
    out = pd.concat(frames, ignore_index=True)
    out["filingDate"] = pd.to_datetime(out["filingDate"])
    return out


def run(only: list[str] | None = None) -> tuple[pd.DataFrame, pd.DataFrame]:
    """`only`: optional trust-name prefixes to restrict discovery (used to bootstrap checkpoint families while the
    full-universe run is still fetching; the full run's outputs supersede these)."""
    filings = pd.read_parquet(config.WORKDIR / "filings_10d.parquet")
    filings["filed"] = pd.to_datetime(filings["filed"])
    if only:
        mask = False
        for p in only:
            mask = mask | filings.company.str.lower().str.startswith(p.lower())
        filings = filings[mask]
    active = filings[filings.filed >= pd.Timestamp(config.FALLBACK_WINDOW_START)]
    active_ciks = sorted(active.cik.unique())
    print(f"Step 2: {len(active_ciks)} filer CIKs with a 10-D since {config.FALLBACK_WINDOW_START}")

    # Latest ORIGINAL 10-D per filer CIK (fall back to 10-D/A only if no original exists).
    latest = (active.assign(is_orig=active.form_type.eq("10-D"))
              .sort_values(["cik", "is_orig", "filed"]).groupby("cik").tail(1))
    seen_acc: dict[str, int] = {}
    jobs = []
    for r in latest.itertuples():
        if r.accession in seen_acc:
            continue
        seen_acc[r.accession] = r.cik
        jobs.append((edgar.txt_url(r.cik, r.accession), edgar.txt_path(r.cik, r.accession), {"cik": str(r.cik), "accession": r.accession}))
    print(f"  fetching {len(jobs)} latest 10-D full submissions (cover pages + exhibits)")
    fails = fc.scrape_many(jobs, kind="10d_full_submission", batch_size=50)

    rows = []
    for r in latest.itertuples():
        cik0 = seen_acc.get(r.accession, r.cik)
        p = edgar.txt_path(cik0, r.accession)
        base = {"filer_cik": r.cik, "filer_name": r.company, "latest_accession": r.accession, "latest_filed": r.filed.date()}
        if not p.exists():
            rows.append({**base, "parse_status": f"fetch_failed: {fails.get(edgar.txt_url(cik0, r.accession))}"})
            continue
        sub = edgar.parse_submission(fc.read_raw(p))
        main = next((d for d in sub.documents if d.type.upper().startswith("10-D")), None)
        cover = edgar.parse_10d_cover(edgar.html_to_text(main.text)) if main else {}
        ex99 = [d for d in sub.documents if d.type.upper().startswith("EX-99")]
        labels = []
        for d in ex99:
            if d.filename.lower().endswith((".htm", ".html")):
                labels += table_row_labels(d.text)
        fp, _ = format_fingerprint(labels)
        ie_cik = int(cover["issuing_entity_cik"]) if cover.get("issuing_entity_cik") else None
        rows.append({
            **base,
            "issuing_entity_cik": ie_cik,
            "issuing_entity_file_number": cover.get("issuing_entity_file_number") or sub.h("SEC FILE NUMBER"),
            "depositor_cik": int(cover["depositor_cik"]) if cover.get("depositor_cik") else (int(sub.h("DEPOSITOR-CIK")) if sub.h("DEPOSITOR-CIK") else None),
            "depositor_file_number": cover.get("depositor_file_number"),
            "sponsor_cik": int(cover["sponsor_cik"]) if cover.get("sponsor_cik") else (int(sub.h("SPONSOR-CIK")) if sub.h("SPONSOR-CIK") else None),
            "asset_class_raw": sub.h("ABS ASSET CLASS"),
            "period_of_report": sub.h("CONFORMED PERIOD OF REPORT"),
            "header_names": "; ".join(sub.header.get("COMPANY CONFORMED NAME", [])),
            "ex99_types": ",".join(d.type for d in ex99),
            "ex99_has_pdf": any(d.filename.lower().endswith(".pdf") for d in sub.documents),
            "ex99_html": any(d.filename.lower().endswith((".htm", ".html")) for d in ex99),
            "report_format_fp": fp,
            "report_labels": json.dumps(sorted(set(labels))),
            "parse_status": "ok" if main else "no_10d_document",
        })
    trusts = pd.DataFrame(rows)

    # Deals: one per issuing entity. If the cover page lacks the issuing-entity CIK, the filer CIK is used.
    trusts["deal_cik"] = trusts["issuing_entity_cik"].fillna(trusts["filer_cik"]).astype("Int64")
    names = filings.drop_duplicates("cik", keep="last").set_index("cik")["company"].to_dict()
    deals = trusts.sort_values("latest_filed").drop_duplicates("deal_cik", keep="last").copy()
    deals["deal_name"] = deals["deal_cik"].map(lambda c: names.get(int(c), None))
    deals["deal_name"] = deals["deal_name"].fillna(deals["filer_name"])
    deals["asset_class"] = [norm_asset_class(a, n) for a, n in zip(deals.asset_class_raw, deals.deal_name)]
    deals["name_pattern"] = deals["deal_name"].map(family_pattern)
    deals["family_key"] = deals["sponsor_cik"].astype("Int64").astype(str) + "|" + deals["name_pattern"]

    # Filing counts per deal (by issuing-entity CIK, plus filer CIK when they differ).
    f10 = filings.copy()
    f10["tag"] = f10.filed.dt.date.map(config.window_tag)
    cnt = f10.groupby(["cik", "tag"]).size().unstack(fill_value=0)
    for t in ("recent", "fallback", "historical"):
        if t not in cnt:
            cnt[t] = 0
    deals["n_recent"] = deals.deal_cik.map(lambda c: int(cnt.loc[int(c), "recent"]) if int(c) in cnt.index else 0)
    deals["n_fallback"] = deals.deal_cik.map(lambda c: int(cnt.loc[int(c), "fallback"]) if int(c) in cnt.index else 0)
    deals["n_historical"] = deals.deal_cik.map(lambda c: int(cnt.loc[int(c), "historical"]) if int(c) in cnt.index else 0)
    first10d = f10.groupby("cik").filed.min()
    deals["first_10d_filed"] = deals.deal_cik.map(lambda c: first10d.get(int(c)))

    # Governing filings from EDGAR submissions JSON (issuing entity first, then depositor by file number).
    print(f"  fetching submissions JSON for {deals.deal_cik.nunique()} issuing entities")
    sub_jobs = [(edgar.submissions_url(c), config.RAW / "submissions" / f"CIK{int(c):010d}.json.gz", {"cik": str(c)}) for c in deals.deal_cik.unique()]
    fc.scrape_many(sub_jobs, kind="submissions_json", batch_size=100, max_age=0)
    dep_ciks = sorted({int(c) for c in deals.depositor_cik.dropna().unique()})
    print(f"  fetching submissions JSON for {len(dep_ciks)} depositors")
    fc.scrape_many([(edgar.submissions_url(c), config.RAW / "submissions" / f"CIK{c:010d}.json.gz", {"cik": str(c)}) for c in dep_ciks],
                   kind="submissions_json", batch_size=100, max_age=0)
    dep_frames: dict[int, pd.DataFrame] = {}

    gov = []
    for d in deals.itertuples():
        sub = load_submissions(int(d.deal_cik))
        pros, eightk, src = [], [], "issuing_entity"
        if sub:
            sf = submissions_frame(sub)
            pros = sf[sf.form.isin(PROSPECTUS_FORMS)]
            if pros.empty and d.depositor_cik and d.issuing_entity_file_number:
                dc = int(d.depositor_cik)
                if dc not in dep_frames:
                    ds = load_submissions(dc)
                    dep_frames[dc] = submissions_frame(ds) if ds else pd.DataFrame(columns=sf.columns)
                dsf = dep_frames[dc]
                pros = dsf[dsf.form.isin(PROSPECTUS_FORMS) & dsf.fileNumber.astype(str).str.contains(re.escape(str(d.issuing_entity_file_number)), na=False)]
                src = "depositor_by_file_number"
            if not pros.empty:
                t0 = pros.filingDate.min()
                eightk = sf[(sf.form == "8-K") & (sf.filingDate >= t0 - timedelta(days=3)) & (sf.filingDate <= t0 + timedelta(days=60))]
            else:
                eightk = sf[sf.form == "8-K"].sort_values("filingDate").head(3)
        gov.append({
            "deal_cik": d.deal_cik,
            "prospectus_accessions": json.dumps(list(pros.accessionNumber) if len(pros) else []),
            "prospectus_forms": json.dumps(list(pros.form) if len(pros) else []),
            "prospectus_primary_docs": json.dumps(list(pros.primaryDocument) if len(pros) else []),
            "prospectus_source": src if len(pros) else "unresolved",
            "closing_8k_accessions": json.dumps(list(eightk.accessionNumber) if len(eightk) else []),
            "closing_date_proxy": (pros.filingDate.min().date() if len(pros) else None),
        })
    deals = deals.merge(pd.DataFrame(gov), on="deal_cik", how="left")

    # Provisional families; report-format clusters within each family.
    deals["contract_family"] = deals["family_key"]
    fmt_ids = {}
    for fam, g in deals.groupby("contract_family"):
        sets = {str(r.deal_cik): frozenset(json.loads(r.report_labels)) for r in g.itertuples() if isinstance(r.report_labels, str)}
        for k, v in cluster_formats(sets).items():
            fmt_ids[k] = v
    deals["report_format"] = deals["deal_cik"].astype(str).map(lambda k: fmt_ids.get(k))

    fams = (deals.groupby("contract_family")
            .agg(sponsor_cik=("sponsor_cik", "first"), name_pattern=("name_pattern", "first"),
                 asset_class=("asset_class", lambda s: Counter(s).most_common(1)[0][0]),
                 n_deals=("deal_cik", "nunique"), n_recent_filings=("n_recent", "sum"), n_fallback_filings=("n_fallback", "sum"),
                 n_historical_filings=("n_historical", "sum"), n_report_formats=("report_format", "nunique"),
                 deals_with_prospectus=("prospectus_source", lambda s: int((s != "unresolved").sum())),
                 deals_pre_window_history=("n_historical", lambda s: int((s > 0).sum())),
                 ex99_html_share=("ex99_html", "mean"))
            .reset_index().sort_values(["asset_class", "n_recent_filings"], ascending=[True, False]))
    fams["family_status"] = "provisional_name_pattern"
    W = config.WORKDIR
    config.merge_rows(W / "deals.parquet", deals.drop(columns=["report_labels"]), "deal_cik", deals.deal_cik)
    config.merge_rows(W / "deal_report_labels.parquet", deals[["deal_cik", "report_labels"]], "deal_cik", deals.deal_cik)
    config.merge_rows(W / "families.parquet", fams, "contract_family", fams.contract_family)
    config.merge_rows(W / "trusts_cover_pages.parquet", trusts, "filer_cik", trusts.filer_cik)
    write_report(trusts, deals, fams)
    return deals, fams


def write_report(trusts, deals, fams) -> None:
    ac = deals.groupby("asset_class").agg(deals=("deal_cik", "nunique"), families=("contract_family", "nunique"),
                                          recent_filings=("n_recent", "sum"), fallback_filings=("n_fallback", "sum")).sort_values("deals", ascending=False)
    top = fams.sort_values("n_recent_filings", ascending=False).head(80)
    lines = [
        "# Step 2 (phase A) — Discover and link deals",
        "",
        f"- Filer CIKs with a 10-D since {config.FALLBACK_WINDOW_START}: **{len(trusts):,}**; cover pages parsed OK: {int((trusts.parse_status=='ok').sum()):,}",
        f"- Deals (issuing entities): **{deals.deal_cik.nunique():,}**; provisional contract families: **{fams.contract_family.nunique():,}**",
        f"- Deals with a prospectus (424B*) located via EDGAR submissions JSON: {int((deals.prospectus_source!='unresolved').sum()):,} "
        f"(issuing entity {int((deals.prospectus_source=='issuing_entity').sum()):,}, depositor by file number {int((deals.prospectus_source=='depositor_by_file_number').sum()):,}); unresolved {int((deals.prospectus_source=='unresolved').sum()):,}",
        "- Families are provisional (sponsor CIK + trust-name series pattern). MinHash confirmation on the priority-of-payments section runs for candidate families after Step 3 retrieval (`step2b`).",
        "- Report format = greedy clustering (Jaccard >= 0.8) of EX-99 table row-label sets from each deal's latest 10-D.",
        "",
        "## By asset class",
        "",
        ac.to_markdown(),
        "",
        "## Families (top 80 by recent filings)",
        "",
        top[["contract_family", "asset_class", "n_deals", "n_recent_filings", "n_fallback_filings", "deals_pre_window_history", "n_report_formats", "deals_with_prospectus", "ex99_html_share"]].to_markdown(index=False),
        "",
    ]
    (config.REPORTS / "step_2.md").write_text("\n".join(lines))


if __name__ == "__main__":
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("--only", default="", help="comma-separated trust-name prefixes")
    a = ap.parse_args()
    run([x for x in a.only.split(",") if x] or None)
    print(open(config.REPORTS / "step_2.md").read()[:6000])
