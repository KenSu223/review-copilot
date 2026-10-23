from copilot.parsing.grobid import tei_to_doc

TEI = """<?xml version="1.0" encoding="UTF-8"?>
<TEI xmlns="http://www.tei-c.org/ns/1.0">
 <teiHeader><fileDesc><titleStmt><title level="a" type="main">A Tiny Paper</title></titleStmt></fileDesc>
  <profileDesc><abstract><div><p><s coords="1,61.2,79.2,306.0,10.0">We study tiny papers.</s></p></div></abstract></profileDesc>
 </teiHeader>
 <facsimile><surface n="1" ulx="0.0" uly="0.0" lrx="612.0" lry="792.0"/></facsimile>
 <text><body>
  <div><head n="1." coords="1,61.2,100,80,10">Introduction</head>
   <p><s coords="1,61.2,120,200,9;1,61.2,130,100,9">First sentence spans two lines.</s><s coords="1,61.2,140,150,9">Second one.</s></p>
  </div>
  <div><head coords="1,61.2,160,80,10">Run-in heading.</head><p><s coords="1,61.2,170,100,9">Under a run-in head.</s></p></div>
  <figure type="table" coords="1,300,400,200,100"><head>Table 1</head><figDesc><div><p><s coords="1,300,390,200,8">Main results.</s></p></div></figDesc>
   <table><row><cell>Model</cell><cell>Acc</cell></row><row><cell>Ours</cell><cell>91.0</cell></row></table></figure>
 </body></text>
</TEI>"""


def test_tei_to_blocks_structure_and_boxes():
    doc = tei_to_doc(TEI)
    assert doc.title == "A Tiny Paper"
    assert doc.page_sizes == [[612.0, 792.0]]
    kinds = [b["kind"] for b in doc.blocks]
    assert kinds.count("sentence") == 4 and "heading" in kinds and "caption" in kinds and "table" in kinds
    first = next(b for b in doc.blocks if b["text"].startswith("First sentence"))
    assert first["section"] == "1. Introduction"
    assert len(first["boxes"]) == 2  # one box per text line
    box = first["boxes"][0]
    assert abs(box["left"] - 61.2 / 612 * 100) < 1e-6 and abs(box["top"] - 120 / 792 * 100) < 1e-6
    runin = next(b for b in doc.blocks if b["text"] == "Under a run-in head.")
    assert runin["section"] == "1. Introduction › Run-in heading"
    table = next(b for b in doc.blocks if b["kind"] == "table")
    assert "Ours | 91.0" in table["text"]
