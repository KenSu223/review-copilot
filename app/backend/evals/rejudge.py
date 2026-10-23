"""Recompute opinion fidelity (and the report) for an existing persona run without re-running dialogues.

  uv run python -m evals.rejudge ../../eval/persona_runs/<timestamp>
"""
import json
import sys
from pathlib import Path

from sqlmodel import Session

from copilot.db import Paper, engine as db
from evals.personas import Persona
from evals.run import aggregate, fidelity, write_report


def main(run_dir: str) -> None:
    d = Path(run_dir)
    data = json.loads((d / "results.json").read_text())
    gold = data["gold"]
    for run in data["runs"]:
        if run["persona"] in gold:
            p = Persona(name=run["persona"], goal=run["goal"], simulated=True, hidden_opinions=gold[run["persona"]])
            first = run.get("first_message") or ""
            run["fidelity"] = fidelity(p, run["session_id"], run["records"], first)
            print(run["persona"], {k: v for k, v in run["fidelity"].items() if k != "detail"})
    m = aggregate(data["runs"])
    m["wall_seconds"] = data["metrics"].get("wall_seconds")
    data["metrics"] = m
    (d / "results.json").write_text(json.dumps(data, indent=2, default=str))
    with Session(db) as s:
        paper = s.get(Paper, data["paper"])
    write_report(d, paper, data["runs"], m, gold["earnest"], gold["vague"])
    print({k: v for k, v in m["gates"].items()})


if __name__ == "__main__":
    main(sys.argv[1])
