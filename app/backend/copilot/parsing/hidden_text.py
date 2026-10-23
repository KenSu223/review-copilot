"""Detect text a human reader cannot see but an LLM would read (prompt-injection channel):
invisible render mode, zero opacity, near-white fill, microscopic font, or off-page placement."""
from pathlib import Path

import pymupdf


def _is_white(color) -> bool:
    return color is not None and len(color) >= 3 and all(c >= 0.94 for c in color[:3])


def detect(path: Path, max_items: int = 50) -> list[dict]:
    findings: list[dict] = []
    doc = pymupdf.open(path)
    for pno, page in enumerate(doc, start=1):
        pr = page.rect
        for span in page.get_texttrace():
            text = "".join(chr(c[0]) for c in span.get("chars", []) if c[0] >= 32).strip()
            if len(text) < 4:
                continue
            reasons = []
            if span.get("type") == 3:
                reasons.append("invisible render mode")
            if span.get("opacity", 1) == 0:
                reasons.append("zero opacity")
            if _is_white(span.get("color")):
                reasons.append("white text")
            if span.get("size", 10) < 2:
                reasons.append(f"tiny font ({span.get('size', 0):.1f}pt)")
            x0, y0, x1, y1 = span["bbox"]
            if (x1 < pr.x0 or x0 > pr.x1 or y1 < pr.y0 or y0 > pr.y1) and len(text) >= 20:
                reasons.append("outside page")  # short strings here are usually margin stamps
            if not reasons:
                continue
            findings.append({
                "page": pno, "text": text[:300], "reasons": reasons,
                "box": {"page": pno, "left": max(x0, 0) / pr.width * 100, "top": max(y0, 0) / pr.height * 100,
                        "width": max(x1 - x0, 1) / pr.width * 100, "height": max(y1 - y0, 1) / pr.height * 100},
            })
            if len(findings) >= max_items:
                return findings
    return findings


def overlaps(box_a: dict, box_b: dict) -> bool:
    if box_a["page"] != box_b["page"]:
        return False
    return not (box_a["left"] + box_a["width"] < box_b["left"] or box_b["left"] + box_b["width"] < box_a["left"]
                or box_a["top"] + box_a["height"] < box_b["top"] or box_b["top"] + box_b["height"] < box_a["top"])
