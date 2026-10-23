import type { DimState } from "../lib/api";

const ICON: Record<DimState["status"], string> = { covered: "●", partial: "◐", open: "○", skipped: "⊘" };
const TONE: Record<DimState["status"], string> = {
  covered: "text-emerald-700 border-emerald-200 bg-emerald-50",
  partial: "text-amber-700 border-amber-200 bg-amber-50",
  open: "text-stone-500 border-stone-200 bg-white",
  skipped: "text-stone-400 border-stone-200 bg-stone-50",
};

export function DimensionRail({ dims, current, onGoto }: { dims: DimState[]; current: string; onGoto: (key: string) => void }) {
  return (
    <div className="flex flex-wrap gap-1 border-b border-stone-200 bg-white px-3 py-2">
      {dims.map((d) => (
        <button
          key={d.key}
          onClick={() => onGoto(d.key)}
          title={`ARR field: ${d.arr_field} · ${d.status}`}
          className={`rounded-full border px-2 py-0.5 text-[11px] transition ${TONE[d.status]} ${
            d.key === current ? "ring-2 ring-stone-800/70" : ""
          }`}
        >
          <span className="mr-1">{ICON[d.status]}</span>
          {d.label}
        </button>
      ))}
    </div>
  );
}
