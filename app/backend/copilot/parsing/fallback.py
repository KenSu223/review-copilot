"""PyMuPDF fallback: text blocks in a two-column-aware reading order, regex sentence split,
word boxes merged per line, heading detection by pattern. Coarser than GROBID but needs no Docker."""
import re
from pathlib import Path

import pymupdf as fitz

from . import ParsedDoc

SENT_END = re.compile(r"(?<=[.!?])\s+(?=[A-Z(\[])")
# Numbered ("4.2 Results", "A.3 Proofs") or well-known unnumbered section headings.
HEADING = re.compile(r"^((\d{1,2}|[A-H])(\.\d{1,2}){0,2}\.?\s+[A-Z][^.!?]{2,70}|"
                     r"(Abstract|References|Bibliography|Acknowledge?ments?|Appendix|Appendices|Limitations|"
                     r"Conclusions?|Broader Impacts?|Ethics Statement|Ethical Considerations|Impact Statement))$")


def _assign_sections(blocks: list[dict]) -> None:
    """Mark heading-like sentences as headings and carry the current section down (GROBID gives this natively)."""
    section = ""
    for b in blocks:
        t = b["text"].strip()
        if len(t) <= 80 and HEADING.match(t) and not re.search(r"\d\s*%|=|[|πθσβλ∑∫∇]", t):
            b["kind"], section = "heading", t
        b["section"] = section


def _reading_order(blocks, page_w):
    """Full-width blocks stay in place; narrow blocks are grouped left column before right column."""
    def key(b):
        x0, y0, x1, _ = b[:4]
        narrow = (x1 - x0) < 0.6 * page_w
        col = 0 if (not narrow or x0 < page_w / 2) else 1
        return (col if narrow else 0, y0)
    return sorted(blocks, key=key)


def parse(path: Path) -> ParsedDoc:
    doc = fitz.open(path)
    sizes = [[p.rect.width, p.rect.height] for p in doc]
    out, para = [], 0
    for pno, page in enumerate(doc, start=1):
        pw, ph = page.rect.width, page.rect.height
        words = page.get_text("words")  # x0, y0, x1, y1, word, block_no, line_no, word_no
        by_block: dict[int, list] = {}
        for w in words:
            by_block.setdefault(w[5], []).append(w)
        text_blocks = [b for b in page.get_text("blocks") if b[6] == 0]
        for b in _reading_order(text_blocks, pw):
            bw = by_block.get(b[5], [])
            if not bw:
                continue
            para += 1
            # Build the block string while remembering which word each char span belongs to.
            text, spans = "", []
            for w in bw:
                start = len(text) + (1 if text else 0)
                text = f"{text} {w[4]}" if text else w[4]
                spans.append((start, len(text), w))
            pos = 0
            for sent in SENT_END.split(text):
                s0 = text.find(sent, pos)
                s1 = s0 + len(sent)
                pos = s1
                sw = [w for a, z, w in spans if a < s1 and z > s0]
                lines: dict[tuple, list] = {}
                for w in sw:
                    lines.setdefault((w[5], w[6]), []).append(w)
                boxes = []
                for lw in lines.values():
                    x0, y0 = min(w[0] for w in lw), min(w[1] for w in lw)
                    x1, y1 = max(w[2] for w in lw), max(w[3] for w in lw)
                    boxes.append({"page": pno, "left": x0 / pw * 100, "top": y0 / ph * 100,
                                  "width": (x1 - x0) / pw * 100, "height": (y1 - y0) / ph * 100})
                clean = re.sub(r"-\s(?=[a-z])", "", sent).strip()
                if len(clean) > 1:
                    out.append({"kind": "sentence", "section": "", "para": para, "text": clean, "boxes": boxes})
    _assign_sections(out)
    title = (doc.metadata or {}).get("title") or (out[0]["text"][:200] if out else "")
    return ParsedDoc(title=title, page_sizes=sizes, blocks=out, parser="pymupdf")
