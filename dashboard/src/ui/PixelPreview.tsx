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

    // Clear to deep black
    ctx.fillStyle = "#000";
    ctx.fillRect(0, 0, cw, ch);

    if (!frame) {
      // Draw idle crosshair pattern
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

    // Render pixels
    for (let y = 0; y < H; y++) {
      for (let x = 0; x < W; x++) {
        const c = frame[y * W + x];
        if (c === 0) continue; // skip black pixels for performance
        const [r, g, b] = rgb565ToRgb888(c);
        ctx.fillStyle = `rgb(${r},${g},${b})`;
        ctx.fillRect(x * scale, y * scale, scale, scale);
      }
    }

    // Subtle grid overlay for pixel definition
    if (scale >= 4) {
      ctx.strokeStyle = "rgba(255,255,255,0.015)";
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

  return <canvas ref={ref} style={{ aspectRatio: `${W}/${H}` }} />;
}
