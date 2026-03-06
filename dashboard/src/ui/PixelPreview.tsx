import React, { useEffect, useRef } from "react";
import { H, W, rgb565ToRgb888 } from "../lib/frame";

interface Props {
  frame: Uint16Array | null;
  scale?: number;
}

export function PixelPreview({ frame, scale = 6 }: Props) {
  const ref = useRef<HTMLCanvasElement | null>(null);

  useEffect(() => {
    const canvas = ref.current;
    if (!canvas) return;
    const cw = W * scale;
    const ch = H * scale;
    canvas.width = cw;
    canvas.height = ch;
    const ctx = canvas.getContext("2d");
    if (!ctx) return;

    ctx.fillStyle = "#000";
    ctx.fillRect(0, 0, cw, ch);

    if (!frame) {
      ctx.strokeStyle = "rgba(59,125,255,0.08)";
      ctx.lineWidth = 1;
      ctx.beginPath();
      ctx.moveTo(cw / 2, 0);
      ctx.lineTo(cw / 2, ch);
      ctx.moveTo(0, ch / 2);
      ctx.lineTo(cw, ch / 2);
      ctx.stroke();
      return;
    }

    // Build a 1:1 ImageData at native resolution, then scale up — much faster
    // than 2048 individual fillRect calls
    const imgData = ctx.createImageData(W, H);
    const pixels = imgData.data;
    for (let i = 0; i < W * H; i++) {
      const [r, g, b] = rgb565ToRgb888(frame[i]);
      const off = i * 4;
      pixels[off] = r;
      pixels[off + 1] = g;
      pixels[off + 2] = b;
      pixels[off + 3] = 255;
    }

    // Render to an offscreen surface at 1:1, then draw scaled.
    const offscreen = typeof OffscreenCanvas !== "undefined"
      ? new OffscreenCanvas(W, H)
      : document.createElement("canvas");
    offscreen.width = W;
    offscreen.height = H;
    const offCtx = offscreen.getContext("2d");
    if (offCtx) {
      offCtx.putImageData(imgData, 0, 0);
      ctx.imageSmoothingEnabled = false;
      ctx.drawImage(offscreen, 0, 0, cw, ch);
    }

    // Subtle grid overlay at larger scales
    if (scale >= 4) {
      ctx.strokeStyle = "rgba(255,255,255,0.02)";
      ctx.lineWidth = 0.5;
      ctx.beginPath();
      for (let x = 0; x <= W; x++) {
        ctx.moveTo(x * scale, 0);
        ctx.lineTo(x * scale, ch);
      }
      for (let y = 0; y <= H; y++) {
        ctx.moveTo(0, y * scale);
        ctx.lineTo(cw, y * scale);
      }
      ctx.stroke();
    }
  }, [frame, scale]);

  return <canvas ref={ref} style={{ aspectRatio: `${W}/${H}` }} aria-label="64x32 pixel preview" />;
}
