"""PDF -> ordered, citable blocks (sentences, headings, captions, tables) with page-% boxes.

GROBID is the primary parser (sentence segmentation + coordinates for scholarly PDFs);
PyMuPDF is the fallback when GROBID is unavailable or fails.
"""
from dataclasses import dataclass, field
from pathlib import Path
import logging

log = logging.getLogger(__name__)


@dataclass
class ParsedDoc:
    title: str
    page_sizes: list  # [[w, h], ...] in PDF points
    blocks: list = field(default_factory=list)  # dicts: kind, section, para, text, boxes
    parser: str = ""


def parse_pdf(path: Path) -> ParsedDoc:
    from . import grobid, fallback

    try:
        doc = grobid.parse(path)
        if sum(1 for b in doc.blocks if b["kind"] == "sentence") >= 20:
            return doc
        log.warning("GROBID returned too few sentences for %s; using fallback", path.name)
    except Exception as exc:  # GROBID down or failed on this PDF
        log.warning("GROBID failed for %s (%s); using fallback", path.name, exc)
    return fallback.parse(path)
