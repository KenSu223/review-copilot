"""Socratic turn pipeline:  Analyze (structured) -> Policy (deterministic code) -> Realize (cited) -> Guard.

run_turn() is a generator of SSE-style events: {"type": "status"|"message"|"error", ...}.
Everything the reviewer says and the copilot emits is appended to the Event trace.
"""
from __future__ import annotations

import logging
import re
import uuid
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone

from sqlalchemy.orm.attributes import flag_modified
from sqlmodel import Session, select

from .. import llm
from ..db import Event, Paper, PaperMap, ReviewSession, engine
from ..ingest import llm_blocks
from . import prompts as P
from .dimensions import DIM_BY_KEY, DIMENSIONS, ORDER

log = logging.getLogger(__name__)
MAX_TURNS_PER_DIM = 5
HISTORY_MESSAGES = 10

ANALYZE_SCHEMA = {
    "type": "object",
    "properties": {
        "act": {"type": "string", "enum": ["opinion", "fact_question", "verdict_request", "factual_claim_only", "unsure",
                                           "confirm", "meta_next", "meta_skip", "meta_deeper", "offtopic"]},
        "opinion_units": {"type": "array", "items": {
            "type": "object",
            "properties": {
                "statement": {"type": "string"},
                "rationale": {"type": "string"},
                "dimension": {"type": "string", "enum": ORDER},
                "polarity": {"type": "string", "enum": ["positive", "negative", "mixed", "neutral"]},
                "intensity": {"type": "string", "enum": ["hedged", "moderate", "strong"]},
                "independent": {"type": "boolean"},
            },
            "required": ["statement", "rationale", "dimension", "polarity", "intensity", "independent"],
            "additionalProperties": False,
        }},
        "factual_claims": {"type": "array", "items": {"type": "string"}},
        "question": {"type": "string", "description": "the factual or verdict question asked, if any, else ''"},
        "tension_with": {"type": "string"},
    },
    "required": ["act", "opinion_units", "factual_claims", "question", "tension_with"],
    "additionalProperties": False,
}

GUARD_SCHEMA = {
    "type": "object",
    "properties": {
        "verdict": {"type": "string", "enum": ["allow", "revise", "block"]},
        "violations": {"type": "array", "items": {"type": "string"}},
        "fix": {"type": "string"},
    },
    "required": ["verdict", "violations", "fix"],
    "additionalProperties": False,
}

MOVE_CHIPS = {
    "probe_evidence": ["Not sure"],
    "surface_facts": ["Go deeper", "Next dimension"],
    "answer_fact": ["Next dimension"],
    "after_check": ["Next dimension"],
    "perspective": ["Next dimension"],
    "confirm": ["That's accurate", "Let me add more", "Next dimension"],
    "unsure": ["Skip this dimension"],
    "reconcile": [],
    "refuse_redirect": [],
    "redirect": [],
    "close_all": ["Open review draft"],
}
ACTION_ACTS = {"next": "meta_next", "skip": "meta_skip", "confirm": "confirm", "deeper": "meta_deeper"}


# ---------------------------------------------------------------- state helpers
def new_state() -> dict:
    return {"dim_idx": 0, "turn": 0, "finished": False, "units": [], "checks": 0, "refusals": 0,
            "dims": {d["key"]: {"turns": 0, "surfaced": [], "perspective": False, "pending_confirm": False,
                                "skipped": False} for d in DIMENSIONS}}


def dim_status(state: dict, key: str) -> str:
    units = [u for u in state["units"] if u["dimension"] == key and not u.get("deleted")]
    if any(u["rationale"] for u in units) or (key == "summary" and units):
        return "covered"
    if units:
        return "partial"
    return "skipped" if state["dims"][key]["skipped"] else "open"


def public_state(state: dict) -> dict:
    cur = ORDER[min(state["dim_idx"], len(ORDER) - 1)]
    return {"current": cur, "finished": state["finished"], "turn": state["turn"],
            "dims": [{"key": d["key"], "label": d["label"], "arr_field": d["arr_field"], "status": dim_status(state, d["key"])}
                     for d in DIMENSIONS],
            "units": [u for u in state["units"] if not u.get("deleted")]}


def _now():
    return datetime.now(timezone.utc)


# ---------------------------------------------------------------- persistence
def create_session(paper_id: str) -> ReviewSession:
    with Session(engine) as s:
        rs = ReviewSession(id=uuid.uuid4().hex[:12], paper_id=paper_id, state=new_state())
        s.add(rs)
        s.commit()
        s.refresh(rs)
        return rs


def transcript(session_id: str) -> list[dict]:
    with Session(engine) as s:
        rows = s.exec(select(Event).where(Event.session_id == session_id,
                                          Event.type.in_(["user_msg", "copilot_msg"])).order_by(Event.pk))
        return [{"role": "reviewer" if e.type == "user_msg" else "copilot", "turn": e.turn, **e.payload} for e in rows]


def _log_event(s: Session, sid: str, turn: int, type_: str, payload: dict) -> None:
    s.add(Event(session_id=sid, turn=turn, type=type_, payload=payload))


# ---------------------------------------------------------------- policy
def _advance(state: dict) -> None:
    state["dim_idx"] += 1
    while state["dim_idx"] < len(ORDER) and dim_status(state, ORDER[state["dim_idx"]]) == "covered":
        state["dim_idx"] += 1
    if state["dim_idx"] >= len(ORDER):
        state["finished"] = True


def _inventory_text(dim: dict, pmap: dict, surfaced: list[str]) -> tuple[str, list[str]]:
    lines, keys = [], []
    for cat in dim["inventory"]:
        for i, it in enumerate(pmap.get(cat, [])):
            k = f"{cat}:{i}"
            if k in surfaced:
                continue
            lines.append(f"- ({cat}) {it['text']}  [see blocks {', '.join(it['block_ids'][:4])}]")
            keys.append(k)
            if len(lines) >= 6:
                break
    if not lines and dim["inventory"]:
        lines.append(f"- The paper map lists nothing under {', '.join(dim['inventory'])}; you may say you could not locate it.")
    return "\n".join(lines), keys


def decide(state: dict, a: dict, text: str, pmap: dict, new_units: list[dict], checks: list[dict]) -> tuple[str, dict]:
    """Deterministic move selection. Returns (move, params for the instruction template)."""
    if state["finished"] and not new_units:
        return "close_all", {}
    # Reviewer-led: if they start talking about another dimension, follow them there.
    if new_units and not any(u["dimension"] == ORDER[min(state["dim_idx"], len(ORDER) - 1)] for u in new_units):
        state["dim_idx"], state["finished"] = ORDER.index(new_units[0]["dimension"]), False
    key = ORDER[state["dim_idx"]]
    dim, d = DIM_BY_KEY[key], state["dims"][key]
    act = a.get("act", "opinion")
    p = {"dim_label": dim["label"], "opener": dim["opener"], "target": text[:400]}

    if act == "verdict_request":
        state["refusals"] += 1
        return "refuse_redirect", {**p, "target": a.get("question") or text[:300]}
    if act in ("meta_next", "meta_skip") or (act == "confirm" and d["pending_confirm"]):
        d["skipped"] = act == "meta_skip" and dim_status(state, key) == "open"
        d["pending_confirm"] = False
        _advance(state)
        if state["finished"]:
            return "close_all", {}
        nd = DIM_BY_KEY[ORDER[state["dim_idx"]]]
        return "commit_open", {"dim_label": nd["label"], "opener": nd["opener"]}
    if act == "fact_question":
        return "answer_fact", {**p, "target": a.get("question") or text[:300]}
    if checks:
        return "after_check", {**p, "checks": "\n".join(f"- \"{c['claim']}\" -> {c['verdict']}" for c in checks)}
    if act == "unsure":
        return "unsure", p
    if act == "offtopic":
        return "redirect", p
    if a.get("tension_with"):
        earlier = next((u for u in state["units"] if u["id"] == a["tension_with"]), None)
        if earlier and new_units:
            return "reconcile", {**p, "earlier": earlier["statement"], "target": new_units[0]["statement"]}

    in_dim = [u for u in new_units if u["dimension"] == key] or new_units
    if d["turns"] >= MAX_TURNS_PER_DIM or act == "confirm":  # soft cap: summarize and offer to move on
        return _confirm(state, key, p)
    if in_dim:
        lacking = next((u for u in in_dim if not u["rationale"] and key != "summary"), None)
        if lacking:
            return "probe_evidence", {**p, "target": lacking["statement"]}
    if dim["inventory"] and len(d["surfaced"]) < 3 and (in_dim or act == "meta_deeper"):
        inv, keys = _inventory_text(dim, pmap, d["surfaced"])
        d["surfaced"] += keys[:3]
        return "surface_facts", {**p, "inventory": inv}
    if in_dim and not d["perspective"] and key in ("soundness", "strengths", "weaknesses"):
        d["perspective"] = True
        return "perspective", {**p, "target": in_dim[0]["statement"]}
    if in_dim or dim_status(state, key) != "open":
        return _confirm(state, key, p)
    return "probe_evidence", p


def _confirm(state: dict, key: str, p: dict) -> tuple[str, dict]:
    units = [u for u in state["units"] if u["dimension"] == key and not u.get("deleted")]
    if not units:
        return "probe_evidence", p
    d = state["dims"][key]
    if d.get("confirms", 0) >= 1:  # already confirmed once: additions are recorded; move on instead of looping
        d["pending_confirm"] = False
        _advance(state)
        if state["finished"]:
            return "close_all", {}
        nd = DIM_BY_KEY[ORDER[state["dim_idx"]]]
        return "commit_open", {"dim_label": nd["label"], "opener": nd["opener"]}
    d["confirms"] = d.get("confirms", 0) + 1
    d["pending_confirm"] = True
    recorded = "\n".join(f"- {u['id']}: \"{u['statement']}\"" + (f" because \"{u['rationale']}\"" if u["rationale"] else "")
                         for u in units)
    return "confirm", {**p, "recorded": recorded}


# ---------------------------------------------------------------- LLM steps
def _analyze(text: str, state: dict, last_copilot: str) -> dict:
    key = ORDER[min(state["dim_idx"], len(ORDER) - 1)]
    earlier = "\n".join(f"{u['id']} [{u['dimension']}]: {u['statement']}" for u in state["units"][-12:]) or "(none)"
    user = (f"Current dimension: {key}\nCopilot's previous message: \"{last_copilot[:800]}\"\n"
            f"Earlier recorded units:\n{earlier}\n\nReviewer message:\n\"\"\"{text}\"\"\"")
    data, _ = llm.structured("analyze", P.ANALYZE_SYSTEM, user, ANALYZE_SCHEMA)
    return data


def _inline(segments: list[dict]) -> str:
    return "".join(seg["text"] + (" [cited]" if seg["cites"] else "") for seg in segments)


def _guard(draft: str, move: str) -> dict:
    user = f"Copilot move: {move}\nDraft message (\"[cited]\" marks text grounded with a paper citation):\n<<<{draft}>>>"
    data, _ = llm.structured("guard", P.GUARD_SYSTEM, user, GUARD_SCHEMA)
    return data


def _check_statement(claim: str, blocks, title) -> dict:
    out = llm.cited("statement_check", P.STATEMENT_CHECK_SYSTEM, blocks, title, [], f'Reviewer statement to check: "{claim}"')
    m = re.search(r"VERDICT:\s*(supported|partly_supported|contradicted|not_located)", out.text)
    verdict = m.group(1) if m else "not_located"
    segs = []
    for seg in out.segments:
        t = re.sub(r"VERDICT:\s*\w+\s*", "", seg["text"])
        if t.strip():
            segs.append({"text": t, "cites": seg["cites"]})
    return {"claim": claim, "verdict": verdict, "segments": segs}


def _history(session_id: str) -> list[dict]:
    msgs = transcript(session_id)[-HISTORY_MESSAGES:]
    hist = []
    for m in msgs:
        role = "user" if m["role"] == "reviewer" else "assistant"
        text = m.get("text") or "".join(seg["text"] for seg in m.get("segments", []))
        if hist and hist[-1]["role"] == role:
            hist[-1]["content"] += "\n" + text
        else:
            hist.append({"role": role, "content": text or "(empty)"})
    if hist and hist[0]["role"] == "assistant":
        hist.insert(0, {"role": "user", "content": "[Session started]"})
    if hist and hist[-1]["role"] == "user":  # the latest reviewer message is passed separately
        hist.pop()
    return hist


# ---------------------------------------------------------------- the turn
def run_turn(session_id: str, text: str = "", action: str = ""):
    with Session(engine) as s:
        rs = s.get(ReviewSession, session_id)
        if rs is None:
            yield {"type": "error", "message": "session not found"}
            return
        state = rs.state or new_state()
        paper = s.get(Paper, rs.paper_id)
        pm = s.get(PaperMap, rs.paper_id)
        pmap = pm.data if pm and pm.status == "ready" else {}
        blocks = [(b.block_id, b.text) for b in llm_blocks(s, rs.paper_id)]
        title = paper.title

    if action.startswith("goto:"):
        target = action.split(":", 1)[1]
        if target in ORDER:
            state["dim_idx"], state["finished"] = ORDER.index(target), False
        action, text = "start", ""

    import time as _time
    t_start = _time.time()
    timing: dict[str, float] = {}
    state["turn"] += 1
    turn = state["turn"]
    last_copilot = next((m.get("plain", "") for m in reversed(transcript(session_id)) if m["role"] == "copilot"), "")
    history = _history(session_id)

    with Session(engine) as s:
        if text:
            _log_event(s, session_id, turn, "user_msg", {"text": text, "action": action})
            s.commit()

    # 1) Analyze
    new_units, checks = [], []
    if action == "start" or not text:
        analysis = {"act": "start"}
    elif action in ACTION_ACTS:
        analysis = {"act": ACTION_ACTS[action], "opinion_units": [], "factual_claims": []}
    else:
        yield {"type": "status", "step": "analyze", "label": "Reading your message…"}
        try:
            _t = _time.time()
            analysis = _analyze(text, state, last_copilot)
            timing["analyze"] = round(_time.time() - _t, 2)
        except Exception as exc:
            log.exception("analyze failed")
            analysis = {"act": "opinion", "opinion_units": [], "factual_claims": [], "error": str(exc)[:200]}
        cur_key = ORDER[min(state["dim_idx"], len(ORDER) - 1)]
        for u in analysis.get("opinion_units", []):
            if not u.get("independent", True):
                continue  # bare assent / echo of the copilot never becomes the reviewer's opinion
            unit = {"id": f"U{len(state['units']) + 1}", "turn": turn, "dimension": u.get("dimension") or cur_key,
                    "statement": u["statement"], "rationale": u.get("rationale", ""), "polarity": u.get("polarity", "neutral"),
                    "intensity": u.get("intensity", "moderate"), "confirmed": False, "source": "dialogue"}
            state["units"].append(unit)
            new_units.append(unit)
        claims = [c for c in analysis.get("factual_claims", []) if c.strip()][:2]
        if claims:
            yield {"type": "status", "step": "check", "label": "Checking your statement against the paper…"}
            _t = _time.time()
            with ThreadPoolExecutor(max_workers=2) as ex:
                checks = list(ex.map(lambda c: _check_statement(c, blocks, title), claims))
            timing["checks"] = round(_time.time() - _t, 2)
            state["checks"] += len(checks)

    # 2) Policy
    if analysis.get("act") == "start":
        if state["finished"]:
            move, params = "close_all", {}
        else:
            dim = DIM_BY_KEY[ORDER[state["dim_idx"]]]
            move, params = "commit_open", {"dim_label": dim["label"], "opener": dim["opener"]}
    else:
        move, params = decide(state, analysis, text, pmap, new_units, checks)
    cur_key = ORDER[min(state["dim_idx"], len(ORDER) - 1)]
    state["dims"][cur_key]["turns"] += 1

    # 3) Realize (+ 4) Guard with one revision)
    instruction = P.MOVE_INSTRUCTIONS[move].format(**{k: v for k, v in params.items()})
    reviewer_line = f'Reviewer\'s latest message (turn T{turn}): "{text}"\n' if text else "(No reviewer message: start of this dimension.)\n"
    user_text = f"[Current dimension: {DIM_BY_KEY[cur_key]['label']}] [Move: {move}]\n{reviewer_line}\nInstruction: {instruction}"
    yield {"type": "status", "step": "realize", "label": "Looking up the paper…" if move in ("surface_facts", "answer_fact", "refuse_redirect", "after_check") else "Drafting a question…"}
    guard_log = []
    out = None
    for attempt in range(2):
        try:
            _t = _time.time()
            out = llm.cited("realize", P.FIREWALL_RULES, blocks, title, history, user_text)
            timing[f"realize{attempt}"] = round(_time.time() - _t, 2)
            timing[f"realize{attempt}_cache_read"] = out.log.cache_read if out.log else 0
        except Exception as exc:
            log.exception("realize failed")
            yield {"type": "error", "message": f"LLM error: {exc}"}
            return
        yield {"type": "status", "step": "guard", "label": "Checking neutrality…"}
        try:
            _t = _time.time()
            g = _guard(_inline(out.segments), move)
            timing[f"guard{attempt}"] = round(_time.time() - _t, 2)
        except Exception as exc:
            g = {"verdict": "allow", "violations": [], "fix": f"guard unavailable: {exc}"}
        guard_log.append({"attempt": attempt, **g, "draft": out.text})
        if g["verdict"] == "allow":
            break
        user_text += f"\n\nYour previous draft violated: {', '.join(g['violations'])}. Fix: {g['fix']} Rewrite it."
        out = None if attempt == 1 else out
    if out is None or guard_log[-1]["verdict"] != "allow":
        dim = DIM_BY_KEY[cur_key]
        fallback = dim["opener"] if move == "commit_open" else f"How, if at all, would you like to develop your view on {dim['label'].lower()}?"
        segments, fell_back = [{"text": fallback, "cites": []}], True
    else:
        segments, fell_back = out.segments, False

    chips = (DIM_BY_KEY[ORDER[state["dim_idx"]]]["chips"] + ["Skip this dimension"]) if move == "commit_open" else MOVE_CHIPS.get(move, [])
    plain = "".join(seg["text"] for seg in segments)
    message = {"segments": segments, "plain": plain, "move": move, "dimension": cur_key, "chips": chips,
               "checks": checks, "new_units": [u["id"] for u in new_units], "fallback": fell_back}
    timing["total"] = round(_time.time() - t_start, 2)
    message["timing"] = timing

    from .review import session_lock
    with session_lock(session_id), Session(engine) as s:
        latest = (s.get(ReviewSession, session_id).state or {})
        for key in ("draft", "scores"):  # keep edits made while this turn was running
            if key in latest:
                state[key] = latest[key]
        edited = {u["id"]: u for u in latest.get("units", [])}
        state["units"] = [edited.get(u["id"], u) for u in state["units"]]
        if analysis.get("act") != "start":
            _log_event(s, session_id, turn, "analyze", analysis)
        for c in checks:
            _log_event(s, session_id, turn, "check", c)
        _log_event(s, session_id, turn, "guard", {"move": move, "attempts": guard_log})
        _log_event(s, session_id, turn, "copilot_msg", message)
        rs = s.get(ReviewSession, session_id)
        rs.state, rs.updated_at = dict(state), _now()
        flag_modified(rs, "state")
        s.add(rs)
        s.commit()

    yield {"type": "message", "turn": turn, "message": message, "state": public_state(state)}
