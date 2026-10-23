import { useState } from "react";
import { type DimState, type OpinionUnit, reviewApi } from "../lib/api";

const POL: Record<string, string> = { positive: "+", negative: "-", mixed: "±", neutral: "·" };

/** The reviewer's own opinion units, grouped by review dimension. Only these feed the final review. */
type Props = { units: OpinionUnit[]; dims: DimState[]; sessionId: string | null; onChanged: () => void };

export function LedgerPanel({ units, dims, sessionId, onChanged }: Props) {
  const [edit, setEdit] = useState<{ id: string; statement: string; rationale: string } | null>(null);
  const save = async () => {
    if (!edit || !sessionId) return;
    await reviewApi.patchUnit(sessionId, edit.id, { statement: edit.statement, rationale: edit.rationale });
    setEdit(null);
    onChanged();
  };
  const remove = async (id: string) => {
    if (!sessionId) return;
    await reviewApi.patchUnit(sessionId, id, { deleted: true });
    onChanged();
  };
  if (!units.length)
    return <div className="p-4 text-sm text-stone-500">Your opinions will appear here as you state them in the dialogue.</div>;
  return (
    <div className="px-3 py-3">
      <div className="mb-3 rounded-md bg-stone-100 px-3 py-2 text-xs text-stone-600">
        Only statements <b>you</b> made are recorded. Bare agreement with the copilot is never recorded as your opinion.
      </div>
      {dims.map((d) => {
        const us = units.filter((u) => u.dimension === d.key);
        if (!us.length) return null;
        return (
          <section key={d.key} className="mb-4">
            <h3 className="mb-1 px-1 text-xs font-semibold uppercase tracking-wide text-stone-500">{d.label}</h3>
            {us.map((u) => (
              <div key={u.id} className="group mb-1.5 rounded-md border border-stone-200 px-2.5 py-1.5 text-[13px]">
                {edit?.id === u.id ? (
                  <div className="space-y-1">
                    <textarea className="w-full rounded border p-1 text-[13px]" rows={2} value={edit.statement} onChange={(e) => setEdit({ ...edit, statement: e.target.value })} />
                    <input className="w-full rounded border p-1 text-[12px]" placeholder="because… (your reason)" value={edit.rationale} onChange={(e) => setEdit({ ...edit, rationale: e.target.value })} />
                    <div className="flex gap-2 text-xs"><button className="rounded bg-stone-900 px-2 py-0.5 text-white" onClick={save}>Save</button><button onClick={() => setEdit(null)}>Cancel</button></div>
                  </div>
                ) : (<>
                <div className="flex gap-2">
                  <span className="font-mono text-[10px] text-stone-400">
                    {u.id}·T{u.turn}
                  </span>
                  <span className="text-stone-400">{POL[u.polarity] ?? "·"}</span>
                  <span className="flex-1">“{u.statement}”</span>
                </div>
                {u.rationale ? (
                  <div className="ml-12 text-[12px] text-stone-500">because “{u.rationale}”</div>
                ) : (
                  <div className="ml-12 text-[11px] italic text-amber-700">no reason stated yet</div>
                )}
                <div className="ml-12 mt-0.5 hidden gap-3 text-[11px] text-stone-500 group-hover:flex">
                  <button onClick={() => setEdit({ id: u.id, statement: u.statement, rationale: u.rationale })}>Edit</button>
                  <button onClick={() => remove(u.id)}>Remove</button>
                </div>
                </>)}
              </div>
            ))}
          </section>
        );
      })}
    </div>
  );
}
