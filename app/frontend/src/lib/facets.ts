import type { Facet, PaperMapData } from "./api";

// Fixed facet -> color mapping (same in every paper); pale fills so text stays readable.
export const FACETS: { key: Facet; label: string; fill: string; dot: string }[] = [
  { key: "claim", label: "Claim", fill: "rgba(34,197,94,0.20)", dot: "bg-green-500" },
  { key: "method", label: "Method / setup", fill: "rgba(59,130,246,0.18)", dot: "bg-blue-500" },
  { key: "result", label: "Result", fill: "rgba(239,68,68,0.18)", dot: "bg-red-500" },
  { key: "limitation", label: "Stated limitation", fill: "rgba(249,115,22,0.24)", dot: "bg-orange-500" },
];
export const ACTIVE_FILL = "rgba(251,191,36,0.45)"; // evidence for the current turn / selection
export const HIDDEN_FILL = "rgba(168,85,247,0.35)"; // invisible-to-humans text

export const BRIEF_SECTIONS: { key: keyof Omit<PaperMapData, "facets">; label: string; facet: Facet }[] = [
  { key: "contributions", label: "Stated contributions", facet: "claim" },
  { key: "claims", label: "Main claims", facet: "claim" },
  { key: "models_and_methods", label: "Method & models", facet: "method" },
  { key: "datasets", label: "Datasets", facet: "method" },
  { key: "baselines", label: "Baselines", facet: "method" },
  { key: "metrics", label: "Metrics", facet: "method" },
  { key: "results", label: "Reported results", facet: "result" },
  { key: "stated_limitations", label: "Limitations the authors state", facet: "limitation" },
  { key: "availability", label: "Code / data / reproducibility details", facet: "method" },
];
