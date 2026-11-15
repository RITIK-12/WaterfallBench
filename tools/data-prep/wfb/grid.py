"""Parse a servicer/trustee report's HTML tables into labelled value cells.

Each value cell gets a location (table index, row index, physical column) and a label path
(section > parent line > row label > column header). A report *format* is the set of label paths; the
versioned label map for a format maps canonical field -> label path. Certification reads values from these
cells (never from Firecrawl output), and the Step 9 sanitizer removes cells by the same locations.
"""

from __future__ import annotations

import hashlib
import html as _html
import re
from dataclasses import dataclass, field
from decimal import Decimal, InvalidOperation

from lxml import html as lxml_html

MONEY = re.compile(r"^\(?-?\$?\s*\(?-?\s*([\d,]+\.\d{2})\s*\)?$")
MONEY_INT = re.compile(r"^\(?-?\$\s*\(?([\d,]+)\)?$")
PCT = re.compile(r"^\(?(-?[\d,]*\.?\d+)\s*%\)?$")
DEC = re.compile(r"^-?\d*\.\d{3,}$")
INT = re.compile(r"^-?[\d,]+$")
STATUS_WORDS = {"yes", "no", "pass", "fail", "passed", "failed", "true", "false", "n/a", "na", "none", "met", "not met",
                "in effect", "not in effect", "occurred", "not occurred", "breached", "not breached"}
LINE_NO = re.compile(r"^\(?(\d{1,3}[A-Za-z]?)[.)]\s*$|^\(?(\d{1,3}[A-Za-z]?)[.)]\s+(.*)$")
SUB_NO = re.compile(r"^\(?([a-z]{1,2}|[ivx]{1,4})[.)]\s+(.*)$")
GLUE = {"$", "(", ")", "%", "$(", "-", "—", "–"}
DASHES = {"-", "—", "–", "$ -", "$-", "$ —", "$—"}
SCALE = re.compile(r"\(\s*(?:\$\s*)?in\s+(thousands|millions)\s*\)|\$\s*000s?\b|\(\$000\)", re.I)


@dataclass
class Cell:
    table: int
    row: int
    col: int
    section: str
    parent: str
    label: str
    column: str
    text: str
    kind: str          # money | pct | decimal | int | status
    value: object      # int cents | Decimal | int | str
    line: str = ""     # printed line number, e.g. "26.a"
    scale: int = 1

    @property
    def num(self) -> Decimal | None:
        """Numeric value as printed (scale applied, money in dollars) regardless of kind."""
        if self.kind == "money":
            return Decimal(self.value) / 100
        if self.kind in ("pct", "decimal", "int"):
            return Decimal(self.value)
        return None

    @property
    def path(self) -> str:
        return " > ".join(x for x in (self.section, self.parent, self.label, self.column) if x)


@dataclass
class Grid:
    cells: list[Cell] = field(default_factory=list)
    scale_notes: list[str] = field(default_factory=list)

    def fingerprint(self) -> str:
        paths = sorted({norm(c.section) + "|" + norm(c.parent) + "|" + norm_label(c.label) + "|" + norm(c.column) for c in self.cells})
        return hashlib.sha1("\n".join(paths).encode()).hexdigest()[:12]


def clean(t: str) -> str:
    return " ".join(_html.unescape(t).replace("\xa0", " ").split())


def norm(t: str) -> str:
    return re.sub(r"[^a-z0-9]+", " ", t.lower()).strip()


CLASS_TOKEN = re.compile(r"\bclass(es)?\s+[a-z]-?\d*[a-z]?\b", re.I)


def norm_label(t: str) -> str:
    """Label normalised for format comparison across deals (class names and dates abstracted)."""
    t = CLASS_TOKEN.sub("class X", t)
    t = re.sub(r"\d{1,2}/\d{1,2}/\d{2,4}", "DATE", t)
    t = re.sub(r"\d+(\.\d+)?%", "PCT", t)
    return norm(t)


def parse_value(t: str, scale: int = 1):
    s = t.strip()
    low = s.lower()
    if low in STATUS_WORDS:
        return "status", s
    neg = s.startswith("(") and s.endswith(")") or s.startswith("-") or "$(" in s or "( " in s
    m = MONEY.match(s)
    if m and ("$" in s or "," in m.group(1)) and not DEC.match(s):
        cents = int(Decimal(m.group(1).replace(",", "")) * 100) * scale
        return "money", -cents if neg else cents
    m = MONEY_INT.match(s)
    if m:
        cents = int(m.group(1).replace(",", "")) * 100 * scale
        return "money", -cents if neg else cents
    m = PCT.match(s)
    if m:
        try:
            v = Decimal(m.group(1).replace(",", ""))
            return "pct", -v if s.startswith("(") else v
        except InvalidOperation:
            return None
    if DEC.match(s) or re.match(r"^-?\d+\.\d{1,2}$", s):
        return "decimal", Decimal(s)
    if INT.match(s) and len(s.replace(",", "").lstrip("-")) <= 12:
        return "int", int(s.replace(",", ""))
    return None


def _merge_glue(texts: list[tuple[int, int, str]]) -> list[tuple[int, int, str]]:
    """Attach "$", "%", "(" and ")" cells to the number they belong to, keeping the number's column."""
    out: list[list] = []
    pending = ""
    for a, b, t in texts:
        if t in ("$", "(", "$(", "($"):
            pending += t
            continue
        if t in ("%", ")", "%)") and out and re.search(r"\d$", out[-1][2]):
            out[-1][2] += t
            continue
        if pending:
            t = (pending + " " + t) if re.match(r"^[\d(]", t) else ("-" if t in ("-", "—", "–") else t)
            pending = ""
        out.append([a, b, t])
    return [tuple(x) for x in out]


def _grid_rows(table):
    rows = []
    for tr in table.xpath(".//tr"):
        col, cells = 0, []
        for td in tr.xpath("./td|./th"):
            span = int(td.get("colspan", "1") or 1) if (td.get("colspan", "1") or "1").isdigit() else 1
            cells.append((col, col + span - 1, clean(td.text_content()), td))
            col += span
        rows.append(cells)
    return rows


def parse_report(src: str) -> Grid:
    doc = lxml_html.fromstring(src)
    g = Grid()
    page_scale = 1
    body_text = clean(doc.text_content()[:5000])
    sm = SCALE.search(body_text)
    if sm:
        page_scale = 1000 if "thousand" in sm.group(0).lower() or "000" in sm.group(0) else 1_000_000
        g.scale_notes.append(f"document: {sm.group(0)}")
    section = ""
    for ti, table in enumerate(doc.xpath("//table")):
        if table.xpath("ancestor::table"):
            continue
        scale = page_scale
        headers: list[tuple[int, int, str]] = []
        parent, parent_no = "", ""
        for ri, cells in enumerate(_grid_rows(table)):
            texts = _merge_glue([(a, b, t) for (a, b, t, _) in cells if t])
            if not texts:
                continue
            # printed formula notes under a line, e.g. "(Ln1 - Ln2 - Ln3 - Ln4)", are annotations, not sections
            if len(texts) == 1 and re.match(r"^\(?\s*(Ln\s*\d|Lines?\s*\d|sum\b)", texts[0][2], re.I):
                continue
            tsm = SCALE.search(" ".join(t for _, _, t in texts))
            if tsm and len(texts) <= 3:
                scale = 1000 if "thousand" in tsm.group(0).lower() or "000" in tsm.group(0) else 1_000_000
                g.scale_notes.append(f"table {ti}: {tsm.group(0)}")
            vals, labels = [], []
            for a, b, t in texts:
                if t in DASHES and labels:
                    vals.append((a, b, t, ("dash", 0)))  # a dash in a value position prints a zero amount
                    continue
                if t in GLUE:
                    continue
                pv = parse_value(t, scale)
                # a lone small integer before any label is a line number, not a value
                if pv and not labels and not vals and pv[0] == "int" and LINE_NO.match(t + "."):
                    labels.append(t + ".")
                    continue
                if pv and (labels or vals):
                    vals.append((a, b, t, pv))
                elif pv and pv[0] == "status" and labels:
                    vals.append((a, b, t, pv))
                else:
                    labels.append(t)
            if not vals:
                if len(labels) == 1 and not LINE_NO.match(labels[0]) and not SUB_NO.match(labels[0]):
                    section = labels[0][:120]
                    headers = []
                elif len(labels) >= 2 and not any(LINE_NO.match(x) or SUB_NO.match(x) for x in labels[:1]):
                    headers = [(a, b, t) for (a, b, t) in texts if t not in GLUE]
                else:
                    # numbered parent line with no value of its own, e.g. "29. | Class A Noteholder Interest Amounts"
                    lab = " ".join(labels)
                    m = LINE_NO.match(labels[0]) if labels else None
                    if m:
                        parent_no = (m.group(1) or m.group(2) or "").rstrip(".")
                        parent = " ".join(labels[1:]) if m.group(1) else (m.group(3) or "")
                    else:
                        parent = lab
                continue
            label_parts = [x for x in labels]
            line = ""
            is_sub = False
            if label_parts:
                m = LINE_NO.match(label_parts[0])
                if m:
                    line = (m.group(1) or m.group(2) or "").rstrip(".")
                    if m.group(1):
                        label_parts = label_parts[1:]
                    else:
                        label_parts[0] = m.group(3)
                    parent, parent_no = " ".join(label_parts), line
                else:
                    sm2 = SUB_NO.match(label_parts[0])
                    if sm2:
                        is_sub = True
                        line = f"{parent_no}.{sm2.group(1)}" if parent_no else sm2.group(1)
                        label_parts[0] = sm2.group(2)
            label = " ".join(label_parts)
            for a, b, t, (kind, v) in vals:
                col_label = ""
                for ha, hb, ht in headers:
                    if ha <= b and a <= hb:
                        col_label = ht
                        break
                g.cells.append(Cell(ti, ri, a, section, parent if is_sub else "", label, col_label, t, kind, v, line, scale))
    return g
