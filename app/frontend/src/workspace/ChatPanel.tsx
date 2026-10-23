import { useEffect, useRef, useState } from "react";
import { type Block, type ChatMessage, type Check, type CopilotMessage, type SessionState, streamTurn } from "../lib/api";
import { CitedText } from "./CitedText";

const VERDICT: Record<Check["verdict"], { label: string; cls: string }> = {
  supported: { label: "Supported", cls: "bg-emerald-100 text-emerald-800" },
  partly_supported: { label: "Partly supported", cls: "bg-amber-100 text-amber-800" },
  contradicted: { label: "Contradicted by the paper", cls: "bg-rose-100 text-rose-800" },
  not_located: { label: "Not located in the paper", cls: "bg-stone-200 text-stone-700" },
};
const CHIP_ACTION: Record<string, string> = {
  "Next dimension": "next",
  "Skip this dimension": "skip",
  "That's accurate": "confirm",
  "Go deeper": "deeper",
};
const MOVE_LABEL: Record<string, string> = {
  commit_open: "your view first",
  probe_evidence: "grounding",
  surface_facts: "facts from the paper",
  answer_fact: "fact answer",
  refuse_redirect: "your judgment",
  after_check: "statement check",
  unsure: "uncertainty",
  reconcile: "reconcile",
  perspective: "perspective",
  confirm: "confirm record",
  redirect: "back on track",
  close_all: "wrap-up",
};

type Props = {
  sessionId: string;
  messages: ChatMessage[];
  setMessages: (fn: (m: ChatMessage[]) => ChatMessage[]) => void;
  setState: (s: SessionState) => void;
  byId: Map<string, Block>;
  onCite: (ids: string[]) => void;
  onOpenDraft: () => void;
  pendingAction: { action: string; nonce: number } | null;
  prefill?: { text: string; nonce: number } | null;
};

export function ChatPanel({ sessionId, messages, setMessages, setState, byId, onCite, onOpenDraft, pendingAction, prefill }: Props) {
  const [input, setInput] = useState("");
  const [status, setStatus] = useState<string | null>(null);
  const [error, setError] = useState("");
  const bottomRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLTextAreaElement>(null);
  useEffect(() => {
    if (!prefill) return;
    setInput(prefill.text);
    setTimeout(() => inputRef.current?.focus(), 50);
  }, [prefill?.nonce]); // eslint-disable-line react-hooks/exhaustive-deps
  const busy = status !== null;

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, status]);

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
        } else setError(ev.message);
      });
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e));
    } finally {
      setStatus(null);
    }
  };

  // Start the dialogue on a fresh session; run rail "goto" actions.
  useEffect(() => {
    if (messages.length === 0 && !busy) send("", "start");
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [sessionId]);
  useEffect(() => {
    if (pendingAction) send("", pendingAction.action);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [pendingAction?.nonce]);

  const lastCopilot = [...messages].reverse().find((m) => m.role === "copilot") as CopilotMessage | undefined;

  return (
    <div className="flex h-full flex-col">
      <div className="min-h-0 flex-1 space-y-3 overflow-y-auto px-3 py-3">
        {messages.map((m, i) =>
          m.role === "reviewer" ? (
            <div key={i} className="flex justify-end">
              <div className="max-w-[85%] rounded-2xl rounded-br-sm bg-stone-800 px-3 py-2 text-[13px] leading-relaxed text-white">
                {m.text}
              </div>
            </div>
          ) : (
            <div key={i} className="max-w-[92%]">
              <div className="mb-1 text-[10px] uppercase tracking-wide text-stone-400">
                Copilot · {m.dimension} · {MOVE_LABEL[m.move] ?? m.move}
                {m.fallback && " · safe fallback"}
              </div>
              {m.checks?.map((c, j) => (
                <div key={j} className="mb-2 rounded-lg border border-stone-200 bg-stone-50 px-3 py-2 text-[12.5px]">
                  <div className="mb-1 flex items-center gap-2">
                    <span className={`rounded px-1.5 py-0.5 text-[10px] font-semibold ${VERDICT[c.verdict].cls}`}>
                      {VERDICT[c.verdict].label}
                    </span>
                    <span className="truncate italic text-stone-600">“{c.claim}”</span>
                  </div>
                  <CitedText segments={c.segments} byId={byId} onCite={onCite} />
                  <div className="mt-1.5 flex gap-2 text-[11px]">
                    <button className="text-stone-500 hover:text-stone-800" onClick={() => setInput(c.claim)}>
                      Revise my statement
                    </button>
                  </div>
                </div>
              ))}
              <div className="rounded-2xl rounded-tl-sm border border-stone-200 bg-white px-3 py-2 text-[13px] leading-relaxed">
                <CitedText segments={m.segments} byId={byId} onCite={onCite} />
              </div>
            </div>
          ),
        )}
        {status && (
          <div className="flex items-center gap-2 text-xs text-stone-500">
            <span className="h-2 w-2 animate-ping rounded-full bg-amber-500" /> {status}
          </div>
        )}
        {error && <div className="text-xs text-rose-600">{error}</div>}
        <div ref={bottomRef} />
      </div>

      {lastCopilot && lastCopilot.chips.length > 0 && !busy && (
        <div className="flex flex-wrap gap-1.5 border-t border-stone-100 px-3 pt-2">
          {lastCopilot.chips.map((c) => (
            <button
              key={c}
              onClick={() => (c === "Open review draft" ? onOpenDraft() : send(c, CHIP_ACTION[c] ?? ""))}
              className="rounded-full border border-stone-300 bg-white px-2.5 py-1 text-xs text-stone-700 hover:bg-stone-100"
            >
              {c}
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
          rows={2}
          placeholder="Your view, a question about the paper, or a statement to check…"
          className="flex-1 resize-none rounded-lg border border-stone-300 px-3 py-2 text-[13px] outline-none focus:border-stone-500"
        />
        <button disabled={busy} className="self-end rounded-lg bg-stone-900 px-4 py-2 text-sm text-white disabled:opacity-40">
          Send
        </button>
      </form>
    </div>
  );
}
