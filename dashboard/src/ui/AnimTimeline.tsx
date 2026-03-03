import React, { useEffect, useRef } from "react";
import { W, H, rgb565ToRgb888 } from "../lib/frame";

interface Props {
  frames: Uint16Array[];
  activeIndex: number;
  onSelect: (index: number) => void;
}

function renderThumb(canvas: HTMLCanvasElement, frame: Uint16Array) {
  const tw = 32;
  const th = 16;
  canvas.width = tw;
  canvas.height = th;
  const ctx = canvas.getContext("2d");
  if (!ctx) return;

  const imgData = ctx.createImageData(W, H);
  for (let i = 0; i < W * H; i++) {
    const [r, g, b] = rgb565ToRgb888(frame[i]);
    imgData.data[i * 4] = r;
    imgData.data[i * 4 + 1] = g;
    imgData.data[i * 4 + 2] = b;
    imgData.data[i * 4 + 3] = 255;
  }

  const offscreen = document.createElement("canvas");
  offscreen.width = W;
  offscreen.height = H;
  offscreen.getContext("2d")!.putImageData(imgData, 0, 0);

  ctx.imageSmoothingEnabled = false;
  ctx.drawImage(offscreen, 0, 0, tw, th);
}

export function AnimTimeline({ frames, activeIndex, onSelect }: Props) {
  const canvasRefs = useRef<Map<number, HTMLCanvasElement>>(new Map());

  useEffect(() => {
    canvasRefs.current.forEach((canvas, idx) => {
      if (frames[idx]) renderThumb(canvas, frames[idx]);
    });
  }, [frames]);

  return (
    <div className="timeline">
      <span className="muted" style={{ flexShrink: 0 }}>{frames.length}f</span>
      <div className="timeline-frames">
        {frames.map((_, idx) => (
          <canvas
            key={idx}
            className={`timeline-frame ${idx === activeIndex ? "active" : ""}`}
            ref={(el) => { if (el) canvasRefs.current.set(idx, el); }}
            onClick={() => onSelect(idx)}
            title={`Frame ${idx + 1}`}
          />
        ))}
      </div>
    </div>
  );
}
