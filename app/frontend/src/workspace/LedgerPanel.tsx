import { useEffect, useState } from "react";
import { type Block, type CoverageField, type Drift, type OpinionUnit, type Register, reviewApi } from "../lib/api";

const POL: Record<string, string> = { positive: "+", negative: "-", mixed: "±", neutral: "·" };
export const REGISTER_LABEL: Record<Register, string> = { words: "Your words", polished: "Polished", formal: "Formal" };
const CRIT_LABEL: Record<string, string> = {
  clarity: "clarity", rigor: "experiments", novelty: "novelty", usefulness: "usefulness", theory: "theory",
  analysis: "analysis", reproducibility: "reproducibility", limitations: "limitations",
};

export function RegisterSlider({ value, onChange, busy }: { value: Register; onChange: (r: Register) => void; busy?: boolean }) {
  return (
    <div className="flex items-center gap-2 text-[11px] text-stone-500">
      <span>Faithful</span>
      <div className="flex rounded-full border border-stone-300 p-0.5">
        {(["words", "polished", "formal"] as Register[]).map((r) => (
          <button
            key={r}
            disabled={busy}
            onClick={() => onChange(r)}
            className={`rounded-full px-2 py-0.5 ${value === r ? "bg-stone-900 text-white" : "text-stone-600"} disabled:opacity-50`}
          >
            {REGISTER_LABEL[r]}
          </button>
        ))}
      </div>
      <span>Professional</span>
    </div>
  );
}

export const driftWarn = (d?: Drift | null) => !!d && (!d.entailed || d.polarity !== "preserved" || d.intensity !== "preserved");

/** The reviewer's own statements, grouped by review field. Only these (and paper facts they confirmed) feed the review. */
type Props = {
  units: OpinionUnit[];
  fields: CoverageField[];
  sessionId: string | null;
  byId: Map<string, Block>;
  onCite: (ids: string[]) => void;
  onChanged: () => void;
};

export function LedgerPanel({ units, fields, sessionId, byId, onCite, onChanged }: Props) {
  const [edit, setEdit] = useState<{ id: string; statement: string; rationale: string } | null>(null);
  const [register, setRegister] = useState<Register>("words");
  const [variants, setVariants] = useState<Record<string, { text: string; drift: Drift | null }>>({});
  const [loading, setLoading] = useState(false);
  useEffect(() => {
    if (!sessionId || register === "words") return setVariants({});
    setLoading(true);
    reviewApi.rephraseUnits(sessionId, register).then((r) => setVariants(r.units)).finally(() => setLoading(false));
  }, [sessionId, register, units.length]);

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
    return <div className="p-4 text-sm text-stone-500">Your opinions will appear here as you chat about the paper.</div>;
  return (
    <div className="px-3 py-3">
      <div className="mb-3 rounded-md bg-stone-100 px-3 py-2 text-xs text-stone-600">
        Only things <b>you</b> said are recorded, in your words. Bare agreement with the copilot is never recorded as your opinion.
      </div>
      <div className="mb-3 flex items-center justify-between">
        <RegisterSlider value={register} onChange={setRegister} busy={loading} />
        {loading && <span className="text-[11px] text-stone-400">rephrasing…</span>}
      </div>
      {fields.map((f) => {
        const us = units.filter((u) => u.dimension === f.key);
        if (!us.length) return null;
        return (
          <section key={f.key} className="mb-4">
            <h3 className="mb-1 px-1 text-xs font-semibold uppercase tracking-wide text-stone-500">{f.label}</h3>
            {us.map((u) => {
              const isFact = u.source === "paper_fact";
              const v = !isFact && register !== "words" ? variants[u.id] : undefined;
              return (
                <div key={u.id} className="group mb-1.5 rounded-md border border-stone-200 px-2.5 py-1.5 text-[13px]">
                  {edit?.id === u.id ? (
                    <div className="space-y-1">
                      <textarea className="w-full rounded border p-1 text-[13px]" rows={2} value={edit.statement} onChange={(e) => setEdit({ ...edit, statement: e.target.value })} />
                      <input className="w-full rounded border p-1 text-[12px]" placeholder="because… (your reason)" value={edit.rationale} onChange={(e) => setEdit({ ...edit, rationale: e.target.value })} />
                      <div className="flex gap-2 text-xs">
                        <button className="rounded bg-stone-900 px-2 py-0.5 text-white" onClick={save}>Save</button>
                        <button onClick={() => setEdit(null)}>Cancel</button>
                      </div>
                    </div>
                  ) : (
                    <>
                      <div className="flex gap-2">
                        <span className="font-mono text-[10px] text-stone-400">{u.id}·T{u.turn}</span>
                        <span className="text-stone-400">{isFact ? "" : POL[u.polarity] ?? "·"}</span>
                        <span className="flex-1">{v ? v.text : `“${u.statement}”`}</span>
                        {u.criterion && <span className="shrink-0 rounded bg-stone-100 px-1 text-[10px] text-stone-500">{CRIT_LABEL[u.criterion] ?? u.criterion}</span>}
                      </div>
                      {v && <div className="ml-12 text-[11px] text-stone-400">your words: “{u.statement}”</div>}
                      {v && driftWarn(v.drift) && (
                        <div className="ml-12 text-[11px] text-amber-700">⚠ wording drift{v.drift?.note ? `: ${v.drift.note}` : ""}</div>
                      )}
                      {isFact ? (
                        <div className="ml-12 text-[11px] text-amber-800">
                          paper fact, confirmed by you at T{u.turn}{" "}
                          {u.block_ids?.length ? (
                            <button className="underline" onClick={() => onCite(u.block_ids!)}>p.{byId.get(u.block_ids[0])?.boxes[0]?.page ?? "?"}</button>
                          ) : null}
                        </div>
                      ) : u.rationale ? (
                        <div className="ml-12 text-[12px] text-stone-500">because “{u.rationale}”</div>
                      ) : (
                        <div className="ml-12 text-[11px] italic text-amber-700">no reason stated yet</div>
                      )}
                      <div className="ml-12 mt-0.5 hidden gap-3 text-[11px] text-stone-500 group-hover:flex">
                        {!isFact && <button onClick={() => setEdit({ id: u.id, statement: u.statement, rationale: u.rationale })}>Edit</button>}
                        <button onClick={() => remove(u.id)}>Remove</button>
                      </div>
                    </>
                  )}
                </div>
              );
            })}
          </section>
        );
      })}
    </div>
  );
}
