"""Versioned label maps: canonical field -> (table context, row label, column label) per report format.

Canonical field names are derived deterministically from the normalised label path of each value cell, with
period-varying fragments (dates, percentages printed inside labels) abstracted and class names kept. A report
*format* groups reports whose class-abstracted label sets match (Jaccard >= FORMAT_JACCARD). Within a format,
each deal's label map lists its fields; certification locates every field's cell(s) by this map.
"""

from __future__ import annotations

import hashlib
import json
import re
from collections import Counter, defaultdict
from dataclasses import asdict, dataclass
from pathlib import Path

from . import config, grid

LABEL_MAPS = config.WORKDIR / "label_maps"
LABEL_MAP_VERSION = "lm-2"  # lm-2: printed formula references like "(Ln 50 + Ln 51)" / "(sum a - h)" stripped from names
FORMAT_JACCARD = 0.85

DATE = re.compile(r"\b\d{1,2}/\d{1,2}/\d{2,4}\b|\b(january|february|march|april|may|june|july|august|september|october|november|december)\s+\d{1,2},?\s+\d{4}\b", re.I)
PCTIN = re.compile(r"\d+(\.\d+)?\s*%")
MONEYIN = re.compile(r"\$\s*[\d,]+(\.\d+)?")


FORMULA = re.compile(r"\((?=[^()]*(?:\bln\s*\d|\bline|\bsum\b|\d+[a-z]?\s*[+\-–]\s*\d))[\sA-Za-z\d+\-–/.,]*\)", re.I)


def match_norm(t: str) -> str:
    for _ in range(3):  # nested formula parentheses, innermost first
        t = FORMULA.sub(" ", t)
    t = DATE.sub(" date ", t)
    t = PCTIN.sub(" pct ", t)
    t = MONEYIN.sub(" amt ", t)
    t = re.sub(r"[^a-z0-9]+", " ", t.lower())
    return " ".join(t.split())


def slug(t: str) -> str:
    return re.sub(r"\s+", "_", match_norm(t))[:90].strip("_")


def cell_key(c: grid.Cell) -> tuple[str, str, str, str]:
    return (match_norm(c.section), match_norm(c.parent), match_norm(c.label), match_norm(c.column))


def field_names(cells: list[grid.Cell]) -> list[str]:
    """Canonical field per cell: parent/label/column slug; section prefixed only when needed for uniqueness.

    A label path that repeats within one report (e.g. "Note Balance @ <date>" before and after the
    distribution) gets an occurrence suffix (__2, __3...) in document order, which is stable within a format.
    """
    base = []
    occ: Counter = Counter()
    for c in cells:
        parts = [slug(c.parent), slug(c.label), slug(c.column)]
        b = "__".join(p for p in parts if p) or "unlabelled"
        k = cell_key(c)
        occ[k] += 1
        base.append(b if occ[k] == 1 else f"{b}__{occ[k]}")
    counts = Counter(zip(base, [match_norm(c.section) for c in cells]))
    by_base = defaultdict(set)
    for b, c in zip(base, cells):
        by_base[b].add(match_norm(c.section))
    out = []
    for b, c in zip(base, cells):
        out.append(f"{slug(c.section)}__{b}" if len(by_base[b]) > 1 else b)
    return out


def jaccard(a: frozenset, b: frozenset) -> float:
    return len(a & b) / max(1, len(a | b))


def class_abstract_keys(cells: list[grid.Cell]) -> frozenset:
    return frozenset("|".join(grid.norm_label(x) for x in (c.section, c.parent, c.label, c.column)) for c in cells)


@dataclass
class FieldSpec:
    field: str
    section: str
    parent: str
    label: str
    column: str
    kind: str          # majority value kind across the format's reports
    example_line: str


def build_label_map(family: str, fmt_id: str, deal_cik: int, report_grids: list[grid.Grid]) -> dict:
    """Label map for one deal within one format, from all of that deal's reports in the format.

    A field is kept only if its key is unambiguous in the label path sense (duplicates with equal values are
    allowed by certification). Kind is the majority kind observed for the key.
    """
    seen: dict[str, FieldSpec] = {}
    kinds: dict[str, Counter] = defaultdict(Counter)
    for g in report_grids:
        names = field_names(g.cells)
        for name, c in zip(names, g.cells):
            kinds[name][c.kind] += 1
            if name not in seen:
                seen[name] = FieldSpec(name, match_norm(c.section), match_norm(c.parent), match_norm(c.label), match_norm(c.column), c.kind, c.line)
    for name, fs in seen.items():
        k = kinds[name]
        # money printed without "$" on zero rows parses as decimal; a field seen as money anywhere is money
        k.pop("dash", None)
        fs.kind = "money" if k.get("money") else (k.most_common(1)[0][0] if k else "money")
    lm = {
        "version": LABEL_MAP_VERSION, "family": family, "format": fmt_id, "deal_cik": int(deal_cik),
        "n_reports": len(report_grids), "fields": [asdict(v) for v in sorted(seen.values(), key=lambda x: x.field)],
    }
    p = LABEL_MAPS / family / fmt_id / f"{deal_cik}.json"
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(lm, indent=1))
    return lm


def locate(g: grid.Grid, fs: dict) -> list[grid.Cell]:
    names = field_names(g.cells)
    key = (fs["section"], fs["parent"], fs["label"], fs["column"])
    return [c for n, c in zip(names, g.cells) if n == fs["field"] and cell_key(c) == key]


def typed_value(c: grid.Cell, kind: str):
    """Certified value of a cell under the field's label-map kind."""
    from decimal import Decimal
    if c.kind == "dash":
        return 0 if kind in ("money", "int") else (Decimal(0) if kind in ("pct", "decimal") else None)
    if kind == "money":
        if c.kind == "money":
            return int(c.value)
        n = c.num
        return None if n is None else int((n * 100 * c.scale).to_integral_value())
    if kind == "int":
        return int(c.value) if c.kind == "int" else None
    if kind in ("pct", "decimal"):
        return None if c.num is None else Decimal(c.num)
    if kind == "status":
        return str(c.value) if c.kind == "status" else None
    return None


def schema_for(lm: dict) -> dict:
    """Firecrawl JSON-extraction schema for one deal's label map (money as integer cents)."""
    props = {}
    for f in lm["fields"]:
        where = " > ".join(x for x in (f["section"], f["parent"], f["label"], f["column"]) if x)
        if f["kind"] == "money":
            props[f["field"]] = {"type": "integer", "description": (
                f"Dollar amount printed in the row '{where}', as integer cents: copy every digit of the printed "
                "amount including the two digits after the decimal point, and drop only '$', commas and the decimal "
                "point. Never add or remove digits. Examples: $1,234.56 -> 123456; $27,550.00 -> 2755000; "
                "$3,914,142.67 -> 391414267; $0.00 -> 0. Negative if shown in parentheses.")}
        elif f["kind"] == "int":
            props[f["field"]] = {"type": "integer", "description": f"Integer count in the row '{where}'."}
        elif f["kind"] in ("pct", "decimal"):
            props[f["field"]] = {"type": "string", "description": f"Number exactly as printed (digits only, no % sign) in the row '{where}'."}
        else:
            props[f["field"]] = {"type": "string", "description": f"Status text exactly as printed in the row '{where}'."}
    return {"type": "object", "properties": props}
