"""Reviewer criteria, levels, and per-paper context: the structure of the evidence-led conversation.

The conversation is organized by the reviewer's OWN criteria (what they value and where they look);
ARR fields stay in the background (dimensions.py) and only appear in the draft.
See docs/conversation_redesign.md §4.
"""

# What a reviewer may value, with default places to look (editable by the reviewer) and the ARR
# fields an opinion on this criterion usually informs. `categories` are paper-map categories that hold
# objective items related to the criterion.
CRITERIA = [
    {"key": "clarity", "label": "Clear story and writing",
     "plain": "Is it easy to follow what the paper does and why?",
     "where": ["Abstract", "Problem statement", "Contribution statements", "Method overview", "Figure 1",
               "Notation and definitions"],
     "fields": ["strengths", "weaknesses"], "categories": ["contributions", "models_and_methods"]},
    {"key": "rigor", "label": "Rigorous experiments",
     "plain": "Do the experiments back up what the paper claims?",
     "where": ["Main results tables", "Baselines", "Metrics", "Seeds / variance / significance", "Experimental setup"],
     "fields": ["soundness", "strengths", "weaknesses"], "categories": ["results", "baselines", "metrics", "datasets"]},
    {"key": "novelty", "label": "New idea",
     "plain": "What is new here compared with earlier work, as the paper describes it?",
     "where": ["The paper's own novelty claims", "Contrasts drawn in related work"],
     "fields": ["excitement", "strengths", "weaknesses"], "categories": ["contributions", "claims"]},
    {"key": "usefulness", "label": "Practical usefulness",
     "plain": "Would this matter for people who build or use such systems?",
     "where": ["Motivation", "Application settings", "Efficiency or cost results"],
     "fields": ["excitement", "strengths", "weaknesses"], "categories": ["claims", "results"]},
    {"key": "theory", "label": "Theory",
     "plain": "Are the formal results stated with their assumptions and proved?",
     "where": ["Assumptions", "Theorem statements", "Proofs (often in the appendix)"],
     "fields": ["soundness", "strengths", "weaknesses"], "categories": ["claims", "models_and_methods"]},
    {"key": "analysis", "label": "Analysis and ablations",
     "plain": "Does the paper show why the method works, not only that it works?",
     "where": ["Ablation sections", "Error analysis", "Qualitative examples"],
     "fields": ["soundness", "strengths", "weaknesses"], "categories": ["results"]},
    {"key": "reproducibility", "label": "Reproducibility",
     "plain": "Could someone rerun this from what is described and released?",
     "where": ["Code and data availability", "Hyperparameters", "Compute", "Appendix details"],
     "fields": ["reproducibility"], "categories": ["availability", "models_and_methods", "datasets"]},
    {"key": "limitations", "label": "Honest limitations",
     "plain": "Do the authors say where the work stops working or could cause harm?",
     "where": ["Limitations section", "Failure cases", "Ethics statement"],
     "fields": ["limitations_ethics", "weaknesses"], "categories": ["stated_limitations"]},
]
CRITERION = {c["key"]: c for c in CRITERIA}
CRITERION_KEYS = [c["key"] for c in CRITERIA]

# L0 "starter lens": what the ARR review form asks about, in plain language. These come from the venue's
# form, not from the LLM's taste, so offering them does not impose a standard of quality.
STARTER_LENS = [
    {"key": "clarity", "text": "Whether the paper is clear enough to follow"},
    {"key": "rigor", "text": "Whether the claims are supported by the experiments"},
    {"key": "novelty", "text": "What the paper says is new"},
    {"key": "reproducibility", "text": "Whether the work could be reproduced"},
    {"key": "limitations", "text": "Whether limitations and possible harms are discussed"},
]

LEVELS = {
    "L0": "This is one of my first reviews",
    "L1": "I've reviewed a few papers",
    "L2": "I review regularly for major venues",
    "L3": "I've served as an area chair or senior reviewer",
}
FAMILIARITY = {"new": "New to it", "basics": "Know the basics", "nearby": "Work nearby", "expert": "Work in this area"}
READ_STATUS = {"not_yet": "Not yet", "skimmed": "Skimmed", "read": "Read it"}
# Time budget (minutes) -> number of agenda cards presented proactively.
CARDS_FOR_BUDGET = {15: 4, 30: 7, 60: 10}
MINUTES_PER_CARD = 2
# Evidence passages per card, by level (§5.6).
PASSAGES_FOR_LEVEL = {"L0": (2, 3), "L1": (1, 3), "L2": (1, 2), "L3": (1, 2)}

# Plain-language explanations of the ARR form fields for beginners. Paraphrased from the ACL Rolling Review
# reviewer guidelines (https://aclrollingreview.org/reviewerguidelines); not quotations.
FIELD_HELP = {
    "summary": "a short, neutral description of what the paper does and claims, without evaluation",
    "strengths": "what you think the paper does well, and why",
    "weaknesses": "what you think falls short, where in the paper, and why it matters",
    "soundness": "whether the paper's claims are backed by its experiments, analysis, or arguments",
    "excitement": "how interesting or important you find the work",
    "reproducibility": "how easily someone could reproduce the results from what is described and released",
    "limitations_ethics": "whether limitations and possible societal impact are discussed, and any ethical concerns",
    "overall": "your overall assessment, weighing everything else",
}
FIELD_HELP_SOURCE = "ARR reviewer guidelines (paraphrased)"
# Plain names for review parts, used in the chat UI instead of ARR vocabulary (ARR names appear only in the draft).
FIELD_PLAIN = {
    "summary": "what the paper does", "strengths": "what worked for you", "weaknesses": "what didn't work for you",
    "soundness": "whether the claims are backed up", "excitement": "how interesting the work is to you",
    "reproducibility": "whether it could be reproduced", "limitations_ethics": "limitations and possible impact",
    "overall": "your overall take",
}


def profile_criteria(profile: dict) -> list[str]:
    """The reviewer's criteria in rank order (onboarding answers + criteria learned during conversations)."""
    keys = [c["key"] for c in profile.get("criteria", []) if c.get("key") in CRITERION]
    keys += [c["key"] for c in profile.get("learned", []) if c.get("key") in CRITERION and c["key"] not in keys]
    return keys


def where_to_look(profile: dict, key: str) -> list[str]:
    for c in profile.get("criteria", []) + profile.get("learned", []):
        if c.get("key") == key and c.get("where"):
            return c["where"]
    return CRITERION[key]["where"]


def help_style(profile: dict) -> str:
    """guided | evidence | quick (quick mode is the default for L3)."""
    return profile.get("help_style") or ("quick" if profile.get("level") == "L3" else "guided")


def session_quick(profile: dict, ctx: dict) -> bool:
    """Quick mode for this paper: chosen in the profile, or an L2/L3 reviewer who has already read the paper (§4.3)."""
    return help_style(profile) == "quick" or (profile.get("level") in ("L2", "L3") and ctx.get("read_status") == "read")
