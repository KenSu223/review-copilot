"""Evidence-led engine: code boundaries, coverage, agenda helpers, header parsing (no LLM calls)."""
from types import SimpleNamespace

from copilot.dialogue import agenda as A
from copilot.dialogue import engine as E
from copilot.dialogue import monitor as M


def card(cid, crit="clarity", status="pending", kind="evidence"):
    return {"id": cid, "kind": kind, "criterion": crit, "title": f"t{cid}", "block_ids": ["s-0001"], "why": "",
            "absent": [], "status": status, "read_min": 1, "reactions": [], "followups": 0, "extra_ids": [],
            "presented_turn": None}


def state(level="L2", style="evidence", study=False, cards=None, criteria=("clarity", "rigor"), read="skimmed"):
    prof = {"level": level, "help_style": style, "study_mode": study,
            "criteria": [{"key": k, "where": []} for k in criteria]}
    st = E.new_state(prof, {"familiarity": "basics", "read_status": read, "time_budget": 30})
    st["agenda"] = {"status": "ready", "cards": cards or [card("C1"), card("C2", "rigor"), card("C3")],
                    "current": None, "glossary": [], "contributions": [], "criteria": list(criteria)}
    return st


def unit(uid, dim, rationale="r", source="dialogue"):
    return {"id": uid, "turn": 1, "dimension": dim, "criterion": None, "statement": "s", "rationale": rationale,
            "polarity": "negative", "intensity": "moderate", "source": source}


def test_start_presents_top_criterion_card_first():
    st = state()
    allowed, params = E.allowed_actions(st, "", "start", False, False)
    assert allowed == ["present_card"] and [c["id"] for c in params["candidates"]] == ["C1"]


def test_first_impression_only_in_study_mode_and_quick_mode_asks_for_notes():
    assert E.allowed_actions(state(study=True), "", "start", False, False)[0] == ["ask_first_impression"]
    assert E.allowed_actions(state(style="quick"), "", "start", False, False)[0] == ["ask_dump"]
    assert E.allowed_actions(state(), "", "start", False, False)[0] != ["ask_first_impression"]


def test_experienced_reviewers_who_read_the_paper_start_in_quick_mode():
    assert E.allowed_actions(state(level="L2", read="read"), "", "start", False, False)[0] == ["ask_dump"]
    assert E.allowed_actions(state(level="L1", read="read"), "", "start", False, False)[0] == ["present_card"]


def test_topic_ends_only_when_reviewer_says_so():
    st = state()
    st["topic"] = {"type": "card", "card": "C1", "followups": 0}
    st["agenda"]["cards"][0]["status"] = "active"
    allowed, _ = E.allowed_actions(st, "opinion", "", False, False)
    assert "present_card" not in allowed and "bridge" not in allowed
    assert set(allowed) <= {"follow_up", "present_more", "offer_wrap", "reconcile"}
    E._end_topic(st, "done")
    assert st["topic"] is None and st["agenda"]["cards"][0]["status"] == "done"
    allowed, params = E.allowed_actions(st, "done_topic", "done", False, False)
    assert "present_card" in allowed and params["candidates"][0]["id"] == "C2"


def test_reactions_leave_the_choice_to_the_agent_and_more_is_honored():
    st = state()
    st["topic"] = {"type": "card", "card": "C1", "followups": 0}
    st["agenda"]["cards"][0]["status"] = "active"
    assert set(E.allowed_actions(st, "reaction", "react:looks_good", False, False)[0]) == {"follow_up", "present_more", "offer_wrap"}
    assert E.allowed_actions(st, "more_evidence", "more", False, False)[0] == ["present_more"]
    assert E.allowed_actions(st, "form_question", "", False, False)[0] == ["explain_field"]


def test_absence_items_never_outnumber_facts_shown():
    c = card("C1")
    c["absent"] = [{"item": "seed variance", "checked": "Sec. 6"}, {"item": "code", "checked": "App. B"}]
    st = state(cards=[c])
    ctx = E._context(st, ["present_card"], {"candidates": [c]}, "", "", "", [], [], {"s-0001": "x"}, {})
    assert "seed variance" not in ctx  # 2 absences vs 1 passage
    st["sym"]["presence"] = 3
    ctx = E._context(st, ["present_card"], {"candidates": [c]}, "", "", "", [], [], {"s-0001": "x"}, {})
    assert "seed variance" in ctx


def test_topic_turn_budget_leaves_only_move_on():
    st = state()
    st["topic"] = {"type": "card", "card": "C1", "followups": 0}
    st["agenda"]["cards"][0].update(status="active", turns=E.TOPIC_TURNS)
    allowed, _ = E.allowed_actions(st, "opinion", "", False, False)
    assert allowed == ["offer_wrap"]
    assert E.allowed_actions(st, "more_evidence", "more", False, False)[0] == ["present_more"]  # explicit request


def test_follow_up_is_capped():
    st = state()
    st["topic"] = {"type": "card", "card": "C1", "followups": 0}
    st["agenda"]["cards"][0].update(status="active", followups=E.MAX_FOLLOWUPS)
    allowed, _ = E.allowed_actions(st, "opinion", "", False, False)
    assert "follow_up" not in allowed and "offer_wrap" in allowed


def test_forced_steps_for_verdicts_checks_and_questions():
    st = state()
    assert E.allowed_actions(st, "verdict_request", "", True, False)[0] == ["decline_redirect"]
    assert E.allowed_actions(st, "opinion", "", True, False)[0] == ["report_check"]
    assert E.allowed_actions(st, "fact_question", "", False, False)[0] == ["answer_fact"]


def test_bridge_symmetry_between_strengths_and_weaknesses():
    st = state(cards=[card("C1", status="done")], criteria=("clarity",))
    st["units"] = [unit("U1", "summary"), unit("U2", "soundness"), unit("U3", "overall"), unit("U4", "excitement"),
                   unit("U5", "reproducibility"), unit("U6", "limitations_ethics")]
    st["sym"]["bridge_problem"] = 1  # already bridged once toward problems
    field, _ = E._bridge_target(st)
    assert field == "strengths"
    st["sym"]["bridge_good"] = 1
    assert E._bridge_target(st)[0] in ("strengths", "weaknesses")


def test_monitor_reports_fields_not_content():
    st = state()
    st["units"] = [unit("U1", "weaknesses", rationale="")]
    cov = M.coverage(st)
    assert {g["field"] for g in cov["gaps"]} >= {"strengths", "weaknesses"}
    assert all(set(g) == {"field", "note"} for g in cov["gaps"]) and not cov["ready"]


def test_confirmed_paper_fact_covers_summary():
    st = state()
    st["units"] = [unit("P1", "summary", rationale="", source="paper_fact")]
    assert M.field_status(st, "summary") == "covered"


def test_header_is_parsed_and_stripped():
    hdr = "ACTION: present_card | CARD: C2 | WHY: top criterion, not yet shown\n"
    out = SimpleNamespace(text=hdr + "They compare five models.",
                          segments=[{"text": hdr + "They compare ", "cites": []},
                                    {"text": "five models.", "cites": ["s-0003"]}])
    head, segs = E._strip_header(out)
    assert head == {"action": "present_card", "card": "C2", "field": None, "why": "top criterion, not yet shown"}
    assert segs[0]["text"] == "They compare " and segs[1]["cites"] == ["s-0003"]
    assert E._validate(head, ["present_card"], {"candidates": [card("C1")]}).startswith("For present_card")


def test_remember_offer_after_two_comments_on_an_unlisted_criterion():
    st = state(criteria=("rigor",))
    st["units"] = [{**unit("U1", "strengths"), "criterion": "clarity"}, {**unit("U2", "weaknesses"), "criterion": "clarity"}]
    assert E._remember_offer(st) == {"criterion": "clarity", "label": "Clear story and writing"}
    assert E._remember_offer(st) is None  # offered once


def test_agenda_helpers():
    assert A._counts(["a", "b", "c"], 7) == {"a": 3, "b": 2, "c": 2}
    assert A.needs({"level": "L0"}, {"familiarity": "expert", "read_status": "read"})["orientation"]
    assert not A.needs({"level": "L3"}, {"familiarity": "basics", "read_status": "not_yet"})["orientation"]
    n = A.needs({"level": "L2"}, {"familiarity": "new", "read_status": "read"})
    assert n["background"] and n["glossary"] and n["orientation"]
