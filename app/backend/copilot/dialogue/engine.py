"""Evidence-led conversation engine (docs/conversation_redesign.md §5).

One turn:
  1. Monitor: on typed messages, one structured call extracts the dialogue act, the reviewer's opinion units (their
     own words), factual claims, and stated preferences. Chip clicks are deterministic (no call).
  2. Statement checks (cited), only when the reviewer made factual claims.
  3. Code computes the ALLOWED next steps: hard boundaries, not decisions (allowed actions only, topics end only when
     the reviewer says so, follow-up caps, strengths/weaknesses bridge symmetry, monitor reports fields not content).
  4. Conversation agent (cited): chooses ONE allowed step dynamically and writes the message.
  5. Guard (cross-family): audits wording and evidence selection; one revision, then a safe fallback.
The number of LLM calls therefore varies with what the turn needs. While the reviewer reads, the agent's next step
after "Done with this" is prefetched.

Sessions created with flow="commit_first" run the legacy engine (legacy.py) for the A/B comparison (§9).
"""
from __future__ import annotations

import copy
import logging
import re
import threading
import time
import uuid
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone

from sqlalchemy.orm.attributes import flag_modified
from sqlmodel import Session, select

from .. import llm
from ..db import Event, Paper, ReviewerProfile, ReviewSession, engine
from ..ingest import llm_blocks
from . import agenda as A
from . import criteria as C
from . import legacy
from . import monitor as M
from . import prompts as P
from .dimensions import DIM_BY_KEY
from .legacy import _history, transcript  # noqa: F401  (shared trace helpers)

log = logging.getLogger(__name__)
MAX_FOLLOWUPS = 2
TOPIC_TURNS = 4  # copilot turns on one topic before only "move on?" remains (the reviewer can say "Keep going")
CANDIDATES = 6  # the agent may pick any of the next planned cards (it revises the plan as it goes)
ABSENCE = re.compile(r"\b(couldn'?t|could not|didn'?t|did not|can'?t|cannot) (find|locate|see)\b", re.I)
HEADER = re.compile(r"^\s*ACTION:\s*([a-z_]+)[ \t]*(?:\|[ \t]*CARD:[ \t]*(C\d+)[ \t]*)?(?:\|[ \t]*FIELD:[ \t]*([a-z_]+)[ \t]*)?"
                    r"(?:\|[ \t]*WHY:[ \t]*([^\n]*))?\n?", re.I)

REACT = {"looks_good": "Looks good", "mixed": "Mixed", "off": "Something's off", "not_sure": "Not sure"}
DONE = {"label": "Done with this", "action": "done"}
CARD_CHIPS = [{"label": v, "action": f"react:{k}"} for k, v in REACT.items()] + \
    [{"label": "Show me more", "action": "more"}, DONE, {"label": "Skip", "action": "skip"}]
CHIPS = {
    "present_card": CARD_CHIPS, "present_more": CARD_CHIPS,
    "follow_up": [{"label": "Not sure", "action": "react:not_sure"}, DONE],
    "offer_wrap": [DONE, {"label": "Keep going", "action": "keep"}],
    "answer_fact": [{"label": "Show me more", "action": "more"}, DONE],
    "report_check": [DONE], "decline_redirect": [{"label": "Not sure", "action": "react:not_sure"}],
    "support_unsure": [{"label": "Show me more", "action": "more"}, {"label": "Skip", "action": "skip"}],
    "reconcile": [], "summary_check": [{"label": "Skip", "action": "skip"}],
    "ask_preference": [{"label": "Skip", "action": "skip"}],
    "offer_draft": [{"label": "Open review draft", "action": "open_draft"}, {"label": "Keep chatting", "action": "keep"}],
    "ask_first_impression": [{"label": "Skip", "action": "skip"}], "ask_dump": [{"label": "Skip", "action": "skip"}],
    "redirect": [], "bridge": [{"label": "Not sure", "action": "react:not_sure"}, {"label": "Skip", "action": "skip"}],
    "explain_field": [],
}
# Which reserve-card criteria can supply evidence when bridging to a field.
FIELD_CRITERIA = {"soundness": ["rigor", "theory", "analysis"], "excitement": ["novelty", "usefulness"],
                  "reproducibility": ["reproducibility"], "limitations_ethics": ["limitations"]}

_RUNNING: set[str] = set()
_PREFETCH: dict[str, dict] = {}
_PF_LOCK = threading.Lock()


def _now():
    return datetime.now(timezone.utc)


# ---------------------------------------------------------------- profile + sessions
def load_profile() -> dict:
    with Session(engine) as s:
        p = s.get(ReviewerProfile, "default")
        return dict(p.data) if p else {}


def save_profile(data: dict) -> dict:
    with Session(engine) as s:
        p = s.get(ReviewerProfile, "default") or ReviewerProfile(id="default")
        p.data, p.updated_at = dict(data), _now()
        flag_modified(p, "data")
        s.add(p)
        s.commit()
        return dict(p.data)


def new_state(profile: dict, ctx: dict) -> dict:
    quick = C.session_quick(profile, ctx)
    study = bool(profile.get("study_mode"))
    return {
        "flow": "evidence", "turn": 0, "finished": False, "units": [], "checks": 0, "refusals": 0,
        "profile": copy.deepcopy(profile), "paper_ctx": dict(ctx), "study_mode": study, "quick": quick,
        "agenda": {"status": "planning", "cards": [], "current": None, "glossary": [], "contributions": [], "criteria": []},
        "topic": None,  # {"type": "card"|"field"|"impression"|"preference", ...}
        # First impression: off by default, on in study mode, the natural entry point in quick mode (§5.8).
        "first_impression": {"enabled": study or quick, "asked": False, "text": ""},
        "dump_done": not quick,
        "sym": {"bridge_good": 0, "bridge_problem": 0, "presence": 0, "absence": 0},
        "skipped_fields": [], "bridged_fields": [], "explained_fields": [], "asked_pref": [], "remember_offered": [],
    }


def create_session(paper_id: str, paper_ctx: dict | None = None, flow: str = "evidence",
                   profile: dict | None = None, origin: str = "app") -> ReviewSession:
    """origin: "app" (the reviewer's sessions) or "eval" (persona-suite sessions, hidden from the app)."""
    with Session(engine) as s:
        if flow == "commit_first":
            state = {**legacy.new_state(), "flow": "commit_first"}
        else:
            prof = profile if profile is not None else load_profile()
            ctx = {"familiarity": "basics", "read_status": "not_yet", "time_budget": 30, **(paper_ctx or {})}
            state = new_state(prof, ctx)
            # Only sessions that use the saved profile write learned preferences back to it (evals pass their own).
            state["profile_source"] = "explicit" if profile is not None else "saved"
        state["origin"], state["paper_id"] = origin, paper_id
        rs = ReviewSession(id=uuid.uuid4().hex[:12], paper_id=paper_id, state=state)
        s.add(rs)
        s.add(Event(session_id=rs.id, turn=0, type="session_start",
                    payload={"flow": flow, "profile": state.get("profile"), "paper_ctx": state.get("paper_ctx")}))
        s.commit()
        s.refresh(rs)
    if flow != "commit_first":
        A.plan_in_background(rs.id)
    return rs


# ---------------------------------------------------------------- state helpers
def _cards(state: dict) -> list[dict]:
    return state.get("agenda", {}).get("cards", [])


def _card(state: dict, cid: str | None) -> dict | None:
    return next((c for c in _cards(state) if c["id"] == cid), None) if cid else None


def _current(state: dict) -> dict | None:
    t = state.get("topic") or {}
    return _card(state, t.get("card")) if t.get("type") in ("card", "field") else None


def _pending(state: dict) -> list[dict]:
    return [c for c in _cards(state) if c["status"] == "pending"]


def _criterion_label(key: str | None) -> str:
    return C.CRITERION[key]["label"] if key in C.CRITERION else ""


def _why(state: dict, card: dict, field: str | None = None) -> str:
    crit = card.get("criterion")
    if field:
        return f"To round out your review: {C.FIELD_PLAIN[field]}"
    if card["kind"] == "evidence" and crit in C.profile_criteria(state.get("profile", {})):
        return f"Because you said you care about {_criterion_label(crit).lower()}"
    if card["kind"] == "evidence" and crit:
        return f"A starting point for {_criterion_label(crit).lower()}"
    return card.get("why", "")


def public_state(state: dict) -> dict:
    if state.get("flow", "commit_first") == "commit_first":
        return {**legacy.public_state(state), "flow": "commit_first"}
    ag = state.get("agenda", {})
    confirmed = {u.get("fact_id") for u in state.get("units", []) if u.get("source") == "paper_fact" and not u.get("deleted")}
    cards = [{"id": c["id"], "kind": c["kind"], "criterion": c.get("criterion"),
              "criterion_label": _criterion_label(c.get("criterion")), "title": c["title"], "status": c["status"],
              "read_min": c["read_min"], "block_ids": c["block_ids"] + c.get("extra_ids", []), "why": _why(state, c),
              "n_absent": len(c.get("absent", []))} for c in ag.get("cards", [])]
    cur = _current(state)
    left = len(_pending(state)) + (1 if cur else 0)
    prof = state.get("profile", {})
    return {
        "flow": "evidence", "turn": state.get("turn", 0), "finished": state.get("finished", False),
        "agenda": {"status": ag.get("status"), "error": ag.get("error", ""), "cards": cards,
                   "current": cur["id"] if cur else None, "glossary": ag.get("glossary", []),
                   "contributions": [{**f, "confirmed": f["id"] in confirmed} for f in ag.get("contributions", [])]},
        "coverage": M.coverage(state),
        "units": [u for u in state.get("units", []) if not u.get("deleted")],
        "progress": {"cards_left": left, "minutes_left": left * C.MINUTES_PER_CARD},
        "level": prof.get("level", ""), "help_style": "quick" if state.get("quick") else C.help_style(prof),
        "paper_ctx": state.get("paper_ctx", {}),
        "study_mode": state.get("study_mode", False), "topic": state.get("topic"),
        "first_impression": state.get("first_impression", {}),
    }


# ---------------------------------------------------------------- boundaries (code), not decisions
def _bridge_target(state: dict) -> tuple[str | None, dict | None]:
    """The next field to bridge to, respecting strengths/weaknesses symmetry. Reports a field, never content."""
    cov = {f["key"]: f["status"] for f in M.coverage(state)["fields"]}
    crit_fields = [f for k in C.profile_criteria(state.get("profile", {})) for f in C.CRITERION[k]["fields"]]
    order = list(dict.fromkeys(crit_fields + M.CORE + M.SECONDARY))
    order = [f for f in order if f not in ("summary", "overall")] + ["overall"]
    sym = state["sym"]
    for f in order:
        if cov.get(f) != "missing" or f in state.get("skipped_fields", []) or f in state.get("bridged_fields", []):
            continue  # a field is bridged to at most once; the reviewer can always come back to it
        if f == "weaknesses" and sym["bridge_problem"] + 1 - sym["bridge_good"] > 1:
            continue  # at most one more bridge toward problems than toward what worked
        if f == "strengths" and sym["bridge_good"] + 1 - sym["bridge_problem"] > 1:
            continue
        card = next((c for c in _cards(state) if c["status"] == "reserve" and c.get("criterion") in FIELD_CRITERIA.get(f, [])), None)
        return f, card
    return None, None


def allowed_actions(state: dict, act: str, action: str, has_checks: bool, tension: bool) -> tuple[list[str], dict]:
    """Hard boundaries: which steps the agent may choose from this turn, plus the cards/fields it may use."""
    fi = state["first_impression"]
    cur, topic = _current(state), state.get("topic") or {}
    params: dict = {}
    if action == "start":
        if not state.get("dump_done"):
            return ["ask_dump"], params
        if fi["enabled"] and not fi["asked"]:
            return ["ask_first_impression"], params
    if act == "verdict_request":
        return ["decline_redirect"], params
    if has_checks:
        return ["report_check"], params
    if act == "fact_question":
        return ["answer_fact"], params
    if act == "form_question":
        return ["explain_field"], params
    if act == "wants_draft":
        return ["offer_draft"], params
    if action.startswith("card:"):
        card = _card(state, action.split(":", 1)[1])
        if card:
            params["candidates"] = [card]
            return ["present_card"], params
    active = cur is not None or topic.get("type") == "field"
    if action == "more" or act == "more_evidence":
        if cur:
            return ["present_more"], params  # the reviewer asked for it
    can_follow = (cur or {}).get("followups", topic.get("followups", 0)) < MAX_FOLLOWUPS
    spent = (cur or topic).get("turns", 0) >= TOPIC_TURNS  # budgeted length (§5.7): no endless probing on one topic
    if act == "unsure" or action == "react:not_sure":
        return ["support_unsure"] + (["present_more"] if cur else []), params
    if active:
        if act in ("chat", "offtopic"):
            return ["redirect"], params
        allowed = ["reconcile"] if tension else []
        if can_follow and not spent:
            allowed.append("follow_up")
        if cur and not spent:
            allowed.append("present_more")
        allowed.append("offer_wrap")
        return allowed, params
    # No active topic: the agent picks what comes next.
    allowed = ["reconcile"] if tension else []
    pend = _pending(state)
    if pend:
        params["candidates"] = pend[:CANDIDATES]
        allowed.append("present_card")
        crit = pend[0].get("criterion")
        if not C.profile_criteria(state.get("profile", {})) and crit and crit not in state["asked_pref"]:
            allowed.append("ask_preference")  # onboarding skipped: ask just in time
    field, card = _bridge_target(state)
    if field:
        params["bridge"] = {"field": field, "card": card}
        allowed.append("bridge")
    cov = M.coverage(state)
    summary = next(f for f in cov["fields"] if f["key"] == "summary")
    if summary["status"] == "missing" and "summary" not in state.get("skipped_fields", []) \
            and not any(c["kind"] == "orientation" and c["status"] == "pending" for c in _cards(state)):
        params["summary_card"] = next((c for c in _cards(state) if c["kind"] in ("summary", "orientation")), None)
        allowed.append("summary_check")
    if cov["ready"] or not pend:
        allowed.append("offer_draft")
    if pend and (action == "start" or not any(c.get("presented_turn") for c in _cards(state))):
        # The opening follows the plan: orientation/background first if the per-paper answers call for it,
        # otherwise the reviewer's top criterion.
        allowed = ["present_card"] + (["ask_preference"] if "ask_preference" in allowed else [])
        params["candidates"] = pend[:1]
    return allowed or ["offer_draft"], params


# ---------------------------------------------------------------- agent context
def _passages(card: dict, text_of: dict, ids: list[str] | None = None) -> str:
    return "\n".join(f"  [{b}] \"{text_of.get(b, '')[:400]}\"" for b in (ids or card["block_ids"]))


def _context(state: dict, allowed: list[str], params: dict, act: str, action: str, text: str,
             new_units: list, checks: list, text_of: dict, analysis: dict) -> str:
    prof = state.get("profile", {})
    level = prof.get("level", "L1")
    crit = C.profile_criteria(prof)
    lines = [f"[Reviewer] level {level} ({C.LEVELS.get(level, '')}); help style: "
             f"{'quick' if state.get('quick') else C.help_style(prof)}; criteria in their "
             f"rank order: " + ("; ".join(f"{_criterion_label(k)} (looks at: {', '.join(C.where_to_look(prof, k))})"
                                          for k in crit) or "not stated yet")]
    rule = P.LEVEL_RULES.get(level, "")
    if level in ("L0", "L1"):
        rule += " When asking about problems, you may prompt the structure (what, where, why it matters), never the content."
    style = "quick" if state.get("quick") else C.help_style(prof)
    rule += " " + P.HELP_STYLE_RULES.get(style, "")
    if level == "L0" and prof.get("help_goal") in P.HELP_GOAL_RULES:
        rule += " " + P.HELP_GOAL_RULES[prof["help_goal"]]
    lines.append(f"[Presentation for this level] {rule}")
    cur, topic = _current(state), state.get("topic") or {}
    if cur:
        shown = cur["block_ids"] + cur.get("extra_ids", [])
        lines.append(f"[Current topic] card {cur['id']} \"{cur['title']}\" ({_criterion_label(cur.get('criterion')) or cur['kind']}). "
                     f"Passages already shown:\n{_passages(cur, text_of, shown)}")
    elif topic.get("type") == "field":
        lines.append(f"[Current topic] the part of the review about {DIM_BY_KEY[topic['field']]['label'].lower()}.")
    sym = state["sym"]
    for c in params.get("candidates", []):
        # Absences never outnumber the facts shown (symmetry counter, §7).
        ok = sym["absence"] + len(c.get("absent", [])) <= sym["presence"] + len(c["block_ids"])
        absent = "; ".join(f"{a['item']} (checked: {a['checked']})" for a in c.get("absent", [])) if ok else ""
        lines.append(f"[Candidate card {c['id']}] \"{c['title']}\" ({_criterion_label(c.get('criterion')) or c['kind']}); "
                     f"shown to the reviewer as: {_why(state, c)}. Passages:\n{_passages(c, text_of)}"
                     + (f"\n  Could not be located (mention neutrally if you present this card): {absent}" if absent else ""))
    if "bridge" in params:
        b = params["bridge"]
        lines.append(f"[Bridge target] FIELD: {b['field']} (nothing recorded yet about {C.FIELD_PLAIN[b['field']]}; "
                     f"say it in those plain words)" + (f"; card {b['card']['id']} passages:\n"
                                                                      f"{_passages(b['card'], text_of)}" if b["card"] else "; no card"))
        if level == "L0" and b["field"] not in state["explained_fields"]:
            lines.append(f"[Form field explanation to use] The ARR form asks here for {C.FIELD_HELP[b['field']]}.")
    if prof.get("help_goal") == "form" and level == "L0":
        for c in params.get("candidates", [])[:1]:
            f = (C.CRITERION.get(c.get("criterion") or "", {}).get("fields") or [None])[0]
            if f and f not in state["explained_fields"]:
                lines.append(f"[Form field explanation to use] This card touches {C.FIELD_PLAIN[f]}; the ARR form asks "
                             f"there for {C.FIELD_HELP[f]}.")
    if "explain_field" in allowed:
        lines.append("[Review form, plain-language descriptions (paraphrased from the ARR reviewer guidelines)]\n"
                     + "\n".join(f"  {DIM_BY_KEY[k]['arr_field']}: {v}" for k, v in C.FIELD_HELP.items()))
    if "summary_card" in params:
        facts = _contributions(state)
        lines.append("[What the paper says it contributes]\n" + "\n".join(f"  {f['id']}: {f['text']}" for f in facts))
    cov = M.coverage(state)
    lines.append("[Review coverage] " + ", ".join(f"{f['key']}: {f['status']}" for f in cov["fields"]))
    lines.append(f"[Symmetry so far] bridges toward what worked: {sym['bridge_good']}, toward problems: "
                 f"{sym['bridge_problem']}; facts shown: {sym['presence']}, absences mentioned: {sym['absence']}.")
    turn_bits = [f"reviewer act: {act or 'none'}"]
    if action.startswith("react:"):
        turn_bits.append(f"they clicked the reaction \"{REACT[action.split(':')[1]]}\"")
    if new_units:
        turn_bits.append("noted from their message: " + "; ".join(f"{u['id']} \"{u['statement']}\"" for u in new_units))
    if checks:
        turn_bits.append("statement checks: " + "; ".join(f"\"{c['claim']}\" -> {c['verdict']}" for c in checks))
    if analysis.get("tension_with"):
        earlier = next((u for u in state["units"] if u["id"] == analysis["tension_with"]), None)
        if earlier:
            turn_bits.append(f"possible tension with their earlier note {earlier['id']} \"{earlier['statement']}\"")
    if act == "verdict_request" and analysis.get("question"):
        turn_bits.append(f"they asked you: \"{analysis['question']}\"")
    lines.append("[This turn] " + "; ".join(turn_bits))
    lines.append(f"[Reviewer's latest message] \"{text}\"" if text else "[Reviewer's latest message] (none)")
    lines.append("[Allowed actions: choose exactly ONE]\n" + "\n".join(f"- {a}: {P.ACTION_GUIDE[a]}" for a in allowed))
    if "present_card" in allowed and "bridge" in allowed:
        lines.append("Prefer present_card while the reviewer's planned cards remain; bridge when they are used up or the "
                     "reviewer has already talked about them.")
    if "summary_check" in allowed:
        lines.append("Prefer summary_check near the end, once the reviewer has seen the paper.")
    lines.append("Remember: first line `ACTION: ... | WHY: ...`, then the message. One question. Cite every paper fact.")
    return "\n\n".join(lines)


def _inline(segments: list[dict], text_of: dict | None = None) -> str:
    """The draft as the Guard sees it: cited spans are followed by the paper sentence they are grounded in."""
    out = []
    for seg in segments:
        out.append(seg["text"])
        if seg["cites"]:
            ev = " … ".join((text_of or {}).get(b, "")[:240] for b in seg["cites"][:2]).strip()
            out.append(f" ⟦cited: \"{ev}\"⟧" if ev else " [cited]")
    return "".join(out)


def _strip_header(out) -> tuple[dict, list[dict]]:
    m = HEADER.match(out.text or "")
    head = {"action": m.group(1).lower(), "card": m.group(2), "field": m.group(3),
            "why": (m.group(4) or "").strip()} if m else {}
    segs, cut = [], len(m.group(0)) if m else 0
    for seg in out.segments:
        t = seg["text"]
        if cut > 0:
            take = min(cut, len(t))
            t, cut = t[take:], cut - take
        if t.strip() or seg["cites"]:
            segs.append({"text": t, "cites": seg["cites"]})
    if segs:
        segs[0]["text"] = segs[0]["text"].lstrip()
    return head, segs


def _validate(head: dict, allowed: list[str], params: dict) -> str:
    if head.get("action") not in allowed:
        return f"ACTION must be one of: {', '.join(allowed)}."
    if head["action"] == "present_card":
        ids = [c["id"] for c in params.get("candidates", [])]
        if head.get("card") not in ids:
            return f"For present_card, CARD must be one of: {', '.join(ids)}."
    return ""


def _guard(draft: str, action: str, topic_desc: str, level: str) -> dict:
    """Audit one outgoing message. A failed Guard call is retried once; if it fails again the caller falls back."""
    user = (f"Copilot action: {action}\nTopic, why it is shown, and the selected evidence:\n{topic_desc}\n"
            f"Reviewer level: {level}\n"
            f"Draft message (\"[cited]\" marks text grounded with a paper citation):\n<<<{draft}>>>")
    for attempt in range(2):
        try:
            data, _ = llm.structured("guard", P.GUARD_SYSTEM, user, P.GUARD_SCHEMA)
            return data
        except Exception as exc:
            last = exc
    return {"verdict": "unavailable", "violations": ["guard_unavailable"], "fix": str(last)[:200]}


def _topic_desc(state: dict, card: dict | None, text_of: dict) -> str:
    """What the Guard needs to audit selection: the topic, the planner's reason, the passages, the not-found items."""
    if not card:
        return "No card; the message should not introduce selected evidence beyond what the reviewer asked about."
    absent = "; ".join(f"{a['item']} (checked: {a['checked']})" for a in card.get("absent", [])) or "none"
    return (f"Card \"{card['title']}\" ({_criterion_label(card.get('criterion')) or card['kind']}); shown because: "
            f"{_why(state, card)}; planner's reason: {card.get('why', '')}\nPassages:\n{_passages(card, text_of)}\n"
            f"Not-found items: {absent}")


def _guard_checks(checks: list[dict], level: str, text_of: dict) -> None:
    """Statement-check text reaches the reviewer too, so it passes the Guard; on failure keep only quoted evidence."""
    def one(c):
        g = _guard(_inline(c["segments"], text_of), "statement_check", "A neutral check of the reviewer's factual statement.", level)
        c["guard"] = g
        if g["verdict"] != "allow":
            cited = [seg for seg in c["segments"] if seg["cites"]]
            c["segments"] = cited or [{"text": "See the highlighted passages in the paper.", "cites": []}]
    with ThreadPoolExecutor(max_workers=2) as ex:
        list(ex.map(one, checks))


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


def decide_and_write(state: dict, allowed: list[str], params: dict, act: str, action: str, text: str,
                     new_units: list, checks: list, analysis: dict, blocks, title: str, history: list,
                     timing: dict) -> dict:
    """Conversation agent + Guard. Pure with respect to state (no writes): returns the chosen step and message."""
    text_of = dict(blocks)
    user_text = _context(state, allowed, params, act, action, text, new_units, checks, text_of, analysis)
    cur = _current(state)
    level = state.get("profile", {}).get("level", "L1")
    guard_log, head, segs = [], {}, None
    for attempt in range(2):
        t0 = time.time()
        out = llm.cited("realize", P.FIREWALL_RULES, blocks, title, history, user_text)
        timing[f"agent{attempt}"] = round(time.time() - t0, 2)
        timing[f"agent{attempt}_cache_read"] = out.log.cache_read if out.log else 0
        head, segs = _strip_header(out)
        problem = _validate(head, allowed, params)
        if problem:
            guard_log.append({"attempt": attempt, "verdict": "revise", "violations": ["invalid_action"], "fix": problem,
                              "draft": out.text})
            user_text += f"\n\nYour previous draft was invalid: {problem} Rewrite it."
            segs = None
            continue
        card = _card(state, head.get("card")) if head["action"] == "present_card" else \
            ((params.get("bridge") or {}).get("card") if head["action"] == "bridge" else cur)
        t0 = time.time()
        g = _guard(_inline(segs, text_of), head["action"], _topic_desc(state, card, text_of), level)
        timing[f"guard{attempt}"] = round(time.time() - t0, 2)
        guard_log.append({"attempt": attempt, **g, "draft": out.text})
        if g["verdict"] == "allow":
            break
        if g["verdict"] == "unavailable":  # never send an unaudited message
            segs = None
            break
        user_text += f"\n\nYour previous draft violated: {', '.join(g['violations'])}. Fix: {g['fix']} Rewrite it."
        segs = None
    fell_back = segs is None
    if fell_back:
        action_name = head.get("action") if head.get("action") in allowed else allowed[0]
        head = {"action": action_name, "card": (params.get("candidates") or [{}])[0].get("id"), "field": None,
                "why": "safe fallback"}
        segs = [{"text": P.FALLBACK.get(action_name, P.FALLBACK["redirect"]), "cites": []}]
    if head["action"] == "bridge":
        head["field"] = params["bridge"]["field"]  # code decides the target field; the agent decides whether to bridge
    return {"head": head, "segments": segs, "guard": guard_log, "fallback": fell_back}


def _contributions(state: dict) -> list[dict]:
    """The paper's own stated contributions (confirmable facts); loaded lazily if the map was not ready at planning."""
    ag = state.get("agenda", {})
    if not ag.get("contributions") and state.get("paper_id"):
        from ..db import PaperMap
        with Session(engine) as s:
            pm = s.get(PaperMap, state["paper_id"])
        if pm and pm.status == "ready":
            ag["contributions"] = [{"id": f"F{i + 1}", "text": it["text"], "block_ids": it["block_ids"]}
                                   for i, it in enumerate(pm.data.get("contributions", [])[:5])]
    return ag.get("contributions", [])


def _fingerprint(state: dict) -> str:
    """What a prefetched step depends on; if any of it changed, the prefetch is discarded."""
    cards = [(c["id"], c["status"]) for c in _cards(state)]
    units = sorted(u["id"] for u in state.get("units", []) if not u.get("deleted"))
    return repr((cards, units, state["sym"], state.get("skipped_fields"), state.get("bridged_fields"), state.get("topic")))


# ---------------------------------------------------------------- applying a step
def _record_units(state: dict, analysis: dict, turn: int) -> list[dict]:
    cur = _current(state)
    topic = state.get("topic") or {}
    out = []
    for u in analysis.get("opinion_units", []):
        if not u.get("independent", True):
            continue  # bare assent / echo of the copilot never becomes the reviewer's opinion
        n = sum(1 for x in state["units"] if x["id"].startswith("U")) + 1
        unit = {"id": f"U{n}", "turn": turn, "dimension": u.get("dimension") or topic.get("field") or "overall",
                "criterion": u.get("criterion") if u.get("criterion") in C.CRITERION else (cur or {}).get("criterion"),
                "statement": u["statement"], "rationale": u.get("rationale", ""), "polarity": u.get("polarity", "neutral"),
                "intensity": u.get("intensity", "moderate"), "confirmed": False, "source": "dialogue",
                "card": cur["id"] if cur else None}
        state["units"].append(unit)
        out.append(unit)
    return out


def _end_topic(state: dict, how: str) -> None:
    """The reviewer ended the current topic (done | skip)."""
    topic = state.get("topic") or {}
    cur = _current(state)
    if cur:
        cur["status"] = "done" if how == "done" else "skipped"
    if how == "skip" and topic.get("field"):
        state["skipped_fields"] = list(dict.fromkeys(state["skipped_fields"] + [topic["field"]]))
    if topic.get("type") == "impression":
        state["dump_done"] = True
    state["topic"] = None


def _remember_offer(state: dict) -> dict | None:
    known = set(C.profile_criteria(state.get("profile", {}))) | set(state["remember_offered"]) | \
        set(state.get("profile", {}).get("declined", []))
    counts: dict[str, int] = {}
    for u in state["units"]:
        if u.get("criterion") and not u.get("deleted") and u.get("source") == "dialogue":
            counts[u["criterion"]] = counts.get(u["criterion"], 0) + 1
    for k, n in counts.items():
        if n >= 2 and k not in known:
            state["remember_offered"].append(k)
            return {"criterion": k, "label": _criterion_label(k)}
    return None


def _apply(state: dict, step: dict, params: dict, turn: int, text_of: dict) -> dict:
    """State effects of the chosen step; returns the message extras (focus, chips, facts, field help)."""
    head, segs = step["head"], step["segments"]
    action = head["action"]
    cited = list(dict.fromkeys(b for s in segs for b in s["cites"]))
    own = "".join(s["text"] for s in segs if not s["cites"])
    state["sym"]["presence"] += sum(1 for s in segs if s["cites"])
    state["sym"]["absence"] += len(ABSENCE.findall(own))
    extras: dict = {"focus": None, "facts": [], "field_help": None}
    chips = list(CHIPS.get(action, []))
    cur = _current(state)
    topic = state.get("topic") or {}
    if action == "present_card":
        card = _card(state, head.get("card")) or params["candidates"][0]
        card["status"], card["presented_turn"] = "active", turn
        state["topic"] = {"type": "card", "card": card["id"], "followups": 0}
        ids = card["block_ids"] + [b for b in cited if b not in card["block_ids"]]
        extras["focus"] = {"block_ids": ids, "card": card["id"], "title": card["title"], "why": _why(state, card),
                           "criterion": card.get("criterion"), "read_min": card["read_min"]}
        if card["kind"] == "orientation":
            extras["facts"] = _contributions(state)
            chips = [DONE] + chips[-1:]
        prof = state.get("profile", {})
        f = (C.CRITERION.get(card.get("criterion") or "", {}).get("fields") or [None])[0]
        if prof.get("level") == "L0" and prof.get("help_goal") == "form" and f and f not in state["explained_fields"]:
            state["explained_fields"].append(f)
            extras["field_help"] = {"field": f, "label": DIM_BY_KEY[f]["arr_field"], "text": C.FIELD_HELP[f],
                                    "source": C.FIELD_HELP_SOURCE}
    elif action == "present_more" and cur:
        new = [b for b in cited if b not in cur["block_ids"] + cur["extra_ids"]]
        cur["extra_ids"] += new
        cur["followups"] = 0
        if new:
            extras["focus"] = {"block_ids": new, "card": cur["id"], "title": cur["title"], "why": _why(state, cur),
                               "criterion": cur.get("criterion"), "read_min": A._read_min(new, text_of)}
    elif action == "follow_up":
        if cur:
            cur["followups"] += 1
        elif topic:
            topic["followups"] = topic.get("followups", 0) + 1
    elif action == "bridge":
        field = head["field"]
        card = params["bridge"]["card"]
        state.setdefault("bridged_fields", []).append(field)
        if field == "strengths":
            state["sym"]["bridge_good"] += 1
        elif field == "weaknesses":
            state["sym"]["bridge_problem"] += 1
        if card:
            card["status"], card["presented_turn"] = "active", turn
            state["topic"] = {"type": "field", "field": field, "card": card["id"], "followups": 0}
            extras["focus"] = {"block_ids": card["block_ids"] + [b for b in cited if b not in card["block_ids"]],
                               "card": card["id"], "title": card["title"], "why": _why(state, card, field),
                               "criterion": card.get("criterion"), "read_min": card["read_min"]}
            chips = CARD_CHIPS
        else:
            state["topic"] = {"type": "field", "field": field, "followups": 0}
            if cited:
                extras["focus"] = {"block_ids": cited, "card": None, "title": C.FIELD_PLAIN[field].capitalize(),
                                   "why": f"To round out your review: {C.FIELD_PLAIN[field]}",
                                   "criterion": None, "read_min": A._read_min(cited, text_of)}
        if state.get("profile", {}).get("level") == "L0" and field not in state["explained_fields"]:
            state["explained_fields"].append(field)
            extras["field_help"] = {"field": field, "label": DIM_BY_KEY[field]["arr_field"],
                                    "text": C.FIELD_HELP[field], "source": C.FIELD_HELP_SOURCE}
    elif action == "summary_check":
        card = params.get("summary_card")
        state["topic"] = {"type": "field", "field": "summary", "card": card["id"] if card else None, "followups": 0}
        if card:
            card["status"], card["presented_turn"] = "active", turn
        ids = (card["block_ids"] if card else []) + [b for b in cited if not card or b not in card["block_ids"]]
        if ids:
            extras["focus"] = {"block_ids": ids, "card": card["id"] if card else None,
                               "title": "What the paper says it contributes",
                               "why": "To help with the summary: the paper's own contribution statements",
                               "criterion": None, "read_min": A._read_min(ids, text_of)}
        extras["facts"] = _contributions(state)
    elif action == "ask_preference":
        crit = (params.get("candidates") or [{}])[0].get("criterion")
        if crit:
            state["asked_pref"].append(crit)
        state["topic"] = {"type": "preference", "criterion": crit}
    elif action in ("ask_first_impression", "ask_dump"):
        state["first_impression"]["asked"] = True
        state["topic"] = {"type": "impression"}
    elif action == "offer_draft":
        state["finished"] = True
    elif action == "decline_redirect":
        state["refusals"] += 1
    if action in ("answer_fact", "report_check", "decline_redirect", "reconcile") and cited:
        extras["focus"] = {"block_ids": cited, "card": cur["id"] if cur else None, "title": cur["title"] if cur else "",
                           "why": "Where this is in the paper", "criterion": (cur or {}).get("criterion"),
                           "read_min": A._read_min(cited, text_of)}
    extras["chips"] = chips
    return extras


# ---------------------------------------------------------------- the turn
def run_turn(session_id: str, text: str = "", action: str = ""):
    with Session(engine) as s:
        rs = s.get(ReviewSession, session_id)
        if rs is None:
            yield {"type": "error", "message": "session not found"}
            return
        state = rs.state or {}
    if state.get("flow", "commit_first") == "commit_first":
        yield from legacy.run_turn(session_id, text, action)
        return
    if action == "start" and (session_id in _RUNNING or state.get("turn", 0) > 0):
        return  # "start" is idempotent: never open a session twice
    _RUNNING.add(session_id)
    try:
        yield from _run(session_id, text, action)
    finally:
        _RUNNING.discard(session_id)


def turn_running(session_id: str) -> bool:
    return session_id in _RUNNING


def _load(session_id: str):
    with Session(engine) as s:
        rs = s.get(ReviewSession, session_id)
        paper = s.get(Paper, rs.paper_id)
        blocks = [(b.block_id, b.text) for b in llm_blocks(s, rs.paper_id)]
        return dict(rs.state), paper.title, blocks


def _run(session_id: str, text: str, action: str):
    t_start = time.time()
    timing: dict[str, float] = {}
    state, title, blocks = _load(session_id)
    needs_agenda = not (action == "start" and (not state.get("dump_done")
                                               or (state["first_impression"]["enabled"] and not state["first_impression"]["asked"])))
    if needs_agenda and state.get("agenda", {}).get("status") == "planning":
        if session_id not in A.ACTIVE:  # e.g. the server restarted while planning: plan again
            A.plan_in_background(session_id)
        yield {"type": "status", "step": "plan", "label": "Preparing your reading plan from your preferences…"}
        ag = A.wait_ready(session_id)
        state, title, blocks = _load(session_id)
        if state.get("agenda", {}).get("status") == "planning":  # timed out: continue without cards, don't wait again
            state["agenda"] = ag

    base_turn = state["turn"]
    state["turn"] += 1
    turn = state["turn"]
    last_copilot = next((m.get("plain", "") for m in reversed(transcript(session_id)) if m["role"] == "copilot"), "")
    history = _history(session_id)
    with Session(engine) as s:
        if text:
            s.add(Event(session_id=session_id, turn=turn, type="user_msg", payload={"text": text, "action": action}))
            s.commit()

    # 1) Monitor (typed messages only) -> act, units, claims, preference
    analysis: dict = {"opinion_units": [], "factual_claims": []}
    act = ""
    if action and action != "start":
        act = {"done": "done_topic", "skip": "skip_topic", "more": "more_evidence", "keep": "keep"}.get(
            action, "reaction" if action.startswith("react:") else action.split(":")[0])
    elif text:
        yield {"type": "status", "step": "analyze", "label": "Reading your message…"}
        try:
            t0 = time.time()
            topic = state.get("topic") or {}
            cur = _current(state)
            analysis = M.analyze(text, state, last_copilot, cur["title"] if cur else topic.get("field", ""))
            timing["monitor"] = round(time.time() - t0, 2)
        except Exception as exc:
            log.exception("monitor failed")
            analysis = {"act": "opinion", "opinion_units": [], "factual_claims": [], "error": str(exc)[:200]}
        act = analysis.get("act", "opinion")
    topic = state.get("topic") or {}
    if topic.get("type") == "impression" and text and not action:  # only typed text is a first impression
        state["first_impression"]["text"] = text
        state["dump_done"] = True
        state["topic"] = None
        act = act if act in ("verdict_request", "fact_question") else "first_impression"
    elif topic.get("type") == "preference" and act not in ("verdict_request", "fact_question"):
        state["topic"] = None
    elif topic.get("type") == "impression" and action:  # a click (skip, rail "go") ends the question, unrecorded
        state["dump_done"], state["topic"] = True, None
    new_units = _record_units(state, analysis, turn)
    pref = analysis.get("preference") or {}
    if act == "preference" and pref.get("criterion") in C.CRITERION:
        learned = {"key": pref["criterion"], "where": pref.get("where") or [], "turn": turn, "session": session_id}
        if pref["criterion"] not in C.profile_criteria(state["profile"]):
            A.extend_in_background(session_id, pref["criterion"])
        state["profile"].setdefault("learned", []).append(learned)
        if state.get("profile_source") == "saved":
            prof = load_profile()
            prof.setdefault("learned", []).append(learned)
            save_profile(prof)

    # Reviewer-controlled topic changes
    fingerprint = _fingerprint(state)  # before the reviewer's change, as at prefetch time
    if act in ("done_topic", "skip_topic"):
        _end_topic(state, "done" if act == "done_topic" else "skip")
    elif act == "keep":
        cur = _current(state)
        if cur:
            cur["followups"], cur["turns"] = 0, 0
        if state.get("topic"):
            state["topic"]["turns"] = 0
        state["finished"] = False
    elif action.startswith("card:"):
        cur = _current(state)
        if cur:  # the reviewer jumped elsewhere: keep what was said, end this topic
            cur["status"] = "done" if (cur["reactions"] or any(u.get("card") == cur["id"] for u in state["units"])) else "pending"
            state["topic"] = None
    if action.startswith("react:"):
        cur = _current(state)
        if cur:
            cur["reactions"].append({"turn": turn, "reaction": action.split(":")[1]})

    # 2) Statement checks
    checks = []
    claims = [c for c in analysis.get("factual_claims", []) if c.strip()][:2]
    if claims:
        yield {"type": "status", "step": "check", "label": "Checking your statement against the paper…"}
        t0 = time.time()
        with ThreadPoolExecutor(max_workers=2) as ex:
            checks = list(ex.map(lambda c: _check_statement(c, blocks, title), claims))
        _guard_checks(checks, state.get("profile", {}).get("level", "L1"), dict(blocks))
        timing["checks"] = round(time.time() - t0, 2)
        state["checks"] += len(checks)

    # 3) Boundaries -> 4) agent -> 5) guard  (or a prefetched step)
    allowed, params = allowed_actions(state, act, action, bool(checks), bool(analysis.get("tension_with")))
    step = None
    if act == "done_topic":  # the case the prefetch was computed for (a skip changes what comes next)
        with _PF_LOCK:
            pf = _PREFETCH.pop(session_id, None)
        if pf and pf["base_turn"] == base_turn and pf["allowed"] == allowed and pf["fingerprint"] == fingerprint:
            if not pf["ready"].is_set():
                yield {"type": "status", "step": "agent", "label": "Finding the passages…"}
                pf["ready"].wait(30)  # already in flight since the previous message: wait instead of starting over
            if pf.get("step"):
                step, timing["prefetched"] = pf["step"], 1
    if step is None:
        yield {"type": "status", "step": "agent",
               "label": "Finding the passages…" if any(a in allowed for a in ("present_card", "bridge", "answer_fact"))
               else "Thinking about what to ask…"}
        try:
            step = decide_and_write(state, allowed, params, act, action, text, new_units, checks, analysis, blocks,
                                    title, history, timing)
        except Exception as exc:
            log.exception("agent failed")
            yield {"type": "error", "message": f"LLM error: {exc}"}
            return
    extras = _apply(state, step, params, turn, dict(blocks))
    holder = _current(state) or state.get("topic")
    if holder is not None and step["head"]["action"] not in ("present_card", "bridge", "summary_check"):
        holder["turns"] = holder.get("turns", 0) + 1  # a new topic starts at 0
    remember = _remember_offer(state) if new_units else None

    segments = step["segments"]
    cur = _current(state)
    message = {
        "segments": segments, "plain": "".join(s["text"] for s in segments), "action": step["head"]["action"],
        "move": step["head"]["action"], "dimension": (cur or {}).get("criterion") or (state.get("topic") or {}).get("field") or "",
        "chips": extras["chips"], "checks": checks, "new_units": [u["id"] for u in new_units], "fallback": step["fallback"],
        "focus": extras["focus"], "facts": extras["facts"], "field_help": extras["field_help"], "remember": remember,
        "allowed": allowed,
    }
    timing["total"] = round(time.time() - t_start, 2)
    message["timing"] = timing

    from .review import session_lock
    with session_lock(session_id), Session(engine) as s:
        rs = s.get(ReviewSession, session_id)
        latest = rs.state or {}
        for key in ("draft", "scores", "unit_variants"):  # edits made while this turn was running
            if key in latest:
                state[key] = latest[key]
        if latest.get("agenda", {}).get("status") == "ready" and state.get("agenda", {}).get("status") != "ready":
            state["agenda"] = latest["agenda"]
        state["profile"]["learned"] = latest.get("profile", {}).get("learned", state["profile"].get("learned", []))
        state["profile"]["declined"] = latest.get("profile", {}).get("declined", [])
        edited = {u["id"]: u for u in latest.get("units", [])}
        mine = {u["id"] for u in state["units"]}
        state["units"] = [edited.get(u["id"], u) for u in state["units"]] + \
            [u for u in latest.get("units", []) if u["id"] not in mine]  # e.g. paper facts confirmed meanwhile
        if text:
            s.add(Event(session_id=session_id, turn=turn, type="analyze", payload={**analysis, "act": act}))
        for c in checks:
            s.add(Event(session_id=session_id, turn=turn, type="check", payload=c))
        if act == "first_impression":
            s.add(Event(session_id=session_id, turn=turn, type="first_impression", payload={"text": text}))
        s.add(Event(session_id=session_id, turn=turn, type="agent",
                    payload={"allowed": allowed, "chosen": step["head"], "why": step["head"].get("why", ""),
                             "candidates": [c["id"] for c in params.get("candidates", [])],
                             "bridge": params.get("bridge", {}).get("field") if params.get("bridge") else None,
                             "focus": extras["focus"], "prompt_version": P.PROMPT_VERSION}))
        s.add(Event(session_id=session_id, turn=turn, type="guard", payload={"move": step["head"]["action"], "attempts": step["guard"]}))
        s.add(Event(session_id=session_id, turn=turn, type="copilot_msg", payload=message))
        rs.state, rs.updated_at = dict(state), _now()
        flag_modified(rs, "state")
        s.add(rs)
        s.commit()

    yield {"type": "message", "turn": turn, "message": message, "state": public_state(state)}
    if any(c.get("action") == "done" for c in extras["chips"]) and _current(state):
        _prefetch(session_id, state, turn, title, blocks)


def _prefetch(session_id: str, state: dict, turn: int, title: str, blocks) -> None:
    """While the reviewer reads, precompute the agent's step for "Done with this" (no state is written)."""
    st = copy.deepcopy(state)
    fingerprint = _fingerprint(st)
    st["turn"] = turn + 1
    _end_topic(st, "done")
    allowed, params = allowed_actions(st, "done_topic", "done", False, False)
    entry = {"base_turn": turn, "allowed": allowed, "step": None, "ready": threading.Event(), "fingerprint": fingerprint}
    with _PF_LOCK:
        _PREFETCH[session_id] = entry

    def work():
        try:
            entry["step"] = decide_and_write(st, allowed, params, "done_topic", "done", "", [], [], {}, blocks, title,
                                             _history(session_id), {})
        except Exception:
            log.exception("prefetch failed")
        finally:
            entry["ready"].set()
    threading.Thread(target=work, daemon=True).start()


# ---------------------------------------------------------------- reviewer-side edits (no LLM)
def rail(session_id: str, card_id: str, op: str) -> dict:
    """Agenda rail: reorder (up/down), skip, or restore a card that is not the current topic."""
    from .review import session_lock
    with session_lock(session_id), Session(engine) as s:
        rs = s.get(ReviewSession, session_id)
        state = dict(rs.state)
        cards = state["agenda"]["cards"]
        i = next((k for k, c in enumerate(cards) if c["id"] == card_id), None)
        if i is None:
            raise KeyError(card_id)
        c = cards[i]
        if op == "skip" and c["status"] in ("pending", "reserve"):
            c["status"] = "skipped"
        elif op == "restore" and c["status"] in ("skipped", "reserve", "done"):
            c["status"] = "pending"
        elif op in ("up", "down"):
            j = i - 1 if op == "up" else i + 1
            if 0 <= j < len(cards):
                cards[i], cards[j] = cards[j], cards[i]
        rs.state = state
        flag_modified(rs, "state")
        s.add(rs)
        with _PF_LOCK:
            _PREFETCH.pop(session_id, None)
        s.add(Event(session_id=session_id, turn=state.get("turn", 0), type="rail", payload={"card": card_id, "op": op}))
        s.commit()
        return public_state(state)


def confirm_facts(session_id: str, fact_ids: list[str]) -> dict:
    """Paper facts the reviewer explicitly confirmed for the summary (own provenance type, disclosed on export)."""
    from .review import session_lock
    with session_lock(session_id), Session(engine) as s:
        rs = s.get(ReviewSession, session_id)
        state = dict(rs.state)
        have = {u.get("fact_id") for u in state["units"] if u.get("source") == "paper_fact" and not u.get("deleted")}
        for f in state["agenda"].get("contributions", []):
            if f["id"] in fact_ids and f["id"] not in have:
                n = sum(1 for u in state["units"] if u["id"].startswith("P")) + 1
                state["units"].append({"id": f"P{n}", "turn": state["turn"], "dimension": "summary", "criterion": None,
                                       "statement": f["text"], "rationale": "", "polarity": "neutral", "intensity": "moderate",
                                       "confirmed": True, "source": "paper_fact", "fact_id": f["id"],
                                       "block_ids": f["block_ids"], "card": None})
        rs.state = state
        flag_modified(rs, "state")
        s.add(rs)
        s.add(Event(session_id=session_id, turn=state["turn"], type="facts_confirmed", payload={"fact_ids": fact_ids}))
        s.commit()
        return public_state(state)


def remember(session_id: str, criterion: str, accept: bool) -> dict:
    """Just-in-time taste: remember (or not) a criterion the reviewer keeps commenting on."""
    from .review import session_lock
    with session_lock(session_id), Session(engine) as s:
        rs = s.get(ReviewSession, session_id)
        state = dict(rs.state)
        prof = load_profile()
        if accept and criterion in C.CRITERION:
            item = {"key": criterion, "where": C.CRITERION[criterion]["where"], "turn": state["turn"], "session": session_id}
            if criterion not in C.profile_criteria(state["profile"]):
                A.extend_in_background(session_id, criterion)
            state["profile"].setdefault("learned", []).append(item)
            prof.setdefault("learned", []).append(item)
        else:
            state["profile"].setdefault("declined", []).append(criterion)
            prof.setdefault("declined", []).append(criterion)
        if state.get("profile_source", "saved") == "saved":
            save_profile(prof)
        rs.state = state
        flag_modified(rs, "state")
        s.add(rs)
        s.add(Event(session_id=session_id, turn=state["turn"], type="remember", payload={"criterion": criterion, "accept": accept}))
        s.commit()
        return public_state(state)


def confirm_check(session_id: str, turn: int, index: int) -> dict:
    """The reviewer ticks the evidence of a statement check for the review: it becomes a confirmed paper fact (P#)."""
    from .review import session_lock
    with session_lock(session_id), Session(engine) as s:
        rs = s.get(ReviewSession, session_id)
        state = dict(rs.state)
        checks = [e.payload for e in s.exec(select(Event).where(Event.session_id == session_id, Event.type == "check",
                                                                Event.turn == turn).order_by(Event.pk))]
        if index >= len(checks):
            raise KeyError(index)
        c, fid = checks[index], f"K{turn}-{index}"
        if not any(u.get("fact_id") == fid and not u.get("deleted") for u in state["units"]):
            cited = [seg for seg in c.get("segments", []) if seg.get("cites")]
            text = " ".join(seg["text"].strip() for seg in cited)[:400] or c["claim"]
            dim = next((u["dimension"] for u in state["units"] if u.get("turn") == turn and u.get("source") == "dialogue"),
                       "soundness")
            n = sum(1 for u in state["units"] if u["id"].startswith("P")) + 1
            state["units"].append({"id": f"P{n}", "turn": turn, "dimension": dim, "criterion": None, "statement": text,
                                   "rationale": "", "polarity": "neutral", "intensity": "moderate", "confirmed": True,
                                   "source": "paper_fact", "fact_id": fid, "check_claim": c["claim"],
                                   "check_verdict": c.get("verdict"),
                                   "block_ids": list(dict.fromkeys(b for seg in cited for b in seg["cites"])), "card": None})
        rs.state = state
        flag_modified(rs, "state")
        s.add(rs)
        s.add(Event(session_id=session_id, turn=state["turn"], type="facts_confirmed", payload={"check": fid}))
        s.commit()
        return public_state(state)
