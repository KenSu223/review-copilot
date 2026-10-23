"""Review dimensions (ARR-form based) that structure the Socratic dialogue.

Each dimension opens with a COMMIT question (reviewer states a view BEFORE any paper facts are shown,
to avoid anchoring), then the copilot surfaces objective inventory items from the paper map, probes
for evidence, checks factual statements, and confirms the recorded view.
"""
STANCE_CHIPS = ["Convinced", "Partly", "Not convinced", "Not sure"]

DIMENSIONS = [
    {
        "key": "summary", "label": "Summary", "stage": "S1", "arr_field": "Paper Summary",
        "opener": "Before I show anything from the paper: in 2–3 sentences, how would you describe what this paper claims to contribute?",
        "inventory": ["contributions"], "chips": [],
    },
    {
        "key": "soundness", "label": "Soundness", "stage": "S2", "arr_field": "Soundness",
        "opener": "How convinced are you so far, if at all, that the paper's main claims are supported by its evidence — and what is that based on?",
        "inventory": ["claims", "results", "models_and_methods", "datasets", "baselines", "metrics"], "chips": STANCE_CHIPS,
    },
    {
        "key": "strengths", "label": "Strengths", "stage": "S3", "arr_field": "Summary of Strengths",
        "opener": "What, if anything, do you see as the paper's main strengths?",
        "inventory": [], "chips": [],
    },
    {
        "key": "weaknesses", "label": "Weaknesses", "stage": "S3", "arr_field": "Summary of Weaknesses",
        "opener": "What, if anything, do you see as the paper's main weaknesses?",
        "inventory": ["stated_limitations"], "chips": [],
    },
    {
        "key": "excitement", "label": "Excitement", "stage": "S4", "arr_field": "Excitement",
        "opener": "If this paper were removed from the literature, what, if anything, would be missing in your view?",
        "inventory": ["contributions"], "chips": [],
    },
    {
        "key": "reproducibility", "label": "Reproducibility", "stage": "S4", "arr_field": "Reproducibility",
        "opener": "How easily, if at all, do you think someone could reproduce the paper's results?",
        "inventory": ["availability", "models_and_methods", "datasets"], "chips": ["Easily", "With some difficulty", "Hardly", "Not sure"],
    },
    {
        "key": "limitations_ethics", "label": "Limitations & ethics", "stage": "S4", "arr_field": "Limitations and Societal Impact / Ethical Concerns",
        "opener": "How, if at all, have the authors addressed limitations and possible societal impact, from your reading?",
        "inventory": ["stated_limitations"], "chips": [],
    },
    {
        "key": "overall", "label": "Overall", "stage": "S4", "arr_field": "Overall Assessment",
        "opener": "Which considerations, if any, weigh most in your overall assessment of this paper?",
        "inventory": [], "chips": [],
    },
]
DIM_BY_KEY = {d["key"]: d for d in DIMENSIONS}
ORDER = [d["key"] for d in DIMENSIONS]
