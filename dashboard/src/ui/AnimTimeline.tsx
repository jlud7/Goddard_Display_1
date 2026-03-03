import React, { useEffect, useRef } from "react";
import { W, H, rgb565ToRgb888 } from "../lib/frame";

const THUMB_W = 32;
const THUMB_H = 16;

interface Props {
  frames: Uint16Array[];
  activeIndex: number;
  onSelect: (index: number) => void;
}

// Shared offscreen canvas for rendering full-res ImageData before scaling
let _offscreen: HTMLCanvasElement | null = null;
function getOffscreen(): HTMLCanvasElement {
  if (!_offscreen) {
    _offscreen = document.createElement("canvas");
    _offscreen.width = W;
    _offscreen.height = H;
  }
  return _offscreen;
}

function renderThumb(canvas: HTMLCanvasElement, frame: Uint16Array) {
  canvas.width = THUMB_W;
  canvas.height = THUMB_H;
  const ctx = canvas.getContext("2d");
  if (!ctx) return;

  // Build ImageData at native resolution (64x32), then scale down to thumbnail
  const offscreen = getOffscreen();
  const offCtx = offscreen.getContext("2d");
  if (!offCtx) return;

  const imgData = offCtx.createImageData(W, H);
  const pixels = imgData.data;
  for (let i = 0; i < W * H; i++) {
    const [r, g, b] = rgb565ToRgb888(frame[i]);
    const off = i * 4;
    pixels[off] = r;
    pixels[off + 1] = g;
    pixels[off + 2] = b;
    pixels[off + 3] = 255;
  }
  offCtx.putImageData(imgData, 0, 0);

  ctx.imageSmoothingEnabled = false;
  ctx.drawImage(offscreen, 0, 0, THUMB_W, THUMB_H);
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
            ref={(el) => {
              if (el) canvasRefs.current.set(idx, el);
              else canvasRefs.current.delete(idx);
            }}
            onClick={() => onSelect(idx)}
            title={`Frame ${idx + 1}`}
          />
        ))}
      </div>
    </div>
  );
}
