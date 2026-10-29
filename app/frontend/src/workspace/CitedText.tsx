import type { ReactNode } from "react";
import type { Block, GlossaryTerm, Segment } from "../lib/api";

type Props = { segments: Segment[]; byId: Map<string, Block>; onCite: (ids: string[]) => void; glossary?: GlossaryTerm[] };

const escape = (s: string) => s.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");

/** Key terms get a dotted underline; hovering shows the paper's own sentence that defines them (paper-internal only). */
function withGlossary(text: string, glossary: GlossaryTerm[], onCite: (ids: string[]) => void): ReactNode {
  if (!glossary.length) return text;
  const re = new RegExp(`\\b(${glossary.map((g) => escape(g.term)).sort((a, b) => b.length - a.length).join("|")})\\b`, "gi");
  const out: ReactNode[] = [];
  let last = 0;
  for (const m of text.matchAll(re)) {
    const g = glossary.find((x) => x.term.toLowerCase() === m[0].toLowerCase());
    if (!g || m.index === undefined) continue;
    out.push(text.slice(last, m.index));
    out.push(
      <span
        key={`${m.index}-${g.term}`}
        title={`In the paper: ${g.text}`}
        onClick={() => onCite([g.block_id])}
        className="cursor-help decoration-sky-500 decoration-dotted underline-offset-2 [text-decoration-line:underline]"
      >
        {m[0]}
      </span>,
    );
    last = m.index + m[0].length;
  }
  out.push(text.slice(last));
  return out;
}

/** Renders copilot text; every cited span gets a dotted underline + a page chip that jumps to the evidence. */
export function CitedText({ segments, byId, onCite, glossary = [] }: Props) {
  return (
    <span className="whitespace-pre-wrap">
      {segments.map((seg, i) => {
        if (!seg.cites.length) return <span key={i}>{withGlossary(seg.text, glossary, onCite)}</span>;
        const first = byId.get(seg.cites[0]);
        const page = first?.boxes[0]?.page;
        const preview = seg.cites.map((id) => byId.get(id)?.text ?? id).join(" … ");
        return (
          <span key={i}>
            <span className="decoration-amber-500 decoration-dotted underline-offset-2 [text-decoration-line:underline]">
              {withGlossary(seg.text, glossary, onCite)}
            </span>
            <button
              onClick={() => onCite(seg.cites)}
              title={preview}
              className="mx-0.5 inline-flex -translate-y-px items-center rounded border border-amber-300 bg-amber-50 px-1 font-mono text-[10px] leading-4 text-amber-800 hover:bg-amber-100"
            >
              p.{page ?? "?"}
            </button>
          </span>
        );
      })}
    </span>
  );
}
