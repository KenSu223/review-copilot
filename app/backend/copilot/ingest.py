"""Bring a paper into the system: store the PDF, parse it, persist blocks."""
import hashlib
import logging
import re

import httpx
from sqlmodel import Session, delete, select

from .config import PDF_DIR
from .db import Block, Paper, PaperMap, engine
from .parsing import hidden_text, parse_pdf

log = logging.getLogger(__name__)
ARXIV_ID = re.compile(r"(\d{4}\.\d{4,5}(v\d+)?|[a-z\-]+(\.[A-Z]{2})?/\d{7}(v\d+)?)")


def store_pdf(data: bytes, filename: str, source: str = "upload") -> Paper:
    if not data.startswith(b"%PDF"):
        raise ValueError("Not a PDF file")
    pid = hashlib.sha256(data).hexdigest()[:16]
    (PDF_DIR / f"{pid}.pdf").write_bytes(data)
    with Session(engine) as s:
        paper = s.get(Paper, pid)
        if paper is None:
            paper = Paper(id=pid, filename=filename, source=source)
            s.add(paper)
            s.commit()
            s.refresh(paper)
        return paper


def fetch_arxiv(ref: str) -> tuple[bytes, str]:
    m = ARXIV_ID.search(ref)
    if not m:
        raise ValueError(f"Could not find an arXiv id in {ref!r}")
    aid = m.group(1)
    resp = httpx.get(f"https://arxiv.org/pdf/{aid}", follow_redirects=True, timeout=60,
                     headers={"User-Agent": "review-copilot/0.1 (research prototype)"})
    resp.raise_for_status()
    return resp.content, aid


def parse_and_save(pid: str) -> None:
    """Parse the stored PDF, flag hidden text, replace its blocks, then build the paper map.
    Runs in a background task."""
    with Session(engine) as s:
        paper = s.get(Paper, pid)
        try:
            pdf = PDF_DIR / f"{pid}.pdf"
            doc = parse_pdf(pdf)
            hidden = hidden_text.detect(pdf)
            s.exec(delete(Block).where(Block.paper_id == pid))
            for i, b in enumerate(doc.blocks):
                # Blocks overlapping invisible text are kept for display but never shown to the LLM.
                if hidden and any(hidden_text.overlaps(hb["box"], box) for hb in hidden for box in b["boxes"]):
                    b = {**b, "kind": "hidden"}
                s.add(Block(paper_id=pid, block_id=f"s-{i:04d}", order=i, **b))
            paper.title = doc.title or paper.filename
            paper.page_sizes = doc.page_sizes
            paper.n_pages = len(doc.page_sizes)
            paper.parser = doc.parser
            paper.hidden_text = hidden
            paper.status, paper.error = "ready", ""
        except Exception as exc:
            log.exception("parse failed for %s", pid)
            paper.status, paper.error = "error", str(exc)[:500]
        s.add(paper)
        s.commit()
        ok = paper.status == "ready"
    if ok:
        build_map(pid)


def llm_blocks(s: Session, pid: str) -> list[Block]:
    """Blocks the LLM may see (hidden-text blocks excluded)."""
    rows = s.exec(select(Block).where(Block.paper_id == pid).order_by(Block.order))
    return [b for b in rows if b.kind != "hidden"]


def build_map(pid: str) -> None:
    from .agents import paper_map

    with Session(engine) as s:
        pm = s.get(PaperMap, pid) or PaperMap(paper_id=pid)
        pm.status, pm.error = "computing", ""
        s.add(pm)
        s.commit()
        paper = s.get(Paper, pid)
        blocks = [(b.block_id, b.kind, b.text) for b in llm_blocks(s, pid)]
        title = paper.title
    try:
        data, call = paper_map.build(blocks, title)
        status, err = "ready", ""
    except Exception as exc:
        log.exception("paper map failed for %s", pid)
        data, call, status, err = {}, {}, "error", str(exc)[:500]
    with Session(engine) as s:
        pm = s.get(PaperMap, pid)
        pm.data, pm.call, pm.status, pm.error = data, call, status, err
        s.add(pm)
        s.commit()
