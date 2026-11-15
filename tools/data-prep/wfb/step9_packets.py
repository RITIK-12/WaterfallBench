"""Steps 9-10: task packets (EDGAR HTML as filed), output removal, leakage tests and baselines.

For every selected task (selection.parquet):
  docs/full/      governing documents as filed (final prospectus + closing 8-K agreement exhibits), HTML
  reports/        period_<YYYY-MM>_opening_state.html  - the complete original report of the preceding period
                  period_<YYYY-MM>_graded.html         - each graded period's original report with outputs removed
  instructions.md, answer_schema.json
  ../../meta/<task_id>.json  (PRIVATE: answer key, cell locations, checks, provenance, baselines)

Output removal (one rule per family, applied to every report): a certified field is an INPUT only if the family's
frozen reference consumes it (refs/<family>.py INPUTS); every other certified field (outputs and IGNORED derived
fields) has its cell blanked by the exact (table,row,column) location the certifier read; rows left with no value are
deleted with their labels. Remaining text equal to any output value (outside input cells) is removed as a derived
value. C2: graded periods 2-4 also lose beginning balances/carryovers (family continuity pairs) and any input whose
amount equals an earlier graded output.

Leakage tests (a failing task is dropped, never patched by hand): removed label paths absent from graded reports;
value scan of graded reports, instructions and schema (outputs allowed only inside input cells); filenames; period
limit. Baselines (copy-prior, all-zeros) are graded with the benchmark service's own grader. >= 5 non-trivial fields
per graded period are required.

Usage: python -m wfb.step9_packets --family carmax [--roles task,reserve]
       python -m wfb.step9_packets --finalize        # pick the final tasks per family into tasks/ + meta/
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import shutil
import sys
from decimal import Decimal
from pathlib import Path

import pandas as pd
from lxml import etree
from lxml import html as lxml_html

from . import config, fc, grid, labels
from .step4_extract import family_module, parser
from .step7_refs import FROZEN, _kinds, _load_ref, _typed
from .step8_select import CAT_NAMES, SELECTION

BUILD = config.WORKDIR / "build"            # every built packet (tasks + reserves), status in packets.parquet
FINAL_TASKS = config.DATASET / "tasks"
FINAL_META = config.DATASET / "meta"       # PRIVATE answer keys: git-ignored, never published
PACKETS = config.WORKDIR / "packets.parquet"
SERVICE_SRC = config.REPO / "service" / "src"
MIN_NONTRIVIAL = 5
TYPE_OF = {"money": "money_cents", "int": "int", "pct": "decimal", "decimal": "decimal", "status": "status"}
STATUS_PAIRS = {"yes": "no", "pass": "fail", "passed": "failed", "true": "false", "met": "not met",
                "in effect": "not in effect", "occurred": "not occurred", "breached": "not breached"}


def _grader():
    if str(SERVICE_SRC) not in sys.path:
        sys.path.insert(0, str(SERVICE_SRC))
    from waterfallbench_benchmark_service import grading
    return grading


# ----------------------------------------------------------------------------------------------- HTML editing

def _rows(doc):
    tables = doc.xpath("//table")
    cache = {}

    def row(t, r):
        if t not in cache:
            cache[t] = grid._grid_rows(tables[t])
        return cache[t][r]
    return row


def _td(rowfn, c: grid.Cell):
    row = rowfn(c.table, c.row)
    for i, (a, b, t, td) in enumerate(row):
        if a == c.col:
            return td, row, i
    return None, row, -1


def _blank(td) -> None:
    for ch in list(td):
        td.remove(ch)
    td.text = None


def _money_strings(cents: int) -> list[str]:
    d = Decimal(abs(int(cents))) / 100
    return [f"{d:,.2f}", f"{d:.2f}"]


def _thousands(cents: int) -> str | None:
    d = Decimal(abs(int(cents))) / 100
    return f"{(d / 1000):,.0f}" if abs(cents) >= 100_000_000 else None


def _patterns(outputs: dict[str, tuple[str, object, str]]) -> list[tuple[str, re.Pattern]]:
    """outputs: field -> (kind, value, printed text). Patterns that identify an output value in text."""
    pats = []
    for f, (kind, v, printed) in outputs.items():
        strings = []
        strings = []
        if kind == "money" and v is not None and abs(int(v)) >= 100:
            strings = _money_strings(int(v))
            th = _thousands(int(v))
            if th:  # the same amount in thousands only counts when printed as a dollar amount
                pats.append((f, re.compile(r"\$\s*" + re.escape(th) + r"(?![\d]|,\d|\.\d)")))
        elif kind in ("pct", "decimal", "int") and printed:
            p = re.sub(r"[$%()\s]", "", printed)
            try:
                nz = Decimal(re.sub(r"[^\d.\-]", "", p) or "0") != 0
            except Exception:
                nz = False
            if len(re.sub(r"\D", "", p)) >= 4 and nz:
                strings = [p]
        for s in dict.fromkeys(strings):
            pats.append((f, re.compile(r"(?<![\d,.])" + re.escape(s) + r"(?![\d]|,\d|\.\d)")))
    return pats


def _inside(el, keep: set) -> bool:
    if el in keep:
        return True
    return any(a in keep for a in el.iterancestors())


def sanitize(src: str, fam, remove: list[grid.Cell], keep: list[grid.Cell], outputs: dict) -> tuple[str, list[str]]:
    doc = lxml_html.fromstring(src)
    rowfn = _rows(doc)
    keep_tds = {td for td in (_td(rowfn, c)[0] for c in keep) if td is not None}
    touched = {}
    for c in remove:
        td, row, i = _td(rowfn, c)
        if td is None or td in keep_tds:
            continue
        _blank(td)
        for j, glue in ((i - 1, {"$", "(", "$(", "($"}), (i + 1, {"%", ")", "%)"})):  # currency/percent glue cells
            if 0 <= j < len(row) and row[j][2] in glue and row[j][3] not in keep_tds:
                _blank(row[j][3])
        tr = td.getparent()
        while tr is not None and tr.tag != "tr":
            tr = tr.getparent()
        if tr is not None:
            touched[tr] = row
    removed_labels = []
    for tr, row in touched.items():
        texts = [grid.clean(td.text_content()) for (_, _, _, td) in row]
        has_value = any(t and t not in grid.GLUE and grid.parse_value(t) and not grid.LINE_NO.match(t + ".") for t in texts[1:])
        if not has_value and tr.getparent() is not None:
            removed_labels.append(" ".join(t for t in texts if t))
            tr.getparent().remove(tr)
    # comments and any remaining text equal to an output value outside input cells are derived values: remove
    for cm in doc.xpath("//comment()"):
        par = cm.getparent()
        if par is not None:
            if cm.tail:
                prev = cm.getprevious()
                if prev is not None:
                    prev.tail = (prev.tail or "") + cm.tail
                else:
                    par.text = (par.text or "") + cm.tail
            par.remove(cm)
    pats = _patterns(outputs)
    for el in list(doc.iter()):
        if not isinstance(el.tag, str) or el.tag in ("script", "style"):
            continue
        if el.text and not _inside(el, keep_tds) and any(p.search(el.text) for _, p in pats):
            cell = el if el.tag in ("td", "th") else _cell_of(el)
            if cell is not None:
                _blank(cell)          # a table cell holding an output value is a derived value: blank the cell
            else:
                for _, p in pats:
                    el.text = p.sub("", el.text)
        par = el.getparent()
        if el.tail and par is not None and not _inside(par, keep_tds) and any(p.search(el.tail) for _, p in pats):
            cell = par if par.tag in ("td", "th") else _cell_of(par)
            if cell is not None:
                _blank(cell)
            else:
                for _, p in pats:
                    el.tail = p.sub("", el.tail)
    for m in doc.xpath("//meta"):
        m.getparent().remove(m)
    out = lxml_html.tostring(doc.getroottree(), encoding="unicode", method="html", doctype="<!DOCTYPE html>")
    return out, removed_labels


def _cell_of(el):
    for a in el.iterancestors():
        if a.tag in ("td", "th"):
            return a
        if a.tag == "table":
            return None
    return None


def leakage_hits(src: str, outputs: dict, input_cents: set[int], input_printed: set[str]) -> list[str]:
    """Independent scan of the SERIALISED graded report: every text node and attribute. An occurrence of an output
    value is allowed only when that value is also the value of an input field of the period (inputs stay visible)."""
    doc = lxml_html.fromstring(src)
    hits = []
    pats = _patterns(outputs)
    texts = []
    for el in doc.iter():
        if isinstance(el.tag, str):
            texts += [el.text or "", el.tail or ""] + list(el.attrib.values())
        else:
            texts += [str(el)]
    for txt in texts:
        if not txt:
            continue
        for f, p in pats:
            m = p.search(txt)
            if not m:
                continue
            kind, v, printed = outputs[f]
            if kind == "money" and v is not None and int(v) in input_cents:
                continue
            if printed and re.sub(r"[$%()\s]", "", printed) in input_printed:
                continue
            hits.append(f"{f}: {txt.strip()[:60]!r}")
    return hits


# ----------------------------------------------------------------------------------------------- packet build

class Ctx:
    def __init__(self, family: str):
        self.fam = family_module(family)
        self.module = family
        self.ref, self.sha = _load_ref(self.fam)
        fz = json.loads(FROZEN.read_text()) if FROZEN.exists() else {}
        self.frozen = fz.get(self.fam.FAMILY_ID, {})
        cp = pd.read_parquet(config.WORKDIR / "certified_periods.parquet")
        self.cp = cp[cp.family == self.fam.FAMILY_ID].set_index("accession")
        self.reps = pd.read_parquet(config.WORKDIR / f"reports_{self.fam.FAMILY_ID}.parquet").set_index("accession")
        cv = pd.read_parquet(config.WORKDIR / "certified_values.parquet")
        cv = cv[cv.family == self.fam.FAMILY_ID]
        self.vals = {r.accession: json.loads(r.values) for r in cv.itertuples()}
        self.locs = {r.accession: r.cell_locations for r in cv.itertuples()}
        self.man = pd.read_parquet(config.WORKDIR / "docs_manifest.parquet")
        self.deals = pd.read_parquet(config.WORKDIR / "deals.parquet").set_index("deal_cik")
        sp = pd.read_parquet(config.WORKDIR / "splits.parquet")
        self.split_mode = (sp[sp.family == self.fam.FAMILY_ID].split_mode.iloc[0] if (sp.family == self.fam.FAMILY_ID).any() else None)
        self.rx_in = [re.compile(p) for p in self.ref.INPUTS]
        self.rx_ign = [re.compile(p) for p in getattr(self.ref, "IGNORED", [])]
        # status vocabularies across the family (enum = observed values plus their opposites)
        self.status_vals: dict[str, set] = {}

    def lm(self, acc: str) -> dict:
        r = self.reps.loc[acc]
        return json.loads((labels.LABEL_MAPS / self.fam.FAMILY_ID / r.report_format / f"{int(r.deal_cik)}.json").read_text())

    def html(self, acc: str) -> str:
        return fc.read_raw(config.WORKDIR / self.reps.loc[acc, "raw_path"])

    def is_input(self, f: str) -> bool:
        return any(p.search(f) for p in self.rx_in)

    def is_ignored(self, f: str) -> bool:
        return any(p.search(f) for p in self.rx_ign)


def _enum(ctx: Ctx, field: str, observed: str) -> list[str]:
    seen = set()
    for v in ctx.vals.values():
        if field in v:
            seen.add(v[field])
    seen.add(observed)
    out = set(seen)
    for s in seen:
        low = s.lower()
        for a, b in list(STATUS_PAIRS.items()) + [(b, a) for a, b in STATUS_PAIRS.items()]:
            if low == a:
                out.add(b.upper() if s.isupper() else (b.title() if s[:1].isupper() else b))
    return sorted(out)


def _governing_docs(ctx: Ctx, deal: int) -> list[pd.Series]:
    m = ctx.man[(ctx.man.deal_cik == deal) & ctx.man.filename.str.lower().str.endswith((".htm", ".html"))]
    from .params import prospectus_for
    pr = prospectus_for(int(deal))      # the FINAL prospectus (same choice as parameter anchoring)
    docs = [pr] if pr is not None else []
    ek = m[(m.form == "8-K") & m.doc_type.str.upper().str.match(r"^EX-(4|10|99)\b")]
    if len(ek):  # closing agreements: the latest closing 8-K's copy of each exhibit (earlier 8-Ks repeat them)
        # governing filings carry no filed date in the manifest; within one filer agent the accession sequence
        # increases with filing order, so the highest accession is the latest (executed) copy
        ek = ek.assign(_ord=ek.accession.str.split("-").map(lambda x: (x[1], x[2]) if len(x) == 3 else ("", ""))) \
               .sort_values("_ord").drop_duplicates("doc_type", keep="last").drop(columns="_ord")
    docs += [r for _, r in ek.iterrows()]
    return docs


def _clean_label(path: str) -> str:
    parts = [re.sub(r"[\u200b\u00a0\s]+", " ", x).strip(" :") for x in (path or "").split(" > ")]
    return " > ".join(x for x in parts if x)


def _date(per: str) -> str:
    return f"{per[:4]}-{per[4:6]}-{per[6:8]}" if per and len(per) == 8 else str(per)


def _month(per: str) -> str:
    return f"{per[:4]}-{per[4:6]}"


def build_task(ctx: Ctx, sel) -> dict:
    fam = ctx.fam
    task_id = sel.task_id
    cat = sel.category
    deal = int(sel.deal_cik)
    graded = json.loads(sel.graded_accessions)
    opening = sel.opening_accession
    res = {"task_id": task_id, "family": fam.FAMILY_ID, "category": cat, "role": sel.role, "status": "ok", "reason": None}
    tdir = BUILD / "tasks" / task_id
    if tdir.exists():
        shutil.rmtree(tdir)
    (tdir / "docs" / "full").mkdir(parents=True)
    (tdir / "reports").mkdir(parents=True)
    provenance = []

    gov = _governing_docs(ctx, deal)
    if not gov:
        return {**res, "status": "dropped", "reason": "no governing documents"}
    for r in gov:
        kind = ("prospectus" if str(r.doc_type).upper().startswith("424B")
                else f"closing-8k-agreement_{str(r.doc_type).lower().replace('.', '-')}")
        name = f"{kind}__{Path(r.filename).stem}.html"
        (tdir / "docs" / "full" / name).write_text(fc.read_raw(config.WORKDIR / r.raw_path), encoding="utf-8")
        provenance.append({"file": f"docs/full/{name}", "source_url": r.source_url, "accession": r.accession, "sha256": r.sha256})

    kinds = _kinds(fam, deal)
    open_vals = _typed(ctx.vals[opening], kinds)
    op = ctx.cp.loc[opening]
    oname = f"period_{_month(op.period_of_report)}_opening_state.html"
    (tdir / "reports" / oname).write_text(ctx.html(opening), encoding="utf-8")
    provenance.append({"file": f"reports/{oname}", "source_url": ctx.reps.loc[opening, "source_url"], "accession": opening,
                       "sha256": hashlib.sha256(ctx.html(opening).encode()).hexdigest()})

    fields_by_period, answer_by_period, prev_out_cents = {}, {}, set()
    period_info, leaks = [], []
    prev_vals_raw = ctx.vals[opening]
    for i, acc in enumerate(graded):
        lm = ctx.lm(acc)
        src = ctx.html(acc)
        g = parser(fam)(src)
        raw = ctx.vals[acc]
        cur = _typed(raw, kinds)
        inputs = {k for k in raw if ctx.is_input(k)}
        outputs = [k for k in raw if k not in inputs and not ctx.is_ignored(k)]
        removed = set(raw) - inputs
        if cat == "C2" and i > 0:
            begins = {b for a, b in fam.continuity_pairs(prev_vals_raw)} & inputs
            carry = {k for k in inputs if kinds.get(k, "money") == "money" and cur.get(k) and abs(int(cur[k])) >= 100
                     and int(cur[k]) in prev_out_cents}
            removed |= begins | carry
        fs_by = {f["field"]: f for f in lm["fields"]}
        rm_cells, keep_cells, outvals = [], [], {}
        printed = {}
        for f in raw:
            fs = fs_by.get(f)
            if fs is None:
                continue
            cells = labels.locate(g, fs)
            if f in removed:
                rm_cells += cells
                if f in outputs or (cat == "C2" and i > 0):
                    outvals[f] = (kinds.get(f, "money"), cur.get(f), cells[0].text if cells else "")
                printed[f] = _clean_label(cells[0].path) if cells else ""
            else:
                keep_cells += cells
        # values of earlier graded periods must not leak into later ones either
        for f, (k, v, t) in list(outvals.items()):
            if k == "money" and v is not None:
                prev_out_cents.add(int(v))
        clean_html, removed_labels = sanitize(src, fam, rm_cells, keep_cells, outvals)
        kept = set(raw) - removed
        in_cents = {int(cur[k]) for k in kept if kinds.get(k, "money") == "money" and cur.get(k) is not None}
        in_printed = {re.sub(r"[$%()\s]", "", c.text) for c in keep_cells}
        hits = leakage_hits(clean_html, outvals, in_cents, in_printed)
        g2 = parser(fam)(clean_html)
        key = lambda f: (fs_by[f]["section"], fs_by[f]["parent"], fs_by[f]["label"], fs_by[f]["column"])
        rm_keys = {key(f) for f in removed if f in fs_by} - {key(f) for f in kept if f in fs_by}
        label_hits = [c.path for c in g2.cells if labels.cell_key(c) in rm_keys]
        per = ctx.cp.loc[acc]
        gname = f"period_{_month(per.period_of_report)}_graded.html"
        (tdir / "reports" / gname).write_text(clean_html, encoding="utf-8")
        provenance.append({"file": f"reports/{gname}", "source_url": ctx.reps.loc[acc, "source_url"], "accession": acc,
                           "derived": "original report with output values removed (Step 9)"})
        leaks += [f"{gname}: {h}" for h in hits] + [f"{gname}: removed label path present: {h}" for h in label_hits]
        # answer + field specs
        fspecs, ans = {}, {}
        for f in sorted(outputs):
            kd = kinds.get(f, "money")
            t = TYPE_OF.get(kd, "money_cents")
            v = cur[f]
            ans[f] = int(v) if t in ("money_cents", "int") else (str(v) if t == "decimal" else str(v))
            ov = open_vals.get(f)
            trivial = (t in ("money_cents", "int", "decimal") and Decimal(str(v)) == 0) or (ov is not None and str(ov) == str(v))
            spec = {"type": t, "trivial": bool(trivial), "label": printed.get(f, "")}
            if t == "status":
                spec["enum"] = _enum(ctx, f, str(v))
            fspecs[f] = spec
        key = f"period_{i + 1}" if cat == "C2" else ""
        fields_by_period[key] = fspecs
        answer_by_period[key] = ans
        n_nt = sum(1 for s in fspecs.values() if not s["trivial"])
        period_info.append({"accession": acc, "period_of_report": per.period_of_report, "filed": str(per.filed),
                            "report": gname, "n_outputs": len(fspecs), "n_nontrivial": n_nt,
                            "continuity": per.continuity, "removed_rows": len(removed_labels),
                            "distribution_date": json.loads(per.period_meta).get("distribution_date") if isinstance(per.period_meta, str) else None})
        prev_vals_raw = raw
        if n_nt < MIN_NONTRIVIAL:
            res.update(status="dropped", reason=f"period {per.period_of_report}: only {n_nt} non-trivial fields")

    # instructions + schema
    deal_name = ctx.deals.loc[deal, "deal_name"] if deal in ctx.deals.index else str(deal)
    asset = ctx.deals.loc[deal, "asset_class"] if deal in ctx.deals.index else "unknown"
    fields_meta = fields_by_period[""] if cat != "C2" else fields_by_period
    answer = answer_by_period[""] if cat != "C2" else answer_by_period
    instr = _instructions(task_id, cat, deal_name, period_info, oname, fields_by_period)
    schema = _schema(cat, fields_by_period)
    (tdir / "instructions.md").write_text(instr, encoding="utf-8")
    (tdir / "answer_schema.json").write_text(json.dumps(schema, indent=1), encoding="utf-8")
    # leakage in instructions / schema / filenames
    allout = {}
    for k, fsp in fields_by_period.items():
        for f in fsp:
            v = answer_by_period[k][f]
            allout[f"{k}.{f}"] = ("money" if fsp[f]["type"] == "money_cents" else "decimal", v if fsp[f]["type"] == "money_cents" else None, "")
    for f, p in _patterns(allout):
        if p.search(instr) or p.search(json.dumps(schema)):
            leaks.append(f"instructions/schema: {f}")
        for path in tdir.rglob("*"):
            if p.search(path.name):
                leaks.append(f"filename {path.name}: {f}")
    # period limit: nothing after the last graded period, no 10-D/A for graded periods
    last = max(pi["period_of_report"] for pi in period_info)
    if op.period_of_report >= min(pi["period_of_report"] for pi in period_info) or any(ctx.cp.loc[a].form != "10-D" for a in graded + [opening]):
        leaks.append("period limit / report version violated")
    if leaks:
        res.update(status="dropped", reason="leakage: " + "; ".join(leaks[:5]))

    meta = {
        "task_id": task_id, "category": cat, "category_name": CAT_NAMES[cat], "excerpt_derivable": False,
        "asset_class": asset, "family": fam.FAMILY_ID, "deal": deal_name, "deal_cik": deal,
        "window_tag": sel.window_tag, "continuity_pending": any(pi["continuity"] == "continuity_pending" for pi in period_info),
        "fields": fields_meta, "answer": answer,
        "graded_periods": period_info, "opening_state": {"accession": opening, "period_of_report": op.period_of_report, "report": oname},
        "stress_signals": json.loads(sel.stress_signals), "split": "test", "split_mode": ctx.split_mode,
        "closing_anchor": "not_applicable", "pdf_source": None, "format": "html_as_filed",
        "reference": {"module": f"refs/{fam.FAMILY_ID}.py", "frozen_sha256": ctx.frozen.get("sha256"),
                      "test_pass_rate": ctx.frozen.get("test_pass_rate")},
        "checks_passed": {a: {c: bool(ctx.cp.loc[a, c]) for c in ctx.cp.columns if c.startswith("check_")} for a in graded},
        "cell_locations": {a: json.loads(ctx.locs[a]) for a in graded},
        "provenance": provenance, "leakage": {"passed": not leaks, "hits": leaks[:20]},
    }
    # baselines graded by the service's own grader
    gr = _grader()
    copy_prior, zeros = {}, {}
    for k, fsp in fields_by_period.items():
        cp_ans, z_ans = {}, {}
        for f, s in fsp.items():
            if f in open_vals:
                ov = open_vals[f]
                cp_ans[f] = int(ov) if s["type"] in ("money_cents", "int") else str(ov)
            z_ans[f] = 0 if s["type"] in ("money_cents", "int", "decimal") else ""
        if k:
            copy_prior[k], zeros[k] = cp_ans, z_ans
        else:
            copy_prior, zeros = cp_ans, z_ans
    try:
        meta["baselines"] = {"copy_prior": gr.headline_metrics(gr.grade_submission(meta, copy_prior)),
                             "all_zeros": gr.headline_metrics(gr.grade_submission(meta, zeros))}
        gr.parse_answer_key(meta)
        if gr.headline_metrics(gr.grade_submission(meta, answer)).get("fully_resolved") is not True:
            res.update(status="dropped", reason="answer key does not grade as fully resolved")
    except Exception as e:
        res.update(status="dropped", reason=f"grader rejected meta: {type(e).__name__}: {e}")
    mdir = BUILD / "meta"
    mdir.mkdir(parents=True, exist_ok=True)
    (mdir / f"{task_id}.json").write_text(json.dumps(meta, indent=1, default=str), encoding="utf-8")
    res.update(n_fields=sum(len(v) for v in fields_by_period.values()),
               n_nontrivial=sum(1 for v in fields_by_period.values() for s in v.values() if not s["trivial"]),
               window_tag=sel.window_tag, deal_cik=deal,
               copy_prior_line_item=(meta.get("baselines", {}).get("copy_prior", {}) or {}).get("line_item_accuracy"))
    return res


def _instructions(task_id, cat, deal_name, periods, opening_name, fields_by_period) -> str:
    what = {"C1": "Compute every output field of ONE monthly distribution.",
            "C2": "Compute every output field of FOUR consecutive monthly distributions, starting from the opening state only.",
            "C3": "Compute every output field of ONE monthly distribution (this period contains a stress event)."}[cat]
    lines = [f"# WaterfallBench task `{task_id}`", "", f"**Deal:** {deal_name}  ", f"**Category:** {cat} {CAT_NAMES[cat]}", "",
             what, "",
             "Files (all are SEC EDGAR HTML as filed):",
             "- `/workspace/docs/`: the deal's governing documents (final prospectus; closing agreements where filed).",
             f"- `/workspace/reports/{opening_name}`: the complete servicer report of the period before the first graded period.",
             ]
    for i, p in enumerate(periods):
        dd = p.get("distribution_date") or _date(p["period_of_report"])
        extra = " Beginning balances and carryovers are also removed: they equal your results for the previous period." if (cat == "C2" and i > 0) else ""
        lines.append(f"- `/workspace/reports/{p['report']}`: the servicer report for the distribution of {dd}, with every output value "
                     f"removed. Input values (collections, pool data, rates, beginning balances) remain.{extra}")
    lines += ["", "Rules:",
              "- Money: integer US cents, exactly to the cent as the trustee reports it (e.g. $1,234.56 -> 123456).",
              "- Percentages and other decimals: the number as it would be printed, without a % sign.",
              "- Statuses: one of the listed values.",
              "- Apply the priority of payments and definitions in the governing documents; deal parameters come from those documents.",
              ""]
    for k, fsp in fields_by_period.items():
        hdr = f"## Required output fields{(' — ' + k) if k else ''}"
        lines += [hdr, "", "| field | type | report line |", "|---|---|---|"]
        for f, s in fsp.items():
            t = s["type"] + (f" ({'/'.join(s['enum'])})" if s.get("enum") else "")
            lines.append(f"| `{f}` | {t} | {s.get('label', '')} |")
        lines.append("")
    shape = '{"period_1": {"<field>": <value>, ...}, "period_2": {...}, "period_3": {...}, "period_4": {...}}' if cat == "C2" else '{"<field>": <value>, ...}'
    lines += ["## Answer", "", f"Write `/workspace/answer.json` as {shape}, matching `/workspace/answer_schema.json`.", ""]
    return "\n".join(lines)


def _props(fsp: dict) -> dict:
    props = {}
    for f, s in fsp.items():
        if s["type"] == "money_cents":
            props[f] = {"type": "integer", "description": "US cents"}
        elif s["type"] == "int":
            props[f] = {"type": "integer"}
        elif s["type"] == "decimal":
            props[f] = {"type": ["number", "string"], "description": "decimal as printed, no % sign"}
        else:
            props[f] = {"type": "string", "enum": s.get("enum", [])}
    return {"type": "object", "additionalProperties": False, "required": list(fsp), "properties": props}


def _schema(cat, fields_by_period) -> dict:
    base = {"$schema": "https://json-schema.org/draft/2020-12/schema"}
    if cat == "C2":
        return {**base, "type": "object", "additionalProperties": False, "required": list(fields_by_period),
                "properties": {k: _props(v) for k, v in fields_by_period.items()}}
    return {**base, **_props(fields_by_period[""])}


def build(family: str, roles=("task", "reserve")) -> pd.DataFrame:
    ctx = Ctx(family)
    sel = pd.read_parquet(SELECTION)
    sel = sel[(sel.family == ctx.fam.FAMILY_ID) & sel.role.isin(roles)]
    rows = []
    for s in sel.itertuples():
        try:
            rows.append(build_task(ctx, s))
        except Exception as e:  # a crash drops the task with its reason; nothing is patched by hand
            rows.append({"task_id": s.task_id, "family": ctx.fam.FAMILY_ID, "category": s.category, "role": s.role,
                         "status": "dropped", "reason": f"error: {type(e).__name__}: {e}"})
    out = pd.DataFrame(rows)
    config.merge_rows(PACKETS, out, "family", [ctx.fam.FAMILY_ID])
    ok = out[out.status == "ok"]
    lines = [f"## {ctx.fam.FAMILY_ID}", "", f"- Built {len(out)} packets ({(out.role == 'task').sum()} tasks, {(out.role == 'reserve').sum()} reserves); "
             f"passed all gates: {len(ok)}", "", out.drop(columns=[c for c in ("deal_cik",) if c in out]).to_markdown(index=False), ""]
    config.update_report("step_9.md", ctx.fam.FAMILY_ID, "\n".join(lines), "# Steps 9-10 — Packets, output removal, leakage tests, baselines")
    print("\n".join(lines[:3]))
    print(out[["task_id", "role", "status", "reason"]].to_string()[:4000])
    return out


def finalize() -> pd.DataFrame:
    """Final tasks: per family, its passing 'task' packets topped up from its own passing reserves (failed category
    first) to TASKS_PER_FAMILY. If a family cannot reach that (too few eligible periods), the shortfall is filled from
    other families' passing reserves, spread round-robin, so the total reaches TASKS_PER_FAMILY x families.
    Unused passing reserves are kept under reserves/ (never published with the final set)."""
    pk = pd.read_parquet(PACKETS)
    ok = pk[pk.status == "ok"]
    final, notes = [], []
    left_by_fam = {}
    for fam_id, g in pk.groupby("family"):
        tasks = list(ok[(ok.family == fam_id) & (ok.role == "task")].task_id)
        res = ok[(ok.family == fam_id) & (ok.role == "reserve")]
        failed_cats = list(g[(g.role == "task") & (g.status != "ok")].category)
        pick = []
        for c in failed_cats:
            m = res[(res.category == c) & ~res.task_id.isin(pick)]
            if len(m) and len(tasks) + len(pick) < config.TASKS_PER_FAMILY:
                pick.append(m.task_id.iloc[0])
        tg = getattr(config, "CATEGORY_TARGETS", None) or {}
        cnt = ok[ok.task_id.isin(tasks)].category.value_counts().to_dict()
        for t, c in zip(res.task_id, res.category):
            under = (not tg) or cnt.get(c, 0) < tg.get(c, 0)   # keep the per-family category shape
            if len(tasks) + len(pick) < config.TASKS_PER_FAMILY and t not in pick and under:
                pick.append(t)
                cnt[c] = cnt.get(c, 0) + 1
        final += tasks + pick
        # cross-family cover uses C1 reserves first (C1 is the category that absorbs shortfalls)
        left = res[~res.task_id.isin(pick)].sort_values("category")
        left_by_fam[fam_id] = list(left.task_id)
        n = len(tasks) + len(pick)
        if n < config.TASKS_PER_FAMILY:
            notes.append(f"{fam_id}: {n} tasks (short {config.TASKS_PER_FAMILY - n}: not enough eligible test periods)")
    target = config.TASKS_PER_FAMILY * pk.family.nunique()
    while len(final) < target and any(left_by_fam.values()):
        for fam_id in sorted(left_by_fam, key=lambda f: -len(left_by_fam[f])):
            if left_by_fam[fam_id] and len(final) < target:
                t = left_by_fam[fam_id].pop(0)
                final.append(t)
                notes.append(f"{fam_id}: +1 reserve {t} to cover another family's shortfall")
    for d in (FINAL_TASKS, FINAL_META, config.WORKDIR / "reserves"):
        if d.exists():
            shutil.rmtree(d)
        d.mkdir(parents=True)
    for t in final:
        shutil.copytree(BUILD / "tasks" / t, FINAL_TASKS / t)
        shutil.copy2(BUILD / "meta" / f"{t}.json", FINAL_META / f"{t}.json")
    spare = [t for v in left_by_fam.values() for t in v]
    for t in spare:
        shutil.copytree(BUILD / "tasks" / t, config.WORKDIR / "reserves" / "tasks" / t)
    fin = pk[pk.task_id.isin(final)]
    config.write_atomic(fin.assign(final=True), config.WORKDIR / "final_tasks.parquet")
    lines = ["## Final allocation", "", f"- Final tasks: {len(final)} (target {target}); unused passing reserves kept: {len(spare)}",
             *[f"- {n}" for n in notes], "",
             fin.groupby(["family", "category"]).size().unstack(fill_value=0).to_markdown(), ""]
    config.update_report("step_9.md", "final", "\n".join(lines).replace("## Final allocation", ""), "# Steps 9-10 — Packets, output removal, leakage tests, baselines")
    print("\n".join(lines))
    return fin


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--family")
    ap.add_argument("--roles", default="task,reserve")
    ap.add_argument("--finalize", action="store_true")
    a = ap.parse_args()
    if a.finalize:
        finalize()
    else:
        build(a.family, tuple(a.roles.split(",")))
