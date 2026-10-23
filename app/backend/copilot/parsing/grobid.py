"""GROBID client + TEI -> blocks.

TEI coords are "page,x,y,w,h" (PDF points, top-left origin), one box per text line, ';'-separated.
We store boxes as percentages of the page so the frontend can draw them at any zoom.
"""
import re
from pathlib import Path

import httpx
from lxml import etree

from ..config import GROBID_URL
from . import ParsedDoc

NS = {"t": "http://www.tei-c.org/ns/1.0"}
T = "{http://www.tei-c.org/ns/1.0}"


def process(path: Path, timeout: float = 180.0) -> str:
    data = {
        "segmentSentences": "1",
        "consolidateHeader": "0",
        "consolidateCitations": "0",
        "teiCoordinates": ["s", "head", "figure", "formula"],
    }
    with path.open("rb") as fh:
        resp = httpx.post(f"{GROBID_URL}/api/processFulltextDocument",
                          files={"input": (path.name, fh, "application/pdf")}, data=data, timeout=timeout)
    resp.raise_for_status()
    return resp.text


def _text(el) -> str:
    return re.sub(r"\s+", " ", "".join(el.itertext())).strip()


def _boxes(coords: str | None, sizes: list) -> list:
    out = []
    for part in (coords or "").split(";"):
        try:
            page, x, y, w, h = part.split(",")
            p = int(page)
            pw, ph = sizes[p - 1]
            out.append({"page": p, "left": float(x) / pw * 100, "top": float(y) / ph * 100,
                        "width": float(w) / pw * 100, "height": float(h) / ph * 100})
        except (ValueError, IndexError):
            continue
    return out


def tei_to_doc(tei: str) -> ParsedDoc:
    root = etree.fromstring(tei.encode("utf-8"))
    sizes = [[float(s.get("lrx")), float(s.get("lry"))] for s in root.iterfind(".//t:facsimile/t:surface", NS)]
    title_el = root.find(".//t:titleStmt/t:title", NS)
    title = _text(title_el) if title_el is not None else ""
    blocks: list[dict] = []
    para_counter = [0]

    def add(kind, section, text, coords, para=None):
        if not text:
            return
        blocks.append({"kind": kind, "section": section, "para": para_counter[0] if para is None else para,
                       "text": text, "boxes": _boxes(coords, sizes)})

    major = [""]  # last numbered section; unnumbered run-in heads become "major › sub"

    def walk_div(div, section):
        head = div.find("t:head", NS)
        if head is not None:
            n, title_txt = head.get("n") or "", _text(head)
            if n or not major[0] or section in ("Abstract", "Appendix"):
                major[0] = f"{n} {title_txt}".strip()
                section = major[0]
            else:
                section = f"{major[0]} › {title_txt.rstrip('.: ')}"
            add("heading", section, title_txt, head.get("coords"))
        for child in div:
            if child.tag == f"{T}p":
                para_counter[0] += 1
                for s in child.iterfind("t:s", NS):
                    add("sentence", section, _text(s), s.get("coords"))
            elif child.tag == f"{T}formula":
                para_counter[0] += 1
                add("formula", section, _text(child), child.get("coords"))
            elif child.tag == f"{T}div":
                section = walk_div(child, section)
        return section

    for div in root.iterfind(".//t:profileDesc/t:abstract//t:div", NS):
        walk_div(div, "Abstract")
    body = root.find(".//t:text/t:body", NS)
    section = ""
    if body is not None:
        for div in body.iterfind("t:div", NS):
            section = walk_div(div, section)
    back = root.find(".//t:text/t:back", NS)
    if back is not None:
        for div in back.iter(f"{T}div"):
            if div.find("t:head", NS) is not None and div.find("t:p", NS) is not None:
                walk_div(div, "Appendix")

    # Figures and tables: caption sentences + a table-content block (numbers matter for facts).
    for fig in root.iter(f"{T}figure"):
        head = fig.find("t:head", NS)
        label = _text(head) if head is not None else ("Table" if fig.get("type") == "table" else "Figure")
        label = re.sub(r"\s+\.$", "", label)
        para_counter[0] += 1
        caps = list(fig.iterfind(".//t:figDesc//t:s", NS))
        if caps:
            for s in caps:
                add("caption", label, _text(s), s.get("coords") or fig.get("coords"))
        else:
            desc = fig.find("t:figDesc", NS)
            if desc is not None:
                add("caption", label, _text(desc), fig.get("coords"))
        table = fig.find("t:table", NS)
        if table is not None:
            rows = [" | ".join(_text(c) for c in row.iterfind("t:cell", NS)) for row in table.iterfind("t:row", NS)]
            rows = [r for r in rows if r.strip(" |")]
            if rows:
                add("table", label, f"{label} (table content): " + " // ".join(rows), fig.get("coords"))

    return ParsedDoc(title=title, page_sizes=sizes, blocks=blocks, parser="grobid-0.9.1")


def parse(path: Path) -> ParsedDoc:
    return tei_to_doc(process(path))
