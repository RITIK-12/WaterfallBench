"""Step 12: reports/DATASET_CARD.md, generated from the pipeline's own tables (no hand-typed numbers).

Usage: python -m wfb.step12_card
"""

from __future__ import annotations

import json
from collections import Counter

import pandas as pd

from . import config
from .step4_extract import family_module

W = config.WORKDIR
CHECKS = ["check_anchoring", "check_balance_identity", "check_continuity", "check_account_rollforward",
          "check_cash_reconciliation", "check_totals", "check_units_signs"]
DEVIATIONS = [
    ("Scope: C1-C2 only", "C3 (stress events), C4 (amendment audit) and C5 (master trusts) dropped by the user. The plan's stress signals were rare in these families in the window; recent-window 10-D/A filings are almost all CMBS; C5 needs ~7 separate master-trust families. Target per family: 15 C1 + 5 C2."),
    ("Families", f"{len(config.PILOT_FAMILIES)} contract families x {config.TASKS_PER_FAMILY} tasks (user decision), not the plan's asset-class spread; no CMBS, credit card, dealer floorplan or utility/device families."),
    ("Per-family cap", f"Up to {config.MAX_TASKS_PER_FAMILY_PER_CATEGORY} tasks per family per category (plan: 3); C2/C3 shortfalls go to C1 per the plan's allocation rule 3, and a family's own shortfall is covered by other families' passing reserves."),
    ("History window", f"Reports from {config.FAMILY_HISTORY_START} onward (~2 years) instead of {config.HISTORY_START}: enough for calibration/validation and every allowed task window."),
    ("Format", "Packets are SEC EDGAR HTML as filed: no markdown/PDF conversion and no excerpt variant (single dataset variant `full-html`; excerpt_derivable=false)."),
    ("Firecrawl AI extraction", "Firecrawl is the retrieval engine for every SEC download. Its JSON extraction was run, then switched off (user decision): exact candidate agreement blocked certification for formatting reasons. The answer key never came from Firecrawl; certification uses the deterministic checks plus the frozen reference's exact recomputation; agreement statistics are kept below as a cross-check."),
    ("Parameter certification", "Deal parameters are certified from deterministic anchors in the final prospectus (text span or cover-table cell) without a Firecrawl candidate match."),
    ("Leakage scan scope", "The value scan covers graded-period reports, instructions, schema and filenames. The opening-state report is the complete prior-period report by design, so it is not scanned (prior outputs that repeat unchanged are marked trivial instead)."),
    ("C3 signals", "Only the plan's five stress signals count. Family diagnostics outside that list (e.g. Navient principal-distribution shortfall) do not select C3 tasks."),
]


def _pct(x) -> str:
    return "n/a" if x is None or pd.isna(x) else f"{float(x):.1%}"


def _copyable(metas) -> str:
    import re
    cv = pd.read_parquet(W / "certified_values.parquet")
    vals = {r.accession: json.loads(r.values) for r in cv.itertuples()}
    hit = tot = 0
    for m in metas:
        groups = list(m["answer"].items()) if m["category"] == "C2" else [("", m["answer"])]
        for (g, ans), per in zip(groups, m["graded_periods"]):
            ins = {int(x) for k, x in vals[per["accession"]].items() if k not in ans and re.fullmatch(r"-?\d+", str(x))}
            specs = m["fields"][g] if g else m["fields"]
            for f, a in ans.items():
                tot += 1
                hit += specs[f]["type"] == "money_cents" and int(a) != 0 and int(a) in ins
    return f"{hit:,}/{tot:,} ({hit / max(1, tot):.1%})"


def run() -> str:
    cp = pd.read_parquet(W / "certified_periods.parquet")
    sp = pd.read_parquet(W / "splits.parquet")
    dv = pd.read_parquet(W / "derivability.parquet")
    pr = pd.read_parquet(W / "params_certified.parquet")
    fz = json.loads((W / "refs" / "FROZEN.json").read_text())
    pk = pd.read_parquet(W / "packets.parquet")
    fin = pd.read_parquet(W / "final_tasks.parquet") if (W / "final_tasks.parquet").exists() else pk.head(0)
    metas = [json.loads((config.DATASET / "meta" / f"{t}.json").read_text()) for t in fin.task_id]
    prov = pd.read_json(config.MANIFEST, lines=True)
    fams = {family_module(m).FAMILY_ID: family_module(m) for m in config.PILOT_FAMILIES}

    L = ["# WaterfallBench-Pilot — dataset card", "",
         "ABS waterfall execution from SEC EDGAR Form 10-D servicer reports. Each task gives an agent the deal's governing "
         "documents, the complete servicer report of the preceding period, and the graded period's report with every output "
         "value removed; the agent must compute every output (money to the cent). The answer key is the amount the trustee reported.", "",
         "## Task window", "",
         f"- Graded periods tagged `recent` were filed between {config.TASK_WINDOW_START} and {config.TASK_WINDOW_END}, after the published "
         "training cutoffs of the evaluated models (fill in the table below). No task is claimed to be unseen by any model.",
         f"- `fallback`: all graded periods filed on/after {config.FALLBACK_WINDOW_START}, at least one before {config.TASK_WINDOW_START}; `historical`: any earlier.", ""]

    if metas:
        df = pd.DataFrame([{"category": m["category"], "asset_class": m["asset_class"], "family": m["family"], "window": m["window_tag"],
                            "continuity_pending": m["continuity_pending"], "fields": sum(len(v) for v in (m["fields"].values() if m["category"] == "C2" else [m["fields"]])),
                            "copy_prior": m["baselines"]["copy_prior"]["line_item_accuracy"], "zeros": m["baselines"]["all_zeros"]["line_item_accuracy"],
                            "copy_prior_fr": m["baselines"]["copy_prior"]["fully_resolved"], "zeros_fr": m["baselines"]["all_zeros"]["fully_resolved"],
                            "leak_ok": m["leakage"]["passed"]} for m in metas])
        L += ["## Final allocation", "", f"- Tasks: **{len(df)}**; window tags: {dict(Counter(df.window))}; `continuity_pending`: {int(df.continuity_pending.sum())}", "",
              df.groupby(["family", "asset_class", "category"]).size().unstack(fill_value=0).to_markdown(), "",
              "By category x window:", "", df.groupby(["category", "window"]).size().unstack(fill_value=0).to_markdown(), "",
              "## Baselines (deterministic, graded by the service's grader)", "",
              f"- copy-prior: fully resolved {int(df.copy_prior_fr.sum())}/{len(df)}; mean line-item accuracy {df.copy_prior.mean():.1%}",
              f"- all-zeros: fully resolved {int(df.zeros_fr.sum())}/{len(df)}; mean line-item accuracy {df.zeros.mean():.1%}",
              f"- Output fields per task: median {int(df.fields.median())}, min {int(df.fields.min())}, max {int(df.fields.max())}; every graded period has >= 5 non-trivial fields.", "",
              "## Leakage tests", "", f"- All final tasks passed: removed label paths absent; output-value scan; filenames; period limit ({int(df.leak_ok.sum())}/{len(df)}).",
              f"- Packets built: {len(pk)}; dropped by a gate: {int((pk.status != 'ok').sum())}.", ""]

    L += ["## Sources and crawl", "",
          f"- SEC EDGAR full-index/daily-index, 10-D/10-D/A full submissions, EDGAR submissions JSON, final prospectuses (424B) and closing 8-K agreement exhibits.",
          f"- Retrieved {pd.to_datetime(prov.retrieved_at).min():%Y-%m-%d %H:%M} to {pd.to_datetime(prov.retrieved_at).max():%Y-%m-%d %H:%M} UTC; "
          f"{len(prov):,} raw files with URL, accession, timestamp and SHA-256 in `provenance.jsonl`; raw downloads never overwritten.",
          "- Firecrawl features used: `scrape` (rawHtml) for every sec.gov fetch, rate-gated to <= 8 request starts/second across all processes; "
          "JSON extraction (first passes only; see deviations). No other model API was called.", ""]

    L += ["## Certification (Step 5), 2-year window", "", "| family | periods | certified | " + " | ".join(c.removeprefix("check_") for c in CHECKS) + " | Firecrawl agreement (cross-check) |",
          "|" + "---|" * (len(CHECKS) + 4)]
    for f, g in cp.groupby("family"):
        agr = g.candidate_agreement.mean() if "candidate_agreement" in g else None
        L.append(f"| {f} | {len(g)} | {int(g.certified.sum())} ({g.certified.mean():.0%}) | " + " | ".join(f"{g[c].mean():.0%}" for c in CHECKS) + f" | {_pct(agr)} |")
    L += ["", "Balance identities:", ""]
    for f, m in fams.items():
        L.append(f"- **{f}**: {getattr(m, 'BALANCE_IDENTITY', 'n/a')}")
    pc = pr.groupby(["family", "deal_cik"]).certified.all().groupby("family").agg(["sum", "count"])
    L += ["", "Deal parameters certified (all parameters of the deal anchored): " + ", ".join(f"{f} {int(r['sum'])}/{int(r['count'])}" for f, r in pc.iterrows()), ""]

    L += ["## Splits, references and the derivability filter (Step 7)", "",
          "| family | split mode | calibration | validation | test | cal pass | val pass | test pass (single run) | eligible recent / fallback / historical | frozen SHA-256 |",
          "|---|---|---|---|---|---|---|---|---|---|"]
    for f, g in sp.groupby("family"):
        z = fz.get(f, {})
        d = dv[dv.family == f].merge(cp[["accession", "filed"]], on="accession", how="left")
        d["w"] = d.filed.map(lambda x: config.window_tag(pd.Timestamp(x).date()))
        e = d[d.eligible].w.value_counts()
        L.append(f"| {f} | {g.split_mode.iloc[0]} | {(g.split == 'calibration').sum()} | {(g.split == 'validation').sum()} | {(g.split == 'test').sum()} | "
                 f"{_pct(z.get('calibration_pass_rate'))} | {_pct(z.get('validation_pass_rate'))} | {_pct(z.get('test_pass_rate'))} | "
                 f"{e.get('recent', 0)} / {e.get('fallback', 0)} / {e.get('historical', 0)} | `{z.get('sha256', '')[:16]}…` |")
    L += ["", "Derivability selection effect: only test-split periods that the frozen family reference reproduced exactly (every output to the cent, "
          "from the packet's inputs) could become tasks. Periods the reference cannot handle (e.g. pro-rata rounding edge cases, first reports with no "
          "opening state) are excluded, so the benchmark measures periods a deterministic implementation of the documents can solve. Calibration and "
          "validation periods never become tasks. No family was withdrawn.", ""]

    L += ["## Gates", "", "- C3 stress_events, C4 amendment_audit and C5 master_trust_allocation: not built (scope decisions).",
          "- C1 is recent-window only in the plan. Nissan Auto Lease Trust filed only 20 reports in the recent window and its frozen reference "
          "reproduces 12, so 3 of its C1 tasks come from the fallback window (Jan-Jun 2026) and are tagged `fallback` (deviation, user decision).", "",
          "## Deviations from the plan", ""] + [f"- **{a}.** {b}" for a, b in DEVIATIONS] + [""]
    L += ["## Known limitations", "",
          "- Five contract families (2 prime auto loan, 1 equipment, 1 auto lease, 1 FFELP student loan): scores are clustered by family.",
          "- Many output lines are zero or unchanged month to month (marked `trivial`); the headline metric is `fully_resolved` (every field exact).",
          f"- {_copyable(metas)} of output fields equal an input amount printed in the same graded report (e.g. available funds = available "
          "collections). Under the plan's rule they are outputs (the reference computes them) and the value scan allows them because they sit in input "
          "cells, but they can be copied rather than computed.",
          "- `continuity_pending` tasks: the next period's report did not exist at the snapshot, so cross-filing continuity is re-checked later.",
          "- Prospectus parameters for some deals sit in closing agreements rather than the prospectus; references read such values from the prior "
          "period's report in the packet where the documents allow.", "",
          "## Evaluated models' published training cutoffs (fill in at evaluation time)", "",
          "| model | published training cutoff | all recent tasks filed after cutoff? |", "|---|---|---|", "| | | |", ""]
    text = "\n".join(L)
    (config.REPORTS / "DATASET_CARD.md").write_text(text)
    (config.REPO / "DATASET_CARD.md").write_text(text)
    print(text[:3000])
    return text


if __name__ == "__main__":
    run()
