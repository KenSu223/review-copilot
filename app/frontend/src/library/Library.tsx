import { useCallback, useEffect, useState } from "react";
import { api, type Paper } from "../lib/api";

export function Library({ onOpen }: { onOpen: (id: string) => void }) {
  const [papers, setPapers] = useState<Paper[]>([]);
  const [arxiv, setArxiv] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [dragging, setDragging] = useState(false);

  const refresh = useCallback(() => api.listPapers().then(setPapers).catch((e) => setError(String(e))), []);
  useEffect(() => {
    refresh();
  }, [refresh]);
  useEffect(() => {
    if (!papers.some((p) => p.status === "parsing")) return;
    const t = setInterval(refresh, 2000);
    return () => clearInterval(t);
  }, [papers, refresh]);

  const run = async (fn: () => Promise<Paper>) => {
    setBusy(true);
    setError("");
    try {
      await fn();
      await refresh();
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e));
    } finally {
      setBusy(false);
    }
  };

  const onFiles = (files: FileList | null) => {
    const f = files?.[0];
    if (f) run(() => api.upload(f));
  };

  return (
    <div className="mx-auto max-w-3xl px-6 py-12">
      <h1 className="text-2xl font-semibold tracking-tight">Review Copilot</h1>
      <p className="mt-1 text-sm text-stone-500">
        Facts from the paper, judgments from you. Open a paper to start reviewing.
      </p>

      <label
        onDragOver={(e) => {
          e.preventDefault();
          setDragging(true);
        }}
        onDragLeave={() => setDragging(false)}
        onDrop={(e) => {
          e.preventDefault();
          setDragging(false);
          onFiles(e.dataTransfer.files);
        }}
        className={`mt-8 flex cursor-pointer flex-col items-center justify-center rounded-xl border-2 border-dashed px-6 py-10 text-sm transition ${
          dragging ? "border-amber-500 bg-amber-50" : "border-stone-300 bg-white hover:border-stone-400"
        }`}
      >
        <input type="file" accept="application/pdf" className="hidden" onChange={(e) => onFiles(e.target.files)} />
        <span className="font-medium">Drop a paper PDF here, or click to choose</span>
        <span className="mt-1 text-stone-500">Parsed locally (GROBID). Use public papers for demos.</span>
      </label>

      <form
        className="mt-4 flex gap-2"
        onSubmit={(e) => {
          e.preventDefault();
          if (arxiv.trim()) run(() => api.importArxiv(arxiv.trim()));
        }}
      >
        <input
          value={arxiv}
          onChange={(e) => setArxiv(e.target.value)}
          placeholder="…or an arXiv id / URL, e.g. 2506.08134"
          className="flex-1 rounded-lg border border-stone-300 bg-white px-3 py-2 text-sm outline-none focus:border-stone-500"
        />
        <button
          disabled={busy}
          className="rounded-lg bg-stone-900 px-4 py-2 text-sm font-medium text-white disabled:opacity-50"
        >
          Import
        </button>
      </form>
      {error && <p className="mt-3 text-sm text-red-600">{error}</p>}

      <h2 className="mt-10 text-sm font-semibold uppercase tracking-wide text-stone-500">Papers</h2>
      <ul className="mt-3 divide-y divide-stone-200 rounded-xl border border-stone-200 bg-white">
        {papers.length === 0 && <li className="px-4 py-6 text-sm text-stone-500">No papers yet.</li>}
        {papers.map((p) => (
          <li key={p.id} className="flex items-center gap-3 px-4 py-3">
            <div className="min-w-0 flex-1">
              <div className="truncate text-sm font-medium">{p.title || p.filename}</div>
              <div className="text-xs text-stone-500">
                {p.source} · {p.n_pages || "?"} pages {p.parser && `· ${p.parser}`}
              </div>
              {p.status === "error" && <div className="text-xs text-red-600">{p.error}</div>}
            </div>
            {p.status === "parsing" ? (
              <span className="text-xs text-amber-600">Parsing…</span>
            ) : (
              <button
                disabled={p.status !== "ready"}
                onClick={() => onOpen(p.id)}
                className="rounded-md border border-stone-300 px-3 py-1 text-sm hover:bg-stone-100 disabled:opacity-40"
              >
                Open
              </button>
            )}
          </li>
        ))}
      </ul>
    </div>
  );
}
