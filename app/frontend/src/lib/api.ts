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
export type CopilotMessage = {
  role: "copilot";
  turn: number;
  segments: Segment[];
  plain: string;
  move: string;
  dimension: string;
  chips: string[];
  checks: Check[];
  new_units: string[];
  fallback: boolean;
};
export type ReviewerMessage = { role: "reviewer"; turn: number; text: string; action?: string };
export type ChatMessage = CopilotMessage | ReviewerMessage;
export type DimState = { key: string; label: string; arr_field: string; status: "covered" | "partial" | "open" | "skipped" };
export type OpinionUnit = {
  id: string;
  turn: number;
  dimension: string;
  statement: string;
  rationale: string;
  polarity: string;
  intensity: string;
  confirmed: boolean;
  source: string;
};
export type SessionState = { current: string; finished: boolean; turn: number; dims: DimState[]; units: OpinionUnit[] };
export type TurnEvent =
  | { type: "status"; step: string; label: string }
  | { type: "message"; turn: number; message: CopilotMessage; state: SessionState }
  | { type: "error"; message: string };

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

export type DraftSentence = {
  sid: string;
  text: string;
  original: string;
  kind: "opinion" | "fact" | "connective";
  unit_ids: string[];
  block_ids: string[];
  status: "proposed" | "accepted" | "edited" | "rejected";
  unsourced: boolean;
  drift: { entailed: boolean; polarity: string; intensity: string; note: string } | null;
  check_conflicts?: { claim: string; verdict: string; turn: number }[];
};
export type Draft = { sections: { field: string; sentences: DraftSentence[] }[]; unused_units: string[] };
export type ScoreMeta = Record<string, { label: string; values: number[] }>;
export type DraftView = {
  draft: Draft | null;
  scores: Record<string, { value: number; rationale: string }>;
  score_meta: ScoreMeta;
  fields: { key: string; label: string }[];
  preflight: string[];
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
  exportReview: (sid: string, format: "arr" | "json") =>
    fetch(`/api/sessions/${sid}/export?format=${format}`).then((r) => json<ExportResult>(r)),
};

export const api = {
  listSessions: (pid: string) => fetch(`/api/papers/${pid}/sessions`).then((r) => json<{ id: string; turn: number }[]>(r)),
  newSession: (pid: string) =>
    fetch("/api/sessions", {
      method: "POST",
      headers: { "content-type": "application/json" },
      body: JSON.stringify({ paper_id: pid }),
    }).then((r) => json<{ id: string }>(r)),
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
