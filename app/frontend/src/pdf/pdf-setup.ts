import { GlobalWorkerOptions } from "pdfjs-dist/legacy/build/pdf.mjs";
import workerUrl from "pdfjs-dist/legacy/build/pdf.worker.min.mjs?url";
import "pdfjs-dist/web/pdf_viewer.css";

// The worker must come from the same pdfjs-dist version Lector renders with.
GlobalWorkerOptions.workerSrc = workerUrl;
