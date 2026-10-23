"""Supplementary repeat runs for the Qwen/DeepSeek comparison (does NOT modify bench.py).

Why: bench.py runs each Task-A scenario once (n=2 judged turns per model) and only passes the
judge the sentences behind single-form tags like [S12]. Most Qwen/DeepSeek outputs cite with
lists/ranges ([S2, S4], [S177-S194]), so the judge sees "(none)" and groundedness collapses to 1-2.

This wrapper imports bench.py and, per model:
  * re-runs Task A `--reps` times; each turn is judged twice with the identical judge prompt:
      raw  = cited sentences exactly as bench.py builds them (single [S#] tags only)
      norm = list/range tags expanded to their sentences (ranges capped at 40 sentences)
  * re-runs Task B `--reps` times.
Writes results/repeats_qwen_deepseek/<model>.json (subfolder so results/*.json globs are unaffected).

Usage (from eval/model_bench):
  python wrappers/repeat_qwen_deepseek.py --model deepseek.v3.2 --region us-west-2 --price 0.62,1.85 --reps 2
"""
import argparse, json, pathlib, re, sys, time

HERE = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(HERE))

import bench  # noqa: E402  (bench.py only parses CLI args under __main__)


GROUP_RE = re.compile(r"\[([^\[\]]*S\d[^\[\]]*)\]")


def expand_tags(text, cap=40):
    ids = set()
    for g in GROUP_RE.findall(text):
        for a, b in re.findall(r"S(\d+)\s*[-–—]\s*S?(\d+)", g):
            a, b = int(a), int(b)
            if a <= b:
                ids.update(range(a, min(b, a + cap - 1) + 1))
        ids.update(int(x) for x in re.findall(r"S(\d+)(?!\.\d)", g))
    return sorted(i for i in ids if i < len(bench.SENTS))


def judge_turn(judge, rev, text, ids):
    cited = "\n".join(f"[S{t}] {bench.SENTS[t]}" for t in ids)
    jprompt = (f"Copilot rules:\n{bench.SYSTEM}\n\nReviewer message:\n{rev}\n\nCopilot turn to grade:\n<<<{text}>>>\n\n"
               f"Texts of the sentences it cited:\n{cited or '(none)'}\n\nGrade the copilot turn with the rubric.")
    j = judge("You are a strict evaluator of a Socratic review copilot. Grade only what is in the turn.",
              jprompt, max_tokens=3000, schema=bench.JUDGE_SCHEMA, model="anthropic.claude-opus-5-5", effort="low")
    return json.loads(j["text"])


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--model", required=True)
    ap.add_argument("--region", default="us-west-2")
    ap.add_argument("--price", default=None)
    ap.add_argument("--reps", type=int, default=2)
    ap.add_argument("--max-tokens", type=int, default=6000)
    args = ap.parse_args()
    bench.ARGS = argparse.Namespace(model=args.model, backend="converse", region=args.region,
                                    price=args.price, max_tokens=args.max_tokens)
    bench.load_env()
    call = bench.make_converse(args.region)
    judge = bench.make_mantle()
    pin, pout = (float(x) for x in args.price.split(",")) if args.price else (None, None)
    usd = lambda u: None if pin is None else ((u.get("inputTokens") or 0) * pin + (u.get("outputTokens") or 0) * pout) / 1e6
    out = {"model": args.model, "region": args.region, "price_per_mtok": [pin, pout], "reps": args.reps,
           "taskA": [], "taskB": [], "errors": []}

    for rep in range(args.reps):
        for name, rev in bench.SCENARIOS.items():
            user = f"<paper>\n{bench.PAPER}\n</paper>\n\n{rev}"
            try:
                r = call(bench.SYSTEM, user, max_tokens=args.max_tokens)
            except Exception as e:
                out["errors"].append(f"rep{rep} {name}: {repr(e)[:300]}"); continue
            text = bench.strip_reasoning(r["text"])
            single = sorted({int(x) for x in bench.TAG_RE.findall(text) if int(x) < len(bench.SENTS)})
            norm = expand_tags(text)
            rec = dict(rep=rep, scenario=name, text=text, sec=round(r["sec"], 2), usd=usd(r["usage"]),
                       own_words=len(re.sub(r"\[S\d+\]", "", text).split()), questions=text.count("?"),
                       n_single_ids=len(single), n_norm_ids=len(norm))
            for label, ids in (("raw", single), ("norm", norm)):
                try:
                    rec[f"judge_{label}"] = judge_turn(judge, rev, text, ids)
                except Exception as e:
                    out["errors"].append(f"rep{rep} judge_{label} {name}: {repr(e)[:300]}")
            out["taskA"].append(rec)

        for cname, expect, cand in bench.GUARD_CASES:
            try:
                r = call(bench.GUARD_SYSTEM, f"Draft turn:\n<<<{cand}>>>", max_tokens=2000, schema=bench.GUARD_SCHEMA)
                res = bench.parse_json(r["text"])
                verdict = (res or {}).get("verdict")
                ok = (verdict == "allow") if expect == "allow" else (verdict in ("revise", "block"))
                out["taskB"].append(dict(rep=rep, case=cname, verdict=verdict, ok=bool(ok), sec=round(r["sec"], 2),
                                         method=r["method"]))
            except Exception as e:
                out["taskB"].append(dict(rep=rep, case=cname, error=repr(e)[:300], ok=False))

    d = HERE / "results" / "repeats_qwen_deepseek"
    d.mkdir(exist_ok=True)
    fname = re.sub(r"[^A-Za-z0-9._-]", "_", args.model) + ".json"
    (d / fname).write_text(json.dumps(out, indent=2))
    print(f"wrote {d / fname}; errors={len(out['errors'])}")


if __name__ == "__main__":
    main()
