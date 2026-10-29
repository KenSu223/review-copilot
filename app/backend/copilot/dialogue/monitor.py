"""Coverage monitor (conversation_redesign.md §5.4).

Runs on every typed reviewer message: one structured call extracts what the reviewer said (dialogue act, opinion
units in their own words, factual claims to check, stated preferences). Coverage of the ARR fields is then
computed deterministically from the recorded units, so the gap report is auditable.

The monitor reports WHICH field is missing, never WHAT content to add.
"""
from __future__ import annotations

from .. import llm
from .criteria import CRITERION_KEYS, FIELD_HELP, FIELD_PLAIN
from .dimensions import DIM_BY_KEY, ORDER

CORE = ["summary", "strengths", "weaknesses", "soundness", "overall"]
SECONDARY = ["excitement", "reproducibility", "limitations_ethics"]

ACTS = ["opinion", "fact_question", "form_question", "verdict_request", "factual_claim_only", "unsure", "preference", "done_topic",
        "skip_topic", "more_evidence", "wants_draft", "first_impression", "chat", "offtopic"]

SCHEMA = {
    "type": "object",
    "properties": {
        "act": {"type": "string", "enum": ACTS},
        "opinion_units": {"type": "array", "items": {
            "type": "object",
            "properties": {
                "statement": {"type": "string"},
                "rationale": {"type": "string"},
                "dimension": {"type": "string", "enum": ORDER},
                "criterion": {"type": "string", "enum": CRITERION_KEYS + ["none"]},
                "polarity": {"type": "string", "enum": ["positive", "negative", "mixed", "neutral"]},
                "intensity": {"type": "string", "enum": ["hedged", "moderate", "strong"]},
                "independent": {"type": "boolean"},
            },
            "required": ["statement", "rationale", "dimension", "criterion", "polarity", "intensity", "independent"],
            "additionalProperties": False,
        }},
        "factual_claims": {"type": "array", "items": {"type": "string"}},
        "question": {"type": "string"},
        "tension_with": {"type": "string"},
        "preference": {"type": "object", "properties": {
            "criterion": {"type": "string", "enum": CRITERION_KEYS + ["none"]},
            "where": {"type": "array", "items": {"type": "string"}}},
            "required": ["criterion", "where"], "additionalProperties": False},
    },
    "required": ["act", "opinion_units", "factual_claims", "question", "tension_with", "preference"],
    "additionalProperties": False,
}

SYSTEM = """You read one message from a peer reviewer who is chatting casually with a review copilot about a paper.
Extract structure only from what the REVIEWER wrote. Never invent opinions; copy the reviewer's own words, including
casual ones ("kinda hand-wavy", "pretty neat").

act (the main thing the message does):
- "opinion": states an evaluative view about the paper, however casually.
- "fact_question": asks what the paper says or contains.
- "form_question": asks what a part of the review form means or asks for (e.g. "what goes under soundness?").
- "verdict_request": asks the COPILOT for its judgment, score, decision, or agreement ("is it good?", "do you agree?"),
  or asks it to produce evaluative content ("list the weaknesses", "write my strengths section", "what would a reviewer
  criticize?", "what's the biggest problem?").
- "factual_claim_only": only statements about paper content, no evaluation.
- "unsure": says they are unsure / have no view yet.
- "preference": says what they value in papers in general or where they look for it (not about this paper).
- "done_topic": wants to move on from the current topic. "skip_topic": wants to skip it.
- "more_evidence": wants to see more from the paper on the current topic.
- "wants_draft": wants to see or write the review draft now.
- "first_impression": a first impression of the paper before looking at evidence (only if the copilot asked for one).
- "chat": small talk or thanks. "offtopic": unrelated to the review.

opinion_units: each distinct evaluative view the reviewer INDEPENDENTLY expressed in THIS message.
- statement: verbatim (or near-verbatim) span of the reviewer's words carrying the view.
- rationale: verbatim span giving the reason or evidence, or "" if none.
- dimension: summary | soundness | strengths | weaknesses | excitement | reproducibility | limitations_ethics | overall.
  By what the view is ABOUT: whether claims are supported by experiments/analysis/proofs -> soundness; describing what
  the paper does -> summary; something done well -> strengths; a problem -> weaknesses (a negative view on evidence is
  soundness); views on clarity, writing, presentation, or figures -> strengths (positive) or weaknesses (negative); interest/impact/novelty -> excitement; code/data/details to rerun -> reproducibility; limitations or
  societal impact -> limitations_ethics; the overall verdict or what weighs most -> overall.
- criterion: which reviewer criterion it bears on: clarity | rigor | novelty | usefulness | theory | analysis |
  reproducibility | limitations, or "none".
- polarity: positive | negative | mixed | neutral. intensity: hedged | moderate | strong (from the wording).
- independent: false if the reviewer merely agreed ("yes", "right", "looks good") with something the copilot said,
  repeated the copilot's words, or picked an offered option without adding substance; true otherwise.
For a first impression or a summary in the reviewer's own words, record it (summary units describe the paper).
Do NOT create units for how the reviewer thinks the AUTHORS might respond, for questions, or for general preferences.

factual_claims: statements the reviewer makes about what the paper does or does not contain/report/claim, verbatim,
whether or not they seem accurate (they will be checked against the paper). Opinions are not factual claims.
tension_with: if a new unit clearly conflicts with an earlier recorded unit (listed), give that unit's id, else "".
preference: for act "preference", the criterion they value and the places they say they look; else criterion "none"
and where []."""


def analyze(text: str, state: dict, last_copilot: str, topic: str) -> dict:
    earlier = "\n".join(f"{u['id']} [{u['dimension']}]: {u['statement']}" for u in state.get("units", [])[-14:]
                        if not u.get("deleted")) or "(none)"
    user = (f"Current topic: {topic or '(none)'}\nCopilot's previous message: \"{last_copilot[:900]}\"\n"
            f"Earlier recorded units:\n{earlier}\n\nReviewer message:\n\"\"\"{text}\"\"\"")
    data, _ = llm.structured("analyze", SYSTEM, user, SCHEMA)
    return data


def field_status(state: dict, key: str) -> str:
    units = [u for u in state.get("units", []) if u["dimension"] == key and not u.get("deleted")]
    if key == "summary" and units:
        return "covered"
    if any(u.get("rationale") for u in units) or (units and any(u.get("source") == "paper_fact" for u in units)):
        return "covered"
    if units:
        return "partial"
    return "skipped" if key in state.get("skipped_fields", []) else "missing"


def coverage(state: dict) -> dict:
    fields = [{"key": k, "label": DIM_BY_KEY[k]["label"], "arr_field": DIM_BY_KEY[k]["arr_field"],
               "status": field_status(state, k), "core": k in CORE, "plain": FIELD_PLAIN[k], "help": FIELD_HELP[k]}
              for k in ORDER]
    status = {f["key"]: f["status"] for f in fields}
    gaps = []
    for k in ORDER:
        if status[k] == "missing":
            gaps.append({"field": k, "note": f"Nothing recorded yet for {DIM_BY_KEY[k]['label'].lower()}."})
        elif status[k] == "partial" and k != "summary":
            gaps.append({"field": k, "note": f"A view on {DIM_BY_KEY[k]['label'].lower()} is recorded without a reason."})
    ready = all(status[k] in ("covered", "partial", "skipped") for k in CORE) and \
        all(status[k] != "missing" or k in state.get("skipped_fields", []) for k in SECONDARY)
    return {"fields": fields, "gaps": gaps, "ready": ready,
            "n_units": len([u for u in state.get("units", []) if not u.get("deleted")])}
