import React, { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { decodeB64ToU16LE, makeFramePacketRGB565, W, H } from "../lib/frame";
import { getJson, postJson } from "../lib/api";
import { PixelPreview } from "./PixelPreview";
import { AnimTimeline } from "./AnimTimeline";
import { Toaster, useToast } from "./Toast";

type ModeId = "clock_fun" | "weather_fun" | "anim_player" | "rainbow" | "starfield" | "text_scroll";

const MODE_LABELS: Record<ModeId, string> = {
  clock_fun: "Clock",
  weather_fun: "Weather",
  anim_player: "Stream",
  rainbow: "Rainbow",
  starfield: "Starfield",
  text_scroll: "Scroller",
};

function formatUptime(ms: number): string {
  const s = Math.floor(ms / 1000);
  const h = Math.floor(s / 3600);
  const m = Math.floor((s % 3600) / 60);
  if (h > 0) return `${h}h ${m}m`;
  if (m > 0) return `${m}m ${s % 60}s`;
  return `${s}s`;
}

function formatHeap(bytes: number): string {
  if (bytes > 1024 * 1024) return `${(bytes / (1024 * 1024)).toFixed(1)}MB`;
  return `${Math.round(bytes / 1024)}KB`;
}

export function App() {
  const [deviceBase, setDeviceBase] = useState<string>("http://led64x32.local");
  const [renderBase, setRenderBase] = useState<string>("http://localhost:8787");
  const [status, setStatus] = useState<any>(null);
  const [mode, setMode] = useState<ModeId>("clock_fun");
  const [brightness, setBrightness] = useState<number>(160);

  const [prompt, setPrompt] = useState<string>("dragon breathing fire");
  const [seed, setSeed] = useState<number>(1234);

  const [frame, setFrame] = useState<Uint16Array | null>(null);
  const [animFrames, setAnimFrames] = useState<Uint16Array[]>([]);
  const [animFps, setAnimFps] = useState<number>(12);
  const [previewIdx, setPreviewIdx] = useState<number>(0);

  const [loading, setLoading] = useState<string | null>(null);
  const [wsConnected, setWsConnected] = useState(false);
  const [settingsOpen, setSettingsOpen] = useState(false);

  const [weatherLocation, setWeatherLocation] = useState("Miami, FL");

  const wsRef = useRef<WebSocket | null>(null);
  const eventsWsRef = useRef<WebSocket | null>(null);
  const frameId = useRef<number>(0);
  const playTimerRef = useRef<ReturnType<typeof setInterval> | null>(null);

  const { toasts, addToast, removeToast } = useToast();

  const frameWsUrl = useMemo(() => {
    try {
      const u = new URL(deviceBase);
      const proto = u.protocol === "https:" ? "wss:" : "ws:";
      return `${proto}//${u.host}/ws/frame`;
    } catch {
      return "";
    }
  }, [deviceBase]);

  const eventsWsUrl = useMemo(() => {
    try {
      const u = new URL(deviceBase);
      const proto = u.protocol === "https:" ? "wss:" : "ws:";
      return `${proto}//${u.host}/ws/events`;
    } catch {
      return "";
    }
  }, [deviceBase]);

  const refreshStatus = useCallback(async () => {
    try {
      const s = await getJson(`${deviceBase}/api/status`);
      setStatus(s);
      setBrightness(s.brightness);
      setMode(s.mode);
    } catch {
      setStatus(null);
    }
  }, [deviceBase]);

  function connectFrameWs() {
    if (!frameWsUrl) return;
    if (wsRef.current) wsRef.current.close();
    try {
      const ws = new WebSocket(frameWsUrl);
      ws.binaryType = "arraybuffer";
      ws.onopen = () => setWsConnected(true);
      ws.onclose = () => setWsConnected(false);
      ws.onerror = () => setWsConnected(false);
      wsRef.current = ws;
    } catch {
      setWsConnected(false);
    }
  }

  function connectEventsWs() {
    if (!eventsWsUrl) return;
    if (eventsWsRef.current) eventsWsRef.current.close();
    try {
      const ws = new WebSocket(eventsWsUrl);
      ws.onclose = () => setStatus(null);
      ws.onmessage = (ev) => {
        try {
          const data = JSON.parse(ev.data);
          if (data.event === "telemetry" || data.event === "connect") {
            setStatus((prev: any) => ({ ...prev, ...data }));
            if (data.mode) setMode(data.mode);
          }
        } catch { /* ignore */ }
      };
      eventsWsRef.current = ws;
    } catch { /* ignore */ }
  }

  async function setDeviceMode(next: ModeId) {
    try {
      await postJson(`${deviceBase}/api/mode`, { mode: next, params: {} });
      setMode(next);
      addToast(`Switched to ${MODE_LABELS[next] || next}`, "success");
      await refreshStatus();
    } catch (e: any) {
      addToast(`Mode switch failed: ${e.message}`, "error");
    }
  }

  async function setDeviceBrightness(val: number) {
    try {
      await postJson(`${deviceBase}/api/brightness`, { value: val });
      setBrightness(val);
    } catch {
      addToast("Brightness update failed", "error");
    }
  }

  async function generateImage() {
    setLoading("image");
    try {
      const res = await postJson(`${renderBase}/render/image`, { prompt, seed, style: "pixel_art" });
      const u16 = decodeB64ToU16LE(res.rgb565_b64);
      setFrame(u16);
      setAnimFrames([]);
      setPreviewIdx(0);
      addToast("Image generated", "success");
    } catch (e: any) {
      addToast(`Generation failed: ${e.message}`, "error");
    } finally {
      setLoading(null);
    }
  }

  async function generateAnim() {
    setLoading("anim");
    try {
      const res = await postJson(`${renderBase}/render/anim`, {
        prompt, seed, frames: 24, fps: animFps, style: "pixel_anim",
      });
      const frames: Uint16Array[] = res.frames_b64.map((b64: string) => decodeB64ToU16LE(b64));
      setAnimFrames(frames);
      setFrame(frames[0] ?? null);
      setPreviewIdx(0);
      addToast(`Animation generated (${frames.length} frames)`, "success");
    } catch (e: any) {
      addToast(`Animation failed: ${e.message}`, "error");
    } finally {
      setLoading(null);
    }
  }

  function sendFrameOnce(u16: Uint16Array) {
    const ws = wsRef.current;
    if (!ws || ws.readyState !== WebSocket.OPEN) {
      addToast("WebSocket not connected", "error");
      return;
    }
    const pkt = makeFramePacketRGB565(u16, frameId.current++);
    ws.send(pkt);
  }

  async function playAnimOnDevice() {
    if (playTimerRef.current) {
      clearInterval(playTimerRef.current);
      playTimerRef.current = null;
      addToast("Playback stopped", "info");
      return;
    }

    await setDeviceMode("anim_player");
    const ws = wsRef.current;
    if (!ws || ws.readyState !== WebSocket.OPEN) {
      addToast("WebSocket not connected. Reconnect first.", "error");
      return;
    }
    const frames = animFrames.length ? animFrames : (frame ? [frame] : []);
    if (!frames.length) {
      addToast("No frames to play", "error");
      return;
    }

    let i = 0;
    const interval = Math.max(1, Math.floor(1000 / animFps));
    addToast(`Streaming ${frames.length} frames at ${animFps} FPS`, "info");

    playTimerRef.current = setInterval(() => {
      try {
        sendFrameOnce(frames[i]);
        setPreviewIdx(i);
        setFrame(frames[i]);
        i = (i + 1) % frames.length;
      } catch {
        if (playTimerRef.current) clearInterval(playTimerRef.current);
        playTimerRef.current = null;
      }
    }, interval);

    setTimeout(() => {
      if (playTimerRef.current) {
        clearInterval(playTimerRef.current);
        playTimerRef.current = null;
        addToast("Playback finished", "info");
      }
    }, 30000);
  }

  async function pushWeather() {
    setLoading("weather");
    try {
      const loc = weatherLocation.trim() || "Miami,FL";
      const w = await getJson(`${renderBase}/weather?location=${encodeURIComponent(loc)}&units=imperial`);
      if (!w.ok) throw new Error("Weather fetch failed");
      const temp = w.current.temp;
      const cond = w.current.condition;
      await setDeviceMode("weather_fun");
      await postJson(`${deviceBase}/api/params`, { params: { tempF: temp, condition: cond, variant: 1 } });
      addToast(`${Math.round(temp)}\u00B0F, ${cond} in ${w.location?.name || loc}`, "success");
    } catch (e: any) {
      addToast(`Weather failed: ${e.message}`, "error");
    } finally {
      setLoading(null);
    }
  }

  async function sendClockStyle(style: number, blink: boolean) {
    try {
      await setDeviceMode("clock_fun");
      await postJson(`${deviceBase}/api/params`, { params: { style, blink } });
    } catch (e: any) {
      addToast(`Failed: ${e.message}`, "error");
    }
  }

  function selectTimelineFrame(idx: number) {
    if (animFrames[idx]) {
      setFrame(animFrames[idx]);
      setPreviewIdx(idx);
    }
  }

  useEffect(() => {
    refreshStatus();
  }, [refreshStatus]);

  useEffect(() => {
    connectFrameWs();
    connectEventsWs();
    return () => {
      if (wsRef.current) wsRef.current.close();
      if (eventsWsRef.current) eventsWsRef.current.close();
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [frameWsUrl, eventsWsUrl]);

  const isConnected = status !== null;

  return (
    <>
      <header className="app-header">
        <div className="app-header-left">
          <div className="app-logo">G</div>
          <div>
            <div className="app-title">Goddard Display</div>
            <div className="app-subtitle">64x32 LED Control</div>
          </div>
        </div>
        <div className="header-status">
          <span className="status-pill" data-status={isConnected ? "connected" : "disconnected"}>
            <span className="status-dot" />
            {isConnected ? (MODE_LABELS[mode] || mode) : "Offline"}
          </span>
          {wsConnected && (
            <span className="status-pill" data-status="connected">
              <span className="status-dot" />
              WS
            </span>
          )}
          <button className="btn btn-sm btn-ghost" onClick={() => setSettingsOpen(!settingsOpen)}>
            {settingsOpen ? "Close" : "Settings"}
          </button>
        </div>
      </header>

      {settingsOpen && (
        <div style={{ padding: "var(--space-lg) var(--space-xl)", maxWidth: 1400, margin: "0 auto" }}>
          <div className="card col gap-lg">
            <div className="section-header">
              <span className="section-title">Connection Settings</span>
              <button className="btn btn-sm" onClick={() => { refreshStatus(); connectFrameWs(); connectEventsWs(); addToast("Reconnecting...", "info"); }}>
                Reconnect All
              </button>
            </div>
            <div className="row gap-lg">
              <div className="field" style={{ flex: 1 }}>
                <div className="label">Device URL</div>
                <input type="text" value={deviceBase} onChange={(e) => setDeviceBase(e.target.value)} />
              </div>
              <div className="field" style={{ flex: 1 }}>
                <div className="label">Render Service URL</div>
                <input type="text" value={renderBase} onChange={(e) => setRenderBase(e.target.value)} />
              </div>
            </div>
          </div>
        </div>
      )}

      <div className="main-grid">
        {/* Left: Controls */}
        <div className="col gap-xl">

          <div className="stat-grid">
            <div className="stat-card">
              <div className="stat-value">{status?.brightness ?? "--"}</div>
              <div className="stat-label">Brightness</div>
            </div>
            <div className="stat-card">
              <div className="stat-value">{status?.heapFree ? formatHeap(status.heapFree) : "--"}</div>
              <div className="stat-label">Free Heap</div>
            </div>
            <div className="stat-card">
              <div className="stat-value">{status?.uptimeMs ? formatUptime(status.uptimeMs) : "--"}</div>
              <div className="stat-label">Uptime</div>
            </div>
          </div>

          <div className="card col gap-lg">
            <div className="section-header">
              <span className="section-title">Display Mode</span>
            </div>
            <div className="mode-tabs">
              {(Object.keys(MODE_LABELS) as ModeId[]).map((m) => (
                <button key={m} className={`mode-tab ${mode === m ? "active" : ""}`} onClick={() => setDeviceMode(m)}>
                  {MODE_LABELS[m]}
                </button>
              ))}
            </div>
            <div className="section-divider" />
            <div className="field">
              <div className="label">Brightness</div>
              <div className="brightness-display">
                <span className="brightness-value">{brightness}</span>
                <div className="brightness-slider-track">
                  <input
                    type="range"
                    min={0}
                    max={255}
                    value={brightness}
                    onChange={(e) => setBrightness(parseInt(e.target.value, 10))}
                    onMouseUp={() => setDeviceBrightness(brightness)}
                    onTouchEnd={() => setDeviceBrightness(brightness)}
                  />
                </div>
              </div>
            </div>
          </div>

          <div className="card col gap-lg">
            <div className="section-header">
              <div>
                <span className="section-title">Pixel Art Studio</span>
                <div className="section-subtitle">Generate images and animations for the display</div>
              </div>
            </div>
            <div className="field">
              <div className="label">Prompt</div>
              <textarea value={prompt} onChange={(e) => setPrompt(e.target.value)} maxLength={200} placeholder="Describe what you want to see..." />
              <div className="muted">{prompt.length}/200 characters</div>
            </div>
            <div className="row gap-md">
              <div className="field" style={{ flex: 1 }}>
                <div className="label">Seed</div>
                <input type="number" value={seed} onChange={(e) => setSeed(parseInt(e.target.value, 10))} />
              </div>
              <div className="field" style={{ flex: 1 }}>
                <div className="label">Anim FPS</div>
                <input type="number" value={animFps} min={1} max={30} onChange={(e) => setAnimFps(parseInt(e.target.value, 10))} />
              </div>
            </div>
            <div className="row gap-sm">
              <button className="btn btn-primary" disabled={!!loading} onClick={generateImage}>
                {loading === "image" ? <><span className="spinner" /> Generating...</> : "Generate Image"}
              </button>
              <button className="btn btn-primary" disabled={!!loading} onClick={generateAnim}>
                {loading === "anim" ? <><span className="spinner" /> Generating...</> : "Generate Animation"}
              </button>
              <button className="btn" disabled={!frame} onClick={() => { if (frame) { setDeviceMode("anim_player"); sendFrameOnce(frame); } }}>
                Send Frame
              </button>
              <button className="btn" disabled={!animFrames.length && !frame} onClick={playAnimOnDevice}>
                {playTimerRef.current ? "Stop Playback" : "Play on Device"}
              </button>
            </div>
            <div className="section-divider" />
            <div className="section-title">Presets</div>
            <div className="preset-grid">
              <button className="btn-preset" onClick={() => { setPrompt("mario pixel sprite"); generateImage(); }}>Mario</button>
              <button className="btn-preset" onClick={() => { setPrompt("metroid floating orb"); generateImage(); }}>Metroid</button>
              <button className="btn-preset" onClick={() => { setPrompt("zelda triforce sword"); generateImage(); }}>Zelda</button>
              <button className="btn-preset" onClick={() => { setPrompt("random pokemon"); generateImage(); }}>Pokemon</button>
              <button className="btn-preset" onClick={() => { setPrompt("dragon breathing fire"); generateAnim(); }}>Dragon</button>
              <button className="btn-preset" onClick={() => { setPrompt("rain falling city"); generateAnim(); }}>Rain</button>
              <button className="btn-preset" onClick={() => { setPrompt("time orbiting clock"); generateAnim(); }}>Orbit</button>
              <button className="btn-preset" onClick={() => { setPrompt("neon abstract shapes"); generateImage(); }}>Abstract</button>
            </div>
          </div>

          <div className="card col gap-lg">
            <div className="section-header">
              <span className="section-title">Quick Controls</span>
            </div>
            <div className="weather-row">
              <div className="field" style={{ flex: 1 }}>
                <div className="label">Weather Location</div>
                <input type="text" value={weatherLocation} onChange={(e) => setWeatherLocation(e.target.value)} placeholder="City, State" />
              </div>
              <button className="btn btn-primary" disabled={!!loading} onClick={pushWeather} style={{ height: 38 }}>
                {loading === "weather" ? <span className="spinner" /> : "Push Weather"}
              </button>
            </div>
            <div className="section-divider" />
            <div className="label">Clock Styles</div>
            <div className="row gap-sm">
              <button className="btn" onClick={() => sendClockStyle(0, true)}>Centered</button>
              <button className="btn" onClick={() => sendClockStyle(1, true)}>Bottom</button>
              <button className="btn" onClick={() => sendClockStyle(2, false)}>Glow</button>
            </div>
          </div>

        </div>

        {/* Right: Preview */}
        <div className="col gap-xl">
          <div className="card col gap-lg" style={{ position: "sticky", top: 80 }}>
            <div className="section-header">
              <span className="section-title">Live Preview</span>
              <span className="muted">64 x 32 px</span>
            </div>
            <PixelPreview frame={frame} scale={6} />
            {animFrames.length > 0 && (
              <AnimTimeline frames={animFrames} activeIndex={previewIdx} onSelect={selectTimelineFrame} />
            )}
            <div className="muted">
              For best results use short prompts, large shapes, and high contrast colors. The procedural
              provider generates offline demos. Swap in a real image model via the render service provider interface.
            </div>
          </div>
        </div>
      </div>

      <Toaster toasts={toasts} onRemove={removeToast} />
    </>
  );
}
