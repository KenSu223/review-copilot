"""Review synthesis with opinion provenance, the drift check, scores, and export.

Contract (ARR: no generated first drafts; paraphrasing the reviewer is fine):
- Every evaluative sentence must cite >= 1 of the reviewer's opinion units (their own words).
- Factual sentences may only use paper facts the reviewer explicitly confirmed (P#: the paper's stated contributions or
  the evidence of a statement check, ticked by the reviewer; own provenance type, disclosed on export).
- Every sentence comes in three registers, from the reviewer's own casual words to formal review prose
  (the faithful-to-professional slider, conversation_redesign.md §6); every register is drift-checked.
- No new evaluative adjectives; hedges and intensity preserved. Fields the reviewer never addressed stay empty.
- Scores are entered by the reviewer only; the system never proposes them.
"""
from __future__ import annotations

import json
import threading
import uuid
from collections import defaultdict
from contextlib import contextmanager

from sqlalchemy.orm.attributes import flag_modified
from sqlmodel import Session, select

from .. import llm
from ..db import Block, Event, Paper, ReviewSession, engine
from .dimensions import DIMENSIONS

FIELDS = [
    ("summary", "Paper Summary"),
    ("strengths", "Summary of Strengths"),
    ("weaknesses", "Summary of Weaknesses"),
    ("comments", "Comments, Suggestions and Typos"),
    ("soundness", "Soundness — justification"),
    ("excitement", "Excitement — justification"),
    ("reproducibility", "Reproducibility — justification"),
    ("limitations_ethics", "Limitations and Societal Impact / Ethical Concerns"),
]
FIELD_KEYS = [k for k, _ in FIELDS]
SCORES = {
    "soundness": {"label": "Soundness", "values": [1, 1.5, 2, 2.5, 3, 3.5, 4, 4.5, 5]},
    "excitement": {"label": "Excitement", "values": [1, 1.5, 2, 2.5, 3, 3.5, 4, 4.5, 5]},
    "overall": {"label": "Overall Assessment", "values": [1, 1.5, 2, 2.5, 3, 3.5, 4, 4.5, 5]},
    "reproducibility": {"label": "Reproducibility", "values": [1, 2, 3, 4, 5]},
    "confidence": {"label": "Reviewer Confidence", "values": [1, 2, 3, 4, 5]},
}

SYNTH_SCHEMA = {
    "type": "object",
    "properties": {"sections": {"type": "array", "items": {
        "type": "object",
        "properties": {
            "field": {"type": "string", "enum": FIELD_KEYS},
            "sentences": {"type": "array", "items": {
                "type": "object",
                "properties": {
                    "words": {"type": "string"},
                    "polished": {"type": "string"},
                    "formal": {"type": "string"},
                    "kind": {"type": "string", "enum": ["opinion", "fact", "connective"]},
                    "unit_ids": {"type": "array", "items": {"type": "string"}},
                    "block_ids": {"type": "array", "items": {"type": "string"}},
                },
                "required": ["words", "polished", "formal", "kind", "unit_ids", "block_ids"],
                "additionalProperties": False,
            }},
        },
        "required": ["field", "sentences"],
        "additionalProperties": False,
    }}},
    "required": ["sections"],
    "additionalProperties": False,
}

SYNTH_SYSTEM = """You organize a peer reviewer's OWN statements into an outline for the ACL Rolling Review form.
The statements come from a casual chat. You are not a reviewer and you have no opinions. You may only rephrase what
the reviewer said. Write every sentence in three registers:
- words: the reviewer's own words, as close to verbatim as possible; fix typos and join fragments only.
- polished: grammatical review prose in a neutral register; same claims, same polarity, same hedges and intensity.
- formal: formal ACL-review style; same constraints. Formality never adds certainty, severity, or new judgments.
Rules:
- Every opinion sentence must list the unit_ids (U#) it is based on, and must be entailed by those units.
- Preserve the reviewer's polarity, hedges, and intensity exactly ("seems", "somewhat", "major"). Do not strengthen,
  soften, or generalize. Do not add evaluative adjectives the reviewer did not use.
- Fact sentences may only restate paper facts the reviewer confirmed (units P#): list the P# in unit_ids and its block
  ids in block_ids. The paper's stated contributions belong in the summary; other confirmed facts go with the opinions
  they relate to. Never state any other fact about the paper.
- Write in the reviewer's own voice, as reviewers write reviews (first person or impersonal: "The experiments
  seem illustrative."), never in the third person ("The reviewer thinks...").
- Keep sentences short; prefer the reviewer's wording. One idea per sentence. Weaknesses as separate sentences so
  they can be numbered. Do not repeat the same sentence in several fields; justification fields stay brief.
- Map units to fields: summary units -> summary; positive points -> strengths; negative points -> weaknesses;
  soundness/excitement/reproducibility/limitations_ethics units -> the matching justification field (and also
  strengths/weaknesses when they are clearly a strength or weakness); suggestions or typos -> comments.
- Omit a field entirely if no unit supports it. Never invent content to fill a field."""

ENTAIL_SCHEMA = {
    "type": "object",
    "properties": {"results": {"type": "array", "items": {
        "type": "object",
        "properties": {
            "sid": {"type": "string"},
            "entailed": {"type": "boolean"},
            "polarity": {"type": "string", "enum": ["preserved", "changed"]},
            "intensity": {"type": "string", "enum": ["preserved", "strengthened", "softened"]},
            "note": {"type": "string"},
        },
        "required": ["sid", "entailed", "polarity", "intensity", "note"],
        "additionalProperties": False,
    }}},
    "required": ["results"],
    "additionalProperties": False,
}

ENTAIL_SYSTEM = """For each draft review sentence (ids look like <sentence>:<register>), compare it ONLY with the reviewer's
own statements it cites.
entailed: is every evaluative claim in the sentence supported by those statements (no added judgments)?
polarity: preserved or changed. intensity: preserved, strengthened (more certain/severe than the reviewer said),
or softened. note: one short phrase naming any drift (e.g., "'a bit unclear' -> 'lacks clarity'")."""


REGISTERS = ["words", "polished", "formal"]
REPHRASE_SCHEMA = {
    "type": "object",
    "properties": {"items": {"type": "array", "items": {"type": "object", "properties": {
        "uid": {"type": "string"}, "text": {"type": "string"}},
        "required": ["uid", "text"], "additionalProperties": False}}},
    "required": ["items"],
    "additionalProperties": False,
}
REPHRASE_SYSTEM = """Rephrase each of a peer reviewer's own casual statements in the requested register, one sentence each.
polished: grammatical review prose in a neutral register. formal: formal ACL-review style.
Keep the same claim, polarity, hedges, and intensity. Add no judgments, no certainty, no severity. First person or
impersonal, never "the reviewer"."""

_LOCKS: dict[str, threading.Lock] = defaultdict(threading.Lock)


@contextmanager
def session_lock(sid: str):
    """Serialize read-modify-write of a session's state (edits can arrive concurrently)."""
    with _LOCKS[sid]:
        yield


def _load(sid: str):
    with Session(engine) as s:
        rs = s.get(ReviewSession, sid)
        if rs is None:
            raise KeyError(sid)
        return rs.state or {}, rs.paper_id


def _save(sid: str, state: dict, event: tuple[str, dict] | None = None) -> None:
    with Session(engine) as s:
        rs = s.get(ReviewSession, sid)
        rs.state = dict(state)
        flag_modified(rs, "state")
        s.add(rs)
        if event:
            s.add(Event(session_id=sid, turn=state.get("turn", 0), type=event[0], payload=event[1]))
        s.commit()


def edit_unit(sid: str, uid: str, changes: dict) -> dict:
    with session_lock(sid):
        return _edit_unit(sid, uid, changes)


def _edit_unit(sid: str, uid: str, changes: dict) -> dict:
    state, _ = _load(sid)
    unit = next((u for u in state.get("units", []) if u["id"] == uid), None)
    if unit is None:
        raise KeyError(uid)
    before = dict(unit)
    for k in ("statement", "rationale", "dimension", "deleted", "confirmed"):
        if k in changes:
            unit[k] = changes[k]
    unit["source"] = "dialogue+edited" if any(k in changes for k in ("statement", "rationale")) else unit["source"]
    _save(sid, state, ("unit_edit", {"id": uid, "before": before, "after": dict(unit)}))
    return unit


def set_score(sid: str, field: str, value, rationale: str = "", block_ids: list | None = None) -> dict:
    with session_lock(sid):
        return _set_score(sid, field, value, rationale, block_ids)


def _set_score(sid: str, field: str, value, rationale: str = "", block_ids: list | None = None) -> dict:
    state, _ = _load(sid)
    scores = state.setdefault("scores", {})
    prev = scores.get(field, {}).get("value")
    scores[field] = {"value": value, "rationale": rationale, "block_ids": block_ids or [], "previous": prev}
    _save(sid, state, ("score", {"field": field, "value": value, "previous": prev, "rationale": rationale,
                                 "block_ids": block_ids or []}))
    return scores[field]


def synthesize(sid: str) -> dict:
    state, pid = _load(sid)
    units = [u for u in state.get("units", []) if not u.get("deleted")]
    with Session(engine) as s:
        checks = [{**e.payload, "turn": e.turn} for e in s.exec(select(Event).where(Event.session_id == sid, Event.type == "check"))]
        blocks = {b.block_id: b.text for b in s.exec(select(Block).where(Block.paper_id == pid))}
    # Paper facts enter only when the reviewer confirmed them (P# units); statement checks are used only for conflict flags.
    unit_lines = "\n".join(
        (f"{u['id']} [confirmed paper fact; blocks {', '.join(u.get('block_ids', []))}]: \"{u['statement']}\""
         if u.get("source") == "paper_fact" else
         f"{u['id']} [{u['dimension']}, {u['polarity']}, {u['intensity']}]: \"{u['statement']}\""
         + (f" because \"{u['rationale']}\"" if u.get("rationale") else "")) for u in units) or "(none)"
    user = f"Reviewer's opinion units and confirmed paper facts:\n{unit_lines}"
    data, call = llm.structured("synthesize", SYNTH_SYSTEM, user, SYNTH_SCHEMA)

    register = (state.get("draft") or {}).get("register", "polished")
    valid_u, valid_b = {u["id"] for u in units}, set(blocks)
    sections = []
    for sec in data.get("sections", []):
        sents = []
        for st in sec.get("sentences", []):
            uids = [x for x in st.get("unit_ids", []) if x in valid_u]
            bids = [x for x in st.get("block_ids", []) if x in valid_b]
            unsourced = (st["kind"] == "opinion" and not uids) or (st["kind"] == "fact" and not bids)
            variants = {r: st[r].strip() for r in REGISTERS}
            sents.append({"sid": uuid.uuid4().hex[:8], "variants": variants, "register": None,
                          "text": variants[register], "kind": st["kind"], "unit_ids": uids, "block_ids": bids,
                          "status": "proposed", "unsourced": unsourced, "drift": None, "drifts": {},
                          "original": variants[register]})
        if sents:
            sections.append({"field": sec["field"], "sentences": sents})
    _entailment(sections, {u["id"]: u for u in units}, register)
    _flag_check_conflicts(sections, units, checks)
    used = {x for sec in sections for st in sec["sentences"] for x in st["unit_ids"]}
    draft = {"sections": sections, "register": register,
             "unused_units": [u["id"] for u in units if u["id"] not in used], "model_call": call.__dict__}
    state["draft"] = draft
    _save(sid, state, ("draft", {"n_sentences": sum(len(s["sentences"]) for s in sections), "model": call.model}))
    return draft


def set_register(sid: str, register: str, sentence_id: str | None = None) -> dict:
    """Faithful-to-professional slider: globally, or for one sentence. Edited sentences keep the reviewer's text."""
    if register not in REGISTERS:
        raise ValueError(register)
    with session_lock(sid):
        state, _ = _load(sid)
        draft = state.get("draft") or {}
        if sentence_id is None:
            draft["register"] = register
        for sec in draft.get("sections", []):
            for st in sec["sentences"]:
                if sentence_id is not None and st["sid"] != sentence_id:
                    continue
                if sentence_id is not None:
                    st["register"] = register
                eff = st.get("register") or draft.get("register", "polished")
                if st["status"] != "edited" and st.get("variants"):
                    st["text"] = st["variants"][eff]
                    st["drift"] = st.get("drifts", {}).get(eff)
        _save(sid, state, ("register", {"register": register, "sentence": sentence_id}))
        return draft


def rephrase_units(sid: str, register: str) -> dict:
    """My opinions panel: each recorded statement in the chosen register, drift-checked; cached per unit."""
    if register not in REGISTERS:
        raise ValueError(register)
    state, _ = _load(sid)
    units = [u for u in state.get("units", []) if not u.get("deleted") and u.get("source") != "paper_fact"]
    cache = state.get("unit_variants", {})
    todo = [u for u in units if register != "words" and register not in cache.get(u["id"], {})]
    if todo:
        user = f"Register: {register}\n" + "\n".join(
            f"{u['id']}: \"{u['statement']}\"" + (f" because \"{u['rationale']}\"" if u.get("rationale") else "") for u in todo)
        data, _ = llm.structured("rephrase", REPHRASE_SYSTEM, user, REPHRASE_SCHEMA)
        got = {it["uid"]: it["text"].strip() for it in data.get("items", [])}
        items = [f"{u['id']}:{register}: SENTENCE: \"{got[u['id']]}\"\n   REVIEWER SAID: \"{u['statement']}\""
                 + (f" because \"{u['rationale']}\"" if u.get("rationale") else "") for u in todo if u["id"] in got]
        drift = {}
        if items:
            try:
                d, _ = llm.structured("entailment", ENTAIL_SYSTEM, "\n".join(items), ENTAIL_SCHEMA)
                drift = {r["sid"].split(":")[0]: r for r in d.get("results", [])}
            except Exception:
                drift = {}
        with session_lock(sid):
            state, _ = _load(sid)
            cache = state.setdefault("unit_variants", {})
            for uid, text in got.items():
                cache.setdefault(uid, {})[register] = {"text": text, "drift": drift.get(uid)}
            _save(sid, state)
    out = {}
    for u in units:
        if register == "words":
            out[u["id"]] = {"text": u["statement"], "drift": None}
        elif register in cache.get(u["id"], {}):
            out[u["id"]] = cache[u["id"]][register]
    return {"register": register, "units": out}


def _flag_check_conflicts(sections: list, units: list, checks: list) -> None:
    """Objective flag: a sentence built on a unit from a turn whose factual statement the paper contradicted.
    The reviewer decides what to do; the system never removes it."""
    by_turn: dict[int, list] = {}
    for c in checks:
        if c.get("verdict") in ("contradicted", "partly_supported"):
            by_turn.setdefault(c.get("turn", -1), []).append(c)
    turn_of = {u["id"]: u["turn"] for u in units}
    stop = {"the", "a", "an", "and", "or", "of", "to", "in", "is", "are", "it", "they", "this", "that", "i", "any", "what", "no", "not"}

    def words(t: str) -> set:
        return {w for w in "".join(ch.lower() if ch.isalnum() else " " for ch in t).split() if w not in stop and len(w) > 2}

    for sec in sections:
        for st in sec["sentences"]:
            sw, conf = words(st["text"]), []
            for uid in st["unit_ids"]:
                for c in by_turn.get(turn_of.get(uid), []):
                    cw = words(c["claim"])
                    if cw and len(sw & cw) / len(cw) >= 0.4:  # the sentence restates the checked claim
                        conf.append({"claim": c["claim"], "verdict": c["verdict"], "turn": c.get("turn")})
            st["check_conflicts"] = conf


def _entailment(sections: list, units: dict, register: str) -> None:
    """Drift check of every register of every opinion sentence against the reviewer's own statements."""
    items = []
    for sec in sections:
        for st in sec["sentences"]:
            if st["kind"] == "opinion" and st["unit_ids"]:
                src = " | ".join(f"\"{units[u]['statement']}\"" + (f" because \"{units[u]['rationale']}\"" if units[u].get("rationale") else "")
                                 for u in st["unit_ids"] if u in units)
                for r in REGISTERS:
                    items.append(f"{st['sid']}:{r}: SENTENCE: \"{st['variants'][r]}\"\n   REVIEWER SAID: {src}")
    if not items:
        return
    try:
        data, _ = llm.structured("entailment", ENTAIL_SYSTEM, "\n".join(items), ENTAIL_SCHEMA)
    except Exception:
        return
    for r in data.get("results", []):
        sid_, _, reg = r["sid"].partition(":")
        for sec in sections:
            for st in sec["sentences"]:
                if st["sid"] == sid_ and reg in REGISTERS:
                    st["drifts"][reg] = r
    for sec in sections:
        for st in sec["sentences"]:
            st["drift"] = st["drifts"].get(st.get("register") or register)


def edit_sentence(sid: str, sentence_id: str, changes: dict) -> dict:
    with session_lock(sid):
        return _edit_sentence(sid, sentence_id, changes)


def _edit_sentence(sid: str, sentence_id: str, changes: dict) -> dict:
    state, _ = _load(sid)
    for sec in state.get("draft", {}).get("sections", []):
        for st in sec["sentences"]:
            if st["sid"] == sentence_id:
                before = dict(st)
                if "text" in changes and changes["text"] != st["text"]:
                    st["text"], st["status"] = changes["text"], "edited"
                if "status" in changes:
                    st["status"] = changes["status"]
                if "unit_ids" in changes:
                    st["unit_ids"] = changes["unit_ids"]
                    st["unsourced"] = st["kind"] == "opinion" and not st["unit_ids"]
                _save(sid, state, ("sentence_edit", {"sid": sentence_id, "before": before, "after": dict(st)}))
                return st
    raise KeyError(sentence_id)


# ---------------------------------------------------------------- export
def preflight(state: dict) -> list[str]:
    issues = []
    draft = state.get("draft")
    if not draft:
        return ["No draft yet."]
    sents = [st for sec in draft["sections"] for st in sec["sentences"]]
    if any(st["unsourced"] and st["status"] != "rejected" for st in sents):
        issues.append("Some sentences have no source (link them to your statement or delete them).")
    if any(st["status"] == "proposed" for st in sents):
        issues.append("Some sentences are still proposals (accept, edit, or reject each).")
    missing = [SCORES[k]["label"] for k in SCORES if k not in state.get("scores", {})]
    if missing:
        issues.append("Scores not set by you: " + ", ".join(missing) + ".")
    return issues


def export(sid: str, fmt: str = "arr") -> dict:
    state, pid = _load(sid)
    with Session(engine) as s:
        paper = s.get(Paper, pid)
        events = [{"turn": e.turn, "type": e.type, "at": e.created_at.isoformat(), "payload": e.payload}
                  for e in s.exec(select(Event).where(Event.session_id == sid).order_by(Event.pk))]
    draft = state.get("draft") or {"sections": []}
    keep = {sec["field"]: [st for st in sec["sentences"] if st["status"] in ("accepted", "edited")] for sec in draft["sections"]}
    lines = []
    for key, label in FIELDS:
        sents = keep.get(key, [])
        lines.append(f"## {label}")
        if not sents:
            lines.append("[Not addressed by the reviewer]")
        elif key == "weaknesses":
            lines += [f"{i}. {st['text']}" for i, st in enumerate(sents, 1)]
        else:
            lines.append(" ".join(st["text"] for st in sents))
        lines.append("")
    for k, meta in SCORES.items():
        v = state.get("scores", {}).get(k, {}).get("value")
        lines.append(f"{meta['label']}: {v if v is not None else '[not set]'}")
    n_user = sum(1 for e in events if e["type"] == "user_msg")
    unit_by = {u["id"]: u for u in state.get("units", [])}
    n_facts = sum(1 for v in keep.values() for st in v
                  if any(unit_by.get(u, {}).get("source") == "paper_fact" for u in st["unit_ids"]))
    disclosure = ("AI-use disclosure: I used a review copilot that located passages in the paper, answered factual "
                  "questions with citations, and organized my own statements into this form. All assessments, scores, "
                  f"and opinions are mine; every evaluative sentence is linked to my own statements ({n_user} dialogue "
                  "turns logged).")
    if n_facts:
        disclosure += (f" The summary includes {n_facts} sentence(s) restating the paper's own stated contributions, "
                       "which the tool located and I confirmed.")
    report = {
        "schema_version": "rc-trace/0.1", "paper": {"id": pid, "title": paper.title if paper else ""},
        "session_id": sid, "units": state.get("units", []), "scores": state.get("scores", {}),
        "review": [{"field": sec["field"], "sentences": sec["sentences"]} for sec in draft["sections"]],
        "unused_units": draft.get("unused_units", []), "events": events,
        "stats": {
            "reviewer_turns": n_user,
            "opinion_units": len([u for u in state.get("units", []) if not u.get("deleted")]),
            "units_with_rationale": len([u for u in state.get("units", []) if u.get("rationale") and not u.get("deleted")]),
            "statement_checks": sum(1 for e in events if e["type"] == "check"),
            "verdict_requests_declined": state.get("refusals", 0),
            "sentences_total": sum(len(sec["sentences"]) for sec in draft["sections"]),
            "sentences_accepted_or_edited": sum(len(v) for v in keep.values()),
        },
    }
    return {"arr_text": "\n".join(lines).strip(), "disclosure": disclosure, "preflight": preflight(state),
            "report": report if fmt == "json" else None, "report_stats": report["stats"]}


def draft_view(state: dict) -> dict:
    from .criteria import FAMILIARITY
    fam = (state.get("paper_ctx") or {}).get("familiarity")
    return {"draft": state.get("draft"), "scores": state.get("scores", {}), "score_meta": SCORES,
            "fields": [{"key": k, "label": l} for k, l in FIELDS], "preflight": preflight(state),
            "dims": [d["key"] for d in DIMENSIONS], "registers": REGISTERS,
            "register": (state.get("draft") or {}).get("register", "polished"),
            # Shown next to the Confidence score as a reminder of the reviewer's own answer; never a default.
            "familiarity": FAMILIARITY.get(fam, "")}
