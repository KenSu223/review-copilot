import { useEffect, useRef, useState } from "react";
import {
  api,
  type Block,
  type ChatMessage,
  type Check,
  type Chip,
  type CopilotMessage,
  type Fact,
  type Focus,
  type GlossaryTerm,
  type OpinionUnit,
  reviewApi,
  type SessionState,
  streamTurn,
} from "../lib/api";
import { CitedText } from "./CitedText";

const VERDICT: Record<Check["verdict"], { label: string; cls: string }> = {
  supported: { label: "Supported", cls: "bg-emerald-100 text-emerald-800" },
  partly_supported: { label: "Partly supported", cls: "bg-amber-100 text-amber-800" },
  contradicted: { label: "Contradicted by the paper", cls: "bg-rose-100 text-rose-800" },
  not_located: { label: "Not located in the paper", cls: "bg-stone-200 text-stone-700" },
};
const ACTION_LABEL: Record<string, string> = {
  present_card: "from the paper",
  present_more: "more from the paper",
  follow_up: "follow-up",
  answer_fact: "fact answer",
  report_check: "statement check",
  decline_redirect: "your call",
  reconcile: "your two notes",
  support_unsure: "no rush",
  offer_wrap: "move on?",
  bridge: "another part of the review",
  summary_check: "summary",
  ask_preference: "your standard",
  offer_draft: "draft",
  ask_first_impression: "first impression",
  ask_dump: "your notes",
  redirect: "back to the paper",
};
// Plain names in the chat; ARR names appear only in the draft.
const FIELD_LABEL: Record<string, string> = {
  summary: "what it does", soundness: "claims backed up?", strengths: "what worked", weaknesses: "what didn't",
  excitement: "interest", reproducibility: "reproducibility", limitations_ethics: "limitations", overall: "overall take",
};
const CRIT_LABEL: Record<string, string> = {
  clarity: "Clarity", rigor: "Experiments", novelty: "Novelty", usefulness: "Usefulness", theory: "Theory",
  analysis: "Analysis", reproducibility: "Reproducibility", limitations: "Limitations",
};
const POL: Record<string, string> = { positive: "+", negative: "−", mixed: "±", neutral: "" };
const STARTED = new Set<string>();

type Props = {
  sessionId: string;
  messages: ChatMessage[];
  setMessages: (fn: (m: ChatMessage[]) => ChatMessage[]) => void;
  state: SessionState | null;
  setState: (s: SessionState) => void;
  byId: Map<string, Block>;
  glossary: GlossaryTerm[];
  onCite: (ids: string[]) => void;
  onFocus: (f: Focus) => void;
  onOpenDraft: () => void;
  onBusy: (b: boolean) => void;
  pendingAction: { text: string; action: string; nonce: number } | null;
  prefill?: { text: string; nonce: number } | null;
};

export function ChatPanel(props: Props) {
  const { sessionId, messages, setMessages, state, setState, byId, glossary, onCite, onFocus, onOpenDraft, pendingAction, prefill } = props;
  const [input, setInput] = useState("");
  const [status, setStatus] = useState<string | null>(null);
  const [error, setError] = useState("");
  const bottomRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLTextAreaElement>(null);
  const busy = status !== null;
  useEffect(() => props.onBusy(busy), [busy]); // eslint-disable-line react-hooks/exhaustive-deps
  useEffect(() => {
    if (!prefill) return;
    setInput(prefill.text);
    setTimeout(() => inputRef.current?.focus(), 50);
  }, [prefill?.nonce]); // eslint-disable-line react-hooks/exhaustive-deps
  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, status]);

  const units = new Map((state?.units ?? []).map((u) => [u.id, u]));
  const refresh = () => api.getSession(sessionId).then((x) => setState(x.state));

  const send = async (text: string, action = "") => {
    if (busy) return;
    setError("");
    if (text) setMessages((m) => [...m, { role: "reviewer", turn: 0, text, action }]);
    setStatus("…");
    try {
      await streamTurn(sessionId, { text, action }, (ev) => {
        if (ev.type === "status") setStatus(ev.label);
        else if (ev.type === "message") {
          setMessages((m) => [...m, { ...ev.message, role: "copilot", turn: ev.turn }]);
          setState(ev.state);
          if (ev.message.focus?.block_ids.length) onFocus(ev.message.focus);
        } else setError(ev.message);
      });
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e));
    } finally {
      setStatus(null);
    }
  };

  useEffect(() => {
    if (messages.length === 0 && !busy && !STARTED.has(sessionId)) {
      STARTED.add(sessionId); // effects can run twice (React StrictMode); start a session only once
      send("", "start");
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [sessionId]);
  useEffect(() => {
    if (pendingAction) send(pendingAction.text, pendingAction.action);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [pendingAction?.nonce]);

  const lastCopilot = [...messages].reverse().find((m) => m.role === "copilot") as CopilotMessage | undefined;
  const chips: Chip[] = (lastCopilot?.chips ?? []).map((c) => (typeof c === "string" ? { label: c, action: "" } : c));
  const lastAction = lastCopilot?.action ?? lastCopilot?.move;
  const placeholder =
    lastAction === "ask_dump"
      ? "Rough notes are fine: what you liked, what bugged you, anything you want to check…"
      : lastAction === "ask_first_impression"
        ? "One line is fine…"
        : "Say what you think, casual is fine. Or ask about the paper…";

  return (
    <div className="flex h-full flex-col">
      <div className="min-h-0 flex-1 space-y-3 overflow-y-auto px-3 py-3">
        {messages.map((m, i) => {
          if (m.role === "reviewer")
            return (
              <div key={i} className="flex justify-end">
                <div className="max-w-[85%] rounded-2xl rounded-br-sm bg-stone-800 px-3 py-2 text-[13px] leading-relaxed text-white">{m.text}</div>
              </div>
            );
          const action = m.action ?? m.move;
          return (
            <div key={i} className="max-w-[94%]">
              {m.new_units?.length > 0 && (
                <div className="mb-2 ml-auto flex max-w-[90%] flex-col items-end gap-1">
                  {m.new_units.map((id) => (
                    <UnitPill key={id} id={id} unit={units.get(id)} sessionId={sessionId} onChanged={refresh} />
                  ))}
                </div>
              )}
              <div className="mb-1 flex items-center gap-2 text-[10px] uppercase tracking-wide text-stone-400">
                <span>Copilot · {ACTION_LABEL[action] ?? action}{m.fallback && " · safe fallback"}</span>
              </div>
              {m.focus && (
                <button
                  onClick={() => onFocus(m.focus!)}
                  className="mb-1 flex max-w-full items-center gap-1.5 truncate rounded-md bg-amber-50 px-2 py-1 text-left text-[11px] text-amber-900 hover:bg-amber-100"
                  title="Show these passages in the PDF"
                >
                  <span>◎ {m.focus.title}</span>
                  {m.focus.why && <span className="truncate text-amber-700">· {m.focus.why}</span>}
                  <span className="shrink-0 text-amber-700">· {m.focus.block_ids.length} passage{m.focus.block_ids.length === 1 ? "" : "s"}, ~{m.focus.read_min} min read</span>
                </button>
              )}
              {m.field_help && (
                <div className="mb-1 rounded-md bg-sky-50 px-2 py-1 text-[11px] text-sky-900">
                  <b>Review form · {m.field_help.label}:</b> {m.field_help.text}. <span className="text-sky-700">({m.field_help.source})</span>
                </div>
              )}
              {m.checks?.map((c, j) => (
                <div key={j} className="mb-2 rounded-lg border border-stone-200 bg-stone-50 px-3 py-2 text-[12.5px]">
                  <div className="mb-1 flex items-center gap-2">
                    <span className={`rounded px-1.5 py-0.5 text-[10px] font-semibold ${VERDICT[c.verdict].cls}`}>{VERDICT[c.verdict].label}</span>
                    <span className="truncate italic text-stone-600">“{c.claim}”</span>
                  </div>
                  <CitedText segments={c.segments} byId={byId} onCite={onCite} />
                  <div className="mt-1.5 flex gap-3 text-[11px]">
                    <button className="text-stone-500 hover:text-stone-800" onClick={() => setInput(c.claim)}>Revise my statement</button>
                    {c.segments.some((x) => x.cites.length) &&
                      ((state?.units ?? []).some((u) => u.fact_id === `K${m.turn}-${j}`) ? (
                        <span className="text-emerald-700">evidence in your review</span>
                      ) : (
                        <button className="text-stone-500 hover:text-stone-800" onClick={() => api.confirmCheck(sessionId, m.turn, j).then(setState)}>
                          Use this evidence in my review
                        </button>
                      ))}
                  </div>
                </div>
              ))}
              <div className="rounded-2xl rounded-tl-sm border border-stone-200 bg-white px-3 py-2 text-[13px] leading-relaxed">
                <CitedText segments={m.segments} byId={byId} onCite={onCite} glossary={glossary} />
              </div>
              {m.facts && m.facts.length > 0 && (
                <FactsChecklist facts={m.facts} confirmed={new Set((state?.agenda?.contributions ?? []).filter((f) => f.confirmed).map((f) => f.id))}
                  byId={byId} onCite={onCite} onConfirm={(ids) => api.confirmFacts(sessionId, ids).then(setState)} />
              )}
              {m.remember && <RememberPill sessionId={sessionId} {...m.remember} onDone={setState} />}
            </div>
          );
        })}
        {status && (
          <div className="flex items-center gap-2 text-xs text-stone-500">
            <span className="h-2 w-2 animate-ping rounded-full bg-amber-500" /> {status}
          </div>
        )}
        {error && <div className="text-xs text-rose-600">{error}</div>}
        <div ref={bottomRef} />
      </div>

      {chips.length > 0 && !busy && (
        <div className="flex flex-wrap gap-1.5 border-t border-stone-100 px-3 pt-2">
          {chips.map((c) => (
            <button
              key={c.label}
              onClick={() => (c.action === "open_draft" ? onOpenDraft() : send(c.label, c.action))}
              className="rounded-full border border-stone-300 bg-white px-2.5 py-1 text-xs text-stone-700 hover:bg-stone-100"
            >
              {c.label}
            </button>
          ))}
        </div>
      )}
      <form
        className="flex gap-2 px-3 py-2"
        onSubmit={(e) => {
          e.preventDefault();
          const t = input.trim();
          if (t) {
            setInput("");
            send(t);
          }
        }}
      >
        <textarea
          ref={inputRef}
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={(e) => {
            if (e.key === "Enter" && !e.shiftKey) {
              e.preventDefault();
              (e.currentTarget.form as HTMLFormElement).requestSubmit();
            }
          }}
          rows={lastAction === "ask_dump" ? 6 : 2}
          placeholder={placeholder}
          className="flex-1 resize-none rounded-lg border border-stone-300 px-3 py-2 text-[13px] outline-none focus:border-stone-500"
        />
        <button disabled={busy} className="self-end rounded-lg bg-stone-900 px-4 py-2 text-sm text-white disabled:opacity-40">
          Send
        </button>
      </form>
    </div>
  );
}

/** "Can I quote you on that?": what was just noted from the reviewer's message, with one-click edit or undo. */
function UnitPill({ id, unit, sessionId, onChanged }: { id: string; unit?: OpinionUnit; sessionId: string; onChanged: () => void }) {
  const [edit, setEdit] = useState<string | null>(null);
  if (!unit) return <div className="rounded-full bg-stone-100 px-2.5 py-1 text-[11px] text-stone-400 line-through">{id} not recorded</div>;
  const tag = unit.criterion ? CRIT_LABEL[unit.criterion] ?? unit.criterion : FIELD_LABEL[unit.dimension] ?? unit.dimension;
  const save = async () => {
    if (edit !== null && edit.trim()) await reviewApi.patchUnit(sessionId, id, { statement: edit.trim() });
    setEdit(null);
    onChanged();
  };
  return (
    <div className="flex max-w-full items-center gap-1.5 rounded-full border border-indigo-200 bg-indigo-50 px-2.5 py-1 text-[11px] text-indigo-900">
      <span className="shrink-0 text-indigo-500">Noted</span>
      {edit === null ? (
        <span className="truncate">“{unit.statement}”</span>
      ) : (
        <input autoFocus value={edit} onChange={(e) => setEdit(e.target.value)} onKeyDown={(e) => e.key === "Enter" && save()}
          className="min-w-0 flex-1 rounded border border-indigo-200 bg-white px-1" />
      )}
      <span className="shrink-0 text-indigo-500">→ {tag} {POL[unit.polarity]}</span>
      {edit === null ? (
        <>
          <button className="shrink-0 underline" onClick={() => setEdit(unit.statement)}>Edit</button>
          <button className="shrink-0 underline" onClick={() => reviewApi.patchUnit(sessionId, id, { deleted: true }).then(onChanged)}>Don't record</button>
        </>
      ) : (
        <button className="shrink-0 underline" onClick={save}>Save</button>
      )}
    </div>
  );
}

function FactsChecklist({ facts, confirmed, byId, onCite, onConfirm }: {
  facts: Fact[]; confirmed: Set<string>; byId: Map<string, Block>; onCite: (ids: string[]) => void; onConfirm: (ids: string[]) => void;
}) {
  const [picked, setPicked] = useState<Set<string>>(new Set());
  const open = facts.filter((f) => !confirmed.has(f.id));
  return (
    <div className="mt-1.5 rounded-lg border border-amber-200 bg-amber-50/60 px-3 py-2 text-[12px]">
      <div className="mb-1 text-[11px] text-stone-600">What the paper says it contributes. Tick any you want in your summary, as the paper's own statements:</div>
      {facts.map((f) => (
        <label key={f.id} className="flex items-start gap-2 py-0.5">
          <input type="checkbox" disabled={confirmed.has(f.id)} checked={confirmed.has(f.id) || picked.has(f.id)}
            onChange={() => setPicked((s) => { const n = new Set(s); if (n.has(f.id)) n.delete(f.id); else n.add(f.id); return n; })} />
          <span className="flex-1">{f.text}{" "}
            <button onClick={() => onCite(f.block_ids)} className="rounded border border-amber-300 bg-white px-1 font-mono text-[10px] text-amber-800">
              p.{byId.get(f.block_ids[0])?.boxes[0]?.page ?? "?"}
            </button>
            {confirmed.has(f.id) && <span className="ml-1 text-[10px] text-emerald-700">in your summary</span>}
          </span>
        </label>
      ))}
      {open.length > 0 && (
        <button disabled={picked.size === 0} onClick={() => { onConfirm([...picked]); setPicked(new Set()); }}
          className="mt-1 rounded-md bg-stone-900 px-2 py-0.5 text-[11px] text-white disabled:opacity-40">
          Use selected in my summary
        </button>
      )}
    </div>
  );
}

function RememberPill({ sessionId, criterion, label, onDone }: { sessionId: string; criterion: string; label: string; onDone: (s: SessionState) => void }) {
  const [answered, setAnswered] = useState<boolean | null>(null);
  if (answered !== null)
    return <div className="mt-1.5 text-[11px] text-stone-500">{answered ? `Remembered “${label}” in your profile.` : "Okay, not remembered."}</div>;
  const answer = (accept: boolean) => api.remember(sessionId, criterion, accept).then((s) => { setAnswered(accept); onDone(s); });
  return (
    <div className="mt-1.5 flex items-center gap-2 rounded-md bg-stone-100 px-2 py-1 text-[11px] text-stone-700">
      <span>You've commented on “{label}” a few times. Remember it as something you look at?</span>
      <button className="underline" onClick={() => answer(true)}>Yes</button>
      <button className="underline" onClick={() => answer(false)}>No</button>
    </div>
  );
}
