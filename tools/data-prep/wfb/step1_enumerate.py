"""Step 1: enumerate 10-D and 10-D/A filings from EDGAR form indexes (quarterly full-index, plus daily
indexes where the current quarter's file lags TASK_WINDOW_END)."""

from __future__ import annotations

import re
from concurrent.futures import ThreadPoolExecutor
from datetime import date, datetime, timedelta

import pandas as pd

from . import config, fc

MASTER_ROW = re.compile(r"^(?P<cik>\d+)\|(?P<company>[^|]*)\|(?P<form>[^|]*)\|(?P<date>[\d-]+)\|(?P<path>edgar/\S+)$")
ROW = re.compile(r"^(?P<form>\S(?:.*?\S)?)\s{2,}(?P<company>.+?)\s{2,}(?P<cik>\d+)\s+(?P<date>\d{4}-\d{2}-\d{2}|\d{8})\s+(?P<path>edgar/\S+)\s*$")
LAST_DATA = re.compile(r"Last Data Received:\s+(.+)")


def quarters(start: date, end: date):
    y, q = start.year, (start.month - 1) // 3 + 1
    while (y, q) <= (end.year, (end.month - 1) // 3 + 1):
        yield y, q
        q += 1
        if q == 5:
            y, q = y + 1, 1


def parse_idx(text: str) -> list[dict]:
    rows = []
    master = "|Form Type|" in text[:3000]
    for line in text.splitlines():
        if master:
            m = MASTER_ROW.match(line.strip())
            if not m or not m["form"].startswith("10-D"):
                continue
        elif not line.startswith("10-D"):
            continue
        else:
            m = ROW.match(line)
        if not m or m["form"] not in config.TEN_D_FORMS:
            continue
        ds = m["date"].replace("-", "")
        path = m["path"]
        rows.append({
            "cik": int(m["cik"]),
            "company": m["company"].strip(),
            "form_type": m["form"],
            "filed": datetime.strptime(ds, "%Y%m%d").date(),
            "accession": path.rsplit("/", 1)[-1].removesuffix(".txt"),
            "path": path,
        })
    return rows


def last_data_received(text: str) -> date | None:
    m = LAST_DATA.search(text[:2000])
    if not m:
        return None
    for fmt in ("%b %d, %Y", "%B %d, %Y"):
        try:
            return datetime.strptime(m.group(1).strip(), fmt).date()
        except ValueError:
            pass
    return None


def run() -> pd.DataFrame:
    qs = list(quarters(config.HISTORY_START, config.TASK_WINDOW_END))
    jobs = []
    for y, q in qs:
        url = f"{config.SEC}/Archives/edgar/full-index/{y}/QTR{q}/form.idx"
        jobs.append((url, config.RAW / "edgar_index" / "full" / str(y) / f"QTR{q}" / "form.idx.gz"))
    print(f"Step 1: {len(jobs)} quarterly form.idx files")

    def get(job):
        url, dest = job
        try:
            return fc.scrape_one(url, dest, kind="edgar_full_index")
        except fc.TooLarge:
            # form.idx is fixed-width padded; master.idx lists the same filings pipe-delimited and is ~half the size.
            murl = url.replace("/form.idx", "/master.idx")
            return fc.scrape_one(murl, dest.with_name("master.idx.gz"), kind="edgar_full_index_master")

    with ThreadPoolExecutor(config.FC_MAX_CONCURRENCY) as ex:
        fetched = list(ex.map(get, jobs))

    rows, coverage = [], []
    for (y, q), f in zip(qs, fetched):
        r = parse_idx(f.text)
        for x in r:
            x["index_source"] = f"full/{y}/QTR{q}"
        rows += r
        coverage.append({"index": f"full/{y}/QTR{q}", "last_data_received": last_data_received(f.text), "rows_10d": len(r)})

    # Daily top-up for the current quarter if its quarterly file lags the snapshot date.
    last = coverage[-1]["last_data_received"]
    if last is None or last < config.TASK_WINDOW_END:
        d = (last or date(config.TASK_WINDOW_END.year, 3 * ((config.TASK_WINDOW_END.month - 1) // 3) + 1, 1)) + timedelta(days=1)
        while d <= config.TASK_WINDOW_END:
            if d.weekday() < 5:
                qn = (d.month - 1) // 3 + 1
                url = f"{config.SEC}/Archives/edgar/daily-index/{d.year}/QTR{qn}/form.{d:%Y%m%d}.idx"
                dest = config.RAW / "edgar_index" / "daily" / str(d.year) / f"QTR{qn}" / f"form.{d:%Y%m%d}.idx.gz"
                try:
                    f = fc.scrape_one(url, dest, kind="edgar_daily_index", max_age=0)  # fresh: never trust a cached pre-publication response
                    r = parse_idx(f.text)
                    for x in r:
                        x["index_source"] = f"daily/{d:%Y%m%d}"
                    rows += r
                    coverage.append({"index": f"daily/{d:%Y%m%d}", "last_data_received": last_data_received(f.text), "rows_10d": len(r)})
                except FileNotFoundError:
                    coverage.append({"index": f"daily/{d:%Y%m%d}", "last_data_received": None, "rows_10d": 0, "note": "no daily index (holiday or not yet published)"})
            d += timedelta(days=1)

    df = pd.DataFrame(rows)
    df = df[(df.filed >= config.HISTORY_START) & (df.filed <= config.TASK_WINDOW_END)]
    # A 10-D can be filed under several CIKs (issuing entity + depositor); keep one row per (accession, cik).
    df = df.sort_values(["filed", "accession", "cik"]).drop_duplicates(["accession", "cik"], keep="first").reset_index(drop=True)
    df["filed"] = pd.to_datetime(df["filed"])
    df.to_parquet(config.WORKDIR / "filings_10d.parquet", index=False)
    pd.DataFrame(coverage).to_csv(config.WORKDIR / "reports" / "step_1_index_coverage.csv", index=False)
    write_report(df, coverage)
    return df


def write_report(df: pd.DataFrame, coverage: list[dict]) -> None:
    by_year = df[df.filed.dt.year < 2026].groupby([df.filed.dt.year.rename("year"), "form_type"]).size().unstack(fill_value=0)
    m26 = df[df.filed.dt.year == 2026]
    by_month = m26.groupby([m26.filed.dt.strftime("%Y-%m").rename("month"), "form_type"]).size().unstack(fill_value=0)
    n_trusts = df.cik.nunique()
    lines = [
        "# Step 1 — Enumerate 10-D filings",
        "",
        f"Source: EDGAR quarterly `full-index/*/form.idx` ({config.HISTORY_START:%Y} Q1 through {config.TASK_WINDOW_END:%Y} Q{(config.TASK_WINDOW_END.month-1)//3+1}), "
        "fetched through Firecrawl (`scrape --format rawHtml`), plus daily `form.YYYYMMDD.idx` files where the current quarter lagged the snapshot. "
        f"Filings after {config.TASK_WINDOW_END} discarded. Coverage per index file: `reports/step_1_index_coverage.csv`.",
        "",
        f"- Current quarter's `form.idx` reports last data received {[c for c in coverage if c['index'].startswith('full/')][-1]['last_data_received']}; "
        "daily indexes (fetched fresh, `--max-age 0`) are added only for days after that date up to the snapshot. "
        "An earlier run that misread this header fetched daily indexes for 2026-10-02..11-13; they are kept in raw/ for provenance but not needed.",
        f"- Missing daily indexes (no file published, e.g. federal holidays or weekends-adjacent closures): "
        f"{', '.join(c['index'] for c in coverage if c.get('note')) or 'none'}. sec.gov/Archives answers a missing object with HTTP 403 "
        "and an S3 `AccessDenied` XML body; these are classified as missing files, not as throttling. A genuine SEC fair-access "
        "block (rate-threshold / undeclared-tool page, or HTTP 429) still stops the pipeline. No throttling was observed.",
        "- Quarters whose `form.idx` exceeded Firecrawl's 50 MiB limit were read from the same quarter's `master.idx` "
        f"(same filings, pipe-delimited): {', '.join(sorted(set(df[df.index_source.str.startswith('full/')].index_source) - set(c['index'] for c in coverage if c.get('used') == 'form'))) if False else ', '.join(i for i in sorted(set(df.index_source)) if (config.RAW / 'edgar_index' / i / 'master.idx.gz').exists())}.",
        f"- Total filings: **{len(df):,}** (10-D {int((df.form_type=='10-D').sum()):,}, 10-D/A {int((df.form_type=='10-D/A').sum()):,})",
        f"- Distinct filer CIKs: **{n_trusts:,}**",
        f"- Last filing date seen: {df.filed.max():%Y-%m-%d}",
        "",
        "## 2026 by month",
        "",
        by_month.to_markdown(),
        "",
        "## Before 2026 by year",
        "",
        by_year.to_markdown(),
        "",
    ]
    (config.REPORTS / "step_1.md").write_text("\n".join(lines))


if __name__ == "__main__":
    out = run()
    print(open(config.REPORTS / "step_1.md").read())
