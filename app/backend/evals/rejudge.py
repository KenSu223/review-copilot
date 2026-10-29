"""Recompute opinion fidelity (and the report) for an existing persona run without re-running dialogues.

  uv run python -m evals.rejudge ../../eval/persona_runs/<timestamp>

Works with results grouped by flow (current) and with older single-flow results (a flat list of runs).
"""
import json
import sys
from pathlib import Path

from sqlmodel import Session

from copilot.db import Paper, engine as db
from evals.personas import Persona
from evals.run import ab_table, aggregate, fidelity, write_report

EARNEST_GROUP = {"earnest", "casual", "taste_clarity", "taste_rigor", "taste_novelty"}


def main(run_dir: str) -> None:
    d = Path(run_dir)
    data = json.loads((d / "results.json").read_text())
    gold = data["gold"]
    by_flow = data["runs"] if isinstance(data["runs"], dict) else {"evidence": data["runs"]}
    for flow, runs in by_flow.items():
        for run in runs:
            if run.get("fidelity") is None:
                continue
            hidden = gold["earnest"] if run["persona"] in EARNEST_GROUP else gold["vague"]
            p = Persona(name=run["persona"], goal=run["goal"], simulated=True, hidden_opinions=hidden)
            run["fidelity"] = fidelity(p, run["session_id"], run["records"], run.get("first_message") or "")
            print(flow, run["persona"], {k: v for k, v in run["fidelity"].items() if k != "detail"})
    metrics = {f: aggregate(runs) for f, runs in by_flow.items()}
    data.update({"runs": by_flow, "metrics": metrics, "ab_summary": ab_table(by_flow)[1] if len(by_flow) > 1 else None})
    (d / "results.json").write_text(json.dumps(data, indent=2, default=str))
    with Session(db) as s:
        paper = s.get(Paper, data["paper"])
    write_report(d, paper, by_flow, metrics, gold["earnest"], gold["vague"])
    print({f: m["gates"] for f, m in metrics.items()})


if __name__ == "__main__":
    main(sys.argv[1])
