r"""Supplementary re-grade of existing Task-A outputs with tolerant [S#] tag parsing.

Why: bench.py extracts cited sentences with TAG_RE = r"\[S(\d+)\]", so grouped tags such as
"[S0, S28]" or ranges such as "[S179-S195]" are dropped and the judge is told the turn cited
"(none)", which drives groundedness down even when the cited sentences do support the claim.
This wrapper does NOT re-run the candidate model. It reads results/<model>.json, re-parses the
Task-A text with a tolerant parser (comma lists, ranges "S3-S5" / "S80-155"), and re-runs the
same Opus 5.5 judge with the same prompt and schema as bench.py. Output goes to
wrappers/rejudge_out/<model>.json so results/ stays untouched.

Usage (from eval/model_bench):  python wrappers/rejudge_tolerant_tags.py <model_id> [<model_id> ...]
"""
import json, pathlib, re, sys

HERE = pathlib.Path(__file__).resolve().parent
BENCH = HERE.parent
sys.path.insert(0, str(BENCH))
import bench  # noqa: E402  (module import only; bench.main() is not called)

GROUP_RE = re.compile(r"\[(S\d+(?:\s*[,\-–]\s*S?\d+)*)\]")
MAX_RANGE = 40

def tolerant_tags(text):
    tags, nonstd = [], 0
    for g in GROUP_RE.findall(text):
        parts = re.split(r"\s*,\s*", g)
        if len(parts) > 1 or re.search(r"[\-–]", g):
            nonstd += 1
        for p in parts:
            m = re.match(r"S?(\d+)\s*[\-–]\s*S?(\d+)$", p)
            if m:
                a, b = int(m.group(1)), int(m.group(2))
                if 0 <= b - a <= MAX_RANGE:
                    tags.extend(range(a, b + 1))
                else:
                    tags.extend([a, b])
            else:
                tags.append(int(p.lstrip("S")))
    return tags, nonstd

def main(models):
    bench.load_env()
    judge = bench.make_mantle()
    for model in models:
        fname = re.sub(r"[^A-Za-z0-9._-]", "_", model) + ".json"
        d = json.loads((BENCH / "results" / fname).read_text())
        out = {"model": model, "source": f"results/{fname}", "taskA": {}}
        for name, a in d["taskA"].items():
            rev = bench.SCENARIOS[name]
            text = a["text"]
            tags, nonstd = tolerant_tags(text)
            valid = sorted(set(t for t in tags if t < len(bench.SENTS)))
            cited = "\n".join(f"[S{t}] {bench.SENTS[t]}" for t in valid)
            jprompt = (f"Copilot rules:\n{bench.SYSTEM}\n\nReviewer message:\n{rev}\n\nCopilot turn to grade:\n<<<{text}>>>\n\n"
                       f"Texts of the sentences it cited:\n{cited or '(none)'}\n\nGrade the copilot turn with the rubric.")
            rec = dict(n_tags_tolerant=len(tags), invalid_tags_tolerant=len([t for t in tags if t >= len(bench.SENTS)]),
                       nonstd_tag_groups=nonstd, judge_original=a.get("judge"))
            try:
                j = judge("You are a strict evaluator of a Socratic review copilot. Grade only what is in the turn.",
                          jprompt, max_tokens=3000, schema=bench.JUDGE_SCHEMA, model="anthropic.claude-opus-5-5", effort="low")
                rec["judge_tolerant"] = json.loads(j["text"])
            except Exception as e:
                rec["error"] = repr(e)[:300]
            out["taskA"][name] = rec
        (HERE / "rejudge_out" / fname).write_text(json.dumps(out, indent=2))
        dims = ["neutrality", "groundedness", "question_quality", "concision", "firewall_handling"]
        summ = {k: {"nonstd": v["nonstd_tag_groups"],
                    "orig": [v["judge_original"][x] for x in dims] if v.get("judge_original") else None,
                    "tol": [v["judge_tolerant"][x] for x in dims] if v.get("judge_tolerant") else v.get("error")}
                for k, v in out["taskA"].items()}
        print(model, json.dumps(summ))

if __name__ == "__main__":
    main(sys.argv[1:])
