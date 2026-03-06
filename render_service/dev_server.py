from __future__ import annotations

import json
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs, urlparse

from app.catalog import catalog_payload
from app.display import display_agent_prompt, display_catalog_app
from app.pipeline import (
    provider_status,
    render_agent_request,
    render_anim_artifact,
    render_image_artifact,
)
from app.weather import get_weather_fun


HOST = "127.0.0.1"
PORT = 8787


def json_bytes(payload: object) -> bytes:
    return json.dumps(payload).encode("utf-8")


class Handler(BaseHTTPRequestHandler):
    server_version = "GoddardRender/0.2"

    def _send_json(self, payload: object, status: int = HTTPStatus.OK) -> None:
        body = json_bytes(payload)
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(body)

    def _read_json(self) -> dict:
        length = int(self.headers.get("Content-Length", "0"))
        raw = self.rfile.read(length) if length else b"{}"
        return json.loads(raw.decode("utf-8") or "{}")

    def do_OPTIONS(self) -> None:
        self.send_response(HTTPStatus.NO_CONTENT)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET,POST,OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.end_headers()

    def do_GET(self) -> None:
        parsed = urlparse(self.path)
        if parsed.path in ("/", "/health"):
            self._send_json({"ok": True, "version": "dev-server", **provider_status()})
            return
        if parsed.path == "/catalog/apps":
            self._send_json(catalog_payload())
            return
        if parsed.path == "/weather":
            qs = parse_qs(parsed.query)
            location = qs.get("location", ["Miami,FL"])[0]
            units = qs.get("units", ["imperial"])[0]
            self._send_json(get_weather_fun(location=location, units=units))
            return
        if parsed.path == "/prompts":
            catalog = catalog_payload()
            ai_apps = [app for app in catalog["apps"] if app["kind"].startswith("ai_")]
            self._send_json({
                "images": [app["prompt"] for app in ai_apps if app["kind"] == "ai_image"][:8],
                "animations": [app["prompt"] for app in ai_apps if app["kind"] == "ai_anim"][:8],
            })
            return
        self._send_json({"error": "not_found"}, HTTPStatus.NOT_FOUND)

    def do_POST(self) -> None:
        try:
            payload = self._read_json()
            if self.path == "/render/image":
                prompt = str(payload.get("prompt", ""))
                seed = payload.get("seed")
                artifact = render_image_artifact(prompt, seed=seed)
                self._send_json({
                    "w": 64,
                    "h": 32,
                    "format": "rgb565",
                    "provider": artifact.provider,
                    "prompt_rewrite": artifact.prompt_rewrite,
                    "rgb565_b64": artifact.frame_b64,
                })
                return
            if self.path == "/render/anim":
                prompt = str(payload.get("prompt", ""))
                seed = payload.get("seed")
                frames = int(payload.get("frames", 16))
                fps = int(payload.get("fps", 12))
                artifact = render_anim_artifact(prompt, seed=seed, frames=frames, fps=fps)
                self._send_json({
                    "w": 64,
                    "h": 32,
                    "format": "rgb565",
                    "fps": fps,
                    "provider": artifact.provider,
                    "prompt_rewrite": artifact.prompt_rewrite,
                    "frames_b64": artifact.frames_b64,
                })
                return
            if self.path == "/agent/render":
                prompt = str(payload.get("prompt", ""))
                seed = payload.get("seed")
                frames = int(payload.get("frames", 24))
                fps = int(payload.get("fps", 12))
                artifact = render_agent_request(prompt, seed=seed, frames=frames, fps=fps)
                self._send_json({
                    "kind": artifact.kind,
                    "w": 64,
                    "h": 32,
                    "format": "rgb565",
                    "fps": artifact.fps,
                    "provider": artifact.provider,
                    "prompt_rewrite": artifact.prompt_rewrite,
                    "rgb565_b64": artifact.frame_b64,
                    "frames_b64": artifact.frames_b64,
                })
                return
            if self.path == "/display/render":
                result = display_agent_prompt(
                    device_url=str(payload.get("device_url", "")),
                    prompt=str(payload.get("prompt", "")),
                    seed=payload.get("seed"),
                    frames=int(payload.get("frames", 24)),
                    fps=int(payload.get("fps", 12)),
                    stream_seconds=int(payload.get("stream_seconds", 24)),
                )
                result.update({"w": 64, "h": 32, "format": "rgb565"})
                self._send_json(result)
                return
            if self.path == "/display/app":
                result = display_catalog_app(
                    device_url=str(payload.get("device_url", "")),
                    app_id=str(payload.get("app_id", "")),
                    seed=payload.get("seed"),
                    frames=int(payload.get("frames", 24)),
                    fps=int(payload.get("fps", 12)),
                    stream_seconds=int(payload.get("stream_seconds", 24)),
                    weather_location=str(payload.get("weather_location", "Miami, FL")),
                    message=payload.get("message"),
                )
                result.update({"w": 64, "h": 32, "format": "rgb565"})
                self._send_json(result)
                return
            self._send_json({"error": "not_found"}, HTTPStatus.NOT_FOUND)
        except Exception as exc:
            self._send_json({"error": "render_failed", "detail": str(exc)}, HTTPStatus.INTERNAL_SERVER_ERROR)

    def log_message(self, fmt: str, *args) -> None:
        return


if __name__ == "__main__":
    server = ThreadingHTTPServer((HOST, PORT), Handler)
    print(f"Render service listening on http://{HOST}:{PORT}")
    server.serve_forever()
