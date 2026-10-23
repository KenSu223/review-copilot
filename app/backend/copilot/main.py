"""FastAPI app: paper ingest + blocks (P1). Chat, review, and export routes land in later phases."""
import json
import logging

from fastapi import BackgroundTasks, Depends, FastAPI, File, HTTPException, UploadFile
from fastapi.responses import FileResponse, StreamingResponse
from pydantic import BaseModel
from sqlmodel import Session, select

from .config import PDF_DIR
from .db import Block, Paper, PaperMap, ReviewSession, get_session, init_db
from .db import engine as db_engine
from .dialogue import engine, review
from .ingest import build_map, fetch_arxiv, parse_and_save, store_pdf

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
app = FastAPI(title="Review Copilot API", version="0.1.0")


@app.on_event("startup")
def _startup() -> None:
    init_db()


@app.get("/api/health")
def health() -> dict:
    return {"ok": True}


@app.get("/api/papers")
def list_papers(s: Session = Depends(get_session)) -> list[Paper]:
    return list(s.exec(select(Paper).order_by(Paper.created_at.desc())))


@app.post("/api/papers/upload")
async def upload_paper(bg: BackgroundTasks, file: UploadFile = File(...)) -> Paper:
    data = await file.read()
    try:
        paper = store_pdf(data, file.filename or "paper.pdf")
    except ValueError as exc:
        raise HTTPException(400, str(exc))
    if paper.status != "ready":
        bg.add_task(parse_and_save, paper.id)
    return paper


class ArxivRequest(BaseModel):
    ref: str  # arXiv id or URL


@app.post("/api/papers/arxiv")
def import_arxiv(req: ArxivRequest, bg: BackgroundTasks) -> Paper:
    try:
        data, aid = fetch_arxiv(req.ref)
        paper = store_pdf(data, f"{aid}.pdf", source=f"arxiv:{aid}")
    except Exception as exc:
        raise HTTPException(400, f"arXiv import failed: {exc}")
    if paper.status != "ready":
        bg.add_task(parse_and_save, paper.id)
    return paper


@app.post("/api/papers/{pid}/reparse")
def reparse(pid: str, bg: BackgroundTasks, s: Session = Depends(get_session)) -> Paper:
    paper = s.get(Paper, pid) or _404()
    paper.status = "parsing"
    s.add(paper)
    s.commit()
    s.refresh(paper)
    bg.add_task(parse_and_save, pid)
    return paper


@app.get("/api/papers/{pid}")
def get_paper(pid: str, s: Session = Depends(get_session)) -> Paper:
    return s.get(Paper, pid) or _404()


@app.get("/api/papers/{pid}/pdf")
def get_pdf(pid: str) -> FileResponse:
    path = PDF_DIR / f"{pid}.pdf"
    if not path.exists():
        _404()
    return FileResponse(path, media_type="application/pdf")


@app.get("/api/papers/{pid}/map")
def get_map(pid: str, s: Session = Depends(get_session)) -> PaperMap:
    return s.get(PaperMap, pid) or _404()


@app.post("/api/papers/{pid}/map")
def rebuild_map(pid: str, bg: BackgroundTasks, s: Session = Depends(get_session)) -> dict:
    s.get(Paper, pid) or _404()
    bg.add_task(build_map, pid)
    return {"status": "computing"}


@app.get("/api/papers/{pid}/blocks")
def get_blocks(pid: str, s: Session = Depends(get_session)) -> list[dict]:
    rows = s.exec(select(Block).where(Block.paper_id == pid).order_by(Block.order))
    return [{"id": b.block_id, "kind": b.kind, "section": b.section, "para": b.para,
             "text": b.text, "boxes": b.boxes} for b in rows]


# ---------------------------------------------------------------- review sessions (Socratic dialogue)
class NewSession(BaseModel):
    paper_id: str


class TurnRequest(BaseModel):
    text: str = ""
    action: str = ""  # "" | start | next | skip | confirm | deeper | goto:<dimension>


@app.post("/api/sessions")
def new_session(req: NewSession, s: Session = Depends(get_session)) -> dict:
    s.get(Paper, req.paper_id) or _404()
    rs = engine.create_session(req.paper_id)
    return {"id": rs.id, "paper_id": rs.paper_id}


@app.get("/api/papers/{pid}/sessions")
def list_sessions(pid: str, s: Session = Depends(get_session)) -> list[dict]:
    rows = s.exec(select(ReviewSession).where(ReviewSession.paper_id == pid).order_by(ReviewSession.updated_at.desc()))
    return [{"id": r.id, "updated_at": r.updated_at, "turn": (r.state or {}).get("turn", 0)} for r in rows]


@app.get("/api/sessions/{sid}")
def get_review_session(sid: str, s: Session = Depends(get_session)) -> dict:
    rs = s.get(ReviewSession, sid) or _404()
    return {"id": rs.id, "paper_id": rs.paper_id, "state": engine.public_state(rs.state or engine.new_state()),
            "messages": engine.transcript(sid)}


@app.post("/api/sessions/{sid}/turn")
def take_turn(sid: str, req: TurnRequest) -> StreamingResponse:
    def events():
        for ev in engine.run_turn(sid, req.text.strip(), req.action):
            yield f"data: {json.dumps(ev, default=str)}\n\n"
    return StreamingResponse(events(), media_type="text/event-stream",
                             headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"})


# ---------------------------------------------------------------- ledger, draft, scores, export
class UnitEdit(BaseModel):
    statement: str | None = None
    rationale: str | None = None
    dimension: str | None = None
    deleted: bool | None = None
    confirmed: bool | None = None


@app.patch("/api/sessions/{sid}/units/{uid}")
def patch_unit(sid: str, uid: str, req: UnitEdit) -> dict:
    try:
        return review.edit_unit(sid, uid, req.model_dump(exclude_none=True))
    except KeyError:
        _404()


@app.get("/api/sessions/{sid}/draft")
def get_draft(sid: str, s: Session = Depends(get_session)) -> dict:
    rs = s.get(ReviewSession, sid) or _404()
    return review.draft_view(rs.state or {})


@app.post("/api/sessions/{sid}/draft")
def make_draft(sid: str) -> dict:
    review.synthesize(sid)
    with Session(db_engine) as s:
        return review.draft_view(s.get(ReviewSession, sid).state)


class SentenceEdit(BaseModel):
    text: str | None = None
    status: str | None = None  # accepted | edited | rejected | proposed
    unit_ids: list[str] | None = None


@app.patch("/api/sessions/{sid}/draft/{sentence_id}")
def patch_sentence(sid: str, sentence_id: str, req: SentenceEdit) -> dict:
    try:
        return review.edit_sentence(sid, sentence_id, req.model_dump(exclude_none=True))
    except KeyError:
        _404()


class ScoreSet(BaseModel):
    value: float
    rationale: str = ""
    block_ids: list[str] = []


@app.put("/api/sessions/{sid}/scores/{field}")
def put_score(sid: str, field: str, req: ScoreSet) -> dict:
    if field not in review.SCORES:
        raise HTTPException(400, "unknown score field")
    return review.set_score(sid, field, req.value, req.rationale, req.block_ids)


@app.get("/api/sessions/{sid}/export")
def export_review(sid: str, format: str = "arr") -> dict:
    return review.export(sid, format)


def _404():
    raise HTTPException(404, "Not found")
