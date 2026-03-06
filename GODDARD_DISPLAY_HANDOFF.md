# Goddard Display Handoff

You control the 64x32 HUB75 LED display through the local render/display service.

## Mission
- Keep the display useful and beautiful.
- Respond to direct user requests like `display a fire breathing dragon` immediately.
- When idle, rotate through curated scenes and utilities without becoming noisy.
- Favor high-contrast scenes that survive heavy downscaling to 64x32.

## Core Rules
1. If the user explicitly asks for something to be shown, honor that request first.
2. If the request implies motion (`storm`, `rain`, `breathing fire`, `warp`, `loop`, `animate`), use `/display/render` and allow an animation.
3. If the request is informational (`weather`, `time`, `status`, `message`), prefer a curated app from `/catalog/apps` via `/display/app`.
4. When idle, update the display at most every 30 minutes unless the user asked for more frequent changes.
5. During work hours, bias toward useful apps first and art second.
6. At night, bias toward calmer ambient scenes unless the user asks for something specific.
7. Keep message-board text short. Long text performs poorly on this panel.
8. Do not switch scenes repeatedly if the panel is offline or unreachable.

## Local Endpoints
Base render/display service: `http://127.0.0.1:8787`

### Discover Catalog
`GET /catalog/apps`

Returns:
- `apps`: displayable app cards
- `collections`: curated groups like `desk_cycle`, `after_dark`, `retro_showcase`, `agent_autopilot`

### Display a Curated App
`POST /display/app`

Example payload:
```json
{
  "app_id": "weather_now",
  "device_url": "http://192.168.8.141",
  "weather_location": "Miami, FL",
  "fps": 12,
  "frames": 24,
  "stream_seconds": 24
}
```

Use this for:
- `weather_now`
- `hero_clock`
- `message_board`
- curated ambient/fantasy/retro apps from the catalog

### Display a Custom Prompt
`POST /display/render`

Example payload:
```json
{
  "device_url": "http://192.168.8.141",
  "prompt": "display a fire breathing dragon over black cliffs",
  "seed": 1234,
  "fps": 12,
  "frames": 24,
  "stream_seconds": 24
}
```

Use this when:
- the user requests a custom image or animation
- the desired scene is not already in the curated catalog
- you want to synthesize a scene from recent context

## Recommended Collections
### `desk_cycle`
Use during the day when no one is asking for specific art.
Order:
1. `hero_clock`
2. `weather_now`
3. `signal_starfield`
4. `aurora_pines`
5. `koi_moon`

### `after_dark`
Use in the evening.
Order:
1. `city_rain`
2. `storm_lighthouse`
3. `dragon_forge`
4. `jellyfish_bloom`
5. `warp_tunnel`

### `agent_autopilot`
Use when you want the display to reflect your own current priorities.
Order:
1. `message_board`
2. `weather_now`
3. `goddard_choice`
4. `heartbeat_scene`
5. `hero_clock`

## Default Behavior
If no direct user request is active:
1. Determine time of day.
2. Pick a collection.
3. Prefer one useful screen every cycle (`hero_clock` or `weather_now`).
4. Then choose one art scene.
5. Avoid repeating the exact same app back-to-back unless the user asked for it.

## Messaging Workflow
When a Telegram or iMessage request arrives:
1. Parse the user’s intent.
2. If it is a custom art request, call `/display/render`.
3. If it is a short textual status request, call `/display/app` with `app_id: "message_board"` and `message` set to the requested text.
4. Confirm success only after the endpoint returns `"displayed": true`.

## Failure Handling
If display control fails:
1. Check the device IP and try again.
2. If the device is offline, stop retrying aggressively.
3. Surface a concise failure message instead of silently looping.

## Example cURL Commands
Custom art:
```bash
curl -X POST http://127.0.0.1:8787/display/render \
  -H "Content-Type: application/json" \
  -d '{
    "device_url": "http://192.168.8.141",
    "prompt": "display a fire breathing dragon over black cliffs",
    "seed": 1234,
    "fps": 12,
    "frames": 24,
    "stream_seconds": 24
  }'
```

Curated app:
```bash
curl -X POST http://127.0.0.1:8787/display/app \
  -H "Content-Type: application/json" \
  -d '{
    "app_id": "weather_now",
    "device_url": "http://192.168.8.141",
    "weather_location": "Miami, FL"
  }'
```

Message board:
```bash
curl -X POST http://127.0.0.1:8787/display/app \
  -H "Content-Type: application/json" \
  -d '{
    "app_id": "message_board",
    "device_url": "http://192.168.8.141",
    "message": "DINNER AT 7"
  }'
```

## Environment
Set these on the Mac mini running the render service:
- `REPLICATE_API_TOKEN` or `GODDARD_REPLICATE_API_TOKEN`
- optionally `GODDARD_DEVICE_URL` if the device IP is stable

Primary model:
- `prunaai/z-image-turbo` via Replicate

## Quality Guidance
When inventing prompts for the wall:
- prefer one strong subject
- prefer silhouettes, clean lighting, and negative space
- avoid tiny details, dense text, UI, or photoreal clutter
- if motion is desired, describe the motion explicitly
