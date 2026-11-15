"""Step 8: mining and task selection (C1-C3) per family.

Pools draw only from test-split periods. `--mode preview` selects from every certified test period (before the
family's single test run, so the selection is fixed up front); `--mode final` selects only from periods the frozen
reference reproduced exactly (derivability.parquet). Selection is deterministic:

  * targets: config.TASKS_PER_FAMILY split over config.CATEGORIES as evenly as possible (remainder to C1 first),
    each capped at config.MAX_TASKS_PER_FAMILY_PER_CATEGORY; C2/C3 shortfalls go to C1 (plan allocation rule 3);
  * C3 first (stress signal present; recent, then fallback), then C1 (recent only, the scarcest pool; the latest
    period of each deal first), then C2 (runs of 4 consecutive monthly periods in one deal from periods not yet used;
    recent, then fallback, then historical; graded periods 1-3 need a passed continuity check);
  * deals are taken round-robin so tasks spread across deals; within a deal the most recently filed first;
  * no graded period is used by two tasks of the family;
  * reserves: ceil(RESERVE_FRACTION x TASKS_PER_FAMILY) extra tasks from the leftovers (C1, C2, C3 order).

Usage: python -m wfb.step8_select --family carmax --mode preview|final
"""

from __future__ import annotations

import argparse
import json
import math
import re
from collections import defaultdict

import pandas as pd

from . import config
from .step4_extract import family_module
from .step7_refs import DERIV, SPLITS, _kinds, _params, _typed

SELECTION = config.WORKDIR / "selection.parquet"
CAT_NAMES = {"C1": "monthly_distribution", "C2": "rollforward_4p", "C3": "stress_events"}


# C3 counts only the plan's five signals (Step 8.3). Family modules may report other diagnostics (e.g. a principal
# distribution shortfall); those are not stress events for selection.
PLAN_SIGNAL_PATTERNS = ("trigger_status_change", "reserve_withdrawal", "interest_shortfall", "principal_payment_mode_change",
                        "cleanup_threshold", "optional_purchase")


def plan_signal(name: str) -> bool:
    return not name.startswith("error:") and any(k in name for k in PLAN_SIGNAL_PATTERNS)


def _months(a: str, b: str) -> int:
    return (int(b[:4]) - int(a[:4])) * 12 + int(b[4:6]) - int(a[4:6])


def window_of(filed: list) -> str:
    ds = [pd.Timestamp(d).date() for d in filed]
    if all(config.TASK_WINDOW_START <= d <= config.TASK_WINDOW_END for d in ds):
        return "recent"
    if all(d >= config.FALLBACK_WINDOW_START for d in ds):
        return "fallback"
    return "historical"


def series_of(deal_name: str) -> str:
    m = re.search(r"(\d{4}(?:-[A-Za-z0-9]+)?)\s*$", deal_name or "")
    return (m.group(1) if m else "x").lower()


def targets(n: int) -> dict[str, int]:
    if getattr(config, "CATEGORY_TARGETS", None):
        return {c: int(config.CATEGORY_TARGETS.get(c, 0)) for c in config.CATEGORIES}
    cats = list(config.CATEGORIES)
    base, rem = divmod(n, len(cats))
    t = {c: base + (1 if i < rem else 0) for i, c in enumerate(cats)}
    return {c: min(v, config.MAX_TASKS_PER_FAMILY_PER_CATEGORY) for c, v in t.items()}


def period_table(family: str, mode: str) -> pd.DataFrame:
    """One row per candidate graded period (original 10-D, test split) with window tag, continuity and stress signals."""
    fam = family_module(family)
    cp = pd.read_parquet(config.WORKDIR / "certified_periods.parquet")
    cp = cp[cp.family == fam.FAMILY_ID]
    sp = pd.read_parquet(SPLITS)
    sp = sp[(sp.family == fam.FAMILY_ID) & (sp.split == "test")]
    pool = set(sp.accession)
    if mode == "final":
        dv = pd.read_parquet(DERIV)
        pool &= set(dv[(dv.family == fam.FAMILY_ID) & dv.eligible].accession)
    per = cp[cp.accession.isin(pool) & (cp.form == "10-D") & cp.certified].copy()
    per["window"] = per.filed.map(lambda d: window_of([d]))
    # opening state: the immediately preceding ORIGINAL 10-D of the same deal (any split; it is shown unsanitised)
    orig = cp[cp.form == "10-D"].sort_values("period_of_report")
    prev_of = {}
    for _, g in orig.groupby("deal_cik"):
        rows = list(g.itertuples())
        for a, b in zip(rows, rows[1:]):
            if _months(a.period_of_report, b.period_of_report) == 1:
                prev_of[b.accession] = a.accession
    per["opening_accession"] = per.accession.map(prev_of)
    per = per[per.opening_accession.notna()]
    cv = pd.read_parquet(config.WORKDIR / "certified_values.parquet")
    cv = cv[cv.accession.isin(set(per.accession) | set(per.opening_accession))]
    vals = {r.accession: json.loads(r.values) for r in cv.itertuples()}
    sig = []
    for r in per.itertuples():
        kinds = _kinds(fam, int(r.deal_cik))
        s = []
        if hasattr(fam, "stress_signals") and r.accession in vals and r.opening_accession in vals:
            try:
                s = list(fam.stress_signals(_typed(vals[r.accession], kinds), _typed(vals[r.opening_accession], kinds),
                                            _params(fam, int(r.deal_cik))) or [])
            except Exception as e:  # a broken detector never invents a stress event
                s = [f"error:{type(e).__name__}"]
        sig.append(json.dumps([x for x in s if plan_signal(x)]))
    per["stress_signals"] = sig
    return per.sort_values(["deal_cik", "period_of_report"]).reset_index(drop=True)


def _round_robin(cands: list[tuple[int, str, object]], k: int, used: set[str], key=lambda x: [x]) -> list:
    """cands: (deal, sort_key_desc, item). Take up to k items cycling over deals (best deal first), skipping items
    whose graded accessions overlap `used`."""
    by_deal: dict[int, list] = defaultdict(list)
    for d, s, it in sorted(cands, key=lambda x: x[1], reverse=True):
        by_deal[d].append(it)
    order = sorted(by_deal, key=lambda d: max(str(s) for dd, s, _ in cands if dd == d), reverse=True)
    out = []
    while len(out) < k and any(by_deal[d] for d in order):
        for d in order:
            while by_deal[d]:
                it = by_deal[d].pop(0)
                accs = key(it)
                if used.isdisjoint(accs):
                    out.append(it)
                    used.update(accs)
                    break
            if len(out) >= k:
                break
    return out


def select(family: str, mode: str = "preview") -> pd.DataFrame:
    fam = family_module(family)
    per = period_table(family, mode)
    deals = pd.read_parquet(config.WORKDIR / "deals.parquet").set_index("deal_cik")
    tg = targets(config.TASKS_PER_FAMILY)
    n_res = math.ceil(config.RESERVE_FRACTION * config.TASKS_PER_FAMILY)
    used: set[str] = set()
    picks: list[dict] = []
    byacc = per.set_index("accession")

    def c1_cands(window="recent"):
        r = per[per.window == window]
        return [(int(x.deal_cik), str(x.filed), x.accession) for x in r.itertuples()]

    def c3_cands(window):
        r = per[(per.window == window) & (per.stress_signals != "[]")]
        return [(int(x.deal_cik), str(x.filed), x.accession) for x in r.itertuples()]

    cont = byacc.continuity.to_dict()

    def c2_runs(window):
        runs = []
        for d, g in per.groupby("deal_cik"):
            rows = list(g.sort_values("period_of_report").itertuples())
            for i in range(len(rows) - 3):
                w = rows[i:i + 4]
                if all(_months(a.period_of_report, b.period_of_report) == 1 for a, b in zip(w, w[1:])) \
                        and all(cont.get(x.accession) == "pass" for x in w[:3]) \
                        and window_of([x.filed for x in w]) == window:
                    runs.append((int(d), str(w[-1].filed), tuple(x.accession for x in w)))
        return runs

    def add(cat, items, role):
        for it in items:
            accs = list(it) if isinstance(it, tuple) else [it]
            first = byacc.loc[accs[0]]
            picks.append({"family": fam.FAMILY_ID, "module": family, "category": cat, "role": role,
                          "deal_cik": int(first.deal_cik), "graded_accessions": json.dumps(accs),
                          "opening_accession": first.opening_accession,
                          "periods": json.dumps([byacc.loc[a].period_of_report for a in accs]),
                          "filed": json.dumps([str(byacc.loc[a].filed) for a in accs]),
                          "window_tag": window_of([byacc.loc[a].filed for a in accs]),
                          "stress_signals": json.dumps(sorted({s for a in accs for s in json.loads(byacc.loc[a].stress_signals)}))})

    got = {}
    # C3: recent, then fallback
    c3 = _round_robin(c3_cands("recent"), tg.get("C3", 0), used)
    c3 += _round_robin(c3_cands("fallback"), tg.get("C3", 0) - len(c3), used)
    add("C3", c3, "task"); got["C3"] = len(c3)
    # C1 next: recent only, and the scarcest pool (it may never fall back to older windows); C3 shortfall goes to C1
    c1 = _round_robin(c1_cands(), tg.get("C1", 0) + (tg.get("C3", 0) - got["C3"]), used)
    if getattr(config, "C1_FALLBACK_IF_SHORT", False):   # deviation: plan rule 4 keeps C1 recent-only
        c1 += _round_robin(c1_cands("fallback"), tg.get("C1", 0) + (tg.get("C3", 0) - got["C3"]) - len(c1), used)
    # C2: recent, then fallback, then historical, from periods C1/C3 did not use
    c2: list = []
    for w in ("recent", "fallback", "historical"):
        c2 += _round_robin(c2_runs(w), tg.get("C2", 0) - len(c2), used, key=lambda t: list(t))
    add("C2", c2, "task"); got["C2"] = len(c2)
    # C2 shortfall goes to C1 as well (plan allocation rule 3)
    c1 += _round_robin(c1_cands(), tg.get("C2", 0) - got["C2"], used)
    add("C1", c1, "task"); got["C1"] = len(c1)
    # reserves
    res_c1 = _round_robin(c1_cands(), n_res, used)
    add("C1", res_c1, "reserve")
    left = n_res - len(res_c1)
    if left > 0:
        r2: list = []
        for w in ("recent", "fallback", "historical"):
            r2 += _round_robin(c2_runs(w), left - len(r2), used, key=lambda t: list(t))
        add("C2", r2, "reserve")
        left -= len(r2)
    if left > 0:
        r3 = _round_robin(c3_cands("recent") + c3_cands("fallback"), left, used)
        add("C3", r3, "reserve")

    out = pd.DataFrame(picks)
    if len(out):
        names = out.deal_cik.map(lambda d: deals.loc[d, "deal_name"] if d in deals.index else "")
        out["deal_name"] = names
        out["task_id"] = [f"{c.lower()}-{family}-{series_of(n)}-{json.loads(p)[0][:4]}-{json.loads(p)[0][4:6]}"
                          for c, n, p in zip(out.category, names, out.periods)]
        out["selection_mode"] = mode
        out["targets"] = json.dumps(tg)
    config.merge_rows(SELECTION, out, "family", [fam.FAMILY_ID]) if len(out) else None
    pools = {"C1_recent": len(c1_cands()), "C2_runs": {w: len(c2_runs(w)) for w in ("recent", "fallback", "historical")},
             "C3": {w: len(c3_cands(w)) for w in ("recent", "fallback")}}
    lines = [f"## {fam.FAMILY_ID}", "", f"- Mode: {mode}; candidate graded periods: {len(per)}; pools: {json.dumps(pools)}",
             f"- Targets {json.dumps(tg)}; selected tasks: " + json.dumps(got) + f"; reserves: {int((out.role == 'reserve').sum()) if len(out) else 0}",
             f"- Deals used: {out[out.role == 'task'].deal_cik.nunique() if len(out) else 0}", ""]
    if len(out):
        lines += [out[["task_id", "category", "role", "window_tag", "periods", "stress_signals"]].to_markdown(index=False), ""]
    config.update_report("step_8.md", fam.FAMILY_ID, "\n".join(lines), "# Step 8 — Mining and task selection (C1-C3)")
    print("\n".join(lines[:4]))
    return out


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--family", required=True)
    ap.add_argument("--mode", choices=["preview", "final"], default="preview")
    a = ap.parse_args()
    select(a.family, a.mode)
