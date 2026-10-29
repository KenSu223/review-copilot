export type Box = { page: number; left: number; top: number; width: number; height: number };

export type Paper = {
  id: string;
  title: string;
  source: string;
  filename: string;
  n_pages: number;
  parser: string;
  status: "parsing" | "ready" | "error";
  error: string;
  hidden_text: HiddenFinding[];
  created_at: string;
};

export type HiddenFinding = { page: number; text: string; reasons: string[]; box: Box };

export type MapItem = { text: string; block_ids: string[] };
export type Facet = "claim" | "method" | "result" | "limitation";
export type PaperMapData = {
  contributions: MapItem[];
  claims: MapItem[];
  datasets: MapItem[];
  baselines: MapItem[];
  metrics: MapItem[];
  models_and_methods: MapItem[];
  results: MapItem[];
  stated_limitations: MapItem[];
  availability: MapItem[];
  facets: Record<string, Facet>;
};
export type PaperMap = { paper_id: string; status: "computing" | "ready" | "error"; data: PaperMapData; error: string };

export type Block = {
  id: string; // s-0042
  kind: "sentence" | "heading" | "caption" | "table" | "formula" | "hidden";
  section: string;
  para: number;
  text: string;
  boxes: Box[];
};

async function json<T>(res: Response): Promise<T> {
  if (!res.ok) {
    let detail = res.statusText;
    try {
      detail = (await res.json()).detail ?? detail;
    } catch {
      /* not JSON */
    }
    throw new Error(detail);
  }
  return res.json() as Promise<T>;
}

export type Segment = { text: string; cites: string[] };
export type Check = { claim: string; verdict: "supported" | "partly_supported" | "contradicted" | "not_located"; segments: Segment[] };
export type Chip = { label: string; action: string };
export type Focus = { block_ids: string[]; card: string | null; title: string; why: string; criterion: string | null; read_min: number };
export type Fact = { id: string; text: string; block_ids: string[]; confirmed?: boolean };
export type CopilotMessage = {
  role: "copilot";
  turn: number;
  segments: Segment[];
  plain: string;
  action?: string;
  move: string;
  dimension: string;
  chips: (Chip | string)[];
  checks: Check[];
  new_units: string[];
  fallback: boolean;
  focus?: Focus | null;
  facts?: Fact[];
  field_help?: { field: string; label: string; text: string; source: string } | null;
  remember?: { criterion: string; label: string } | null;
};
export type ReviewerMessage = { role: "reviewer"; turn: number; text: string; action?: string };
export type ChatMessage = CopilotMessage | ReviewerMessage;
export type OpinionUnit = {
  id: string;
  turn: number;
  dimension: string;
  criterion?: string | null;
  statement: string;
  rationale: string;
  polarity: string;
  intensity: string;
  confirmed: boolean;
  source: string; // dialogue | dialogue+edited | paper_fact
  card?: string | null;
  block_ids?: string[];
  fact_id?: string;
  check_claim?: string;
};
export type Card = {
  id: string;
  kind: "evidence" | "orientation" | "background" | "positioning" | "summary";
  criterion: string | null;
  criterion_label: string;
  title: string;
  status: "pending" | "active" | "done" | "skipped" | "reserve";
  read_min: number;
  block_ids: string[];
  why: string;
  n_absent: number;
};
export type CoverageField = {
  key: string;
  label: string;
  arr_field: string;
  status: "covered" | "partial" | "missing" | "skipped";
  core: boolean;
  plain?: string;
  help?: string;
};
export type Coverage = { fields: CoverageField[]; gaps: { field: string; note: string }[]; ready: boolean; n_units: number };
export type GlossaryTerm = { term: string; block_id: string; text: string };
export type PaperCtx = { familiarity: string; read_status: string; time_budget: number };
export type SessionState = {
  flow: "evidence" | "commit_first";
  turn: number;
  finished: boolean;
  agenda: { status: string; error: string; cards: Card[]; current: string | null; glossary: GlossaryTerm[]; contributions: Fact[] };
  coverage: Coverage;
  units: OpinionUnit[];
  progress: { cards_left: number; minutes_left: number };
  level: string;
  help_style: string;
  paper_ctx: PaperCtx;
  study_mode: boolean;
  topic: { type: string; card?: string; field?: string } | null;
};
export type TurnEvent =
  | { type: "status"; step: string; label: string }
  | { type: "message"; turn: number; message: CopilotMessage; state: SessionState }
  | { type: "error"; message: string };

export type Level = "L0" | "L1" | "L2" | "L3";
export type Profile = {
  level?: Level;
  help_goal?: "understand" | "form" | "words";
  criteria?: { key: string; where: string[] }[];
  weigh_text?: string;
  dealbreakers?: string;
  help_style?: "guided" | "evidence" | "quick";
  learned?: { key: string; where: string[] }[];
  declined?: string[];
  study_mode?: boolean;
  skipped?: boolean;
  orientation?: boolean;
};
export type CriterionOption = { key: string; label: string; plain: string; where: string[] };
export type ProfileOptions = {
  levels: Record<Level, string>;
  criteria: CriterionOption[];
  starter_lens: { key: string; text: string }[];
  familiarity: Record<string, string>;
  read_status: Record<string, string>;
  budgets: number[];
  field_help: Record<string, string>;
  field_help_source: string;
};

export async function streamTurn(sid: string, body: { text?: string; action?: string }, onEvent: (e: TurnEvent) => void) {
  const res = await fetch(`/api/sessions/${sid}/turn`, {
    method: "POST",
    headers: { "content-type": "application/json" },
    body: JSON.stringify(body),
  });
  if (!res.ok || !res.body) throw new Error(`turn failed: ${res.status}`);
  const reader = res.body.getReader();
  const decoder = new TextDecoder();
  let buf = "";
  for (;;) {
    const { done, value } = await reader.read();
    if (done) break;
    buf += decoder.decode(value, { stream: true });
    let idx;
    while ((idx = buf.indexOf("\n\n")) >= 0) {
      const chunk = buf.slice(0, idx);
      buf = buf.slice(idx + 2);
      const line = chunk.split("\n").find((l) => l.startsWith("data:"));
      if (line) onEvent(JSON.parse(line.slice(5)));
    }
  }
}

export type Register = "words" | "polished" | "formal";
export type Drift = { entailed: boolean; polarity: string; intensity: string; note: string };
export type DraftSentence = {
  sid: string;
  text: string;
  original: string;
  variants?: Record<Register, string>;
  register?: Register | null;
  drifts?: Partial<Record<Register, Drift>>;
  kind: "opinion" | "fact" | "connective";
  unit_ids: string[];
  block_ids: string[];
  status: "proposed" | "accepted" | "edited" | "rejected";
  unsourced: boolean;
  drift: Drift | null;
  check_conflicts?: { claim: string; verdict: string; turn: number }[];
};
export type Draft = { sections: { field: string; sentences: DraftSentence[] }[]; unused_units: string[]; register?: Register };
export type ScoreMeta = Record<string, { label: string; values: number[] }>;
export type DraftView = {
  draft: Draft | null;
  scores: Record<string, { value: number; rationale: string }>;
  score_meta: ScoreMeta;
  fields: { key: string; label: string }[];
  preflight: string[];
  registers: Register[];
  register: Register;
  familiarity: string;
};
export type ExportResult = {
  arr_text: string;
  disclosure: string;
  preflight: string[];
  report: unknown;
  report_stats: Record<string, number>;
};

const jsonReq = (method: string, body: unknown) => ({
  method,
  headers: { "content-type": "application/json" },
  body: JSON.stringify(body),
});

export const reviewApi = {
  getDraft: (sid: string) => fetch(`/api/sessions/${sid}/draft`).then((r) => json<DraftView>(r)),
  makeDraft: (sid: string) => fetch(`/api/sessions/${sid}/draft`, { method: "POST" }).then((r) => json<DraftView>(r)),
  patchSentence: (sid: string, id: string, body: Partial<DraftSentence>) =>
    fetch(`/api/sessions/${sid}/draft/${id}`, jsonReq("PATCH", body)).then((r) => json<DraftSentence>(r)),
  putScore: (sid: string, field: string, value: number, rationale = "") =>
    fetch(`/api/sessions/${sid}/scores/${field}`, jsonReq("PUT", { value, rationale })).then((r) => json<unknown>(r)),
  patchUnit: (sid: string, uid: string, body: Partial<OpinionUnit> & { deleted?: boolean }) =>
    fetch(`/api/sessions/${sid}/units/${uid}`, jsonReq("PATCH", body)).then((r) => json<OpinionUnit>(r)),
  setRegister: (sid: string, register: Register, sentence_id?: string) =>
    fetch(`/api/sessions/${sid}/register`, jsonReq("PUT", { register, sentence_id })).then((r) => json<DraftView>(r)),
  rephraseUnits: (sid: string, register: Register) =>
    fetch(`/api/sessions/${sid}/units/rephrase`, jsonReq("POST", { register })).then((r) =>
      json<{ register: Register; units: Record<string, { text: string; drift: Drift | null }> }>(r),
    ),
  exportReview: (sid: string, format: "arr" | "json") =>
    fetch(`/api/sessions/${sid}/export?format=${format}`).then((r) => json<ExportResult>(r)),
};

export const api = {
  getProfile: () => fetch("/api/profile").then((r) => json<{ profile: Profile; options: ProfileOptions }>(r)),
  putProfile: (data: Profile) => fetch("/api/profile", jsonReq("PUT", { data })).then((r) => json<{ profile: Profile }>(r)),
  listSessions: (pid: string) =>
    fetch(`/api/papers/${pid}/sessions`).then((r) => json<{ id: string; turn: number; flow: string }[]>(r)),
  newSession: (pid: string, paper_ctx: PaperCtx) =>
    fetch("/api/sessions", jsonReq("POST", { paper_id: pid, paper_ctx })).then((r) => json<{ id: string }>(r)),
  rail: (sid: string, cardId: string, op: "up" | "down" | "skip" | "restore") =>
    fetch(`/api/sessions/${sid}/agenda/${cardId}`, jsonReq("POST", { op })).then((r) => json<SessionState>(r)),
  confirmFacts: (sid: string, fact_ids: string[]) =>
    fetch(`/api/sessions/${sid}/facts`, jsonReq("POST", { fact_ids })).then((r) => json<SessionState>(r)),
  confirmCheck: (sid: string, turn: number, index: number) =>
    fetch(`/api/sessions/${sid}/checks/confirm`, jsonReq("POST", { turn, index })).then((r) => json<SessionState>(r)),
  remember: (sid: string, criterion: string, accept: boolean) =>
    fetch(`/api/sessions/${sid}/remember`, jsonReq("POST", { criterion, accept })).then((r) => json<SessionState>(r)),
  getSession: (sid: string) =>
    fetch(`/api/sessions/${sid}`).then((r) => json<{ id: string; state: SessionState; messages: ChatMessage[] }>(r)),
  listPapers: () => fetch("/api/papers").then((r) => json<Paper[]>(r)),
  getPaper: (id: string) => fetch(`/api/papers/${id}`).then((r) => json<Paper>(r)),
  getBlocks: (id: string) => fetch(`/api/papers/${id}/blocks`).then((r) => json<Block[]>(r)),
  getMap: (id: string) => fetch(`/api/papers/${id}/map`).then((r) => json<PaperMap>(r)),
  rebuildMap: (id: string) => fetch(`/api/papers/${id}/map`, { method: "POST" }).then((r) => json<{ status: string }>(r)),
  pdfUrl: (id: string) => `/api/papers/${id}/pdf`,
  upload: (file: File) => {
    const fd = new FormData();
    fd.append("file", file);
    return fetch("/api/papers/upload", { method: "POST", body: fd }).then((r) => json<Paper>(r));
  },
  importArxiv: (ref: string) =>
    fetch("/api/papers/arxiv", {
      method: "POST",
      headers: { "content-type": "application/json" },
      body: JSON.stringify({ ref }),
    }).then((r) => json<Paper>(r)),
  reparse: (id: string) => fetch(`/api/papers/${id}/reparse`, { method: "POST" }).then((r) => json<Paper>(r)),
};
