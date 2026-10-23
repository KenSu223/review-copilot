"""Supplementary re-judge of canonical Task-A texts with a lenient citation parser.

bench.py's TAG_RE only matches single tags like [S12]; grouped tags ([S2, S3]) and ranges
([S177-S196], incl. unicode hyphens/en-dashes) are neither counted nor passed to the judge,
so the judge sees "(none)" and scores groundedness ~1. This script re-runs the *same* judge
prompt/model/schema, but supplies the cited sentence texts parsed leniently (ranges expanded,
capped at 40 sentences per range). Writes wrappers/rejudge_lenient/<model>.json.
Usage (from eval/model_bench): python wrappers/rejudge_lenient_tags.py results/<model>.json ...
"""
import json, pathlib, re, sys
HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))
import bench  # noqa: E402

BRACKET = re.compile(r"\[([^\[\]]*?S\s*\d+[^\[\]]*?)\]")
ITEM = re.compile(r"S?\s*(\d+)(?:\s*[-‐‑‒–—]\s*S?\s*(\d+))?")

def lenient_tags(text):
    tags, ranges = [], []
    for grp in BRACKET.findall(text):
        for a, b in ITEM.findall(grp):
            a = int(a)
            if b:
                b = int(b); ranges.append((a, b))
                tags.extend(range(a, min(b, a + 39) + 1))
            else:
                tags.append(a)
    return tags, ranges

def main():
    bench.load_env()
    judge = bench.make_mantle()
    outdir = HERE / "rejudge_lenient"; outdir.mkdir(exist_ok=True)
    for path in sys.argv[1:]:
        d = json.loads(pathlib.Path(path).read_text())
        res = {"model": d["model"], "turns": {}}
        for name, rev in bench.SCENARIOS.items():
            if name not in d["taskA"]:
                continue
            text = d["taskA"][name]["text"]
            tags, ranges = lenient_tags(text)
            valid = sorted({t for t in tags if t < len(bench.SENTS)})
            cited = "\n".join(f"[S{t}] {bench.SENTS[t]}" for t in valid)
            jprompt = (f"Copilot rules:\n{bench.SYSTEM}\n\nReviewer message:\n{rev}\n\nCopilot turn to grade:\n<<<{text}>>>\n\n"
                       f"Texts of the sentences it cited:\n{cited or '(none)'}\n\nGrade the copilot turn with the rubric.")
            j = judge("You are a strict evaluator of a Socratic review copilot. Grade only what is in the turn.",
                      jprompt, max_tokens=3000, schema=bench.JUDGE_SCHEMA, model="anthropic.claude-opus-5-5", effort="low")
            res["turns"][name] = dict(n_lenient_tags=len(valid), invalid=len([t for t in tags if t >= len(bench.SENTS)]),
                                      ranges=ranges, judge=json.loads(j["text"]))
        fname = re.sub(r"[^A-Za-z0-9._-]", "_", d["model"]) + ".json"
        (outdir / fname).write_text(json.dumps(res, indent=2))
        print(d["model"], {k: {kk: vv for kk, vv in v["judge"].items() if kk != "issues"} for k, v in res["turns"].items()})

if __name__ == "__main__":
    main()
