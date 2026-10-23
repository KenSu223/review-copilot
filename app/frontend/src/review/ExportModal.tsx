import { useEffect, useState } from "react";
import { type ExportResult, reviewApi } from "../lib/api";

export function ExportModal({ sessionId, onClose }: { sessionId: string; onClose: () => void }) {
  const [res, setRes] = useState<ExportResult | null>(null);
  const [copied, setCopied] = useState("");

  useEffect(() => {
    reviewApi.exportReview(sessionId, "arr").then(setRes);
  }, [sessionId]);

  const copy = (label: string, text: string) => {
    navigator.clipboard.writeText(text);
    setCopied(label);
    setTimeout(() => setCopied(""), 1500);
  };
  const downloadTrace = async () => {
    const full = await reviewApi.exportReview(sessionId, "json");
    const blob = new Blob([JSON.stringify(full.report, null, 2)], { type: "application/json" });
    const a = document.createElement("a");
    a.href = URL.createObjectURL(blob);
    a.download = `review-trace-${sessionId}.json`;
    a.click();
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/30 p-6" onClick={onClose}>
      <div className="flex max-h-full w-full max-w-2xl flex-col rounded-xl bg-white shadow-xl" onClick={(e) => e.stopPropagation()}>
        <div className="flex items-center border-b border-stone-200 px-4 py-3">
          <div className="flex-1 font-semibold">Export review</div>
          <button onClick={onClose} className="text-stone-500">✕</button>
        </div>
        {!res ? (
          <div className="p-4 text-sm text-stone-500">Preparing…</div>
        ) : (
          <div className="min-h-0 flex-1 overflow-y-auto px-4 py-3 text-sm">
            {res.preflight.length > 0 && (
              <div className="mb-3 rounded-md bg-amber-50 px-3 py-2 text-xs text-amber-900">
                <b>Before you submit:</b>
                <ul className="ml-4 list-disc">
                  {res.preflight.map((p) => (
                    <li key={p}>{p}</li>
                  ))}
                </ul>
              </div>
            )}
            <div className="mb-1 flex items-center">
              <span className="flex-1 text-xs font-semibold uppercase text-stone-500">ARR form text (accepted sentences only)</span>
              <button className="text-xs underline" onClick={() => copy("arr", res.arr_text)}>
                {copied === "arr" ? "Copied" : "Copy"}
              </button>
            </div>
            <pre className="mb-3 max-h-72 overflow-auto whitespace-pre-wrap rounded-md bg-stone-50 p-3 text-[12px]">{res.arr_text}</pre>
            <div className="mb-1 flex items-center">
              <span className="flex-1 text-xs font-semibold uppercase text-stone-500">Suggested AI-use disclosure</span>
              <button className="text-xs underline" onClick={() => copy("disc", res.disclosure)}>
                {copied === "disc" ? "Copied" : "Copy"}
              </button>
            </div>
            <p className="mb-3 rounded-md bg-stone-50 p-3 text-[12px]">{res.disclosure}</p>
            <div className="mb-1 text-xs font-semibold uppercase text-stone-500">Engagement trace</div>
            <div className="mb-2 grid grid-cols-3 gap-2 text-[12px]">
              {Object.entries(res.report_stats).map(([k, v]) => (
                <div key={k} className="rounded-md border border-stone-200 px-2 py-1">
                  <div className="text-stone-500">{k.replaceAll("_", " ")}</div>
                  <div className="font-semibold">{v}</div>
                </div>
              ))}
            </div>
            <button onClick={downloadTrace} className="rounded-md border border-stone-300 px-3 py-1.5 text-xs hover:bg-stone-100">
              Download provenance trace (JSON)
            </button>
          </div>
        )}
      </div>
    </div>
  );
}
