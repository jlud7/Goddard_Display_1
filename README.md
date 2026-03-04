# Goddard Display

A full-stack LED matrix control system for 64x32 RGB HUB75 panels, powered by ESP32-S3.

Three integrated components work together: embedded firmware with real-time effects, a Python render service for procedural pixel art generation, and a React dashboard for control and preview.

## Architecture

```
Dashboard (React/TS)  <-->  Render Service (FastAPI)
        |                           |
        |   REST + WebSocket        |  Procedural generation
        +---------------------------+
                    |
             ESP32-S3 Firmware
                    |
            HUB75 LED Matrix (64x32)
```

## Features

### Firmware (ESP32-S3)
- **6 built-in effects**: Clock, Weather, Animation Player, Rainbow, Starfield, Text Scroller
- **Gamma-corrected output** via lookup table for natural LED colors
- **Smooth brightness transitions** (no jarring jumps)
- **Boot animation** with branded sweep and fade
- **Settings persistence** via LittleFS (survives power cycles)
- **Binary WebSocket streaming** for real-time frame ingestion (PANL protocol)
- **REST API** for mode switching, brightness, parameters, and gamma control
- **Live telemetry** via WebSocket events (heap, uptime, mode)
- **Double-buffered rendering** with I2S DMA acceleration

### Dashboard (React + TypeScript + Vite)
- **Apple-quality dark UI** with glassmorphic cards, design tokens, and micro-animations
- **Live device telemetry** via WebSocket (brightness, heap, uptime, mode)
- **Connection status indicators** with animated pulse
- **Toast notification system** for all user actions
- **Animation timeline** with frame-by-frame thumbnail scrubbing
- **Pixel preview** with grid overlay and idle-state crosshair
- **Segmented mode tabs** for quick effect switching
- **Preset gallery** with one-click generation for popular prompts
- **Configurable weather** with location input
- **Responsive layout** for desktop and tablet

### Render Service (FastAPI + Python)
- **11 procedural image generators**: Dragon, Mario, Metroid, Zelda, Pikachu, Neon Grid, Sunset, Galaxy, Fire, Mountain, Abstract
- **6 animation generators**: Dragon fire, Rain, Orbit, Fire, Neon Pulse, Starfield warp
- **Smart image pipeline**: crop, sharpen, downscale, palette quantize, RGB565 encode
- **Live weather** via Open-Meteo (no API key required)
- **Pluggable provider interface** for swapping in AI image models

## Quick Start

### 1. Firmware

Requirements: PlatformIO (VSCode extension or CLI)

1. Open `firmware/` in PlatformIO
2. Edit `src/config.h` with your HUB75 pin mapping and WiFi credentials
3. Build and upload: `pio run --target upload`
4. Device boots with animation, connects to WiFi, and exposes:
   - REST API: `http://led64x32.local/api/*`
   - Frame stream: `ws://led64x32.local/ws/frame`
   - Telemetry: `ws://led64x32.local/ws/events`

### 2. Render Service

Requirements: Python 3.10+

```bash
cd render_service
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --host 0.0.0.0 --port 8787
```

### 3. Dashboard

Requirements: Node 18+

```bash
cd dashboard
npm install
npm run dev
```

Open the dashboard at the printed URL. Connection settings are in the collapsible Settings panel.

## API Reference

### Device REST API

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/status` | GET | Current mode, brightness, gamma, heap, uptime, firmware version |
| `/api/brightness` | POST | `{"value": 0-255}` |
| `/api/mode` | POST | `{"mode": "rainbow", "params": {"speed": 5}}` |
| `/api/params` | POST | `{"params": {...}}` for current effect |
| `/api/gamma` | POST | `{"enabled": true/false}` |
| `/api/save` | POST | Persist current settings to flash |

### Effect Parameters

| Effect | Parameters |
|--------|-----------|
| `clock_fun` | `style` (0-2), `blink` (bool) |
| `weather_fun` | `tempF` (float), `condition` (string), `variant` (0-2) |
| `anim_player` | `fps` (1-30), `loop` (bool), `playing` (bool) |
| `rainbow` | `speed` (1-20), `scale` (1-32), `style` (0-2) |
| `starfield` | `speed` (1-10), `density` (10-80), `warp` (bool) |
| `text_scroll` | `text` (string), `speed` (1-20), `color` (name), `rainbow` (bool), `y` (0-25) |

## Image Provider Interface

The render service uses a pluggable provider system. The default `ProceduralProvider` generates pixel art offline. To use an AI model:

1. Create a new provider in `render_service/app/providers/`
2. Implement the `Provider` interface (`image()` and `animation()`)
3. Update `pipeline.py` to use your provider
