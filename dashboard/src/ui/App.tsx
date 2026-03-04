import React, { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { decodeB64ToU16LE, makeFramePacketRGB565, W, H } from "../lib/frame";
import { getJson, postJson } from "../lib/api";
import { PixelPreview } from "./PixelPreview";
import { AnimTimeline } from "./AnimTimeline";
import { Toaster, useToast } from "./Toast";

type ModeId = "clock_fun" | "weather_fun" | "anim_player" | "rainbow" | "starfield" | "text_scroll";

interface DeviceStatus {
  mode: ModeId;
  brightness: number;
  gamma: boolean;
  heapFree: number;
  uptimeMs: number;
  firmware?: string;
}

const MODE_LABELS: Record<ModeId, string> = {
  clock_fun: "Clock",
  weather_fun: "Weather",
  anim_player: "Stream",
  rainbow: "Rainbow",
  starfield: "Starfield",
  text_scroll: "Scroller",
};

const MODE_ICONS: Record<ModeId, string> = {
  clock_fun: "\u23F0",
  weather_fun: "\u26C5",
  anim_player: "\u25B6",
  rainbow: "\uD83C\uDF08",
  starfield: "\u2728",
  text_scroll: "\uD83D\uDCDC",
};

const PRESET_DATA: { label: string; icon: string; prompt: string; type: "image" | "anim" }[] = [
  // Characters
  { label: "Charmander", icon: "\uD83D\uDD25", prompt: "charmander breathing fire", type: "anim"  },
  { label: "Pikachu",   icon: "\u26A1",        prompt: "pikachu in a field",        type: "image" },
  { label: "Mario",     icon: "\uD83C\uDF44", prompt: "mario pixel sprite",        type: "image" },
  { label: "Zelda",     icon: "\u2694\uFE0F",  prompt: "zelda triforce sword",      type: "image" },
  // Food
  { label: "Pizza",     icon: "\uD83C\uDF55", prompt: "pepperoni pizza",           type: "image" },
  { label: "Burger",    icon: "\uD83C\uDF54", prompt: "cheeseburger",              type: "image" },
  { label: "Sushi",     icon: "\uD83C\uDF63", prompt: "sushi platter",             type: "image" },
  { label: "Ramen",     icon: "\uD83C\uDF5C", prompt: "ramen noodle bowl",         type: "image" },
  { label: "Donut",     icon: "\uD83C\uDF69", prompt: "donut with sprinkles",      type: "image" },
  { label: "Cake",      icon: "\uD83C\uDF82", prompt: "birthday cake",             type: "image" },
  // Animals
  { label: "Cat",       icon: "\uD83D\uDC31", prompt: "cute cat",                  type: "image" },
  { label: "Dog",       icon: "\uD83D\uDC36", prompt: "happy dog",                 type: "image" },
  { label: "Fish",      icon: "\uD83D\uDC20", prompt: "goldfish aquarium",         type: "image" },
  { label: "Owl",       icon: "\uD83E\uDD89", prompt: "owl at night",              type: "image" },
  // Objects
  { label: "Robot",     icon: "\uD83E\uDD16", prompt: "robot mech",                type: "image" },
  { label: "Skull",     icon: "\uD83D\uDC80", prompt: "glowing skull",             type: "image" },
  { label: "Ghost",     icon: "\uD83D\uDC7B", prompt: "spooky ghost",              type: "image" },
  { label: "Heart",     icon: "\u2764\uFE0F",  prompt: "red heart love",            type: "anim"  },
  { label: "Gem",       icon: "\uD83D\uDC8E", prompt: "crystal gem diamond",       type: "image" },
  { label: "Rocket",    icon: "\uD83D\uDE80", prompt: "rocket spaceship",          type: "image" },
  // Scenes
  { label: "Dragon",    icon: "\uD83D\uDC09", prompt: "dragon breathing fire",     type: "anim"  },
  { label: "Ocean",     icon: "\uD83C\uDF0A", prompt: "ocean waves rolling",       type: "anim"  },
  { label: "Sunset",    icon: "\uD83C\uDF05", prompt: "sunset landscape",          type: "image" },
  { label: "Galaxy",    icon: "\uD83C\uDF0C", prompt: "space galaxy",              type: "image" },
  { label: "Snow",      icon: "\u2744\uFE0F",  prompt: "snowy winter scene",        type: "anim"  },
  { label: "Rainbow",   icon: "\uD83C\uDF08", prompt: "rainbow shimmer",           type: "anim"  },
  { label: "City",      icon: "\uD83C\uDF03", prompt: "cityscape night skyline",   type: "image" },
  { label: "Rain",      icon: "\uD83C\uDF27\uFE0F", prompt: "rain falling city",  type: "anim"  },
];

const WS_RECONNECT_DELAYS = [1000, 2000, 4000, 8000, 15000];

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
  const [deviceBase, setDeviceBase] = useState("http://led64x32.local");
  const [renderBase, setRenderBase] = useState("http://localhost:8787");
  const [status, setStatus] = useState<DeviceStatus | null>(null);
  const [mode, setMode] = useState<ModeId>("clock_fun");
  const [brightness, setBrightness] = useState(160);
  const [gammaEnabled, setGammaEnabled] = useState(true);

  const [prompt, setPrompt] = useState("charmander breathing fire");
  const [seed, setSeed] = useState(1234);

  const [frame, setFrame] = useState<Uint16Array | null>(null);
  const [animFrames, setAnimFrames] = useState<Uint16Array[]>([]);
  const [animFps, setAnimFps] = useState(12);
  const [previewIdx, setPreviewIdx] = useState(0);

  const [loading, setLoading] = useState<string | null>(null);
  const [wsConnected, setWsConnected] = useState(false);
  const [settingsOpen, setSettingsOpen] = useState(false);
  const [playing, setPlaying] = useState(false);

  const [weatherLocation, setWeatherLocation] = useState("Miami, FL");

  // Effect parameters
  const [rainbowSpeed, setRainbowSpeed] = useState(3);
  const [rainbowScale, setRainbowScale] = useState(8);
  const [rainbowStyle, setRainbowStyle] = useState(0);
  const [starSpeed, setStarSpeed] = useState(3);
  const [starDensity, setStarDensity] = useState(40);
  const [starWarp, setStarWarp] = useState(false);
  const [scrollText, setScrollText] = useState("GODDARD DISPLAY");
  const [scrollSpeed, setScrollSpeed] = useState(5);
  const [scrollRainbow, setScrollRainbow] = useState(true);

  const wsRef = useRef<WebSocket | null>(null);
  const eventsWsRef = useRef<WebSocket | null>(null);
  const frameIdRef = useRef(0);
  const playTimerRef = useRef<ReturnType<typeof setInterval> | null>(null);
  const playStopTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const wsRetryRef = useRef(0);
  const eventsRetryRef = useRef(0);
  const wsTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const eventsTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const mountedRef = useRef(true);
  const brightnessRef = useRef(brightness);

  const { toasts, addToast, removeToast } = useToast();

  useEffect(() => { brightnessRef.current = brightness; }, [brightness]);

  const [debouncedDeviceBase, setDebouncedDeviceBase] = useState(deviceBase);
  useEffect(() => {
    const t = setTimeout(() => setDebouncedDeviceBase(deviceBase), 500);
    return () => clearTimeout(t);
  }, [deviceBase]);

  const frameWsUrl = useMemo(() => {
    try {
      const u = new URL(debouncedDeviceBase);
      const proto = u.protocol === "https:" ? "wss:" : "ws:";
      return `${proto}//${u.host}/ws/frame`;
    } catch {
      return "";
    }
  }, [debouncedDeviceBase]);

  const eventsWsUrl = useMemo(() => {
    try {
      const u = new URL(debouncedDeviceBase);
      const proto = u.protocol === "https:" ? "wss:" : "ws:";
      return `${proto}//${u.host}/ws/events`;
    } catch {
      return "";
    }
  }, [debouncedDeviceBase]);

  const refreshStatus = useCallback(async () => {
    try {
      const s = await getJson(`${deviceBase}/api/status`) as DeviceStatus;
      setStatus(s);
      setBrightness(s.brightness);
      setMode(s.mode);
      setGammaEnabled(s.gamma);
    } catch {
      setStatus(null);
    }
  }, [deviceBase]);

  const connectFrameWs = useCallback(() => {
    if (!frameWsUrl || !mountedRef.current) return;
    if (wsTimerRef.current) { clearTimeout(wsTimerRef.current); wsTimerRef.current = null; }
    if (wsRef.current) { wsRef.current.close(); wsRef.current = null; }
    try {
      const ws = new WebSocket(frameWsUrl);
      ws.binaryType = "arraybuffer";
      ws.onopen = () => { setWsConnected(true); wsRetryRef.current = 0; };
      ws.onclose = () => {
        setWsConnected(false);
        if (!mountedRef.current) return;
        const delay = WS_RECONNECT_DELAYS[Math.min(wsRetryRef.current, WS_RECONNECT_DELAYS.length - 1)];
        wsRetryRef.current++;
        wsTimerRef.current = setTimeout(connectFrameWs, delay);
      };
      ws.onerror = () => {};
      wsRef.current = ws;
    } catch {
      setWsConnected(false);
    }
  }, [frameWsUrl]);

  const connectEventsWs = useCallback(() => {
    if (!eventsWsUrl || !mountedRef.current) return;
    if (eventsTimerRef.current) { clearTimeout(eventsTimerRef.current); eventsTimerRef.current = null; }
    if (eventsWsRef.current) { eventsWsRef.current.close(); eventsWsRef.current = null; }
    try {
      const ws = new WebSocket(eventsWsUrl);
      ws.onopen = () => { eventsRetryRef.current = 0; };
      ws.onclose = () => {
        setStatus(null);
        if (!mountedRef.current) return;
        const delay = WS_RECONNECT_DELAYS[Math.min(eventsRetryRef.current, WS_RECONNECT_DELAYS.length - 1)];
        eventsRetryRef.current++;
        eventsTimerRef.current = setTimeout(connectEventsWs, delay);
      };
      ws.onerror = () => {};
      ws.onmessage = (ev) => {
        try {
          const data = JSON.parse(ev.data);
          if (data.event === "telemetry" || data.event === "connect") {
            setStatus((prev) => {
              if (!prev) return prev;
              return { ...prev, ...data };
            });
            if (data.mode) setMode(data.mode);
          }
        } catch {}
      };
      eventsWsRef.current = ws;
    } catch {}
  }, [eventsWsUrl]);

  // --- Actions ---

  async function setDeviceMode(next: ModeId) {
    try {
      await postJson(`${deviceBase}/api/mode`, { mode: next, params: {} });
      setMode(next);
      addToast(`Switched to ${MODE_LABELS[next] || next}`, "success");
      await refreshStatus();
    } catch (e: unknown) {
      addToast(`Mode switch failed: ${e instanceof Error ? e.message : "unknown error"}`, "error");
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

  async function toggleGamma() {
    const next = !gammaEnabled;
    try {
      await postJson(`${deviceBase}/api/gamma`, { enabled: next });
      setGammaEnabled(next);
      addToast(`Gamma ${next ? "enabled" : "disabled"}`, "success");
    } catch {
      addToast("Gamma toggle failed", "error");
    }
  }

  async function saveSettingsToDevice() {
    try {
      await postJson(`${deviceBase}/api/save`, {});
      addToast("Settings saved to flash", "success");
    } catch {
      addToast("Save failed", "error");
    }
  }

  async function sendEffectParams(params: Record<string, unknown>) {
    try {
      await postJson(`${deviceBase}/api/params`, { params });
    } catch {
      addToast("Parameter update failed", "error");
    }
  }

  async function generateImage(overridePrompt?: string) {
    const p = overridePrompt ?? prompt;
    setLoading("image");
    try {
      const res = await postJson(`${renderBase}/render/image`, { prompt: p, seed, style: "pixel_art" }) as { rgb565_b64: string };
      const u16 = decodeB64ToU16LE(res.rgb565_b64);
      setFrame(u16);
      setAnimFrames([]);
      setPreviewIdx(0);
      addToast("Image generated", "success");
    } catch (e: unknown) {
      addToast(`Generation failed: ${e instanceof Error ? e.message : "unknown error"}`, "error");
    } finally {
      setLoading(null);
    }
  }

  async function generateAnim(overridePrompt?: string) {
    const p = overridePrompt ?? prompt;
    setLoading("anim");
    try {
      const res = await postJson(`${renderBase}/render/anim`, {
        prompt: p, seed, frames: 24, fps: animFps, style: "pixel_anim",
      }) as { frames_b64: string[] };
      const decoded: Uint16Array[] = res.frames_b64.map((b64: string) => decodeB64ToU16LE(b64));
      setAnimFrames(decoded);
      setFrame(decoded[0] ?? null);
      setPreviewIdx(0);
      addToast(`Animation generated (${decoded.length} frames)`, "success");
    } catch (e: unknown) {
      addToast(`Animation failed: ${e instanceof Error ? e.message : "unknown error"}`, "error");
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
    ws.send(makeFramePacketRGB565(u16, frameIdRef.current++));
  }

  function stopPlayback() {
    if (playTimerRef.current) { clearInterval(playTimerRef.current); playTimerRef.current = null; }
    if (playStopTimerRef.current) { clearTimeout(playStopTimerRef.current); playStopTimerRef.current = null; }
    setPlaying(false);
  }

  async function playAnimOnDevice() {
    if (playTimerRef.current) {
      stopPlayback();
      addToast("Playback stopped", "info");
      return;
    }
    await setDeviceMode("anim_player");
    const ws = wsRef.current;
    if (!ws || ws.readyState !== WebSocket.OPEN) {
      addToast("WebSocket not connected", "error");
      return;
    }
    const frames = animFrames.length ? animFrames : (frame ? [frame] : []);
    if (!frames.length) { addToast("No frames to play", "error"); return; }

    let i = 0;
    const interval = Math.max(1, Math.floor(1000 / animFps));
    const totalDuration = Math.min(frames.length * interval * 5, 30000);

    addToast(`Streaming ${frames.length} frames at ${animFps} FPS`, "info");
    setPlaying(true);

    playTimerRef.current = setInterval(() => {
      const curWs = wsRef.current;
      if (!curWs || curWs.readyState !== WebSocket.OPEN) { stopPlayback(); return; }
      try {
        curWs.send(makeFramePacketRGB565(frames[i], frameIdRef.current++));
        setPreviewIdx(i);
        setFrame(frames[i]);
        i = (i + 1) % frames.length;
      } catch { stopPlayback(); }
    }, interval);

    playStopTimerRef.current = setTimeout(() => {
      if (playTimerRef.current) { stopPlayback(); addToast("Playback finished", "info"); }
    }, totalDuration);
  }

  async function pushWeather() {
    setLoading("weather");
    try {
      const loc = weatherLocation.trim() || "Miami,FL";
      const w = await getJson(`${renderBase}/weather?location=${encodeURIComponent(loc)}&units=imperial`) as Record<string, any>;
      if (!w.ok) throw new Error("Weather fetch failed");
      await setDeviceMode("weather_fun");
      await postJson(`${deviceBase}/api/params`, { params: { tempF: w.current.temp, condition: w.current.condition, variant: 1 } });
      addToast(`${Math.round(w.current.temp)}\u00B0F, ${w.current.condition} in ${w.location?.name || loc}`, "success");
    } catch (e: unknown) {
      addToast(`Weather failed: ${e instanceof Error ? e.message : "unknown error"}`, "error");
    } finally {
      setLoading(null);
    }
  }

  async function sendClockStyle(style: number, blink: boolean) {
    try {
      await setDeviceMode("clock_fun");
      await postJson(`${deviceBase}/api/params`, { params: { style, blink } });
    } catch (e: unknown) {
      addToast(`Failed: ${e instanceof Error ? e.message : "unknown error"}`, "error");
    }
  }

  function randomizeSeed() {
    setSeed(Math.floor(Math.random() * 999999));
  }

  // --- Keyboard shortcuts ---
  useEffect(() => {
    function handleKey(e: KeyboardEvent) {
      const tag = (e.target as HTMLElement).tagName;
      if (tag === "INPUT" || tag === "TEXTAREA" || tag === "SELECT") return;

      if (e.key === "g" && !e.metaKey && !e.ctrlKey) { e.preventDefault(); generateImage(); }
      else if (e.key === "a" && !e.metaKey && !e.ctrlKey) { e.preventDefault(); generateAnim(); }
      else if (e.key === "r" && !e.metaKey && !e.ctrlKey) { e.preventDefault(); randomizeSeed(); }
      else if (e.key === "p" && !e.metaKey && !e.ctrlKey) { e.preventDefault(); playAnimOnDevice(); }
      else if (e.key === "s" && (e.metaKey || e.ctrlKey)) { e.preventDefault(); saveSettingsToDevice(); }
    }
    window.addEventListener("keydown", handleKey);
    return () => window.removeEventListener("keydown", handleKey);
  });

  // --- Lifecycle ---
  useEffect(() => { refreshStatus(); }, [refreshStatus]);

  useEffect(() => {
    mountedRef.current = true;
    connectFrameWs();
    connectEventsWs();
    return () => {
      mountedRef.current = false;
      if (wsTimerRef.current) clearTimeout(wsTimerRef.current);
      if (eventsTimerRef.current) clearTimeout(eventsTimerRef.current);
      if (wsRef.current) wsRef.current.close();
      if (eventsWsRef.current) eventsWsRef.current.close();
    };
  }, [connectFrameWs, connectEventsWs]);

  useEffect(() => {
    return () => {
      if (playTimerRef.current) clearInterval(playTimerRef.current);
      if (playStopTimerRef.current) clearTimeout(playStopTimerRef.current);
    };
  }, []);

  const isConnected = status !== null;

  // --- Mode-specific parameter panels ---
  function renderEffectControls() {
    switch (mode) {
      case "rainbow":
        return (
          <div className="effect-controls">
            <div className="label">Rainbow Parameters</div>
            <div className="param-row">
              <span className="label">Speed</span>
              <input type="range" className="param-slider" min={1} max={20} value={rainbowSpeed}
                onChange={(e) => setRainbowSpeed(parseInt(e.target.value, 10))}
                onMouseUp={() => sendEffectParams({ speed: rainbowSpeed, scale: rainbowScale, style: rainbowStyle })}
                onTouchEnd={() => sendEffectParams({ speed: rainbowSpeed, scale: rainbowScale, style: rainbowStyle })}
              />
              <span className="param-value">{rainbowSpeed}</span>
            </div>
            <div className="param-row">
              <span className="label">Scale</span>
              <input type="range" className="param-slider" min={1} max={32} value={rainbowScale}
                onChange={(e) => setRainbowScale(parseInt(e.target.value, 10))}
                onMouseUp={() => sendEffectParams({ speed: rainbowSpeed, scale: rainbowScale, style: rainbowStyle })}
                onTouchEnd={() => sendEffectParams({ speed: rainbowSpeed, scale: rainbowScale, style: rainbowStyle })}
              />
              <span className="param-value">{rainbowScale}</span>
            </div>
            <div className="row gap-sm">
              {["Diagonal", "Radial", "Wave"].map((label, i) => (
                <button key={i} className={`btn btn-sm ${rainbowStyle === i ? "btn-primary" : ""}`}
                  onClick={() => { setRainbowStyle(i); sendEffectParams({ speed: rainbowSpeed, scale: rainbowScale, style: i }); }}>
                  {label}
                </button>
              ))}
            </div>
          </div>
        );
      case "starfield":
        return (
          <div className="effect-controls">
            <div className="label">Starfield Parameters</div>
            <div className="param-row">
              <span className="label">Speed</span>
              <input type="range" className="param-slider" min={1} max={10} value={starSpeed}
                onChange={(e) => setStarSpeed(parseInt(e.target.value, 10))}
                onMouseUp={() => sendEffectParams({ speed: starSpeed, density: starDensity, warp: starWarp })}
                onTouchEnd={() => sendEffectParams({ speed: starSpeed, density: starDensity, warp: starWarp })}
              />
              <span className="param-value">{starSpeed}</span>
            </div>
            <div className="param-row">
              <span className="label">Density</span>
              <input type="range" className="param-slider" min={10} max={80} value={starDensity}
                onChange={(e) => setStarDensity(parseInt(e.target.value, 10))}
                onMouseUp={() => sendEffectParams({ speed: starSpeed, density: starDensity, warp: starWarp })}
                onTouchEnd={() => sendEffectParams({ speed: starSpeed, density: starDensity, warp: starWarp })}
              />
              <span className="param-value">{starDensity}</span>
            </div>
            <div className="toggle-row">
              <span className="toggle-label">Warp Mode</span>
              <input type="checkbox" className="toggle" checked={starWarp}
                onChange={() => { const next = !starWarp; setStarWarp(next); sendEffectParams({ speed: starSpeed, density: starDensity, warp: next }); }}
              />
            </div>
          </div>
        );
      case "text_scroll":
        return (
          <div className="effect-controls">
            <div className="label">Scroller Parameters</div>
            <div className="scroll-input-row">
              <div className="field">
                <input type="text" value={scrollText} maxLength={256}
                  onChange={(e) => setScrollText(e.target.value)}
                  onKeyDown={(e) => { if (e.key === "Enter") sendEffectParams({ text: scrollText, speed: scrollSpeed, rainbow: scrollRainbow }); }}
                  placeholder="Enter scroll text..."
                />
              </div>
              <button className="btn btn-sm" onClick={() => sendEffectParams({ text: scrollText, speed: scrollSpeed, rainbow: scrollRainbow })}>
                Set
              </button>
            </div>
            <div className="param-row">
              <span className="label">Speed</span>
              <input type="range" className="param-slider" min={1} max={20} value={scrollSpeed}
                onChange={(e) => setScrollSpeed(parseInt(e.target.value, 10))}
                onMouseUp={() => sendEffectParams({ text: scrollText, speed: scrollSpeed, rainbow: scrollRainbow })}
                onTouchEnd={() => sendEffectParams({ text: scrollText, speed: scrollSpeed, rainbow: scrollRainbow })}
              />
              <span className="param-value">{scrollSpeed}</span>
            </div>
            <div className="toggle-row">
              <span className="toggle-label">Rainbow Colors</span>
              <input type="checkbox" className="toggle" checked={scrollRainbow}
                onChange={() => { const next = !scrollRainbow; setScrollRainbow(next); sendEffectParams({ text: scrollText, speed: scrollSpeed, rainbow: next }); }}
              />
            </div>
          </div>
        );
      default:
        return null;
    }
  }

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
          {status?.firmware && <span className="fw-badge">v{status.firmware}</span>}
          <span className="status-pill" data-status={isConnected ? "connected" : "disconnected"} role="status">
            <span className="status-dot" />
            {isConnected ? (MODE_LABELS[mode] || mode) : "Offline"}
          </span>
          {wsConnected && (
            <span className="status-pill" data-status="connected" role="status">
              <span className="status-dot" />
              WS
            </span>
          )}
          <button className="btn btn-sm btn-ghost" onClick={() => setSettingsOpen(!settingsOpen)} aria-expanded={settingsOpen}>
            {settingsOpen ? "Close" : "Settings"}
          </button>
        </div>
      </header>

      {settingsOpen && (
        <div style={{ padding: "var(--space-lg) var(--space-xl)", maxWidth: 1400, margin: "0 auto" }}>
          <div className="card col gap-lg">
            <div className="section-header">
              <span className="section-title">Connection Settings</span>
              <div className="row gap-sm">
                <button className="btn btn-sm" onClick={() => {
                  wsRetryRef.current = 0;
                  eventsRetryRef.current = 0;
                  refreshStatus();
                  connectFrameWs();
                  connectEventsWs();
                  addToast("Reconnecting...", "info");
                }}>
                  Reconnect
                </button>
                <button className="btn btn-sm btn-primary" onClick={saveSettingsToDevice}>
                  Save to Flash
                </button>
              </div>
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
        <div className="col gap-xl">

          <div className="stat-grid">
            <div className="stat-card" data-type="brightness">
              <div className="stat-value">{status?.brightness ?? "--"}</div>
              <div className="stat-label">Brightness</div>
            </div>
            <div className="stat-card" data-type="heap">
              <div className="stat-value">{status?.heapFree ? formatHeap(status.heapFree) : "--"}</div>
              <div className="stat-label">Free Heap</div>
            </div>
            <div className="stat-card" data-type="uptime">
              <div className="stat-value">{status?.uptimeMs ? formatUptime(status.uptimeMs) : "--"}</div>
              <div className="stat-label">Uptime</div>
            </div>
            <div className="stat-card" data-type="gamma">
              <div className="stat-value">{gammaEnabled ? "2.2" : "Off"}</div>
              <div className="stat-label">Gamma</div>
            </div>
          </div>

          <div className="card col gap-lg">
            <div className="section-header">
              <span className="section-title">Display Mode</span>
            </div>
            <div className="mode-tabs" role="tablist">
              {(Object.keys(MODE_LABELS) as ModeId[]).map((m) => (
                <button key={m} role="tab" aria-selected={mode === m} className={`mode-tab ${mode === m ? "active" : ""}`} onClick={() => setDeviceMode(m)}>
                  <span style={{ marginRight: 4 }}>{MODE_ICONS[m]}</span>
                  {MODE_LABELS[m]}
                </button>
              ))}
            </div>

            {renderEffectControls()}

            <div className="section-divider" />
            <div className="field">
              <div className="label">Brightness</div>
              <div className="brightness-display">
                <span className="brightness-value">{brightness}</span>
                <div className="brightness-slider-track">
                  <input type="range" min={0} max={255} value={brightness} aria-label="Brightness"
                    onChange={(e) => setBrightness(parseInt(e.target.value, 10))}
                    onMouseUp={() => setDeviceBrightness(brightnessRef.current)}
                    onTouchEnd={() => setDeviceBrightness(brightnessRef.current)}
                  />
                </div>
              </div>
            </div>
            <div className="toggle-row">
              <span className="toggle-label">Gamma Correction (2.2)</span>
              <input type="checkbox" className="toggle" checked={gammaEnabled} onChange={toggleGamma} aria-label="Toggle gamma correction" />
            </div>
          </div>

          <div className="card col gap-lg">
            <div className="section-header">
              <div>
                <span className="section-title">Pixel Art Studio</span>
                <div className="section-subtitle">Describe anything — characters, food, scenes — and see it in pixel art</div>
              </div>
            </div>
            <div className="field">
              <div className="label">Prompt</div>
              <textarea value={prompt} onChange={(e) => setPrompt(e.target.value)} maxLength={200} placeholder="Describe what you want to see..." />
              <div className="muted">{prompt.length}/200 characters</div>
            </div>
            <div className="row gap-md">
              <div className="seed-row" style={{ flex: 1 }}>
                <div className="field">
                  <div className="label">Seed</div>
                  <input type="number" value={seed} onChange={(e) => setSeed(parseInt(e.target.value, 10) || 0)} />
                </div>
                <button className="btn-icon-sm" onClick={randomizeSeed} title="Random seed (R)" aria-label="Randomize seed">
                  {"\uD83C\uDFB2"}
                </button>
              </div>
              <div className="field" style={{ flex: 1 }}>
                <div className="label">Anim FPS</div>
                <input type="number" value={animFps} min={1} max={30} onChange={(e) => setAnimFps(Math.max(1, Math.min(30, parseInt(e.target.value, 10) || 1)))} />
              </div>
            </div>
            <div className="row gap-sm">
              <button className="btn btn-primary" disabled={!!loading} onClick={() => generateImage()}>
                {loading === "image" ? <><span className="spinner" /> Generating...</> : <>Generate Image <span className="kbd">G</span></>}
              </button>
              <button className="btn btn-primary" disabled={!!loading} onClick={() => generateAnim()}>
                {loading === "anim" ? <><span className="spinner" /> Generating...</> : <>Generate Anim <span className="kbd">A</span></>}
              </button>
              <button className="btn" disabled={!frame} onClick={() => { if (frame) { setDeviceMode("anim_player"); sendFrameOnce(frame); } }}>
                Send Frame
              </button>
              <button className="btn" disabled={!animFrames.length && !frame} onClick={playAnimOnDevice}>
                {playing ? "Stop" : <>Play <span className="kbd">P</span></>}
              </button>
            </div>
            <div className="section-divider" />
            <div className="section-title">Presets</div>
            <div className="preset-grid">
              {PRESET_DATA.map((p) => (
                <button key={p.label} className="btn-preset"
                  onClick={() => {
                    setPrompt(p.prompt);
                    if (p.type === "image") generateImage(p.prompt);
                    else generateAnim(p.prompt);
                  }}>
                  <span className="preset-icon">{p.icon}</span>
                  {p.label}
                </button>
              ))}
            </div>
          </div>

          <div className="card col gap-lg">
            <div className="section-header">
              <span className="section-title">Quick Controls</span>
            </div>
            <div className="weather-row">
              <div className="field" style={{ flex: 1 }}>
                <div className="label">Weather Location</div>
                <input type="text" value={weatherLocation} onChange={(e) => setWeatherLocation(e.target.value)} placeholder="City, State"
                  onKeyDown={(e) => { if (e.key === "Enter") pushWeather(); }}
                />
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

        <div className="col gap-xl">
          <div className="card col gap-lg" style={{ position: "sticky", top: 80 }}>
            <div className="section-header">
              <span className="section-title">Live Preview</span>
              <span className="muted">64 x 32 px</span>
            </div>
            <PixelPreview frame={frame} scale={6} />
            {animFrames.length > 0 && (
              <AnimTimeline frames={animFrames} activeIndex={previewIdx} onSelect={(idx) => { setFrame(animFrames[idx]); setPreviewIdx(idx); }} />
            )}
            {animFrames.length > 0 && (
              <div className="muted" style={{ textAlign: "center" }}>
                Frame {previewIdx + 1} / {animFrames.length}
              </div>
            )}
            <div className="muted">
              Shortcuts: <span className="kbd">G</span> image, <span className="kbd">A</span> anim, <span className="kbd">R</span> seed, <span className="kbd">P</span> play
            </div>
          </div>
        </div>
      </div>

      <Toaster toasts={toasts} onRemove={removeToast} />
    </>
  );
}
