import { useEffect, useState } from "react";
import { api, type CriterionOption, type Level, type Profile, type ProfileOptions } from "../lib/api";

/** One-time reviewer profile. The level comes first; each level gets its own questions (conversation_redesign.md §4). */
export function Onboarding({ onDone, editing }: { onDone: () => void; editing?: boolean }) {
  const [opts, setOpts] = useState<ProfileOptions | null>(null);
  const [p, setP] = useState<Profile>({});
  const [step, setStep] = useState<"level" | "questions">("level");
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState("");

  useEffect(() => {
    api.getProfile().then(({ profile, options }) => {
      setOpts(options);
      // An empty "where to look" list means "the defaults": show them ticked.
      const withDefaults = (profile.criteria ?? []).map((c) =>
        c.where?.length ? c : { ...c, where: options.criteria.find((o) => o.key === c.key)?.where ?? [] },
      );
      setP({ ...profile, criteria: withDefaults });
      if (editing && profile.level) setStep("questions");
    });
  }, [editing]);

  if (!opts) return <div className="p-8 text-sm text-stone-500">Loading…</div>;

  const save = async (data: Profile) => {
    setSaving(true);
    setError("");
    try {
      await api.putProfile(data);
      onDone();
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e));
    } finally {
      setSaving(false);
    }
  };
  const chosen = (p.criteria ?? []).map((c) => c.key);
  const toggleCriterion = (key: string, max: number) => {
    const cur = p.criteria ?? [];
    if (chosen.includes(key)) setP({ ...p, criteria: cur.filter((c) => c.key !== key) });
    else if (cur.length < max) {
      const def = opts.criteria.find((c) => c.key === key)!.where;
      setP({ ...p, criteria: [...cur, { key, where: def }] });
    }
  };
  const move = (key: string, d: -1 | 1) => {
    const cur = [...(p.criteria ?? [])];
    const i = cur.findIndex((c) => c.key === key);
    const j = i + d;
    if (j < 0 || j >= cur.length) return;
    [cur[i], cur[j]] = [cur[j], cur[i]];
    setP({ ...p, criteria: cur });
  };
  const toggleWhere = (key: string, place: string) =>
    setP({
      ...p,
      criteria: (p.criteria ?? []).map((c) =>
        c.key !== key ? c : { ...c, where: c.where.includes(place) ? c.where.filter((w) => w !== place) : [...c.where, place] },
      ),
    });

  const level = p.level;
  return (
    <div className="mx-auto max-w-2xl px-6 py-10">
      <h1 className="text-2xl font-semibold tracking-tight">{editing ? "Your reviewer profile" : "Welcome to Review Copilot"}</h1>
      <p className="mt-1 text-sm text-stone-500">
        A one-time setup, about two minutes. It decides what the copilot shows you and asks you. It never goes into your
        review, and you can change it any time.
      </p>

      {step === "level" && (
        <section className="mt-8">
          <h2 className="text-sm font-semibold">Which describes you best?</h2>
          <div className="mt-3 grid gap-2">
            {(Object.entries(opts.levels) as [Level, string][]).map(([k, label]) => (
              <button
                key={k}
                onClick={() => {
                  setP({
                    ...p,
                    level: k,
                    criteria: k === p.level ? p.criteria : [],
                    help_style: k === "L3" ? "quick" : k === "L0" ? "guided" : p.help_style,
                  });
                  setStep("questions");
                }}
                className={`rounded-xl border px-4 py-3 text-left text-sm transition hover:border-stone-500 ${
                  level === k ? "border-stone-800 bg-stone-50" : "border-stone-200 bg-white"
                }`}
              >
                {label}
              </button>
            ))}
          </div>
          {!editing && (
            <button
              className="mt-4 text-xs text-stone-500 underline"
              onClick={() => save({ level: "L1", skipped: true, criteria: [], help_style: "guided" })}
            >
              Skip for now (the copilot will ask what you look for as topics come up)
            </button>
          )}
        </section>
      )}

      {step === "questions" && level && (
        <section className="mt-8 space-y-7">
          <button className="text-xs text-stone-500 underline" onClick={() => setStep("level")}>
            ← {opts.levels[level]}
          </button>

          {level === "L0" && (
            <>
              <Q title="What would help you most?">
                <Choice
                  value={p.help_goal}
                  options={{ understand: "Understand the paper first", form: "Know what a review asks for", words: "Put my thoughts into words" }}
                  onChange={(v) => setP({ ...p, help_goal: v as Profile["help_goal"] })}
                />
              </Q>
              <Q
                title="Which of these would you feel comfortable starting with?"
                hint="This is what the ACL review form asks about. Pick any; you can talk about the rest later."
              >
                <div className="grid gap-1.5">
                  {opts.starter_lens.map((s) => (
                    <label key={s.key} className="flex items-center gap-2 text-sm">
                      <input type="checkbox" checked={chosen.includes(s.key)} onChange={() => toggleCriterion(s.key, 5)} />
                      {s.text}
                    </label>
                  ))}
                </div>
              </Q>
            </>
          )}

          {(level === "L1" || level === "L2") && (
            <>
              <Q
                title={level === "L1" ? "When you read a paper, what do you usually pay attention to?" : "What makes a paper strong to you?"}
                hint={level === "L1" ? "Up to 3." : "Pick up to 3, in order of importance (use the arrows to reorder)."}
              >
                <CriteriaPicker options={opts.criteria} chosen={chosen} onToggle={(k) => toggleCriterion(k, 3)} />
              </Q>
              {chosen.length > 0 && (
                <Q title="Where do you usually look for each?" hint="Pre-filled with common places; untick or add your own.">
                  <div className="space-y-3">
                    {(p.criteria ?? []).map((c, i) => {
                      const o = opts.criteria.find((x) => x.key === c.key)!;
                      return (
                        <WhereEditor
                          key={c.key}
                          rank={level === "L2" ? i + 1 : undefined}
                          label={o.label}
                          defaults={o.where}
                          where={c.where}
                          onToggle={(w) => toggleWhere(c.key, w)}
                          onAdd={(w) => setP({ ...p, criteria: (p.criteria ?? []).map((x) => (x.key === c.key ? { ...x, where: [...x.where, w] } : x)) })}
                          onMove={level === "L2" ? (d) => move(c.key, d) : undefined}
                        />
                      );
                    })}
                  </div>
                </Q>
              )}
              {level === "L2" && (
                <Q title="Anything that is usually a deal-breaker for you? (optional)" hint="In your own words. The copilot only uses it to decide which passages to show you.">
                  <textarea
                    value={p.dealbreakers ?? ""}
                    onChange={(e) => setP({ ...p, dealbreakers: e.target.value })}
                    rows={2}
                    className="w-full rounded-lg border border-stone-300 px-3 py-2 text-sm"
                  />
                </Q>
              )}
              {level === "L1" && (
                <label className="flex items-center gap-2 text-sm">
                  <input type="checkbox" checked={!!p.orientation} onChange={(e) => setP({ ...p, orientation: e.target.checked })} />
                  Start each paper with a one-minute orientation (what the paper says it does)
                </label>
              )}
              <Q title={level === "L1" ? "How should I help?" : "Mode"}>
                <Choice
                  value={p.help_style}
                  options={
                    level === "L1"
                      ? { guided: "Guide me step by step", evidence: "Show me evidence, I'll react" }
                      : { evidence: "Show me evidence, I'll react", quick: "Quick mode: I'll write my thoughts first" }
                  }
                  onChange={(v) => setP({ ...p, help_style: v as Profile["help_style"] })}
                />
              </Q>
            </>
          )}

          {level === "L3" && (
            <>
              <Q title="In a line or two, what do you weigh most when judging a paper?">
                <textarea
                  value={p.weigh_text ?? ""}
                  onChange={(e) => setP({ ...p, weigh_text: e.target.value })}
                  rows={2}
                  className="w-full rounded-lg border border-stone-300 px-3 py-2 text-sm"
                />
                <div className="mt-2 text-xs text-stone-500">…or pick up to 3:</div>
                <CriteriaPicker options={opts.criteria} chosen={chosen} onToggle={(k) => toggleCriterion(k, 3)} />
              </Q>
              <Q title="Mode">
                <Choice
                  value={p.help_style ?? "quick"}
                  options={{ quick: "Quick mode: I'll write my thoughts first", evidence: "Show me evidence, I'll react" }}
                  onChange={(v) => setP({ ...p, help_style: v as Profile["help_style"] })}
                />
              </Q>
            </>
          )}

          <label className="flex items-start gap-2 rounded-lg bg-stone-100 px-3 py-2 text-xs text-stone-600">
            <input type="checkbox" checked={!!p.study_mode} onChange={(e) => setP({ ...p, study_mode: e.target.checked })} />
            <span>
              <b>Study mode.</b> For user studies only: before showing any evidence, the copilot asks for a one-line first
              impression of each paper.
            </span>
          </label>

          {error && <p className="text-sm text-red-600">{error}</p>}
          <div className="flex gap-2">
            <button
              disabled={saving}
              onClick={() => save({ ...p, skipped: false })}
              className="rounded-lg bg-stone-900 px-4 py-2 text-sm font-medium text-white disabled:opacity-50"
            >
              {saving ? "Saving…" : editing ? "Save profile" : "Start reviewing"}
            </button>
            {editing && (
              <button onClick={onDone} className="rounded-lg px-4 py-2 text-sm text-stone-600 hover:bg-stone-100">
                Cancel
              </button>
            )}
          </div>
        </section>
      )}
    </div>
  );
}

function Q({ title, hint, children }: { title: string; hint?: string; children: React.ReactNode }) {
  return (
    <div>
      <h2 className="text-sm font-semibold">{title}</h2>
      {hint && <p className="mb-2 mt-0.5 text-xs text-stone-500">{hint}</p>}
      <div className={hint ? "" : "mt-2"}>{children}</div>
    </div>
  );
}

function Choice({ value, options, onChange }: { value?: string; options: Record<string, string>; onChange: (v: string) => void }) {
  return (
    <div className="flex flex-wrap gap-2">
      {Object.entries(options).map(([k, label]) => (
        <button
          key={k}
          onClick={() => onChange(k)}
          className={`rounded-full border px-3 py-1.5 text-sm ${value === k ? "border-stone-800 bg-stone-900 text-white" : "border-stone-300 bg-white"}`}
        >
          {label}
        </button>
      ))}
    </div>
  );
}

function CriteriaPicker({ options, chosen, onToggle }: { options: CriterionOption[]; chosen: string[]; onToggle: (k: string) => void }) {
  return (
    <div className="flex flex-wrap gap-2">
      {options.map((o) => {
        const i = chosen.indexOf(o.key);
        return (
          <button
            key={o.key}
            title={o.plain}
            onClick={() => onToggle(o.key)}
            className={`rounded-full border px-3 py-1.5 text-sm ${i >= 0 ? "border-stone-800 bg-stone-900 text-white" : "border-stone-300 bg-white"}`}
          >
            {i >= 0 && <span className="mr-1 text-xs opacity-70">{i + 1}</span>}
            {o.label}
          </button>
        );
      })}
    </div>
  );
}

function WhereEditor(props: {
  rank?: number;
  label: string;
  defaults: string[];
  where: string[];
  onToggle: (w: string) => void;
  onAdd: (w: string) => void;
  onMove?: (d: -1 | 1) => void;
}) {
  const [extra, setExtra] = useState("");
  const all = [...props.defaults, ...props.where.filter((w) => !props.defaults.includes(w))];
  return (
    <div className="rounded-lg border border-stone-200 bg-white px-3 py-2">
      <div className="mb-1.5 flex items-center gap-2 text-sm font-medium">
        {props.rank && <span className="text-xs text-stone-400">#{props.rank}</span>}
        {props.label}
        {props.onMove && (
          <span className="ml-auto flex gap-1 text-xs text-stone-500">
            <button onClick={() => props.onMove!(-1)}>↑</button>
            <button onClick={() => props.onMove!(1)}>↓</button>
          </span>
        )}
      </div>
      <div className="flex flex-wrap gap-1.5">
        {all.map((w) => (
          <button
            key={w}
            onClick={() => props.onToggle(w)}
            className={`rounded-full border px-2 py-0.5 text-xs ${props.where.includes(w) ? "border-stone-500 bg-stone-100" : "border-stone-200 text-stone-400 line-through"}`}
          >
            {w}
          </button>
        ))}
        <form
          onSubmit={(e) => {
            e.preventDefault();
            if (extra.trim()) props.onAdd(extra.trim());
            setExtra("");
          }}
        >
          <input
            value={extra}
            onChange={(e) => setExtra(e.target.value)}
            placeholder="+ add"
            className="w-24 rounded-full border border-dashed border-stone-300 px-2 py-0.5 text-xs outline-none"
          />
        </form>
      </div>
    </div>
  );
}
