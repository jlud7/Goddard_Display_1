import React, { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { decodeB64ToU16LE, makeFramePacketRGB565 } from "../lib/frame";
import { DEFAULT_LONG_TIMEOUT, getJson, postBinary, postJson } from "../lib/api";
import { PixelPreview } from "./PixelPreview";
import { AnimTimeline } from "./AnimTimeline";
import { Toaster, useToast } from "./Toast";

type ModeId = "clock_fun" | "weather_fun" | "anim_player" | "rainbow" | "starfield" | "text_scroll";
type CatalogKind = "ai_image" | "ai_anim" | "builtin_mode" | "weather" | "text";

interface DeviceStatus {
  mode: ModeId;
  brightness: number;
  gamma: boolean;
  heapFree: number;
  uptimeMs: number;
  firmware?: string;
  epoch?: number;
  ip?: string;
  wifiRssi?: number;
  timeSynced?: boolean;
}

interface RenderHealth {
  provider?: string;
  mode?: string;
  replicate_ready?: boolean;
  openai_ready?: boolean;
  provider_chain?: string[];
}

interface AgentRenderResult {
  kind?: "image" | "anim" | string;
  provider?: string;
  prompt_rewrite?: string;
  fps?: number;
  rgb565_b64?: string;
  frames_b64?: string[] | null;
  title?: string;
  app_id?: string;
  catalog_kind?: string;
  streaming?: boolean;
}

interface CatalogApp {
  id: string;
  title: string;
  subtitle: string;
  category: string;
  kind: CatalogKind;
  icon: string;
  accent: string;
  prompt?: string | null;
  mode?: string | null;
  params?: Record<string, unknown>;
  tags: string[];
  featured: boolean;
}

interface CatalogCollection {
  id: string;
  title: string;
  subtitle: string;
  description: string;
  app_ids: string[];
  accent: string;
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
  clock_fun: "◔",
  weather_fun: "☁",
  anim_player: "▶",
  rainbow: "◈",
  starfield: "✦",
  text_scroll: "✎",
};

const QUICK_PROMPTS = [
  "display a fire breathing dragon over black cliffs",
  "display heavy rain over a neon alley",
  "display a glowing koi fish beneath a full moon",
  "display a haunted lighthouse in a thunderstorm",
  "display an arcade racer speeding into a synth sunset",
  "display luminous jellyfish drifting through deep water",
];

const WS_RECONNECT_DELAYS = [1000, 2000, 4000, 8000, 15000];
const DEVICE_BASE_STORAGE_KEY = "goddard-device-base";
const RENDER_BASE_STORAGE_KEY = "goddard-render-base";
const WEATHER_STORAGE_KEY = "goddard-weather-location";
const COLLECTION_STORAGE_KEY = "goddard-collection-id";
const CATEGORY_STORAGE_KEY = "goddard-category-filter";
const MESSAGE_STORAGE_KEY = "goddard-message-draft";

function readStoredValue(key: string): string {
  if (typeof window === "undefined") return "";
  return window.localStorage.getItem(key) ?? "";
}

function joinBaseAndPath(base: string, path: string): string {
  const trimmedBase = base.trim();
  if (!trimmedBase) return path;
  return `${trimmedBase.replace(/\/+$/, "")}${path}`;
}

function makeRelativeWsUrl(path: string): string {
  if (typeof window === "undefined") return "";
  const proto = window.location.protocol === "https:" ? "wss:" : "ws:";
  return `${proto}//${window.location.host}${path}`;
}

function isSocketUsable(socket: WebSocket | null, url: string): boolean {
  return !!socket && socket.url === url && (socket.readyState === WebSocket.OPEN || socket.readyState === WebSocket.CONNECTING);
}

function mergeStatus(prev: DeviceStatus | null, patch: Record<string, unknown>): DeviceStatus {
  return {
    mode: (patch.mode as ModeId | undefined) ?? prev?.mode ?? "clock_fun",
    brightness: typeof patch.brightness === "number" ? patch.brightness : prev?.brightness ?? 160,
    gamma: typeof patch.gamma === "boolean" ? patch.gamma : prev?.gamma ?? true,
    heapFree: typeof patch.heapFree === "number" ? patch.heapFree : prev?.heapFree ?? 0,
    uptimeMs: typeof patch.uptimeMs === "number" ? patch.uptimeMs : prev?.uptimeMs ?? 0,
    firmware: typeof patch.firmware === "string" ? patch.firmware : prev?.firmware,
    epoch: typeof patch.epoch === "number" ? patch.epoch : prev?.epoch,
    ip: typeof patch.ip === "string" ? patch.ip : prev?.ip,
    wifiRssi: typeof patch.wifiRssi === "number" ? patch.wifiRssi : prev?.wifiRssi,
    timeSynced: typeof patch.timeSynced === "boolean" ? patch.timeSynced : prev?.timeSynced,
  };
}

function formatDeviceTime(epoch?: number): string {
  if (!epoch) return "--";
  return new Date(epoch * 1000).toLocaleTimeString([], {
    hour: "numeric",
    minute: "2-digit",
    second: "2-digit",
  });
}

function describeSignal(rssi?: number): string {
  if (typeof rssi !== "number" || rssi === 0) return "No signal data";
  if (rssi >= -60) return "Signal is excellent";
  if (rssi >= -67) return "Signal is strong";
  if (rssi >= -75) return "Signal is usable";
  return "Signal is weak";
}

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

function kindLabel(kind: CatalogKind): string {
  switch (kind) {
    case "ai_anim": return "AI Loop";
    case "ai_image": return "AI Still";
    case "builtin_mode": return "Native";
    case "weather": return "Live";
    case "text": return "Message";
    default: return kind;
  }
}

function normalizeCategoryValue(value: string): string {
  return value.trim() || "All";
}

export function App() {
  const [deviceBase, setDeviceBase] = useState(() => readStoredValue(DEVICE_BASE_STORAGE_KEY));
  const [renderBase, setRenderBase] = useState(() => readStoredValue(RENDER_BASE_STORAGE_KEY));
  const [status, setStatus] = useState<DeviceStatus | null>(null);
  const [renderHealth, setRenderHealth] = useState<RenderHealth | null>(null);
  const [catalogApps, setCatalogApps] = useState<CatalogApp[]>([]);
  const [catalogCollections, setCatalogCollections] = useState<CatalogCollection[]>([]);
  const [selectedCollectionId, setSelectedCollectionId] = useState(() => readStoredValue(COLLECTION_STORAGE_KEY) || "desk_cycle");
  const [selectedCategory, setSelectedCategory] = useState(() => normalizeCategoryValue(readStoredValue(CATEGORY_STORAGE_KEY) || "All"));
  const [galleryQuery, setGalleryQuery] = useState("");
  const [selectedAppId, setSelectedAppId] = useState<string | null>(null);

  const [mode, setMode] = useState<ModeId>("clock_fun");
  const [brightness, setBrightness] = useState(160);
  const [gammaEnabled, setGammaEnabled] = useState(true);

  const [prompt, setPrompt] = useState("display a fire breathing dragon over black cliffs");
  const [seed, setSeed] = useState(1234);
  const [messageDraft, setMessageDraft] = useState(() => readStoredValue(MESSAGE_STORAGE_KEY) || "GODDARD IS LIVE");

  const [frame, setFrame] = useState<Uint16Array | null>(null);
  const [animFrames, setAnimFrames] = useState<Uint16Array[]>([]);
  const [animFps, setAnimFps] = useState(12);
  const [previewIdx, setPreviewIdx] = useState(0);
  const [lastPromptRewrite, setLastPromptRewrite] = useState("");
  const [lastProvider, setLastProvider] = useState("");

  const [loading, setLoading] = useState<string | null>(null);
  const [frameWsConnected, setFrameWsConnected] = useState(false);
  const [eventsWsConnected, setEventsWsConnected] = useState(false);
  const [apiReachable, setApiReachable] = useState(false);
  const [settingsOpen, setSettingsOpen] = useState(false);
  const [playing, setPlaying] = useState(false);

  const [weatherLocation, setWeatherLocation] = useState(() => readStoredValue(WEATHER_STORAGE_KEY) || "Miami, FL");

  const [rainbowSpeed, setRainbowSpeed] = useState(3);
  const [rainbowScale, setRainbowScale] = useState(8);
  const [rainbowStyle, setRainbowStyle] = useState(1);
  const [starSpeed, setStarSpeed] = useState(4);
  const [starDensity, setStarDensity] = useState(46);
  const [starWarp, setStarWarp] = useState(true);
  const [scrollText, setScrollText] = useState("GODDARD DISPLAY");
  const [scrollSpeed, setScrollSpeed] = useState(5);
  const [scrollRainbow, setScrollRainbow] = useState(false);

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

  useEffect(() => { window.localStorage.setItem(DEVICE_BASE_STORAGE_KEY, deviceBase); }, [deviceBase]);
  useEffect(() => { window.localStorage.setItem(RENDER_BASE_STORAGE_KEY, renderBase); }, [renderBase]);
  useEffect(() => { window.localStorage.setItem(WEATHER_STORAGE_KEY, weatherLocation); }, [weatherLocation]);
  useEffect(() => { window.localStorage.setItem(COLLECTION_STORAGE_KEY, selectedCollectionId); }, [selectedCollectionId]);
  useEffect(() => { window.localStorage.setItem(CATEGORY_STORAGE_KEY, selectedCategory); }, [selectedCategory]);
  useEffect(() => { window.localStorage.setItem(MESSAGE_STORAGE_KEY, messageDraft); }, [messageDraft]);

  const deviceApiUrl = useCallback((path: string) => joinBaseAndPath(deviceBase, path), [deviceBase]);
  const renderUrl = useCallback((path: string) => joinBaseAndPath(renderBase, path), [renderBase]);
  const resolvedDeviceUrl = useMemo(() => {
    const direct = deviceBase.trim();
    if (direct) return direct.startsWith("http://") || direct.startsWith("https://") ? direct : `http://${direct}`;
    return status?.ip ? `http://${status.ip}` : "";
  }, [deviceBase, status?.ip]);

  const frameWsUrl = useMemo(() => {
    try {
      const base = debouncedDeviceBase.trim();
      if (!base) return makeRelativeWsUrl("/ws/frame");
      const normalizedBase = base.startsWith("http://") || base.startsWith("https://") ? base : `http://${base}`;
      const u = new URL(normalizedBase);
      const proto = u.protocol === "https:" ? "wss:" : "ws:";
      return `${proto}//${u.host}/ws/frame`;
    } catch {
      return "";
    }
  }, [debouncedDeviceBase]);

  const eventsWsUrl = useMemo(() => {
    try {
      const base = debouncedDeviceBase.trim();
      if (!base) return makeRelativeWsUrl("/ws/events");
      const normalizedBase = base.startsWith("http://") || base.startsWith("https://") ? base : `http://${base}`;
      const u = new URL(normalizedBase);
      const proto = u.protocol === "https:" ? "wss:" : "ws:";
      return `${proto}//${u.host}/ws/events`;
    } catch {
      return "";
    }
  }, [debouncedDeviceBase]);

  const applyPreviewFromResult = useCallback((res: AgentRenderResult) => {
    if (res.prompt_rewrite) setLastPromptRewrite(res.prompt_rewrite);
    if (res.provider) setLastProvider(res.provider);
    if (res.fps) setAnimFps(res.fps);

    if (res.frames_b64?.length) {
      const decoded = res.frames_b64.map((b64) => decodeB64ToU16LE(b64));
      setAnimFrames(decoded);
      setFrame(decoded[0] ?? null);
      setPreviewIdx(0);
      return;
    }

    if (res.rgb565_b64) {
      const u16 = decodeB64ToU16LE(res.rgb565_b64);
      setFrame(u16);
      setAnimFrames([]);
      setPreviewIdx(0);
    }
  }, []);

  const refreshStatus = useCallback(async () => {
    try {
      const s = mergeStatus(null, await getJson(deviceApiUrl("/api/status")));
      setStatus(s);
      setBrightness(s.brightness);
      setMode(s.mode);
      setGammaEnabled(s.gamma);
      setApiReachable(true);
      setFrameWsConnected(true);
    } catch {
      setApiReachable(false);
      setFrameWsConnected(false);
    }
  }, [deviceApiUrl]);

  const refreshRenderHealth = useCallback(async () => {
    try {
      const health = await getJson(renderUrl("/health"), { timeoutMs: 15000 }) as unknown as RenderHealth;
      setRenderHealth(health);
    } catch {
      setRenderHealth(null);
    }
  }, [renderUrl]);

  const refreshCatalog = useCallback(async () => {
    try {
      const catalog = await getJson(renderUrl("/catalog/apps"), { timeoutMs: 15000 }) as unknown as { apps: CatalogApp[]; collections: CatalogCollection[] };
      setCatalogApps(catalog.apps ?? []);
      setCatalogCollections(catalog.collections ?? []);
    } catch {
      setCatalogApps([]);
      setCatalogCollections([]);
    }
  }, [renderUrl]);

  const connectFrameWs = useCallback(() => {
    setFrameWsConnected(apiReachable);
  }, [apiReachable]);

  const connectEventsWs = useCallback(() => {
    if (!eventsWsUrl || !mountedRef.current) return;
    if (isSocketUsable(eventsWsRef.current, eventsWsUrl)) return;
    if (eventsTimerRef.current) { clearTimeout(eventsTimerRef.current); eventsTimerRef.current = null; }
    if (eventsWsRef.current) { eventsWsRef.current.close(); eventsWsRef.current = null; }
    try {
      const ws = new WebSocket(eventsWsUrl);
      ws.onopen = () => { setEventsWsConnected(true); eventsRetryRef.current = 0; };
      ws.onclose = () => {
        setEventsWsConnected(false);
        if (!mountedRef.current) return;
        const delay = WS_RECONNECT_DELAYS[Math.min(eventsRetryRef.current, WS_RECONNECT_DELAYS.length - 1)];
        eventsRetryRef.current++;
        eventsTimerRef.current = setTimeout(connectEventsWs, delay);
      };
      ws.onerror = () => {};
      ws.onmessage = (ev) => {
        try {
          const data = JSON.parse(ev.data) as Record<string, unknown>;
          if (data.event === "telemetry" || data.event === "connect") {
            setStatus((prev) => mergeStatus(prev, data));
            if (typeof data.mode === "string") setMode(data.mode as ModeId);
            if (typeof data.brightness === "number") setBrightness(data.brightness);
            if (typeof data.gamma === "boolean") setGammaEnabled(data.gamma);
          }
        } catch {}
      };
      eventsWsRef.current = ws;
    } catch {}
  }, [eventsWsUrl]);

  async function setDeviceMode(next: ModeId) {
    try {
      await postJson(deviceApiUrl("/api/mode"), { mode: next, params: {} });
      setMode(next);
      addToast(`Switched to ${MODE_LABELS[next] || next}`, "success");
      await refreshStatus();
    } catch (e: unknown) {
      addToast(`Mode switch failed: ${e instanceof Error ? e.message : "unknown error"}`, "error");
    }
  }

  async function setDeviceBrightness(val: number) {
    try {
      await postJson(deviceApiUrl("/api/brightness"), { value: val });
      setBrightness(val);
    } catch {
      addToast("Brightness update failed", "error");
    }
  }

  async function toggleGamma() {
    const next = !gammaEnabled;
    try {
      await postJson(deviceApiUrl("/api/gamma"), { enabled: next });
      setGammaEnabled(next);
      addToast(`Gamma ${next ? "enabled" : "disabled"}`, "success");
    } catch {
      addToast("Gamma toggle failed", "error");
    }
  }

  async function saveSettingsToDevice() {
    try {
      await postJson(deviceApiUrl("/api/save"), {});
      addToast("Settings saved to flash", "success");
    } catch {
      addToast("Save failed", "error");
    }
  }

  async function sendEffectParams(params: Record<string, unknown>) {
    try {
      await postJson(deviceApiUrl("/api/params"), { params });
    } catch {
      addToast("Parameter update failed", "error");
    }
  }

  async function generateImage(overridePrompt?: string) {
    const p = overridePrompt ?? prompt;
    setLoading("image");
    try {
      const res = await postJson(
        renderUrl("/render/image"),
        { prompt: p, seed, style: "pixel_art" },
        { timeoutMs: DEFAULT_LONG_TIMEOUT },
      ) as unknown as AgentRenderResult;
      applyPreviewFromResult(res);
      addToast(`Still generated via ${res.provider ?? "render service"}`, "success");
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
      const res = await postJson(
        renderUrl("/render/anim"),
        { prompt: p, seed, frames: 24, fps: animFps, style: "pixel_anim" },
        { timeoutMs: DEFAULT_LONG_TIMEOUT },
      ) as unknown as AgentRenderResult;
      applyPreviewFromResult(res);
      addToast(`Loop generated via ${res.provider ?? "render service"}`, "success");
    } catch (e: unknown) {
      addToast(`Animation failed: ${e instanceof Error ? e.message : "unknown error"}`, "error");
    } finally {
      setLoading(null);
    }
  }

  async function sendFrameOnce(u16: Uint16Array) {
    await postBinary(deviceApiUrl("/api/frame"), makeFramePacketRGB565(u16, frameIdRef.current++));
  }

  async function sendCurrentFrameToDevice(sourceFrame?: Uint16Array | null) {
    const nextFrame = sourceFrame ?? frame;
    if (!nextFrame) return;
    try {
      await postJson(deviceApiUrl("/api/mode"), {
        mode: "anim_player",
        params: { fps: animFps, loop: true, playing: true },
      });
      setMode("anim_player");
      await sendFrameOnce(nextFrame);
      addToast("Frame sent", "success");
    } catch (e: unknown) {
      addToast(`Send failed: ${e instanceof Error ? e.message : "unknown error"}`, "error");
    }
  }

  function stopPlayback() {
    if (playTimerRef.current) { clearInterval(playTimerRef.current); playTimerRef.current = null; }
    if (playStopTimerRef.current) { clearTimeout(playStopTimerRef.current); playStopTimerRef.current = null; }
    setPlaying(false);
  }

  async function playAnimOnDevice(framesOverride?: Uint16Array[]) {
    if (playTimerRef.current) {
      stopPlayback();
      addToast("Playback stopped", "info");
      return;
    }
    const frames = framesOverride?.length ? framesOverride : (animFrames.length ? animFrames : (frame ? [frame] : []));
    if (!frames.length) { addToast("No frames to play", "error"); return; }
    try {
      await postJson(deviceApiUrl("/api/mode"), {
        mode: "anim_player",
        params: { fps: animFps, loop: true, playing: true },
      });
      setMode("anim_player");
    } catch (e: unknown) {
      addToast(`Mode switch failed: ${e instanceof Error ? e.message : "unknown error"}`, "error");
      return;
    }

    let i = 0;
    const interval = Math.max(1, Math.floor(1000 / animFps));
    const totalDuration = Math.min(frames.length * interval * 5, 30000);

    addToast(`Streaming ${frames.length} frames at ${animFps} FPS`, "info");
    setPlaying(true);
    try {
      await sendFrameOnce(frames[0]);
      setPreviewIdx(0);
      setFrame(frames[0]);
      i = frames.length > 1 ? 1 : 0;
    } catch (e: unknown) {
      stopPlayback();
      addToast(`Initial frame send failed: ${e instanceof Error ? e.message : "unknown error"}`, "error");
      return;
    }

    playTimerRef.current = setInterval(() => {
      void (async () => {
        try {
          await sendFrameOnce(frames[i]);
          setPreviewIdx(i);
          setFrame(frames[i]);
          i = (i + 1) % frames.length;
        } catch {
          stopPlayback();
        }
      })();
    }, interval);

    playStopTimerRef.current = setTimeout(() => {
      if (playTimerRef.current) { stopPlayback(); addToast("Playback finished", "info"); }
    }, totalDuration);
  }

  async function askGoddard() {
    const p = prompt.trim();
    if (!p) {
      addToast("Enter a prompt for Goddard first", "error");
      return;
    }
    if (!resolvedDeviceUrl) {
      addToast("Device target is unknown. Connect the panel first.", "error");
      return;
    }
    setLoading("goddard");
    try {
      const res = await postJson(
        renderUrl("/display/render"),
        {
          prompt: p,
          device_url: resolvedDeviceUrl,
          seed,
          frames: 24,
          fps: animFps,
          stream_seconds: 24,
        },
        { timeoutMs: DEFAULT_LONG_TIMEOUT },
      ) as unknown as AgentRenderResult;
      applyPreviewFromResult(res);
      addToast(
        `Goddard displayed ${res.kind === "anim" || res.streaming ? "a loop" : "a scene"} via ${res.provider ?? "render service"}`,
        "success",
      );
    } catch (e: unknown) {
      addToast(`Goddard failed: ${e instanceof Error ? e.message : "unknown error"}`, "error");
    } finally {
      setLoading(null);
    }
  }

  async function displayCatalogApp(app: CatalogApp, message?: string) {
    if (!resolvedDeviceUrl) {
      addToast("Device target is unknown. Connect the panel first.", "error");
      return;
    }
    setLoading(`app:${app.id}`);
    setSelectedAppId(app.id);
    if (app.prompt) setPrompt(app.prompt);
    try {
      const res = await postJson(
        renderUrl("/display/app"),
        {
          app_id: app.id,
          device_url: resolvedDeviceUrl,
          seed,
          frames: 24,
          fps: animFps,
          stream_seconds: 24,
          weather_location: weatherLocation,
          message,
        },
        { timeoutMs: DEFAULT_LONG_TIMEOUT },
      ) as unknown as AgentRenderResult;
      applyPreviewFromResult(res);
      addToast(`${app.title} sent to the display`, "success");
    } catch (e: unknown) {
      addToast(`${app.title} failed: ${e instanceof Error ? e.message : "unknown error"}`, "error");
    } finally {
      setLoading(null);
    }
  }

  async function pushWeather() {
    const weatherApp = catalogApps.find((app) => app.id === "weather_now");
    if (weatherApp) {
      await displayCatalogApp(weatherApp);
      return;
    }
    setLoading("weather");
    try {
      const loc = weatherLocation.trim() || "Miami,FL";
      const w = await getJson(`${renderUrl("/weather")}?location=${encodeURIComponent(loc)}&units=imperial`) as Record<string, any>;
      if (!w.ok) throw new Error("Weather fetch failed");
      await setDeviceMode("weather_fun");
      await postJson(deviceApiUrl("/api/params"), { params: { tempF: w.current.temp, condition: w.current.condition, variant: 1 } });
      addToast(`${Math.round(w.current.temp)}°F, ${w.current.condition} in ${w.location?.name || loc}`, "success");
    } catch (e: unknown) {
      addToast(`Weather failed: ${e instanceof Error ? e.message : "unknown error"}`, "error");
    } finally {
      setLoading(null);
    }
  }

  async function sendClockStyle(style: number, blink: boolean) {
    try {
      await setDeviceMode("clock_fun");
      await postJson(deviceApiUrl("/api/params"), { params: { style, blink } });
    } catch (e: unknown) {
      addToast(`Failed: ${e instanceof Error ? e.message : "unknown error"}`, "error");
    }
  }

  async function syncClockFromBrowser() {
    setLoading("clock");
    try {
      const tz = Intl.DateTimeFormat().resolvedOptions().timeZone;
      const epoch = Math.floor(Date.now() / 1000);
      await postJson(deviceApiUrl("/api/time"), { epoch, timeZone: tz });
      await refreshStatus();
      addToast(`Clock synced to ${tz}`, "success");
    } catch (e: unknown) {
      addToast(`Clock sync failed: ${e instanceof Error ? e.message : "unknown error"}`, "error");
    } finally {
      setLoading(null);
    }
  }

  function randomizeSeed() {
    setSeed(Math.floor(Math.random() * 999999));
  }

  function reconnectDevice() {
    wsRetryRef.current = 0;
    eventsRetryRef.current = 0;
    void refreshStatus();
    connectFrameWs();

    const eventsSocket = eventsWsRef.current;
    if (!eventsSocket || eventsSocket.readyState === WebSocket.CLOSED) {
      connectEventsWs();
    } else if (eventsSocket.readyState === WebSocket.OPEN) {
      eventsSocket.onopen = null;
      eventsSocket.onclose = null;
      eventsSocket.onerror = null;
      eventsSocket.onmessage = null;
      eventsWsRef.current = null;
      setEventsWsConnected(false);
      eventsSocket.close();
      eventsTimerRef.current = setTimeout(connectEventsWs, 75);
    }

    addToast("Reconnecting...", "info");
  }

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

  useEffect(() => {
    void refreshStatus();
    void refreshRenderHealth();
    void refreshCatalog();
  }, [refreshStatus, refreshRenderHealth, refreshCatalog]);

  useEffect(() => {
    const interval = window.setInterval(() => { void refreshStatus(); void refreshRenderHealth(); }, 15000);
    return () => window.clearInterval(interval);
  }, [refreshStatus, refreshRenderHealth]);

  useEffect(() => {
    mountedRef.current = true;
    connectEventsWs();
    return () => {
      mountedRef.current = false;
      if (wsTimerRef.current) clearTimeout(wsTimerRef.current);
      if (eventsTimerRef.current) clearTimeout(eventsTimerRef.current);
      if (eventsWsRef.current?.readyState === WebSocket.OPEN) eventsWsRef.current.close();
    };
  }, [connectFrameWs, connectEventsWs]);

  useEffect(() => {
    return () => {
      if (playTimerRef.current) clearInterval(playTimerRef.current);
      if (playStopTimerRef.current) clearTimeout(playStopTimerRef.current);
    };
  }, []);

  const isConnected = apiReachable || eventsWsConnected;
  const currentModeLabel = MODE_LABELS[mode] || mode;
  const connectionSummary = isConnected
    ? status?.ip
      ? `${status.ip}${typeof status.wifiRssi === "number" ? ` • ${status.wifiRssi} dBm` : ""}`
      : "Device reachable"
    : "Device offline";
  const signalSummary = describeSignal(status?.wifiRssi);
  const transportModeLabel = deviceBase.trim() ? "Direct device link" : "Proxy uplink";
  const renderModeLabel = renderBase.trim() ? "Custom render host" : "Local orchestrator";
  const previewSummary = animFrames.length
    ? `${animFrames.length} frames loaded at ${animFps} FPS`
    : frame
      ? "Single frame ready to send"
      : "No frame prepared";

  const categories = useMemo(() => {
    const values = new Set<string>(["All"]);
    for (const app of catalogApps) values.add(app.category);
    return Array.from(values);
  }, [catalogApps]);

  const selectedCollection = useMemo(
    () => catalogCollections.find((collection) => collection.id === selectedCollectionId) ?? null,
    [catalogCollections, selectedCollectionId],
  );

  const collectionAppIds = useMemo(() => new Set(selectedCollection?.app_ids ?? []), [selectedCollection]);

  const featuredApps = useMemo(
    () => catalogApps.filter((app) => app.featured).slice(0, 8),
    [catalogApps],
  );

  const filteredApps = useMemo(() => {
    const q = galleryQuery.trim().toLowerCase();
    return catalogApps.filter((app) => {
      if (selectedCategory !== "All" && app.category !== selectedCategory) return false;
      if (!q) return true;
      return [app.title, app.subtitle, app.category, app.prompt ?? "", ...app.tags].join(" ").toLowerCase().includes(q);
    });
  }, [catalogApps, galleryQuery, selectedCategory]);

  const collectionApps = useMemo(
    () => catalogApps.filter((app) => collectionAppIds.has(app.id)),
    [catalogApps, collectionAppIds],
  );

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
                  onClick={() => { setRainbowStyle(i); void sendEffectParams({ speed: rainbowSpeed, scale: rainbowScale, style: i }); }}>
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
                onChange={() => { const next = !starWarp; setStarWarp(next); void sendEffectParams({ speed: starSpeed, density: starDensity, warp: next }); }}
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
                  onKeyDown={(e) => { if (e.key === "Enter") void sendEffectParams({ text: scrollText, speed: scrollSpeed, rainbow: scrollRainbow }); }}
                  placeholder="Enter scroll text..."
                />
              </div>
              <button className="btn btn-sm" onClick={() => void sendEffectParams({ text: scrollText, speed: scrollSpeed, rainbow: scrollRainbow })}>
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
                onChange={() => { const next = !scrollRainbow; setScrollRainbow(next); void sendEffectParams({ text: scrollText, speed: scrollSpeed, rainbow: next }); }}
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
            <div className="app-subtitle">App Library for HUB75</div>
          </div>
        </div>
        <div className="header-status">
          {status?.firmware && <span className="fw-badge">v{status.firmware}</span>}
          <span className="status-pill" data-status={isConnected ? "connected" : "disconnected"} role="status">
            <span className="status-dot" />
            {isConnected ? currentModeLabel : "Offline"}
          </span>
          <span className="status-pill" data-status={apiReachable ? "connected" : "disconnected"} role="status" title="REST API">
            <span className="status-dot" />
            API
          </span>
          <span className="status-pill" data-status={renderHealth?.provider ? "connected" : "disconnected"} role="status" title={renderHealth?.provider ?? "Render offline"}>
            <span className="status-dot" />
            Render
          </span>
          {eventsWsConnected && (
            <span className="status-pill" data-status="connected" role="status">
              <span className="status-dot" />
              Telemetry
            </span>
          )}
          <button className="btn btn-sm btn-ghost" onClick={() => setSettingsOpen(!settingsOpen)} aria-expanded={settingsOpen}>
            {settingsOpen ? "Close" : "Settings"}
          </button>
        </div>
      </header>

      <div className="app-shell">
        <section className="hero-panel hero-panel-rich">
          <div className="hero-copy">
            <div className="hero-eyebrow">Scene Deck</div>
            <h1 className="hero-title">A real display app library, not just a prompt box.</h1>
            <p className="hero-body">
              Curated apps, direct AI rendering, and a clean handoff surface for Goddard on the Mac mini. The dashboard now treats the panel like a programmable ambient product.
            </p>
            <div className="hero-note">
              <strong>{transportModeLabel}</strong>
              <span>{renderModeLabel} • {renderHealth?.provider ?? "Render provider unknown"}</span>
            </div>
            <div className="hero-chip-row">
              <span className="hero-chip">
                <span className="hero-chip-label">Apps</span>
                <strong>{catalogApps.length || "--"}</strong>
              </span>
              <span className="hero-chip">
                <span className="hero-chip-label">Collections</span>
                <strong>{catalogCollections.length || "--"}</strong>
              </span>
              <span className="hero-chip">
                <span className="hero-chip-label">Provider</span>
                <strong>{renderHealth?.provider?.split(":")[0] ?? "--"}</strong>
              </span>
            </div>
            <div className="hero-actions">
              <button className="btn btn-primary" onClick={reconnectDevice}>Reconnect Device</button>
              <button className="btn" disabled={!!loading} onClick={syncClockFromBrowser}>
                {loading === "clock" ? <span className="spinner" /> : "Sync Clock"}
              </button>
              <button className="btn" onClick={saveSettingsToDevice}>Save Device State</button>
            </div>
          </div>

          <div className="hero-atlas hero-atlas-rich">
            <div className="atlas-card atlas-card-primary">
              <div className="atlas-label">Live Route</div>
              <div className="atlas-value">{isConnected ? "Online" : "Offline"}</div>
              <div className="atlas-meta">{connectionSummary}</div>
            </div>
            <div className="atlas-grid">
              <div className="atlas-card">
                <div className="atlas-label">Render Engine</div>
                <div className="atlas-value atlas-value-sm">{renderHealth?.provider?.split(":")[0] ?? "--"}</div>
                <div className="atlas-meta">{renderHealth?.provider_chain?.join(" → ") ?? "No provider chain reported"}</div>
              </div>
              <div className="atlas-card">
                <div className="atlas-label">Device Time</div>
                <div className="atlas-value atlas-value-sm">{formatDeviceTime(status?.epoch)}</div>
                <div className="atlas-meta">{status?.timeSynced ? "Synced from browser or network" : "Clock not synced yet"}</div>
              </div>
              <div className="atlas-card">
                <div className="atlas-label">WiFi Health</div>
                <div className="atlas-value atlas-value-sm">{typeof status?.wifiRssi === "number" ? `${status.wifiRssi} dBm` : "--"}</div>
                <div className="atlas-meta">{signalSummary}</div>
              </div>
              <div className="atlas-card">
                <div className="atlas-label">Target Device</div>
                <div className="atlas-value atlas-value-sm">{resolvedDeviceUrl ? "Resolved" : "Missing"}</div>
                <div className="atlas-meta mono-inline">{resolvedDeviceUrl || "Connect first to discover direct IP"}</div>
              </div>
            </div>
          </div>
        </section>

        {settingsOpen && (
          <div className="settings-drawer">
            <div className="card col gap-lg">
              <div className="section-header">
                <div>
                  <span className="section-title">Connection Settings</span>
                  <div className="section-subtitle">Leave device and render URLs blank to use the local development proxies.</div>
                </div>
                <div className="row gap-sm">
                  <button className="btn btn-sm" onClick={reconnectDevice}>Reconnect</button>
                  <button className="btn btn-sm btn-primary" onClick={saveSettingsToDevice}>Save to Flash</button>
                </div>
              </div>
              <div className="row gap-lg">
                <div className="field" style={{ flex: 1 }}>
                  <div className="label">Device URL</div>
                  <input type="text" value={deviceBase} onChange={(e) => setDeviceBase(e.target.value)} placeholder="http://192.168.x.x" />
                </div>
                <div className="field" style={{ flex: 1 }}>
                  <div className="label">Render Service URL</div>
                  <input type="text" value={renderBase} onChange={(e) => setRenderBase(e.target.value)} placeholder="http://127.0.0.1:8787" />
                </div>
              </div>
            </div>
          </div>
        )}

        <section className="collection-rail-section">
          <div className="section-header rail-header">
            <div>
              <span className="section-title">Collections</span>
              <div className="section-subtitle">Tidbyt-style browsing, but with direct Goddard control and AI-backed scenes.</div>
            </div>
          </div>
          <div className="collection-rail">
            {catalogCollections.map((collection) => {
              const active = collection.id === selectedCollectionId;
              return (
                <button
                  key={collection.id}
                  className={`collection-card ${active ? "active" : ""}`}
                  style={{ ["--collection-accent" as string]: collection.accent }}
                  onClick={() => {
                    setSelectedCollectionId(collection.id);
                    setSelectedCategory("All");
                  }}
                >
                  <div className="collection-card-top">
                    <span className="collection-chip">{collection.app_ids.length} apps</span>
                    <span className="collection-arrow">↗</span>
                  </div>
                  <div className="collection-title">{collection.title}</div>
                  <div className="collection-subtitle">{collection.subtitle}</div>
                  <p className="collection-description">{collection.description}</p>
                </button>
              );
            })}
          </div>
        </section>

        <div className="main-grid main-grid-expanded">
          <div className="col gap-xl">
            <div className="stat-grid stat-grid-wide">
              <div className="stat-card" data-type="brightness"><div className="stat-value">{status?.brightness ?? "--"}</div><div className="stat-label">Brightness</div></div>
              <div className="stat-card" data-type="heap"><div className="stat-value">{status ? formatHeap(status.heapFree) : "--"}</div><div className="stat-label">Free Heap</div></div>
              <div className="stat-card" data-type="uptime"><div className="stat-value">{status ? formatUptime(status.uptimeMs) : "--"}</div><div className="stat-label">Uptime</div></div>
              <div className="stat-card" data-type="gamma"><div className="stat-value">{gammaEnabled ? "2.2" : "Off"}</div><div className="stat-label">Gamma</div></div>
              <div className="stat-card" data-type="clock"><div className="stat-value">{formatDeviceTime(status?.epoch)}</div><div className="stat-label">Device Time</div></div>
              <div className="stat-card" data-type="network"><div className="stat-value">{typeof status?.wifiRssi === "number" ? `${status.wifiRssi} dBm` : "--"}</div><div className="stat-label">{signalSummary}</div></div>
            </div>

            <div className="card card-feature col gap-lg">
              <div className="section-header">
                <div>
                  <span className="section-title">Featured Apps</span>
                  <div className="section-subtitle">High-confidence scenes and utilities tuned to read well on a 64x32 wall.</div>
                </div>
              </div>
              <div className="featured-strip">
                {featuredApps.map((app) => (
                  <button
                    key={app.id}
                    className={`featured-app ${selectedAppId === app.id ? "active" : ""}`}
                    style={{ ["--app-accent" as string]: app.accent }}
                    onClick={() => void displayCatalogApp(app, app.id === "message_board" ? messageDraft : undefined)}
                  >
                    <div className="featured-app-icon">{app.icon}</div>
                    <div className="featured-app-copy">
                      <div className="featured-app-topline">
                        <span className="featured-app-title">{app.title}</span>
                        <span className="featured-app-kind">{kindLabel(app.kind)}</span>
                      </div>
                      <div className="featured-app-subtitle">{app.subtitle}</div>
                    </div>
                  </button>
                ))}
              </div>
            </div>

            <div className="card card-feature col gap-lg">
              <div className="section-header">
                <div>
                  <span className="section-title">App Gallery</span>
                  <div className="section-subtitle">Browse utilities, ambient loops, fantasy scenes, and agent-driven display modes.</div>
                </div>
                {selectedCollection && <span className="collection-chip collection-chip-active">{selectedCollection.title}</span>}
              </div>
              <div className="gallery-toolbar">
                <div className="field gallery-search">
                  <div className="label">Search</div>
                  <input type="text" value={galleryQuery} onChange={(e) => setGalleryQuery(e.target.value)} placeholder="Find rain, retro, weather, dragon..." />
                </div>
                <div className="gallery-filters" role="tablist" aria-label="Category filters">
                  {categories.map((category) => (
                    <button
                      key={category}
                      className={`filter-chip ${selectedCategory === category ? "active" : ""}`}
                      onClick={() => setSelectedCategory(category)}
                    >
                      {category}
                    </button>
                  ))}
                </div>
              </div>
              <div className="app-gallery-grid">
                {filteredApps.map((app) => (
                  <article
                    key={app.id}
                    className={`app-card ${selectedAppId === app.id ? "active" : ""} ${collectionAppIds.has(app.id) ? "in-collection" : ""}`}
                    style={{ ["--app-accent" as string]: app.accent }}
                  >
                    <div className="app-card-head">
                      <div className="app-card-icon">{app.icon}</div>
                      <div className="app-card-meta">
                        <span className="app-card-kind">{kindLabel(app.kind)}</span>
                        <span className="app-card-category">{app.category}</span>
                      </div>
                    </div>
                    <div className="app-card-title">{app.title}</div>
                    <p className="app-card-subtitle">{app.subtitle}</p>
                    <div className="tag-row">
                      {app.tags.slice(0, 3).map((tag) => <span key={tag} className="tag-chip">{tag}</span>)}
                    </div>
                    <div className="app-card-actions">
                      <button className="btn btn-sm btn-primary" disabled={!!loading} onClick={() => void displayCatalogApp(app, app.id === "message_board" ? messageDraft : undefined)}>
                        {loading === `app:${app.id}` ? <span className="spinner" /> : "Display"}
                      </button>
                      {app.prompt && <button className="btn btn-sm" onClick={() => setPrompt(app.prompt ?? "")}>Use Prompt</button>}
                    </div>
                  </article>
                ))}
              </div>
            </div>

            <div className="card card-feature col gap-lg">
              <div className="section-header">
                <div>
                  <span className="section-title">Scene Composer</span>
                  <div className="section-subtitle">Direct prompt-to-display flow with preview, curated suggestions, and reusable message mode.</div>
                </div>
              </div>

              <div className="compose-grid">
                <div className="field compose-prompt">
                  <div className="label">Ask Goddard</div>
                  <textarea value={prompt} onChange={(e) => setPrompt(e.target.value)} maxLength={240} placeholder='Try "display a fire breathing dragon over black cliffs"' />
                  <div className="muted">{prompt.length}/240 characters</div>
                </div>
                <div className="compose-side">
                  <div className="row gap-md compose-meta-row">
                    <div className="seed-row" style={{ flex: 1 }}>
                      <div className="field">
                        <div className="label">Seed</div>
                        <input type="number" value={seed} onChange={(e) => setSeed(parseInt(e.target.value, 10) || 0)} />
                      </div>
                      <button className="btn-icon-sm" onClick={randomizeSeed} title="Random seed (R)" aria-label="Randomize seed">🎲</button>
                    </div>
                    <div className="field" style={{ flex: 1 }}>
                      <div className="label">Anim FPS</div>
                      <input type="number" value={animFps} min={1} max={30} onChange={(e) => setAnimFps(Math.max(1, Math.min(30, parseInt(e.target.value, 10) || 1)))} />
                    </div>
                  </div>
                  <div className="field">
                    <div className="label">Message Board Text</div>
                    <input type="text" value={messageDraft} maxLength={256} onChange={(e) => setMessageDraft(e.target.value)} placeholder="Display a status line or note" />
                  </div>
                </div>
              </div>

              <div className="studio-actions studio-actions-rich">
                <button className="btn btn-primary btn-agent" disabled={!!loading} onClick={askGoddard}>
                  {loading === "goddard" ? <><span className="spinner" /> Rendering & Displaying...</> : "Ask Goddard"}
                </button>
                <button className="btn btn-primary" disabled={!!loading} onClick={() => generateImage()}>
                  {loading === "image" ? <><span className="spinner" /> Generating...</> : <>Generate Still <span className="kbd">G</span></>}
                </button>
                <button className="btn btn-primary" disabled={!!loading} onClick={() => generateAnim()}>
                  {loading === "anim" ? <><span className="spinner" /> Generating...</> : <>Generate Loop <span className="kbd">A</span></>}
                </button>
                <button className="btn" disabled={!frame} onClick={() => { void sendCurrentFrameToDevice(); }}>Send Frame</button>
                <button className="btn" disabled={!animFrames.length && !frame} onClick={() => { void playAnimOnDevice(); }}>
                  {playing ? "Stop" : <>Play <span className="kbd">P</span></>}
                </button>
                <button className="btn" disabled={!!loading} onClick={() => {
                  const messageApp = catalogApps.find((app) => app.id === "message_board");
                  if (messageApp) void displayCatalogApp(messageApp, messageDraft);
                }}>
                  Push Message
                </button>
              </div>

              <div className="quick-prompt-row">
                {QUICK_PROMPTS.map((item) => (
                  <button key={item} className="quick-prompt-chip" onClick={() => setPrompt(item)}>{item}</button>
                ))}
              </div>
            </div>

            <div className="card card-feature col gap-lg">
              <div className="section-header">
                <div>
                  <span className="section-title">Agent Handoff</span>
                  <div className="section-subtitle">The Mac mini agent only needs the handoff file and the local render/display endpoints.</div>
                </div>
              </div>
              <div className="handoff-grid">
                <div className="handoff-card">
                  <div className="label">Device Target</div>
                  <div className="handoff-value mono-inline">{resolvedDeviceUrl || "Resolve from /api/status first"}</div>
                </div>
                <div className="handoff-card">
                  <div className="label">Render Endpoint</div>
                  <div className="handoff-value mono-inline">{(renderBase.trim() || window.location.origin).replace(/\/$/, "")}/display/render</div>
                </div>
                <div className="handoff-card">
                  <div className="label">App Endpoint</div>
                  <div className="handoff-value mono-inline">{(renderBase.trim() || window.location.origin).replace(/\/$/, "")}/display/app</div>
                </div>
              </div>
              <div className="muted">Use the handoff file on the Mac mini to tell Goddard when to call these endpoints, which collection to prefer, and how to send custom image requests from Telegram or Messages.</div>
            </div>

            <div className="card card-feature col gap-lg">
              <div className="section-header">
                <div>
                  <span className="section-title">Display Mode</span>
                  <div className="section-subtitle">Switch instantly between firmware-native looks and streamed content.</div>
                </div>
              </div>
              <div className="mode-tabs" role="tablist">
                {(Object.keys(MODE_LABELS) as ModeId[]).map((m) => (
                  <button key={m} role="tab" aria-selected={mode === m} className={`mode-tab ${mode === m ? "active" : ""}`} onClick={() => void setDeviceMode(m)}>
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
                      onMouseUp={() => void setDeviceBrightness(brightnessRef.current)}
                      onTouchEnd={() => void setDeviceBrightness(brightnessRef.current)}
                    />
                  </div>
                </div>
              </div>
              <div className="toggle-row">
                <span className="toggle-label">Gamma Correction (2.2)</span>
                <input type="checkbox" className="toggle" checked={gammaEnabled} onChange={toggleGamma} aria-label="Toggle gamma correction" />
              </div>
            </div>

            <div className="card card-feature col gap-lg">
              <div className="section-header">
                <div>
                  <span className="section-title">Quick Controls</span>
                  <div className="section-subtitle">Live utility controls for weather, clock, and scroller modes.</div>
                </div>
              </div>
              <div className="weather-row">
                <div className="field" style={{ flex: 1 }}>
                  <div className="label">Weather Location</div>
                  <input type="text" value={weatherLocation} onChange={(e) => setWeatherLocation(e.target.value)} placeholder="City, State"
                    onKeyDown={(e) => { if (e.key === "Enter") void pushWeather(); }}
                  />
                </div>
                <button className="btn btn-primary" disabled={!!loading} onClick={() => void pushWeather()} style={{ height: 38 }}>
                  {loading === "weather" ? <span className="spinner" /> : "Push Weather"}
                </button>
              </div>
              <div className="section-divider" />
              <div className="label">Clock Styles</div>
              <div className="row gap-sm">
                <button className="btn" onClick={() => void sendClockStyle(0, true)}>Centered</button>
                <button className="btn" onClick={() => void sendClockStyle(1, true)}>Bottom</button>
                <button className="btn" onClick={() => void sendClockStyle(2, false)}>Glow</button>
                <button className="btn btn-primary" disabled={!!loading} onClick={syncClockFromBrowser}>
                  {loading === "clock" ? <span className="spinner" /> : "Sync Clock"}
                </button>
              </div>
            </div>
          </div>

          <div className="col gap-xl">
            <div className="card preview-card col gap-lg" style={{ position: "sticky", top: 92 }}>
              <div className="section-header">
                <div>
                  <span className="section-title">Live Preview</span>
                  <div className="section-subtitle">Panel-ready output and current collection focus</div>
                </div>
                <span className="muted">64 x 32 px</span>
              </div>
              <div className="preview-stage preview-stage-rich">
                <div className="preview-screen">
                  <PixelPreview frame={frame} scale={6} />
                </div>
              </div>
              <div className="preview-meta preview-meta-rich">
                <div className="preview-meta-card">
                  <span className="preview-meta-label">Scene</span>
                  <strong className="preview-meta-value">{previewSummary}</strong>
                </div>
                <div className="preview-meta-card">
                  <span className="preview-meta-label">Provider</span>
                  <strong className="preview-meta-value">{lastProvider || renderHealth?.provider || "--"}</strong>
                </div>
                <div className="preview-meta-card">
                  <span className="preview-meta-label">Collection</span>
                  <strong className="preview-meta-value">{selectedCollection?.title ?? "Manual"}</strong>
                </div>
              </div>
              {animFrames.length > 0 && (
                <AnimTimeline frames={animFrames} activeIndex={previewIdx} onSelect={(idx) => { setFrame(animFrames[idx]); setPreviewIdx(idx); }} />
              )}
              <div className="preview-caption preview-caption-rich">
                <span>{animFrames.length > 0 ? `Frame ${previewIdx + 1} / ${animFrames.length}` : "Single frame preview"}</span>
                <span>{frameWsConnected ? "Frame uplink ready" : "Frame uplink offline"}</span>
              </div>
              {lastPromptRewrite && (
                <div className="card-inner prompt-readout">
                  <div className="label">Prompt Rewrite</div>
                  <div className="muted">{lastPromptRewrite}</div>
                </div>
              )}
              {selectedCollection && collectionApps.length > 0 && (
                <div className="card-inner collection-mini-list">
                  <div className="label">Selected Collection</div>
                  <div className="mini-app-list">
                    {collectionApps.map((app) => (
                      <button key={app.id} className={`mini-app-pill ${selectedAppId === app.id ? "active" : ""}`} onClick={() => void displayCatalogApp(app, app.id === "message_board" ? messageDraft : undefined)}>
                        <span>{app.icon}</span>
                        {app.title}
                      </button>
                    ))}
                  </div>
                </div>
              )}
              <div className="muted">
                Shortcuts: <span className="kbd">G</span> still, <span className="kbd">A</span> loop, <span className="kbd">R</span> seed, <span className="kbd">P</span> play
              </div>
            </div>
          </div>
        </div>
      </div>

      <Toaster toasts={toasts} onRemove={removeToast} />
    </>
  );
}
