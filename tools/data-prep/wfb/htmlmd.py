"""Deterministic HTML -> Markdown for EDGAR documents, preserving tables.

Used for raw documents (Step 3) and, crucially, for sanitized graded-period reports (Step 9), so the
markdown an agent sees is generated only from HTML we control. EDGAR tables use spacer cells and split
"$" into its own cell; rows are compacted to their non-empty cells with "$" glued to the amount.
"""

from __future__ import annotations

import html as _html
import re

from lxml import etree
from lxml import html as lxml_html

BLOCK = {"p", "div", "h1", "h2", "h3", "h4", "h5", "h6", "li", "center", "pre", "blockquote", "section", "article"}
SKIP = {"script", "style", "head", "title", "meta"}


def _cell_text(el) -> str:
    t = el.text_content()
    t = _html.unescape(t).replace("\xa0", " ")
    return " ".join(t.split())


def table_rows(table) -> list[list[str]]:
    rows = []
    for tr in table.xpath(".//tr"):
        cells = [_cell_text(td) for td in tr.xpath("./td|./th")]
        out: list[str] = []
        for c in cells:
            if not c:
                continue
            if out and out[-1] in ("$", "(", "$(") and c[:1].isdigit():
                out[-1] = out[-1] + c if out[-1] != "$" else f"$ {c}"
                continue
            if c in (")", "%") and out:
                out[-1] += c
                continue
            out.append(c.replace("|", "\\|"))
        if out:
            rows.append(out)
    return rows


def table_to_md(table) -> str:
    rows = table_rows(table)
    if not rows:
        return ""
    width = max(len(r) for r in rows)
    if width == 1:
        return "\n".join(r[0] for r in rows)
    lines = []
    for i, r in enumerate(rows):
        lines.append("| " + " | ".join(r + [""] * (width - len(r))) + " |")
        if i == 0:
            lines.append("|" + " --- |" * width)
    return "\n".join(lines)


def html_to_md(src: str) -> str:
    if "<" not in src[:5000]:
        return src.strip() + "\n"
    doc = lxml_html.fromstring(src)
    parts: list[str] = []
    buf: list[str] = []

    def flush():
        t = " ".join(" ".join(buf).split())
        if t:
            parts.append(t)
        buf.clear()

    def walk(el):
        tag = el.tag if isinstance(el.tag, str) else ""
        if tag in SKIP or isinstance(el, etree._Comment):
            if el.tail:
                buf.append(_html.unescape(el.tail).replace("\xa0", " "))
            return
        if tag == "table":
            flush()
            md = table_to_md(el)
            if md:
                parts.append(md)
        else:
            if tag in BLOCK or tag == "br":
                flush()
            if el.text:
                buf.append(_html.unescape(el.text).replace("\xa0", " "))
            for ch in el:
                walk(ch)
            if tag in BLOCK:
                flush()
        if el.tail:
            buf.append(_html.unescape(el.tail).replace("\xa0", " "))

    body = doc.find(".//body")
    walk(body if body is not None else doc)
    flush()
    out = "\n\n".join(p for p in parts if p.strip())
    out = re.sub(r"\n{3,}", "\n\n", out)
    return out.strip() + "\n"
