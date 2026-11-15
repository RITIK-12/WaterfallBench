"""Step 7: splits, reference development harness, freeze, and the single test run.

  python -m wfb.step7_refs split    --family carmax     # assign splits (write-once) BEFORE any reference code
  python -m wfb.step7_refs dev      --family carmax     # run the reference on calibration + validation ONLY
  python -m wfb.step7_refs freeze   --family carmax     # record refs/<family>.py SHA-256 in refs/FROZEN.json
  python -m wfb.step7_refs test     --family carmax     # ONE run over every test period; refuses to run twice

Reference modules live in refs/<FAMILY_ID>.py and expose:
  INPUTS: list[str] of field-name regexes the reference consumes (everything else it computes is an output)
  run(cur: dict, prev: dict, params: dict, meta: dict) -> dict[str, value]
where `cur` holds only the graded period's INPUT fields, `prev` the complete opening-state report (prior
period), `params` the deal's certified parameters, `meta` the period's header dates.
"""

from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import re
from datetime import datetime, timezone
from decimal import Decimal

import pandas as pd

from . import config
from .step4_extract import family_module

REFS = config.WORKDIR / "refs"
SPLITS = config.WORKDIR / "splits.parquet"
FROZEN = REFS / "FROZEN.json"
DERIV = config.WORKDIR / "derivability.parquet"
MAX_CAL = 6
MAX_VAL = 6


def _cp(fam) -> pd.DataFrame:
    cp = pd.read_parquet(config.WORKDIR / "certified_periods.parquet")
    return cp[(cp.family == fam.FAMILY_ID)]


def assign_splits(family: str) -> pd.DataFrame:
    fam = family_module(family)
    if SPLITS.exists():
        s = pd.read_parquet(SPLITS)
        if (s.family == fam.FAMILY_ID).any():
            raise SystemExit(f"splits for {fam.FAMILY_ID} already assigned; they are never changed")
    else:
        s = pd.DataFrame()
    cp = _cp(fam)
    cert = cp[cp.certified & (cp.form == "10-D")].copy()
    cert["filed_d"] = pd.to_datetime(cert.filed).dt.date
    cert["pre_window"] = cert.filed_d < config.TASK_WINDOW_START
    pre = cert[cert.pre_window]
    deals_pre = pre.groupby("deal_cik").size().sort_values(ascending=False)
    rows = []
    exposed = cp[cp.design_exposed]
    if len(deals_pre) >= 2:
        mode = "default"
        # Rule fixed before any reference code: if the family has design-exposed periods, their deal is the
        # calibration deal and those periods are calibration; otherwise the deal with most pre-window periods.
        exp_deals = [d for d in exposed.deal_cik.unique() if d in deals_pre.index]
        cal_deal = exp_deals[0] if exp_deals else int(sorted(deals_pre.index, key=lambda d: (-deals_pre[d], d))[0])
        val_deal = int(sorted([d for d in deals_pre.index if d != cal_deal], key=lambda d: (-deals_pre[d], d))[0])
        cal = pre[pre.deal_cik == cal_deal].sort_values("period_of_report")
        must = cal[cal.design_exposed]
        cal = pd.concat([must, cal[~cal.design_exposed].tail(MAX_CAL - len(must))]) if len(must) else cal.tail(MAX_CAL)
        val = pre[pre.deal_cik == val_deal].sort_values("period_of_report").tail(MAX_VAL)
    else:
        mode = "in_window"
        first_deal = cert.sort_values("period_of_report").deal_cik.iloc[0] if len(cert) else None
        d = cert[cert.deal_cik == first_deal].sort_values("period_of_report")
        cal, val = d.head(2), d.iloc[2:4]
    if len(cal) == 0 or len(val) == 0:
        print(f"{fam.FAMILY_ID}: too few certified periods for calibration/validation -> family dropped")
        mode = "dropped"
    cal_acc, val_acc = set(cal.accession), set(val.accession)
    for r in cert.itertuples():
        split = "calibration" if r.accession in cal_acc else "validation" if r.accession in val_acc else "test"
        if split == "test" and r.design_exposed:
            split = "excluded_design_exposed"
        if mode == "dropped":
            split = "dropped_family"
        rows.append({"family": fam.FAMILY_ID, "deal_cik": int(r.deal_cik), "accession": r.accession,
                     "period_of_report": r.period_of_report, "filed": r.filed, "split": split, "split_mode": mode,
                     "assigned_at": datetime.now(timezone.utc).isoformat(timespec="seconds")})
    new = pd.DataFrame(rows)
    with config.shared_lock():
        s = pd.read_parquet(SPLITS) if SPLITS.exists() else pd.DataFrame()
        if len(s) and (s.family == fam.FAMILY_ID).any():
            raise SystemExit(f"splits for {fam.FAMILY_ID} already assigned; they are never changed")
        config.write_atomic(pd.concat([s, new], ignore_index=True), SPLITS)
    print(new.groupby("split").size().to_string())
    return new


def _load_ref(fam):
    path = REFS / f"{fam.FAMILY_ID}.py"
    spec = importlib.util.spec_from_file_location(f"ref_{fam.FAMILY_ID}", path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod, hashlib.sha256(path.read_bytes()).hexdigest()


def _values(accessions: list[str]) -> dict[str, dict]:
    cv = pd.read_parquet(config.WORKDIR / "certified_values.parquet")
    cv = cv[cv.accession.isin(accessions)]
    return {r.accession: json.loads(r.values) for r in cv.itertuples()}


def _typed(v: dict, kinds: dict) -> dict:
    out = {}
    for k, x in v.items():
        kd = kinds.get(k, "money")
        out[k] = int(x) if kd in ("money", "int") else (Decimal(x) if kd in ("pct", "decimal") else x)
    return out


def _kinds(fam, deal: int) -> dict:
    kinds = {}
    for p in (config.WORKDIR / "label_maps" / fam.FAMILY_ID).glob(f"*/{deal}.json"):
        for f in json.loads(p.read_text())["fields"]:
            kinds[f["field"]] = f["kind"]
    return kinds


def _params(fam, deal: int) -> dict:
    p = pd.read_parquet(config.WORKDIR / "params_certified.parquet")
    p = p[(p.family == fam.FAMILY_ID) & (p.deal_cik == deal)]
    if p.empty or not p.certified.all():
        return {}
    return {r.param: r.value for r in p.itertuples()}


def _prev_accession(fam, deal: int, period: str) -> str | None:
    cp = _cp(fam)
    g = cp[(cp.deal_cik == deal) & (cp.form == "10-D") & (cp.period_of_report < period)].sort_values("period_of_report")
    return g.accession.iloc[-1] if len(g) else None


def evaluate(fam, mod, accessions: list[str]) -> pd.DataFrame:
    """Run the reference on periods. `cur` gets ONLY input fields of the graded period; `prev` is the complete
    opening-state report of the preceding period (it is in the packet unsanitised)."""
    sp = pd.read_parquet(SPLITS)
    sp = sp[sp.accession.isin(accessions)]
    cp = _cp(fam).set_index("accession")
    rows = []
    for r in sp.itertuples():
        deal = int(r.deal_cik)
        prev_acc = _prev_accession(fam, deal, r.period_of_report)
        kinds = _kinds(fam, deal)
        vals = _values([r.accession] + ([prev_acc] if prev_acc else []))
        cur_all = _typed(vals[r.accession], kinds)
        prev = _typed(vals[prev_acc], kinds) if prev_acc and prev_acc in vals else None
        params = _params(fam, deal)
        meta = json.loads(cp.loc[r.accession, "period_meta"]) if "period_meta" in cp.columns and isinstance(cp.loc[r.accession, "period_meta"], str) else {}
        if prev_acc and "period_meta" in cp.columns and prev_acc in cp.index and isinstance(cp.loc[prev_acc, "period_meta"], str):
            meta["prev"] = json.loads(cp.loc[prev_acc, "period_meta"])
        rx = [re.compile(p) for p in mod.INPUTS]
        cur_in = {k: x for k, x in cur_all.items() if any(p.search(k) for p in rx)}
        status, mism, n_out, err = "ok", [], 0, None
        if prev is None or not params:
            status = "no_opening_state" if prev is None else "params_not_certified"
        else:
            try:
                out = mod.run(cur_in, prev, params, meta)
                for k, x in out.items():
                    if k in cur_in:
                        continue
                    if k not in cur_all:
                        continue
                    n_out += 1
                    if str(x) != str(cur_all[k]) and not (isinstance(x, Decimal) and Decimal(x) == Decimal(cur_all[k])):
                        mism.append((k, str(x), str(cur_all[k])))
                unproduced = [k for k in cur_all if k not in cur_in and k not in out and not any(re.search(p, k) for p in getattr(mod, "IGNORED", []))]
                if unproduced:
                    mism += [(k, "<not computed>", str(cur_all[k])) for k in unproduced]
            except Exception as e:  # a crash is a failure, never a skip
                status, err = "error", f"{type(e).__name__}: {e}"
        rows.append({"family": fam.FAMILY_ID, "deal_cik": deal, "accession": r.accession, "split": r.split,
                     "period_of_report": r.period_of_report, "status": status, "n_outputs_checked": n_out,
                     "n_mismatch": len(mism), "mismatches": json.dumps(mism[:40]), "error": err,
                     "pass": status == "ok" and not mism})
    return pd.DataFrame(rows)


def dev(family: str) -> pd.DataFrame:
    fam = family_module(family)
    mod, sha = _load_ref(fam)
    sp = pd.read_parquet(SPLITS)
    dv = sp[(sp.family == fam.FAMILY_ID) & sp.split.isin(["calibration", "validation"])]
    res = evaluate(fam, mod, list(dv.accession))
    print(res.groupby("split")["pass"].agg(["sum", "count"]).to_string())
    for r in res[~res["pass"]].itertuples():
        print(f"  {r.split} {r.deal_cik} {r.period_of_report} {r.status} {r.error or ''} {r.mismatches[:600]}")
    return res


def freeze(family: str, note: str = "") -> None:
    fam = family_module(family)
    mod, sha = _load_ref(fam)
    res = dev(family)
    rates = res.groupby("split")["pass"].mean().to_dict()
    with config.shared_lock("frozen"):
        fz = json.loads(FROZEN.read_text()) if FROZEN.exists() else {}
        if fam.FAMILY_ID in fz:
            raise SystemExit(f"{fam.FAMILY_ID} already frozen at {fz[fam.FAMILY_ID]['sha256']}")
        fz[fam.FAMILY_ID] = {"sha256": sha, "frozen_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
                             "calibration_pass_rate": rates.get("calibration"), "validation_pass_rate": rates.get("validation"), "note": note}
        REFS.mkdir(exist_ok=True)
        FROZEN.write_text(json.dumps(fz, indent=1))
    print(f"frozen {fam.FAMILY_ID} sha256={sha}")


def test(family: str) -> pd.DataFrame:
    fam = family_module(family)
    mod, sha = _load_ref(fam)
    fz = json.loads(FROZEN.read_text()) if FROZEN.exists() else {}
    if fam.FAMILY_ID not in fz:
        raise SystemExit("reference not frozen")
    if fz[fam.FAMILY_ID]["sha256"] != sha:
        raise SystemExit(f"refs/{fam.FAMILY_ID}.py changed after freeze -> family must be withdrawn, test not re-scored")
    if DERIV.exists() and (pd.read_parquet(DERIV).family == fam.FAMILY_ID).any():
        raise SystemExit("test run already done for this family; failed periods are dropped, never re-run")
    sp = pd.read_parquet(SPLITS)
    te = sp[(sp.family == fam.FAMILY_ID) & (sp.split == "test")]
    res = evaluate(fam, mod, list(te.accession))
    res["eligible"] = res["pass"]
    res["frozen_sha256"] = sha
    res["run_at"] = datetime.now(timezone.utc).isoformat(timespec="seconds")
    res["excerpt_derivable"] = False  # set by the excerpt pass (Step 9) only for full-pass periods
    with config.shared_lock():
        if DERIV.exists() and (pd.read_parquet(DERIV).family == fam.FAMILY_ID).any():
            raise SystemExit("test run already done for this family")
        config.write_atomic(pd.concat([pd.read_parquet(DERIV), res], ignore_index=True) if DERIV.exists() else res, DERIV)
    with config.shared_lock("frozen"):
        fz = json.loads(FROZEN.read_text())
        fz[fam.FAMILY_ID]["test_pass_rate"] = float(res["pass"].mean()) if len(res) else None
        fz[fam.FAMILY_ID]["test_run_at"] = res["run_at"].iloc[0] if len(res) else None
        FROZEN.write_text(json.dumps(fz, indent=1))
    print(f"test: {int(res['pass'].sum())}/{len(res)} eligible")
    return res


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("cmd", choices=["split", "dev", "freeze", "test"])
    ap.add_argument("--family", required=True)
    ap.add_argument("--note", default="")
    a = ap.parse_args()
    {"split": assign_splits, "dev": dev, "test": test}.get(a.cmd, lambda f: freeze(f, a.note))(a.family)
