"""Legacy commit-first policy (kept for the A/B comparison; no LLM calls)."""
from copilot.dialogue.dimensions import ORDER
from copilot.dialogue.legacy import decide, dim_status, new_state
from copilot.dialogue.review import preflight

PMAP = {"claims": [{"text": "X improves Y", "block_ids": ["s-0001"]}], "results": [], "models_and_methods": [],
        "datasets": [], "baselines": [], "metrics": [], "contributions": [], "stated_limitations": [], "availability": []}


def unit(uid, dim, rationale=""):
    return {"id": uid, "turn": 2, "dimension": dim, "statement": "views", "rationale": rationale,
            "polarity": "negative", "intensity": "moderate"}


def test_verdict_request_is_refused():
    st = new_state()
    move, _ = decide(st, {"act": "verdict_request", "question": "accept?"}, "accept?", PMAP, [], [])
    assert move == "refuse_redirect" and st["refusals"] == 1


def test_opinion_without_reason_is_probed():
    st = new_state()
    st["dim_idx"] = ORDER.index("soundness")
    u = unit("U1", "soundness")
    st["units"].append(u)
    move, params = decide(st, {"act": "opinion"}, "seems weak", PMAP, [u], [])
    assert move == "probe_evidence" and params["target"] == "views"


def test_reasoned_opinion_gets_facts_then_confirm_once_then_moves_on():
    st = new_state()
    st["dim_idx"] = ORDER.index("soundness")
    u = unit("U1", "soundness", rationale="because Table 2")
    st["units"].append(u)
    move, _ = decide(st, {"act": "opinion"}, "...", PMAP, [u], [])
    assert move == "surface_facts"
    st["dims"]["soundness"]["turns"] = 5  # soft cap reached
    move, _ = decide(st, {"act": "opinion"}, "...", PMAP, [], [])
    assert move == "confirm" and st["dims"]["soundness"]["pending_confirm"]
    move, _ = decide(st, {"act": "confirm"}, "yes", PMAP, [], [])
    assert move == "commit_open" and ORDER[st["dim_idx"]] == "strengths"


def test_reviewer_led_dimension_switch():
    st = new_state()  # current: summary
    u = unit("U1", "reproducibility", rationale="no code")
    st["units"].append(u)
    decide(st, {"act": "opinion"}, "...", PMAP, [u], [])
    assert ORDER[st["dim_idx"]] == "reproducibility"
    assert dim_status(st, "reproducibility") == "covered"


def test_preflight_requires_reviewer_scores_and_decisions():
    st = new_state()
    assert preflight(st) == ["No draft yet."]
    st["draft"] = {"sections": [{"field": "summary", "sentences": [
        {"sid": "a", "text": "t", "kind": "opinion", "unit_ids": [], "block_ids": [], "status": "proposed", "unsourced": True}]}]}
    issues = " ".join(preflight(st))
    assert "no source" in issues and "proposals" in issues and "Scores not set" in issues
