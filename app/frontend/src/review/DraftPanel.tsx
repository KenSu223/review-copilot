import { useEffect, useMemo, useState } from "react";
import { type Block, type DraftSentence, type DraftView, type OpinionUnit, type Register, reviewApi } from "../lib/api";
import { driftWarn, RegisterSlider } from "../workspace/LedgerPanel";
import { ExportModal } from "./ExportModal";

type Props = {
  sessionId: string;
  units: OpinionUnit[];
  byId: Map<string, Block>;
  onCite: (ids: string[]) => void;
};

const STATUS_CLS: Record<DraftSentence["status"], string> = {
  proposed: "text-stone-500",
  accepted: "text-stone-900",
  edited: "text-stone-900",
  rejected: "text-stone-400 line-through",
};

export function DraftPanel({ sessionId, units, byId, onCite }: Props) {
  const [view, setView] = useState<DraftView | null>(null);
  const [busy, setBusy] = useState(false);
  const [selected, setSelected] = useState<string | null>(null);
  const [editing, setEditing] = useState<{ sid: string; text: string } | null>(null);
  const [showExport, setShowExport] = useState(false);
  const unitById = useMemo(() => new Map(units.map((u) => [u.id, u])), [units]);

  useEffect(() => {
    reviewApi.getDraft(sessionId).then(setView);
  }, [sessionId]);

  const generate = async () => {
    setBusy(true);
    try {
      setView(await reviewApi.makeDraft(sessionId));
    } finally {
      setBusy(false);
    }
  };
  const patch = async (st: DraftSentence, body: Partial<DraftSentence>) => {
    const upd = await reviewApi.patchSentence(sessionId, st.sid, body);
    setView((v) =>
      v && v.draft
        ? { ...v, draft: { ...v.draft, sections: v.draft.sections.map((sec) => ({ ...sec, sentences: sec.sentences.map((x) => (x.sid === upd.sid ? upd : x)) })) } }
        : v,
    );
    reviewApi.getDraft(sessionId).then((v) => setView((cur) => (cur ? { ...cur, preflight: v.preflight } : v)));
  };
  const setRegister = async (r: Register, sentenceId?: string) => setView(await reviewApi.setRegister(sessionId, r, sentenceId));
  const setScore = async (field: string, value: number) => {
    await reviewApi.putScore(sessionId, field, value);
    setView(await reviewApi.getDraft(sessionId));
  };

  const all = view?.draft?.sections.flatMap((s) => s.sentences) ?? [];
  const sel = all.find((s) => s.sid === selected) ?? null;
  const fieldLabel = (k: string) => view?.fields.find((f) => f.key === k)?.label ?? k;
  const accepted = all.filter((s) => s.status === "accepted" || s.status === "edited").length;

  return (
    <div className="flex h-full flex-col">
      <div className="border-b border-stone-200 px-3 py-2">
        <div className="flex items-center gap-2">
          <div className="min-w-0 flex-1">
            <div className="text-sm font-semibold">Review draft · ARR form</div>
            <div className="text-[11px] text-stone-500">
              Organized only from your statements. {all.length > 0 && `${accepted}/${all.length} accepted`}
            </div>
          </div>
          <button onClick={generate} disabled={busy} className="shrink-0 rounded-md border border-stone-300 px-2.5 py-1 text-xs hover:bg-stone-100 disabled:opacity-50">
            {busy ? "Organizing…" : view?.draft ? "Regenerate" : "Generate outline"}
          </button>
          <button onClick={() => setShowExport(true)} className="shrink-0 rounded-md bg-stone-900 px-2.5 py-1 text-xs text-white">
            Export
          </button>
        </div>
        {view?.draft && (
          <div className="mt-1.5">
            <RegisterSlider value={view.register} onChange={(r) => setRegister(r)} />
          </div>
        )}
      </div>

      <div className="min-h-0 flex-1 overflow-y-auto px-3 py-3">
        {!view?.draft && (
          <div className="rounded-lg border border-dashed border-stone-300 p-4 text-sm text-stone-600">
            When you are ready, <b>Generate outline</b> turns what you said ({units.length} notes so far) into the ARR form,
            in your own words or more formal prose (your choice, per sentence). Each sentence links back to what you said;
            nothing is added on your behalf.
          </div>
        )}
        {view?.draft?.sections.map((sec) => (
          <section key={sec.field} className="mb-4">
            <h3 className="mb-1 text-xs font-semibold uppercase tracking-wide text-stone-500">{fieldLabel(sec.field)}</h3>
            {sec.sentences.map((st, i) => {
              const warn = st.unsourced || driftWarn(st.drift);
              const eff = st.register ?? view.register;
              return (
                <div
                  key={st.sid}
                  onClick={() => setSelected(st.sid)}
                  className={`group mb-1 cursor-pointer rounded-md border-l-4 px-2 py-1.5 text-[13px] ${
                    st.kind === "opinion" ? "border-indigo-400" : st.kind === "fact" ? "border-amber-400" : "border-stone-200"
                  } ${selected === st.sid ? "bg-stone-100" : "hover:bg-stone-50"}`}
                >
                  {editing?.sid === st.sid ? (
                    <div onClick={(e) => e.stopPropagation()}>
                      <textarea
                        value={editing.text}
                        onChange={(e) => setEditing({ ...editing, text: e.target.value })}
                        className="w-full rounded border border-stone-300 p-1.5 text-[13px]"
                        rows={2}
                      />
                      <div className="mt-1 flex gap-2 text-xs">
                        <button className="rounded bg-stone-900 px-2 py-0.5 text-white" onClick={() => { patch(st, { text: editing.text }); setEditing(null); }}>
                          Save
                        </button>
                        <button onClick={() => setEditing(null)}>Cancel</button>
                      </div>
                    </div>
                  ) : (
                    <span className={STATUS_CLS[st.status]}>
                      {sec.field === "weaknesses" && <span className="mr-1 text-stone-400">{i + 1}.</span>}
                      {st.text}
                    </span>
                  )}
                  <span className="ml-1.5 inline-flex flex-wrap gap-1 align-middle">
                    {st.unit_ids.map((u) => (
                      <span key={u} className={`rounded px-1 font-mono text-[10px] ${u.startsWith("P") ? "bg-amber-50 text-amber-800" : "bg-indigo-50 text-indigo-700"}`}>
                        {u}·T{unitById.get(u)?.turn ?? "?"}
                      </span>
                    ))}
                    {st.block_ids.slice(0, 3).map((b) => (
                      <button
                        key={b}
                        onClick={(e) => { e.stopPropagation(); onCite([b]); }}
                        className="rounded border border-amber-300 bg-amber-50 px-1 font-mono text-[10px] text-amber-800"
                      >
                        p.{byId.get(b)?.boxes[0]?.page ?? "?"}
                      </button>
                    ))}
                    {st.unsourced && <span className="rounded bg-rose-100 px-1 text-[10px] text-rose-700">⚠ no source</span>}
                    {warn && !st.unsourced && <span className="rounded bg-amber-100 px-1 text-[10px] text-amber-800">⚠ wording drift</span>}
                    {!!st.check_conflicts?.length && (
                      <span className="rounded bg-rose-50 px-1 text-[10px] text-rose-700">⚠ checked against paper</span>
                    )}
                    {st.status !== "proposed" && <span className="text-[10px] text-stone-400">{st.status}</span>}
                  </span>
                  <div className="mt-1 hidden gap-2 text-[11px] group-hover:flex">
                    {st.variants && st.status !== "edited" && (
                      <span className="mr-1 flex gap-0.5 text-stone-400" title="Register for this sentence">
                        {(["words", "polished", "formal"] as Register[]).map((r) => (
                          <button key={r} onClick={(e) => { e.stopPropagation(); setRegister(r, st.sid); }}
                            className={`rounded px-1 ${eff === r ? "bg-stone-800 text-white" : "hover:bg-stone-200"}`}>
                            {r === "words" ? "W" : r === "polished" ? "P" : "F"}
                          </button>
                        ))}
                      </span>
                    )}
                    <button className="text-emerald-700 hover:underline" onClick={(e) => { e.stopPropagation(); patch(st, { status: "accepted" }); }}>Accept</button>
                    <button className="text-stone-700 hover:underline" onClick={(e) => { e.stopPropagation(); setEditing({ sid: st.sid, text: st.text }); }}>Edit</button>
                    <button className="text-rose-700 hover:underline" onClick={(e) => { e.stopPropagation(); patch(st, { status: "rejected" }); }}>Reject</button>
                  </div>
                </div>
              );
            })}
          </section>
        ))}

        {view?.draft &&
          view.fields
            .filter((f) => !view.draft!.sections.some((sec) => sec.field === f.key))
            .map((f) => (
              <section key={f.key} className="mb-3">
                <h3 className="mb-1 text-xs font-semibold uppercase tracking-wide text-stone-400">{f.label}</h3>
                <div className="rounded-md border border-dashed border-stone-200 px-2 py-1 text-[12px] italic text-stone-400">
                  Not addressed by you. Nothing is filled in on your behalf; go back to the chat if you want to add something.
                </div>
              </section>
            ))}
        {view?.draft && view.draft.unused_units.length > 0 && (
          <div className="mb-4 rounded-md bg-amber-50 px-3 py-2 text-xs text-amber-900">
            Not yet in the draft: {view.draft.unused_units.map((u) => `${u} “${unitById.get(u)?.statement.slice(0, 50) ?? ""}…”`).join("; ")}
          </div>
        )}

        {view && (
          <section className="mb-4">
            <h3 className="mb-1 text-xs font-semibold uppercase tracking-wide text-stone-500">Scores — set by you</h3>
            <div className="grid grid-cols-2 gap-2">
              {Object.entries(view.score_meta).map(([k, meta]) => (
                <label key={k} className="flex flex-col text-[12px] text-stone-600">
                  {meta.label}
                  {k === "confidence" && view.familiarity && (
                    <span className="text-[10px] text-stone-400">At the start you said: “{view.familiarity}” (a reminder; your call)</span>
                  )}
                  <select
                    value={view.scores[k]?.value ?? ""}
                    onChange={(e) => setScore(k, Number(e.target.value))}
                    className="mt-0.5 rounded border border-stone-300 px-2 py-1 text-[13px] text-stone-900"
                  >
                    <option value="" disabled>— choose —</option>
                    {meta.values.map((v) => (
                      <option key={v} value={v}>{v}</option>
                    ))}
                  </select>
                </label>
              ))}
            </div>
            <p className="mt-1 text-[11px] text-stone-400">The copilot never suggests scores.</p>
          </section>
        )}
      </div>

      {sel && (
        <div className="max-h-[38%] overflow-y-auto border-t border-stone-200 bg-stone-50 px-3 py-2 text-[12px]">
          <div className="mb-1 font-semibold text-stone-600">Provenance</div>
          {sel.unit_ids.map((u) => {
            const unit = unitById.get(u);
            if (unit?.source === "paper_fact")
              return (
                <div key={u} className="mb-1">
                  <span className="font-mono text-[10px] text-amber-800">{u}·T{unit.turn}</span> Paper fact, confirmed by you at T{unit.turn}: “{unit.statement}”
                </div>
              );
            return (
              <div key={u} className="mb-1">
                <span className="font-mono text-[10px] text-indigo-700">{u}·T{unit?.turn}</span> Your words: “{unit?.statement}”
                {unit?.rationale && <span className="text-stone-500"> because “{unit.rationale}”</span>}
              </div>
            );
          })}
          {sel.variants && (
            <div className="mb-1 text-stone-500">
              Showing the <b>{sel.register ?? view?.register}</b> version. Your-words version: “{sel.variants.words}”
            </div>
          )}
          {sel.block_ids.length > 0 && (
            <div className="mb-1">
              Paper:{" "}
              {sel.block_ids.map((b) => (
                <button key={b} onClick={() => onCite([b])} className="mr-1 underline decoration-dotted">
                  {byId.get(b)?.text.slice(0, 80)}… (p.{byId.get(b)?.boxes[0]?.page})
                </button>
              ))}
            </div>
          )}
          {sel.drift && (
            <div className="mb-1">
              Wording check: entailed {sel.drift.entailed ? "✓" : "✗"} · polarity {sel.drift.polarity} · intensity {sel.drift.intensity}
              {sel.drift.note && <span className="text-stone-500"> — {sel.drift.note}</span>}
            </div>
          )}
          {sel.check_conflicts?.map((c, i) => (
            <div key={i} className="text-rose-700">
              In T{c.turn} the paper check on “{c.claim}” returned <b>{c.verdict.replace("_", " ")}</b>. Keep, revise, or reject — your call.
            </div>
          ))}
          {sel.status === "edited" && <div className="text-stone-500">Originally proposed: “{sel.original}”</div>}
        </div>
      )}
      {showExport && <ExportModal sessionId={sessionId} onClose={() => setShowExport(false)} />}
    </div>
  );
}
