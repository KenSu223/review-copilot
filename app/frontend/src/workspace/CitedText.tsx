import type { Block, Segment } from "../lib/api";

type Props = { segments: Segment[]; byId: Map<string, Block>; onCite: (ids: string[]) => void };

/** Renders copilot text; every cited span gets a dotted underline + a page chip that jumps to the evidence. */
export function CitedText({ segments, byId, onCite }: Props) {
  return (
    <span className="whitespace-pre-wrap">
      {segments.map((seg, i) => {
        if (!seg.cites.length) return <span key={i}>{seg.text}</span>;
        const first = byId.get(seg.cites[0]);
        const page = first?.boxes[0]?.page;
        const preview = seg.cites.map((id) => byId.get(id)?.text ?? id).join(" … ");
        return (
          <span key={i}>
            <span className="decoration-amber-500 decoration-dotted underline-offset-2 [text-decoration-line:underline]">
              {seg.text}
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
