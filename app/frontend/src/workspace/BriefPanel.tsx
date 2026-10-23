import type { PaperMap } from "../lib/api";
import { BRIEF_SECTIONS, FACETS } from "../lib/facets";

type Props = {
  map: PaperMap | null;
  activeKey: string | null;
  onSelect: (key: string, blockIds: string[]) => void;
  onRebuild: () => void;
};

export function BriefPanel({ map, activeKey, onSelect, onRebuild }: Props) {
  if (!map || map.status === "computing")
    return <div className="p-4 text-sm text-stone-500">Building the objective paper map… (≈30 s)</div>;
  if (map.status === "error")
    return (
      <div className="p-4 text-sm text-red-600">
        Paper map failed: {map.error}{" "}
        <button className="underline" onClick={onRebuild}>
          Retry
        </button>
      </div>
    );
  return (
    <div className="px-3 py-3">
      <div className="mb-3 rounded-md bg-stone-100 px-3 py-2 text-xs text-stone-600">
        <b>Facts only.</b> What the paper itself states, with links to the passages. Your assessment comes next.
      </div>
      {BRIEF_SECTIONS.map((sec) => {
        const items = map.data[sec.key] ?? [];
        const dot = FACETS.find((f) => f.key === sec.facet)?.dot;
        return (
          <section key={sec.key} className="mb-4">
            <h3 className="mb-1 flex items-center gap-2 px-1 text-xs font-semibold uppercase tracking-wide text-stone-500">
              <span className={`inline-block h-2 w-2 rounded-full ${dot}`} />
              {sec.label} <span className="font-normal normal-case text-stone-400">({items.length})</span>
            </h3>
            {items.length === 0 ? (
              <p className="px-1 text-[13px] italic text-stone-400">Not stated in the paper (as extracted).</p>
            ) : (
              <ul>
                {items.map((it, i) => {
                  const key = `${sec.key}-${i}`;
                  return (
                    <li key={key}>
                      <button
                        onClick={() => onSelect(key, it.block_ids)}
                        className={`w-full rounded-md px-2 py-1.5 text-left text-[13px] leading-snug transition ${
                          activeKey === key ? "bg-amber-100" : "hover:bg-stone-100"
                        }`}
                      >
                        {it.text}
                        <span className="ml-1.5 whitespace-nowrap font-mono text-[10px] text-stone-400">
                          [{it.block_ids.length > 2 ? `${it.block_ids[0]} +${it.block_ids.length - 1}` : it.block_ids.join(", ")}]
                        </span>
                      </button>
                    </li>
                  );
                })}
              </ul>
            )}
          </section>
        );
      })}
    </div>
  );
}
