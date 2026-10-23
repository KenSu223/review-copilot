"""SQLite persistence (SQLModel). Event-style tables are append-only by convention."""
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import Column, JSON, event
from sqlmodel import Field, Session, SQLModel, create_engine

from .config import DB_PATH


def _now() -> datetime:
    return datetime.now(timezone.utc)


class Paper(SQLModel, table=True):
    id: str = Field(primary_key=True)  # sha256 prefix of the PDF bytes
    title: str = ""
    source: str = "upload"  # upload | arxiv:<id>
    filename: str = ""
    n_pages: int = 0
    page_sizes: list = Field(default_factory=list, sa_column=Column(JSON))  # [[w, h], ...] in PDF points
    parser: str = ""  # grobid-0.9.1 | pymupdf
    status: str = "parsing"  # parsing | ready | error
    error: str = ""
    hidden_text: list = Field(default_factory=list, sa_column=Column(JSON))  # injection-channel findings
    created_at: datetime = Field(default_factory=_now)


class PaperMap(SQLModel, table=True):
    paper_id: str = Field(primary_key=True)
    status: str = "computing"  # computing | ready | error
    data: dict = Field(default_factory=dict, sa_column=Column(JSON))
    call: dict = Field(default_factory=dict, sa_column=Column(JSON))
    error: str = ""
    created_at: datetime = Field(default_factory=_now)


class ReviewSession(SQLModel, table=True):
    id: str = Field(primary_key=True)
    paper_id: str = Field(index=True)
    state: dict = Field(default_factory=dict, sa_column=Column(JSON))
    created_at: datetime = Field(default_factory=_now)
    updated_at: datetime = Field(default_factory=_now)


class Event(SQLModel, table=True):
    """Append-only interaction trace (messages, analyses, checks, guard verdicts, edits)."""
    pk: Optional[int] = Field(default=None, primary_key=True)
    session_id: str = Field(index=True)
    turn: int = 0
    type: str = ""  # user_msg | copilot_msg | analyze | check | guard | unit_edit | score | ...
    payload: dict = Field(default_factory=dict, sa_column=Column(JSON))
    created_at: datetime = Field(default_factory=_now)


class Block(SQLModel, table=True):
    pk: Optional[int] = Field(default=None, primary_key=True)
    paper_id: str = Field(index=True)
    block_id: str = Field(index=True)  # s-0042: stable id the LLM cites
    order: int = 0
    kind: str = "sentence"  # sentence | heading | caption
    section: str = ""
    para: int = 0
    text: str = ""
    boxes: list = Field(default_factory=list, sa_column=Column(JSON))  # [{page, left, top, width, height}] in %


engine = create_engine(f"sqlite:///{DB_PATH}", connect_args={"check_same_thread": False})


@event.listens_for(engine, "connect")
def _sqlite_pragmas(dbapi_conn, _record):
    cur = dbapi_conn.cursor()
    cur.execute("PRAGMA journal_mode=WAL")
    cur.execute("PRAGMA foreign_keys=ON")
    cur.close()


def init_db() -> None:
    SQLModel.metadata.create_all(engine)


def get_session():
    with Session(engine) as session:
        yield session
