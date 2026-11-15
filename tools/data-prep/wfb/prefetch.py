"""Prefetch one family's full 10-D history and governing filings into the same cache Step 2/3 use.

Purely a cache warm-up (identical URLs and destinations), so Steps 2-3 later find these files already stored.
Usage: python -m wfb.prefetch --name-prefix "CarMax Auto Owner Trust" --concurrency 4
"""

from __future__ import annotations

import argparse
import json

import pandas as pd

from . import config, edgar, fc
from .step2_discover import PROSPECTUS_FORMS


def run(prefix: str, concurrency: int) -> None:
    config.FC_MAX_CONCURRENCY = concurrency
    f = pd.read_parquet(config.WORKDIR / "filings_10d.parquet")
    f = f[f.company.str.lower().str.startswith(prefix.lower())]
    ciks = sorted(f.cik.unique())
    print(f"{prefix}: {len(ciks)} filer CIKs, {f.accession.nunique()} 10-D/10-D/A filings")
    fc.scrape_many([(edgar.submissions_url(c), config.RAW / "submissions" / f"CIK{int(c):010d}.json.gz", {"cik": str(c)}) for c in ciks],
                   kind="submissions_json", batch_size=100, max_age=0)
    jobs = [(edgar.txt_url(r.cik, r.accession), edgar.txt_path(r.cik, r.accession), {"cik": str(r.cik), "accession": r.accession})
            for r in f.drop_duplicates("accession").itertuples()]
    for c in ciks:
        p = config.RAW / "submissions" / f"CIK{int(c):010d}.json.gz"
        if not p.exists():
            continue
        s = json.loads(fc.read_raw(p))
        r = s["filings"]["recent"]
        sf = pd.DataFrame({k: r.get(k, []) for k in ("accessionNumber", "filingDate", "form")})
        pros = sf[sf.form.isin(PROSPECTUS_FORMS)]
        if not pros.empty:
            t0 = pd.to_datetime(pros.filingDate).min()
            ek = sf[(sf.form == "8-K") & (pd.to_datetime(sf.filingDate) >= t0 - pd.Timedelta(days=3)) & (pd.to_datetime(sf.filingDate) <= t0 + pd.Timedelta(days=60))]
            for acc in list(pros.accessionNumber) + list(ek.accessionNumber):
                jobs.append((edgar.txt_url(c, acc), edgar.txt_path(c, acc), {"cik": str(c), "accession": acc}))
    print(f"  {len(jobs)} filings to cache")
    fails = fc.scrape_many(jobs, kind="filing_full_submission", batch_size=60)
    print(f"  done; failures: {len(fails)} {list(fails.items())[:3]}")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--name-prefix", required=True)
    ap.add_argument("--concurrency", type=int, default=4)
    a = ap.parse_args()
    run(a.name_prefix, a.concurrency)
