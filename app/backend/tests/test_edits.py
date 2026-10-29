"""Reviewer-side edits on a stored session (no LLM calls): register slider, confirmed facts, topic rail."""
import uuid

from sqlmodel import Session

from copilot.db import ReviewSession, engine, init_db
from copilot.dialogue import engine as E
from copilot.dialogue import review as R


def make_session(state: dict) -> str:
    init_db()
    sid = uuid.uuid4().hex[:12]
    with Session(engine) as s:
        s.add(ReviewSession(id=sid, paper_id="p", state=state))
        s.commit()
    return sid


def base_state():
    st = E.new_state({"level": "L2", "help_style": "evidence", "criteria": [{"key": "clarity", "where": []}]},
                     {"familiarity": "basics", "read_status": "skimmed", "time_budget": 15})
    st["agenda"] = {"status": "ready", "current": None, "glossary": [],
                    "contributions": [{"id": "F1", "text": "Proposes X", "block_ids": ["s-0001"]}],
                    "cards": [{"id": f"C{i}", "kind": "evidence", "criterion": "clarity", "title": f"t{i}",
                               "block_ids": ["s-0001"], "why": "", "absent": [], "status": "pending", "read_min": 1,
                               "reactions": [], "followups": 0, "extra_ids": [], "presented_turn": None} for i in (1, 2)]}
    return st


def test_register_slider_switches_text_but_keeps_edits():
    st = base_state()
    variants = {"words": "kinda unclear", "polished": "It is somewhat unclear.", "formal": "The exposition is somewhat unclear."}
    st["draft"] = {"register": "polished", "unused_units": [], "sections": [{"field": "weaknesses", "sentences": [
        {"sid": "a", "variants": variants, "register": None, "text": variants["polished"], "kind": "opinion",
         "unit_ids": ["U1"], "block_ids": [], "status": "proposed", "unsourced": False, "drift": None,
         "drifts": {"formal": {"entailed": True, "polarity": "preserved", "intensity": "strengthened", "note": ""}},
         "original": variants["polished"]},
        {"sid": "b", "variants": variants, "register": None, "text": "my own edit", "kind": "opinion",
         "unit_ids": ["U1"], "block_ids": [], "status": "edited", "unsourced": False, "drift": None, "drifts": {},
         "original": variants["polished"]}]}]}
    sid = make_session(st)
    d = R.set_register(sid, "formal")
    a, b = d["sections"][0]["sentences"]
    assert a["text"] == variants["formal"] and a["drift"]["intensity"] == "strengthened"
    assert b["text"] == "my own edit"  # the reviewer's edit is never overwritten
    d = R.set_register(sid, "words", sentence_id="a")
    assert d["sections"][0]["sentences"][0]["text"] == "kinda unclear" and d["register"] == "formal"


def test_confirmed_facts_become_paper_fact_units_once():
    sid = make_session(base_state())
    E.confirm_facts(sid, ["F1"])
    st = E.confirm_facts(sid, ["F1"])
    facts = [u for u in st["units"] if u["source"] == "paper_fact"]
    assert len(facts) == 1 and facts[0]["id"] == "P1" and facts[0]["block_ids"] == ["s-0001"]
    assert st["agenda"]["contributions"][0]["confirmed"]
    assert next(f for f in st["coverage"]["fields"] if f["key"] == "summary")["status"] == "covered"


def test_rail_reorders_and_skips_only_pending_cards():
    sid = make_session(base_state())
    st = E.rail(sid, "C2", "up")
    assert [c["id"] for c in st["agenda"]["cards"]] == ["C2", "C1"]
    st = E.rail(sid, "C1", "skip")
    assert next(c for c in st["agenda"]["cards"] if c["id"] == "C1")["status"] == "skipped"
    st = E.rail(sid, "C1", "restore")
    assert next(c for c in st["agenda"]["cards"] if c["id"] == "C1")["status"] == "pending"


def test_sessions_from_before_the_redesign_are_legacy():
    from copilot.dialogue import legacy
    st = E.public_state(legacy.new_state())  # old sessions have no "flow" key
    assert st["flow"] == "commit_first" and "dims" in st
