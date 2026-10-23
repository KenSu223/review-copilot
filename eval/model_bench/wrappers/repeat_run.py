"""Repeat run of the unmodified bench.py pipeline, writing to wrappers/repeat_runs/results/
instead of results/ (so canonical results are not overwritten). Same prompts, judge, parsing.
Usage (from eval/model_bench): python wrappers/repeat_run.py --model M --region R --price in,out
"""
import argparse, pathlib, sys
HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))
import bench  # noqa: E402

ap = argparse.ArgumentParser()
ap.add_argument("--model", required=True)
ap.add_argument("--backend", default="converse", choices=["converse", "mantle"])
ap.add_argument("--region", default="us-west-2")
ap.add_argument("--price", default=None)
ap.add_argument("--max-tokens", type=int, default=6000)
bench.ARGS = ap.parse_args()
out_root = HERE / "repeat_runs"
(out_root / "results").mkdir(parents=True, exist_ok=True)
bench.HERE = out_root  # main() writes HERE/"results"/<model>.json; paper/sentences already loaded at import
bench.main()
