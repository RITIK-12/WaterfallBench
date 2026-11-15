"""EDGAR helpers: URLs, full-submission SGML splitting, header parsing, HTML-to-text."""

from __future__ import annotations

import html as _html
import re
from dataclasses import dataclass, field
from pathlib import Path

from lxml import html as lxml_html

from . import config

DOC_RE = re.compile(r"<DOCUMENT>(.*?)</DOCUMENT>", re.S)
TAG_RE = {k: re.compile(rf"<{k}>([^\n<]*)") for k in ("TYPE", "SEQUENCE", "FILENAME", "DESCRIPTION")}
TEXT_RE = re.compile(r"<TEXT>(.*?)</TEXT>", re.S)


def acc_nodash(accession: str) -> str:
    return accession.replace("-", "")


def filing_base(cik: int | str, accession: str) -> str:
    return f"{config.SEC}/Archives/edgar/data/{int(cik)}/{acc_nodash(accession)}"


def txt_url(cik: int | str, accession: str) -> str:
    return f"{filing_base(cik, accession)}/{accession}.txt"


def doc_url(cik: int | str, accession: str, filename: str) -> str:
    return f"{filing_base(cik, accession)}/{filename}"


def submissions_url(cik: int | str) -> str:
    return f"{config.SEC_DATA}/submissions/CIK{int(cik):010d}.json"


def raw_dir(cik: int | str, accession: str) -> Path:
    return config.RAW / str(int(cik)) / accession


def txt_path(cik: int | str, accession: str) -> Path:
    return raw_dir(cik, accession) / f"{accession}.txt.gz"


@dataclass
class Document:
    type: str
    sequence: str
    filename: str
    description: str
    text: str  # the body between <TEXT> and </TEXT>, as filed


@dataclass
class Submission:
    accession: str
    header: dict[str, list[str]] = field(default_factory=dict)
    documents: list[Document] = field(default_factory=list)

    def h(self, key: str) -> str | None:
        v = self.header.get(key)
        return v[0] if v else None

    def docs_of(self, prefix: str) -> list[Document]:
        return [d for d in self.documents if d.type.upper().startswith(prefix.upper())]


HDR_KV = re.compile(r"^\s*([A-Z][A-Z0-9 /&()'.-]+?):\s*(.*?)\s*$")
HDR_TAG = re.compile(r"^<([A-Z0-9-]+)>(.*)$")


def parse_submission(raw: str) -> Submission:
    accession = ""
    m = re.search(r"ACCESSION NUMBER:\s*(\S+)", raw[:5000])
    if m:
        accession = m.group(1)
    sub = Submission(accession=accession)
    hdr_end = raw.find("</SEC-HEADER>")
    hdr = raw[: hdr_end if hdr_end > 0 else 20000]
    section = ""
    for line in hdr.splitlines():
        t = HDR_TAG.match(line.strip())
        if t and t.group(2):
            sub.header.setdefault(t.group(1), []).append(t.group(2).strip())
            continue
        kv = HDR_KV.match(line)
        if kv:
            k, v = kv.group(1).strip(), kv.group(2).strip()
            if not v:
                section = k
                continue
            key = k if section in ("", "FILER", "FILED BY") else f"{section}/{k}"
            sub.header.setdefault(k, []).append(v)
            if key != k:
                sub.header.setdefault(key, []).append(v)
    for dm in DOC_RE.finditer(raw):
        body = dm.group(1)
        get = lambda k: (TAG_RE[k].search(body).group(1).strip() if TAG_RE[k].search(body) else "")
        tm = TEXT_RE.search(body)
        sub.documents.append(Document(get("TYPE"), get("SEQUENCE"), get("FILENAME"), get("DESCRIPTION"), tm.group(1) if tm else ""))
    return sub


def html_to_text(s: str) -> str:
    s = s.strip()
    if not s:
        return ""
    if "<" not in s[:2000]:
        return s
    try:
        doc = lxml_html.fromstring(s)
        for bad in doc.xpath("//script|//style"):
            bad.drop_tree()
        for br in doc.xpath("//br"):
            br.tail = "\n" + (br.tail or "")
        for blk in doc.xpath("//p|//div|//tr|//li|//h1|//h2|//h3|//h4|//table"):
            blk.tail = "\n" + (blk.tail or "")
        for td in doc.xpath("//td|//th"):
            td.tail = " | " + (td.tail or "")
        txt = doc.text_content()
    except Exception:
        txt = re.sub(r"<[^>]+>", " ", s)
    txt = _html.unescape(txt).replace("\xa0", " ")
    txt = re.sub(r"[ \t]+", " ", txt)
    txt = re.sub(r"\n\s*\n+", "\n", txt)
    return txt.strip()


FILE_NO = r"((?:333|033|000|001|002|005|811)-\d{3,6}(?:-\d{1,3})?)"
CIK_NO = r"(\d{6,10})"


def _near(text: str, label: str, value: str, window: int = 220) -> str | None:
    for m in re.finditer(label, text, re.I | re.S):
        after = re.search(value, text[m.end() : m.end() + window])
        if after:
            return after.group(1)
        before = list(re.finditer(value, text[max(0, m.start() - window) : m.start()]))
        if before:
            return before[-1].group(1)
    return None


def parse_10d_cover(text: str) -> dict:
    t = text[:15000]
    return {
        "issuing_entity_file_number": _near(t, r"Commission\s+File\s+Number\s+of\s+(?:the\s+)?issuing\s+entity", FILE_NO),
        "issuing_entity_cik": _near(t, r"Central\s+Index\s+Key\s+Number\s+of\s+(?:the\s+)?issuing\s+entity", CIK_NO),
        "depositor_file_number": _near(t, r"Commission\s+File\s+Number\s+of\s+(?:the\s+)?depositor", FILE_NO),
        "depositor_cik": _near(t, r"Central\s+Index\s+Key\s+Number\s+of\s+(?:the\s+)?depositor", CIK_NO),
        "sponsor_cik": _near(t, r"Central\s+Index\s+Key\s+Number\s+of\s+(?:the\s+)?sponsor", CIK_NO),
    }
