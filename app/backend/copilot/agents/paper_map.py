"""Objective paper map: what the paper says it contributes, how it was set up, what it reports,
and what limitations the authors themselves state. No evaluation. Every item cites block ids."""
from .. import llm

ITEM = {
    "type": "object",
    "properties": {
        "text": {"type": "string", "description": "Neutral paraphrase, <= 25 words, close to the paper's own wording"},
        "block_ids": {"type": "array", "items": {"type": "string"}, "description": "ids like s-0042 supporting the item"},
    },
    "required": ["text", "block_ids"],
    "additionalProperties": False,
}
LIST = {"type": "array", "items": ITEM}

SCHEMA = {
    "type": "object",
    "properties": {
        "contributions": LIST,       # what the authors say they contribute
        "claims": LIST,              # main empirical / theoretical claims as stated
        "datasets": LIST,
        "baselines": LIST,
        "metrics": LIST,
        "models_and_methods": LIST,  # proposed method / models / key setup choices
        "results": LIST,             # reported results (with numbers when given)
        "stated_limitations": LIST,  # limitations the authors themselves state
        "availability": LIST,        # code, data, hyper-parameters, seeds, compute, as stated
    },
    "required": ["contributions", "claims", "datasets", "baselines", "metrics", "models_and_methods",
                 "results", "stated_limitations", "availability"],
    "additionalProperties": False,
}

SYSTEM = """You build an OBJECTIVE map of a research paper for a peer reviewer.
Report only what the paper itself states. Never evaluate: no judgments of novelty, quality, rigor,
significance, sufficiency, or clarity, and no evaluative adjectives (strong, weak, limited, novel,
impressive, thorough, comprehensive...). Do not add outside knowledge.
Each item: a short neutral paraphrase close to the paper's wording + the ids of the sentence blocks
that state it (copy ids exactly as given, e.g. s-0042). Prefer 1-3 precise ids over long ranges.
If the paper does not state something for a category, return an empty list for it (do not guess).
Keep each list to the most important items (max 8)."""

FACET_OF = {
    "contributions": "claim", "claims": "claim",
    "datasets": "method", "baselines": "method", "metrics": "method", "models_and_methods": "method",
    "results": "result", "stated_limitations": "limitation", "availability": "method",
}


def build(blocks: list[tuple[str, str, str]], title: str) -> tuple[dict, dict]:
    """blocks: (block_id, kind, text). Returns (validated map, call log dict)."""
    lines = [f"[{bid}] ({kind}) {text}" if kind != "sentence" else f"[{bid}] {text}" for bid, kind, text in blocks]
    user = f"Paper title: {title}\n\nSentence blocks:\n" + "\n".join(lines)
    data, call = llm.structured("paper_map", SYSTEM, user, SCHEMA)
    valid = {bid for bid, _, _ in blocks}
    dropped = 0
    for key in SCHEMA["properties"]:
        items = []
        for it in data.get(key, []):
            ids = [b for b in it.get("block_ids", []) if b in valid]
            dropped += len(it.get("block_ids", [])) - len(ids)
            if ids:
                items.append({"text": it["text"].strip(), "block_ids": ids})
        data[key] = items
    facets: dict[str, str] = {}
    for key, facet in FACET_OF.items():
        for it in data[key]:
            for b in it["block_ids"]:
                facets.setdefault(b, facet)
    data["facets"] = facets
    data["dropped_invalid_ids"] = dropped
    return data, call.__dict__
