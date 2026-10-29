import { useEffect, useState } from "react";
import { api, type PaperCtx, type ProfileOptions } from "../lib/api";

/** Per-paper questions (all levels): area familiarity sets the background, read status and time budget set the plan. */
export function PaperSetup({ onStart, legacy }: { onStart: (ctx: PaperCtx) => void; legacy?: { turns: number; open: () => void } }) {
  const [opts, setOpts] = useState<ProfileOptions | null>(null);
  const [ctx, setCtx] = useState<PaperCtx>({ familiarity: "", read_status: "", time_budget: 30 });
  useEffect(() => {
    api.getProfile().then((r) => setOpts(r.options));
  }, []);
  if (!opts) return null;
  const ready = ctx.familiarity && ctx.read_status;
  const row = (title: string, options: Record<string, string>, key: "familiarity" | "read_status") => (
    <div className="mb-4">
      <div className="mb-1.5 text-sm font-medium">{title}</div>
      <div className="flex flex-wrap gap-1.5">
        {Object.entries(options).map(([k, label]) => (
          <button
            key={k}
            onClick={() => setCtx({ ...ctx, [key]: k })}
            className={`rounded-full border px-3 py-1 text-sm ${ctx[key] === k ? "border-stone-800 bg-stone-900 text-white" : "border-stone-300 bg-white"}`}
          >
            {label}
          </button>
        ))}
      </div>
    </div>
  );
  return (
    <div className="flex h-full items-center justify-center p-6">
      <div className="w-full max-w-md rounded-xl border border-stone-200 bg-white p-5 shadow-sm">
        <div className="mb-1 text-base font-semibold">Before we start on this paper</div>
        <p className="mb-4 text-xs text-stone-500">Three quick questions so the copilot can plan what to show you.</p>
        {row("How familiar are you with this paper's area?", opts.familiarity, "familiarity")}
        {row("Have you read the paper yet?", opts.read_status, "read_status")}
        <div className="mb-5">
          <div className="mb-1.5 text-sm font-medium">How much time do you have?</div>
          <div className="flex gap-1.5">
            {opts.budgets.map((b) => (
              <button
                key={b}
                onClick={() => setCtx({ ...ctx, time_budget: b })}
                className={`rounded-full border px-3 py-1 text-sm ${ctx.time_budget === b ? "border-stone-800 bg-stone-900 text-white" : "border-stone-300 bg-white"}`}
              >
                {b} min
              </button>
            ))}
          </div>
        </div>
        <button
          disabled={!ready}
          onClick={() => onStart(ctx)}
          className="w-full rounded-lg bg-stone-900 px-4 py-2 text-sm font-medium text-white disabled:opacity-40"
        >
          Start
        </button>
        {legacy && (
          <button onClick={legacy.open} className="mt-3 w-full text-center text-xs text-stone-500 underline">
            Or open your earlier session on this paper ({legacy.turns} turns, previous version of the copilot)
          </button>
        )}
      </div>
    </div>
  );
}
