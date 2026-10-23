import { useMemo, useState } from "react";
import type { Block } from "../lib/api";

type Props = { blocks: Block[]; activeIds: Set<string>; onSelect: (id: string) => void };

export function SentenceIndex({ blocks, activeIds, onSelect }: Props) {
  const [query, setQuery] = useState("");
  const groups = useMemo(() => {
    const q = query.trim().toLowerCase();
    const visible = blocks.filter((b) => b.kind !== "heading" && (!q || b.text.toLowerCase().includes(q)));
    const out: { section: string; items: Block[] }[] = [];
    for (const b of visible) {
      const last = out[out.length - 1];
      if (last && last.section === b.section) last.items.push(b);
      else out.push({ section: b.section || "(no section)", items: [b] });
    }
    return out;
  }, [blocks, query]);

  return (
    <div className="flex h-full flex-col">
      <div className="border-b border-stone-200 px-3 py-2">
        <input
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          placeholder="Filter sentences…"
          className="w-full rounded-md border border-stone-300 px-3 py-1.5 text-sm outline-none focus:border-stone-500"
        />
      </div>
      <div className="min-h-0 flex-1 overflow-y-auto px-2 py-2">
        {groups.map((g, gi) => (
          <div key={`${g.section}-${gi}`} className="mb-3">
            <div className="sticky top-0 z-10 bg-white/95 px-2 py-1 text-xs font-semibold text-stone-600 backdrop-blur">
              {g.section}
            </div>
            {g.items.map((b) => (
              <button
                key={b.id}
                data-id={b.id}
                onClick={() => onSelect(b.id)}
                className={`block w-full rounded-md px-2 py-1 text-left text-[13px] leading-snug transition ${
                  activeIds.has(b.id) ? "bg-amber-100" : "hover:bg-stone-100"
                } ${b.kind === "hidden" ? "text-purple-700 line-through" : ""}`}
              >
                <span className="mr-1.5 font-mono text-[10px] text-stone-400">{b.id}</span>
                {b.kind !== "sentence" && (
                  <span className="mr-1 rounded bg-stone-100 px-1 text-[10px] uppercase text-stone-500">{b.kind}</span>
                )}
                {b.text}
              </button>
            ))}
          </div>
        ))}
      </div>
    </div>
  );
}
