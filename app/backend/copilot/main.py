"""FastAPI app: paper ingest, reviewer profile, evidence-led review sessions, draft, scores, export."""
import json
import logging

from fastapi import BackgroundTasks, Depends, FastAPI, File, HTTPException, UploadFile
from fastapi.responses import FileResponse, StreamingResponse
from pydantic import BaseModel, Field
from sqlmodel import Session, select

from .config import PDF_DIR
from .db import Block, Paper, PaperMap, ReviewSession, get_session, init_db
from .dialogue import criteria as C
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


# ---------------------------------------------------------------- reviewer profile (onboarding)
@app.get("/api/profile")
def get_profile() -> dict:
    return {"profile": engine.load_profile(), "options": {
        "levels": C.LEVELS, "criteria": [{k: c[k] for k in ("key", "label", "plain", "where")} for c in C.CRITERIA],
        "starter_lens": C.STARTER_LENS, "familiarity": C.FAMILIARITY, "read_status": C.READ_STATUS,
        "budgets": list(C.CARDS_FOR_BUDGET), "field_help": C.FIELD_HELP, "field_help_source": C.FIELD_HELP_SOURCE}}


class ProfileBody(BaseModel):
    data: dict


@app.put("/api/profile")
def put_profile(req: ProfileBody) -> dict:
    data = dict(req.data)
    if data.get("level") not in C.LEVELS:
        raise HTTPException(400, "level must be one of L0-L3")
    data["criteria"] = [c for c in data.get("criteria", []) if c.get("key") in C.CRITERION][:5]
    return {"profile": engine.save_profile(data)}


# ---------------------------------------------------------------- review sessions (evidence-led dialogue)
class NewSession(BaseModel):
    paper_id: str
    paper_ctx: dict = {}  # familiarity, read_status, time_budget
    flow: str = "evidence"  # evidence | commit_first (legacy, for the A/B comparison)


class TurnRequest(BaseModel):
    text: str = ""
    # "" | start | react:<looks_good|mixed|off|not_sure> | more | skip | done | keep | card:<id>
    action: str = ""


@app.post("/api/sessions")
def new_session(req: NewSession, s: Session = Depends(get_session)) -> dict:
    s.get(Paper, req.paper_id) or _404()
    if req.flow not in ("evidence", "commit_first"):
        raise HTTPException(400, "unknown flow")
    rs = engine.create_session(req.paper_id, req.paper_ctx, req.flow)
    return {"id": rs.id, "paper_id": rs.paper_id}


@app.get("/api/papers/{pid}/sessions")
def list_sessions(pid: str, s: Session = Depends(get_session)) -> list[dict]:
    rows = s.exec(select(ReviewSession).where(ReviewSession.paper_id == pid).order_by(ReviewSession.updated_at.desc()))
    return [{"id": r.id, "updated_at": r.updated_at, "turn": (r.state or {}).get("turn", 0),
             "flow": (r.state or {}).get("flow", "commit_first")} for r in rows
            if (r.state or {}).get("origin", "app") != "eval"]  # persona-suite sessions stay out of the app


@app.get("/api/sessions/{sid}")
def get_review_session(sid: str, s: Session = Depends(get_session)) -> dict:
    rs = s.get(ReviewSession, sid) or _404()
    return {"id": rs.id, "paper_id": rs.paper_id, "state": engine.public_state(rs.state or {}),
            "messages": engine.transcript(sid)}


@app.post("/api/sessions/{sid}/turn")
def take_turn(sid: str, req: TurnRequest) -> StreamingResponse:
    def events():
        for ev in engine.run_turn(sid, req.text.strip(), req.action):
            yield f"data: {json.dumps(ev, default=str)}\n\n"
    return StreamingResponse(events(), media_type="text/event-stream",
                             headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"})


class RailOp(BaseModel):
    op: str  # up | down | skip | restore


@app.post("/api/sessions/{sid}/agenda/{card_id}")
def agenda_rail(sid: str, card_id: str, req: RailOp) -> dict:
    if engine.turn_running(sid):
        raise HTTPException(409, "A turn is in progress; try again in a moment.")
    try:
        return engine.rail(sid, card_id, req.op)
    except KeyError:
        _404()


class FactsBody(BaseModel):
    fact_ids: list[str]


@app.post("/api/sessions/{sid}/facts")
def confirm_facts(sid: str, req: FactsBody) -> dict:
    return engine.confirm_facts(sid, req.fact_ids)


class CheckConfirm(BaseModel):
    turn: int
    index: int = 0


@app.post("/api/sessions/{sid}/checks/confirm")
def confirm_check(sid: str, req: CheckConfirm) -> dict:
    try:
        return engine.confirm_check(sid, req.turn, req.index)
    except KeyError:
        _404()


class RememberBody(BaseModel):
    criterion: str
    accept: bool


@app.post("/api/sessions/{sid}/remember")
def remember(sid: str, req: RememberBody) -> dict:
    return engine.remember(sid, req.criterion, req.accept)


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


class RegisterBody(BaseModel):
    reg: str = Field(alias="register")  # words | polished | formal
    sentence_id: str | None = None


@app.put("/api/sessions/{sid}/register")
def put_register(sid: str, req: RegisterBody) -> dict:
    try:
        review.set_register(sid, req.reg, req.sentence_id)
    except ValueError:
        raise HTTPException(400, "unknown register")
    with Session(db_engine) as s:
        return review.draft_view(s.get(ReviewSession, sid).state)


@app.post("/api/sessions/{sid}/units/rephrase")
def rephrase_units(sid: str, req: RegisterBody) -> dict:
    try:
        return review.rephrase_units(sid, req.reg)
    except ValueError:
        raise HTTPException(400, "unknown register")


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
