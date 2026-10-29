import { useCallback, useEffect, useMemo, useState } from "react";
import { api, type Block, type ChatMessage, type CoverageField, type Facet, type Focus, type Paper, type PaperCtx, type PaperMap, type SessionState } from "../lib/api";
import { ACTIVE_FILL, FACETS, HIDDEN_FILL } from "../lib/facets";
import { PdfPane, type Overlay } from "../pdf/PdfPane";
import { AgendaRail } from "./AgendaRail";
import { BriefPanel } from "./BriefPanel";
import { ChatPanel } from "./ChatPanel";
import { LedgerPanel } from "./LedgerPanel";
import { PaperSetup } from "./PaperSetup";
import { SentenceIndex } from "./SentenceIndex";
import { DraftPanel } from "../review/DraftPanel";

type Tab = "review" | "brief" | "sentences" | "opinions";
const TAB_LABEL: Record<Tab, string> = { review: "Review", brief: "Paper brief", sentences: "Sentences", opinions: "My opinions" };

export function Workspace({ paperId, onBack }: { paperId: string; onBack: () => void }) {
  const [paper, setPaper] = useState<Paper | null>(null);
  const [blocks, setBlocks] = useState<Block[]>([]);
  const [map, setMap] = useState<PaperMap | null>(null);
  const [tab, setTab] = useState<Tab>("review");
  const [mode, setMode] = useState<"dialogue" | "draft">("dialogue");
  const [selTool, setSelTool] = useState<{ x: number; y: number; text: string } | null>(null);
  const [prefill, setPrefill] = useState<{ text: string; nonce: number } | null>(null);
  const onPdfMouseUp = () => {
    const sel = window.getSelection();
    const text = sel?.toString().replace(/\s+/g, " ").trim() ?? "";
    if (!sel || text.length < 4) return setSelTool(null);
    const r = sel.getRangeAt(0).getBoundingClientRect();
    setSelTool({ x: r.left + r.width / 2, y: r.top, text: text.slice(0, 400) });
  };
  const useSelection = (template: (t: string) => string) => {
    if (!selTool) return;
    setPrefill({ text: template(selTool.text), nonce: Date.now() });
    setMode("dialogue");
    setTab("review");
    setSelTool(null);
    window.getSelection()?.removeAllRanges();
  };
  const [sessionId, setSessionId] = useState<string | null>(null);
  const [needsSetup, setNeedsSetup] = useState(false);
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [sstate, setSState] = useState<SessionState | null>(null);
  const [pendingAction, setPendingAction] = useState<{ text: string; action: string; nonce: number } | null>(null);
  const [busy, setBusy] = useState(false);
  const [focus, setFocus] = useState<(Focus & { idx: number }) | null>(null);
  const [enabled, setEnabled] = useState<Record<Facet, boolean>>({ claim: true, method: true, result: true, limitation: true });
  const [active, setActive] = useState<{ key: string; ids: string[] } | null>(null);
  const [jump, setJump] = useState<{ boxes: Block["boxes"]; nonce: number } | null>(null);
  const [showHidden, setShowHidden] = useState(true);

  useEffect(() => {
    api.getPaper(paperId).then(setPaper);
    api.getBlocks(paperId).then(setBlocks);
  }, [paperId]);

  const openSession = async (sid: string) => {
    const sess = await api.getSession(sid);
    setMessages(sess.messages);
    setSState(sess.state);
    setSessionId(sid);
    setNeedsSetup(false);
  };
  const [legacy, setLegacy] = useState<{ id: string; turns: number } | null>(null);
  useEffect(() => {
    (async () => {
      const list = await api.listSessions(paperId);
      const latest = list.find((x) => x.flow === "evidence");
      const old = list.find((x) => x.flow === "commit_first" && x.turn > 0);
      if (old) setLegacy({ id: old.id, turns: old.turn });
      if (latest) await openSession(latest.id);
      else setNeedsSetup(true);
    })();
  }, [paperId]); // eslint-disable-line react-hooks/exhaustive-deps
  const startSession = async (ctx: PaperCtx) => openSession((await api.newSession(paperId, ctx)).id);

  const loadMap = useCallback(() => api.getMap(paperId).then(setMap).catch(() => setMap(null)), [paperId]);
  useEffect(() => {
    loadMap();
  }, [loadMap]);
  useEffect(() => {
    if (map && map.status !== "computing") return;
    const t = setInterval(loadMap, 3000);
    return () => clearInterval(t);
  }, [map, loadMap]);

  const byId = useMemo(() => new Map(blocks.map((b) => [b.id, b])), [blocks]);
  const facetOf = map?.status === "ready" ? map.data.facets : {};

  const counts = useMemo(() => {
    const c: Record<Facet, number> = { claim: 0, method: 0, result: 0, limitation: 0 };
    Object.values(facetOf).forEach((f) => (c[f] += 1));
    return c;
  }, [facetOf]);

  const select = (key: string, ids: string[]) => {
    const boxes = ids.flatMap((id) => byId.get(id)?.boxes ?? []);
    if (!boxes.length) return;
    setActive({ key, ids });
    setJump({ boxes: boxes.filter((b) => b.page === boxes[0].page), nonce: Date.now() });
  };
  // Evidence the copilot presents is highlighted and scrolled to automatically; the navigator steps through it.
  const jumpTo = (id: string) => {
    const boxes = byId.get(id)?.boxes ?? [];
    if (boxes.length) setJump({ boxes: boxes.filter((b) => b.page === boxes[0].page), nonce: Date.now() });
  };
  const showFocus = (f: Focus, idx = 0) => {
    const ids = f.block_ids.filter((id) => byId.has(id));
    if (!ids.length) return;
    setFocus({ ...f, block_ids: ids, idx });
    setActive({ key: `focus-${ids.join(",")}`, ids });
    jumpTo(ids[idx]);
  };
  const step = (d: 1 | -1) => {
    if (!focus) return;
    const idx = (focus.idx + d + focus.block_ids.length) % focus.block_ids.length;
    setFocus({ ...focus, idx });
    jumpTo(focus.block_ids[idx]);
  };

  const overlays: Overlay[] = useMemo(() => {
    const out: Overlay[] = [];
    for (const [id, facet] of Object.entries(facetOf)) {
      if (!enabled[facet]) continue;
      const b = byId.get(id);
      const f = FACETS.find((x) => x.key === facet)!;
      if (b) out.push({ id, boxes: b.boxes, color: f.fill, title: `${f.label} · ${id}` });
    }
    if (showHidden) {
      (paper?.hidden_text ?? []).forEach((h, i) =>
        out.push({ id: `hidden-${i}`, boxes: [h.box], color: HIDDEN_FILL, title: `Hidden text (${h.reasons.join(", ")})` }),
      );
    }
    for (const id of active?.ids ?? []) {
      const b = byId.get(id);
      if (b) out.push({ id: `active-${id}`, boxes: b.boxes, color: ACTIVE_FILL, active: true, title: id });
    }
    return out;
  }, [facetOf, enabled, byId, active, paper, showHidden]);

  const hidden = paper?.hidden_text ?? [];

  return (
    <div className="flex h-full flex-col">
      <header className="flex items-center gap-3 border-b border-stone-200 bg-white px-4 py-2">
        <button onClick={onBack} className="rounded-md px-2 py-1 text-sm text-stone-600 hover:bg-stone-100">
          ← Papers
        </button>
        <div className="min-w-0 flex-1 truncate text-sm font-medium">{paper?.title ?? "…"}</div>
        <span className="text-xs text-stone-500">
          {blocks.length} blocks · {paper?.parser}
        </span>
        {sessionId && (
          <button onClick={() => setNeedsSetup(true)} className="text-xs text-stone-500 hover:underline" title="Start a new review session for this paper">
            New session
          </button>
        )}
        <div className="ml-2 flex rounded-lg border border-stone-300 p-0.5 text-xs">
          {(["dialogue", "draft"] as const).map((m) => (
            <button
              key={m}
              onClick={() => setMode(m)}
              className={`rounded-md px-3 py-1 ${mode === m ? "bg-stone-900 text-white" : "text-stone-600"}`}
            >
              {m === "dialogue" ? "Dialogue" : "Review draft"}
            </button>
          ))}
        </div>
      </header>

      <div className="flex min-h-0 flex-1">
        <section className="flex min-w-0 flex-[55] flex-col">
          <div className="flex flex-wrap items-center gap-1.5 border-b border-stone-200 bg-white px-3 py-1.5 text-xs">
            <span className="mr-1 text-stone-500">Highlights:</span>
            {FACETS.map((f) => (
              <button
                key={f.key}
                onClick={() => setEnabled((e) => ({ ...e, [f.key]: !e[f.key] }))}
                className={`flex items-center gap-1.5 rounded-full border px-2 py-0.5 transition ${
                  enabled[f.key] ? "border-stone-300 bg-white" : "border-transparent bg-stone-100 text-stone-400"
                }`}
              >
                <span className={`h-2 w-2 rounded-full ${enabled[f.key] ? f.dot : "bg-stone-300"}`} />
                {f.label} <span className="text-stone-400">{counts[f.key]}</span>
              </button>
            ))}
            {hidden.length > 0 && (
              <button
                onClick={() => setShowHidden((v) => !v)}
                className="ml-auto rounded-full border border-purple-300 bg-purple-50 px-2 py-0.5 text-purple-700"
              >
                ⚠ Hidden text {hidden.length}
              </button>
            )}
          </div>
          <div className="relative min-h-0 flex-1" onMouseUp={onPdfMouseUp}>
            {selTool && (
              <div
                className="fixed z-40 flex -translate-x-1/2 -translate-y-full gap-1 rounded-lg border border-stone-300 bg-white p-1 text-xs shadow-lg"
                style={{ left: selTool.x, top: selTool.y - 6 }}
                onMouseUp={(e) => e.stopPropagation()}
              >
                <button className="rounded px-2 py-1 hover:bg-stone-100" onClick={() => useSelection((t) => `What does the paper say about “${t}”? `)}>
                  Ask about this
                </button>
                <button className="rounded px-2 py-1 hover:bg-stone-100" onClick={() => useSelection((t) => `On “${t}”: `)}>
                  Comment on this
                </button>
                <button className="rounded px-2 py-1 text-stone-400 hover:bg-stone-100" onClick={() => setSelTool(null)}>
                  ✕
                </button>
              </div>
            )}
            {focus && active?.key.startsWith("focus-") && (
              <div className="absolute left-1/2 top-2 z-30 flex max-w-[90%] -translate-x-1/2 items-center gap-2 rounded-full border border-amber-300 bg-white/95 px-3 py-1 text-xs shadow">
                <span className="truncate font-medium text-amber-900">◎ {focus.title || "From the paper"}</span>
                {focus.block_ids.length > 1 && (
                  <span className="flex shrink-0 items-center gap-1 text-stone-600">
                    <button onClick={() => step(-1)} className="px-1 hover:text-stone-900">‹</button>
                    {focus.idx + 1}/{focus.block_ids.length}
                    <button onClick={() => step(1)} className="px-1 hover:text-stone-900">›</button>
                  </span>
                )}
                <span className="shrink-0 text-stone-500">~{focus.read_min} min</span>
                <button onClick={() => { setFocus(null); setActive(null); }} className="shrink-0 text-stone-400 hover:text-stone-700">✕</button>
              </div>
            )}
            <PdfPane
              url={api.pdfUrl(paperId)}
              overlays={overlays}
              jumpTo={jump}
              onOverlayClick={(id) => !id.startsWith("hidden") && select(id.replace("active-", ""), [id.replace("active-", "")])}
            />
          </div>
        </section>

        {needsSetup ? (
          <aside className="flex min-w-0 flex-[45] flex-col border-l border-stone-200 bg-stone-50">
            <PaperSetup
              onStart={startSession}
              legacy={legacy ? { turns: legacy.turns, open: () => openSession(legacy.id) } : undefined}
            />
          </aside>
        ) : mode === "draft" && sessionId ? (
          <aside className="flex min-w-0 flex-[45] flex-col border-l border-stone-200 bg-white">
            <DraftPanel
              sessionId={sessionId}
              units={sstate?.units ?? []}
              byId={byId}
              onCite={(ids) => select(`cite-${ids.join(",")}`, ids)}
            />
          </aside>
        ) : (
        <aside className="flex min-w-0 flex-[45] flex-col border-l border-stone-200 bg-white">
          {hidden.length > 0 && (
            <div className="border-b border-purple-200 bg-purple-50 px-4 py-2 text-xs text-purple-900">
              <b>Hidden text detected</b> ({hidden.length}): text that is invisible to readers but readable by an AI,
              e.g. “{hidden[0].text.slice(0, 90)}{hidden[0].text.length > 90 ? "…" : ""}”. It is excluded from the
              copilot’s view of the paper.
            </div>
          )}
          <nav className="flex gap-1 border-b border-stone-200 px-3 pt-2">
            {(["review", "brief", "sentences", "opinions"] as Tab[]).map((t) => (
              <button
                key={t}
                onClick={() => setTab(t)}
                className={`rounded-t-md px-3 py-1.5 text-sm ${
                  tab === t ? "border border-b-white border-stone-200 bg-white font-medium" : "text-stone-500"
                }`}
              >
                {TAB_LABEL[t]}
                {t === "opinions" && sstate?.units.length ? ` (${sstate.units.length})` : ""}
              </button>
            ))}
          </nav>
          {tab === "review" && sstate?.agenda && (
            <AgendaRail
              state={sstate}
              busy={busy}
              onGo={(id) => {
                const c = sstate.agenda.cards.find((x) => x.id === id);
                setPendingAction({ text: `Let's look at: ${c?.title ?? id}`, action: `card:${id}`, nonce: Date.now() });
              }}
              onDone={() => setPendingAction({ text: "Done with this", action: "done", nonce: Date.now() })}
              onRail={(id, op) => sessionId && api.rail(sessionId, id, op).then(setSState).catch(() => {})}
              onDraft={() => setMode("draft")}
              onOpinions={() => setTab("opinions")}
            />
          )}
          <div className={`min-h-0 flex-1 ${tab === "review" ? "" : "overflow-y-auto"}`}>
            {tab === "review" ? (
              sessionId ? (
                <ChatPanel
                  key={sessionId}
                  sessionId={sessionId}
                  messages={messages}
                  setMessages={setMessages}
                  state={sstate}
                  setState={setSState}
                  byId={byId}
                  glossary={sstate?.agenda?.glossary ?? []}
                  onCite={(ids) => select(`cite-${ids.join(",")}`, ids)}
                  onFocus={(f) => showFocus(f)}
                  onOpenDraft={() => setMode("draft")}
                  onBusy={setBusy}
                  pendingAction={pendingAction}
                  prefill={prefill}
                />
              ) : (
                <div className="p-4 text-sm text-stone-500">Starting session…</div>
              )
            ) : tab === "opinions" ? (
              <LedgerPanel
                units={sstate?.units ?? []}
                // sessions from the previous version have "dims" instead of a coverage map
                fields={sstate?.coverage?.fields ?? ((sstate as unknown as { dims?: CoverageField[] })?.dims ?? [])}
                sessionId={sessionId}
                byId={byId}
                onCite={(ids) => select(`cite-${ids.join(",")}`, ids)}
                onChanged={() => sessionId && api.getSession(sessionId).then((x) => setSState(x.state))}
              />
            ) : tab === "brief" ? (
              <BriefPanel
                map={map}
                activeKey={active?.key ?? null}
                onSelect={select}
                onRebuild={() => api.rebuildMap(paperId).then(loadMap)}
              />
            ) : (
              <SentenceIndex blocks={blocks} activeIds={new Set(active?.ids ?? [])} onSelect={(id) => select(id, [id])} />
            )}
          </div>
        </aside>
        )}
      </div>
    </div>
  );
}
