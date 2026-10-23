import { useEffect } from "react";
import {
  CanvasLayer,
  CustomLayer,
  Page,
  Pages,
  Root,
  TextLayer,
  usePdfJump,
  type HighlightRect,
} from "@anaralabs/lector";
import "./pdf-setup";
import type { Box } from "../lib/api";

export type Overlay = {
  id: string;
  boxes: Box[];
  color: string; // CSS color for the fill
  active?: boolean;
  title?: string;
};

type Props = {
  url: string;
  overlays: Overlay[];
  jumpTo?: { boxes: Box[]; nonce: number } | null;
  onOverlayClick?: (id: string) => void;
};

const toRects = (boxes: Box[]): HighlightRect[] =>
  boxes.map((b) => ({ pageNumber: b.page, left: b.left, top: b.top, width: b.width, height: b.height, type: "percent" }));

function Jumper({ target }: { target: Props["jumpTo"] }) {
  const { scrollToHighlightRects, jumpToHighlightRects } = usePdfJump();
  useEffect(() => {
    if (!target || target.boxes.length === 0) return;
    const rects = toRects(target.boxes);
    if (!scrollToHighlightRects(rects, "percent", "center", 0, "smooth")) {
      jumpToHighlightRects(rects, "percent", "center");
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [target?.nonce]);
  return null;
}

export function PdfPane({ url, overlays, jumpTo, onOverlayClick }: Props) {
  return (
    <Root
      source={url}
      className="h-full w-full overflow-hidden bg-stone-200"
      isZoomFitWidth
      loader={<div className="p-6 text-sm text-stone-500">Loading PDF…</div>}
    >
      <Jumper target={jumpTo} />
      <Pages className="py-4">
        <Page className="shadow-md">
          <CanvasLayer />
          <TextLayer />
          <CustomLayer>
            {(pageNumber) => (
              <div className="pointer-events-none absolute inset-0 z-10">
                {overlays.flatMap((o) =>
                  o.boxes
                    .filter((b) => b.page === pageNumber)
                    .map((b, i) => (
                      <div
                        key={`${o.id}-${i}`}
                        title={o.title}
                        onClick={() => onOverlayClick?.(o.id)}
                        className={`pointer-events-auto absolute cursor-pointer rounded-[2px] mix-blend-multiply transition-colors ${
                          o.active ? "ring-2 ring-amber-500 animate-[pulse_1.2s_ease-in-out_2]" : ""
                        }`}
                        style={{
                          left: `${b.left}%`,
                          top: `${b.top}%`,
                          width: `${b.width}%`,
                          height: `${b.height}%`,
                          background: o.color,
                        }}
                      />
                    )),
                )}
              </div>
            )}
          </CustomLayer>
        </Page>
      </Pages>
    </Root>
  );
}
