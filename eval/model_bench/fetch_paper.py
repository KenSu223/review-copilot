"""Recreate data/paper_2506.08134.txt (the benchmark paper text, not committed to the repo).

  cd app/backend && uv run python ../../eval/model_bench/fetch_paper.py
"""
from pathlib import Path

import httpx
import pymupdf

ARXIV_ID = "2506.08134"
out = Path(__file__).parent / "data" / f"paper_{ARXIV_ID}.txt"
out.parent.mkdir(exist_ok=True)
pdf = httpx.get(f"https://arxiv.org/pdf/{ARXIV_ID}", follow_redirects=True, timeout=60).content
doc = pymupdf.open(stream=pdf, filetype="pdf")
out.write_text("".join(f"\n\n===== PAGE {i + 1} =====\n" + page.get_text() for i, page in enumerate(doc)))
print(f"wrote {out} ({out.stat().st_size} bytes)")
