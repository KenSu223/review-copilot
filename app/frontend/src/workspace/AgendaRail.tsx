import { useState } from "react";
import type { Card, SessionState } from "../lib/api";

const ICON: Record<Card["status"], string> = { pending: "○", active: "◉", done: "●", skipped: "⊘", reserve: "○" };
const COV: Record<string, string> = { covered: "bg-emerald-500", partial: "bg-amber-400", missing: "bg-stone-200", skipped: "bg-stone-300" };

type Props = {
  state: SessionState;
  busy: boolean;
  onGo: (cardId: string) => void;
  onDone: () => void;
  onRail: (cardId: string, op: "up" | "down" | "skip" | "restore") => void;
  onDraft: () => void;
  onOpinions: () => void;
};

/** Upcoming topics (the reviewer can reorder, skip, or jump), a small review-coverage meter, and progress. */
export function AgendaRail({ state, busy, onGo, onDone, onRail, onDraft, onOpinions }: Props) {
  const [open, setOpen] = useState(false);
  const [showReserve, setShowReserve] = useState(false);
  const { agenda, coverage, progress } = state;
  const main = agenda.cards.filter((c) => c.status !== "reserve");
  const reserve = agenda.cards.filter((c) => c.status === "reserve");
  const current = agenda.cards.find((c) => c.id === agenda.current);
  const row = (c: Card) => (
    <li key={c.id} className={`group flex items-center gap-2 rounded px-1.5 py-1 ${c.id === agenda.current ? "bg-amber-50" : "hover:bg-stone-50"}`}>
      <span className={c.status === "done" ? "text-emerald-600" : c.status === "active" ? "text-amber-600" : "text-stone-400"}>{ICON[c.status]}</span>
      <span className={`min-w-0 flex-1 truncate ${c.status === "skipped" ? "text-stone-400 line-through" : ""}`} title={c.why}>
        {c.title}
      </span>
      {c.criterion_label && <span className="hidden rounded bg-stone-100 px-1.5 text-[10px] text-stone-500 sm:inline">{c.criterion_label}</span>}
      <span className="text-[10px] text-stone-400">~{c.read_min} min</span>
      <span className={`flex gap-1 text-[10px] text-stone-500 ${busy ? "invisible" : "invisible group-hover:visible"}`}>
        {c.id !== agenda.current && c.status !== "skipped" && (
          <button title="Talk about this now" onClick={() => onGo(c.id)} className="hover:text-stone-900">go</button>
        )}
        {c.id === agenda.current && (
          <button title="I'm done with this topic" onClick={onDone} className="hover:text-stone-900">done</button>
        )}
        {(c.status === "pending" || c.status === "reserve") && (
          <>
            <button onClick={() => onRail(c.id, "up")}>↑</button>
            <button onClick={() => onRail(c.id, "down")}>↓</button>
            <button onClick={() => onRail(c.id, "skip")}>skip</button>
          </>
        )}
        {(c.status === "skipped" || c.status === "done") && <button onClick={() => onRail(c.id, "restore")}>restore</button>}
      </span>
    </li>
  );
  return (
    <div className="border-b border-stone-200 bg-white px-3 py-2 text-xs">
      <div className="flex items-center gap-2">
        <button onClick={() => setOpen((v) => !v)} className="flex min-w-0 flex-1 items-center gap-1.5 text-left" title="Show all topics">
          <span className="text-stone-400">{open ? "▾" : "▸"}</span>
          <span className="truncate">
            {agenda.status === "planning" ? (
              <span className="text-stone-500">Planning topics from your preferences…</span>
            ) : current ? (
              <>Now: <b className="font-medium">{current.title}</b></>
            ) : (
              <span className="text-stone-500">Topics</span>
            )}
          </span>
        </button>
        <button
          onClick={onDraft}
          className={`shrink-0 rounded-md px-2 py-1 ${coverage.ready || state.finished ? "bg-stone-900 text-white" : "border border-stone-300 text-stone-700"}`}
        >
          Ready to draft
        </button>
      </div>
      <div className="mt-1 flex items-center gap-3 pl-4 text-[11px] text-stone-500">
        <span className="shrink-0">{progress.cards_left} topics left · ~{progress.minutes_left} min</span>
        <span className="flex shrink-0 items-center gap-0.5" title="Review coverage (ARR form fields)">
          {coverage.fields.map((f) => (
            <span key={f.key} title={`${f.label} (${f.status}): ${f.help ?? ""}`} className={`h-2 w-2 rounded-full ${COV[f.status]}`} />
          ))}
        </span>
        <button onClick={onOpinions} className="ml-auto shrink-0 hover:underline">
          Your review so far: {coverage.n_units} point{coverage.n_units === 1 ? "" : "s"}
        </button>
      </div>
      {open && (
        <div className="mt-2">
          <ul className="space-y-0.5">{main.map(row)}</ul>
          {reserve.length > 0 && (
            <div className="mt-1.5">
              <button className="text-[11px] text-stone-500 hover:underline" onClick={() => setShowReserve((v) => !v)}>
                {showReserve ? "▾" : "▸"} More topics, used to fill gaps in your review ({reserve.length})
              </button>
              {showReserve && <ul className="mt-0.5 space-y-0.5">{reserve.map(row)}</ul>}
            </div>
          )}
          <div className="mt-2 flex flex-wrap gap-x-3 gap-y-0.5 text-[10px] text-stone-500">
            <span>Review coverage:</span>
            {coverage.fields.map((f) => (
              <span key={f.key} className="flex cursor-help items-center gap-1" title={`The review form asks for ${f.help ?? ""}`}>
                <span className={`h-1.5 w-1.5 rounded-full ${COV[f.status]}`} />
                {f.label}
              </span>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
