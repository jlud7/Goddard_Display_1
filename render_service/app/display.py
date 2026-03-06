from __future__ import annotations

import base64
import itertools
import struct
import threading
import time
from typing import Any

import requests

from .catalog import get_app
from .pipeline import RenderArtifact, render_agent_request
from .weather import get_weather_fun


_FRAME_COUNTER = itertools.count(1)
_STREAMS: dict[str, threading.Event] = {}
_STREAM_LOCK = threading.Lock()


def _normalize_device_url(device_url: str) -> str:
    trimmed = device_url.strip()
    if not trimmed:
        raise ValueError("device_url_required")
    if not trimmed.startswith(("http://", "https://")):
        trimmed = f"http://{trimmed}"
    return trimmed.rstrip("/")


def _post_json(url: str, body: dict[str, Any], timeout: int = 10) -> requests.Response:
    response = requests.post(url, json=body, timeout=timeout)
    response.raise_for_status()
    return response


def _post_binary(url: str, body: bytes, timeout: int = 10) -> requests.Response:
    response = requests.post(url, data=body, headers={"Content-Type": "application/octet-stream"}, timeout=timeout)
    response.raise_for_status()
    return response


def _frame_packet(frame_b64: str, frame_id: int) -> bytes:
    pixels = base64.b64decode(frame_b64)
    header = struct.pack("<IHHHHHH", 0x50414E4C, 64, 32, frame_id & 0xFFFF, 0, len(pixels), 0)
    return header + pixels


def _set_mode(device_url: str, mode: str, params: dict[str, Any] | None = None) -> None:
    _post_json(f"{device_url}/api/mode", {"mode": mode, "params": params or {}}, timeout=10)


def _set_params(device_url: str, params: dict[str, Any]) -> None:
    _post_json(f"{device_url}/api/params", {"params": params}, timeout=10)


def _send_frame(device_url: str, frame_b64: str) -> None:
    payload = _frame_packet(frame_b64, next(_FRAME_COUNTER))
    _post_binary(f"{device_url}/api/frame", payload, timeout=10)


def _cancel_stream(device_url: str) -> None:
    with _STREAM_LOCK:
        stop_event = _STREAMS.pop(device_url, None)
    if stop_event:
        stop_event.set()


def _stream_animation(device_url: str, frames_b64: list[str], fps: int, stream_seconds: int, stop_event: threading.Event) -> None:
    interval = max(1 / max(fps, 1), 0.04)
    deadline = time.monotonic() + max(stream_seconds, 1)
    index = 0
    try:
        _set_mode(device_url, "anim_player", {"fps": fps, "loop": True, "playing": True})
        while time.monotonic() < deadline and not stop_event.is_set():
            _send_frame(device_url, frames_b64[index])
            index = (index + 1) % len(frames_b64)
            time.sleep(interval)
    except Exception:
        return
    finally:
        with _STREAM_LOCK:
            if _STREAMS.get(device_url) is stop_event:
                _STREAMS.pop(device_url, None)


def _start_stream(device_url: str, frames_b64: list[str], fps: int, stream_seconds: int) -> None:
    _cancel_stream(device_url)
    stop_event = threading.Event()
    with _STREAM_LOCK:
        _STREAMS[device_url] = stop_event
    thread = threading.Thread(
        target=_stream_animation,
        args=(device_url, frames_b64, fps, stream_seconds, stop_event),
        daemon=True,
        name=f"goddard-stream-{device_url}",
    )
    thread.start()


def display_render_artifact(device_url: str, artifact: RenderArtifact, stream_seconds: int = 24) -> dict[str, Any]:
    base = _normalize_device_url(device_url)
    if artifact.kind == "anim" and artifact.frames_b64:
        _start_stream(base, artifact.frames_b64, artifact.fps, stream_seconds)
        return {
            "ok": True,
            "displayed": True,
            "device_url": base,
            "kind": artifact.kind,
            "provider": artifact.provider,
            "prompt_rewrite": artifact.prompt_rewrite,
            "fps": artifact.fps,
            "frames_b64": artifact.frames_b64,
            "rgb565_b64": artifact.frames_b64[0],
            "streaming": True,
            "stream_seconds": stream_seconds,
        }

    if not artifact.frame_b64:
        raise RuntimeError("missing_frame_data")
    _cancel_stream(base)
    _set_mode(base, "anim_player", {"fps": artifact.fps, "loop": True, "playing": True})
    _send_frame(base, artifact.frame_b64)
    return {
        "ok": True,
        "displayed": True,
        "device_url": base,
        "kind": artifact.kind,
        "provider": artifact.provider,
        "prompt_rewrite": artifact.prompt_rewrite,
        "fps": artifact.fps,
        "rgb565_b64": artifact.frame_b64,
        "frames_b64": None,
        "streaming": False,
    }


def display_agent_prompt(
    device_url: str,
    prompt: str,
    seed: int | None = None,
    frames: int = 24,
    fps: int = 12,
    stream_seconds: int = 24,
) -> dict[str, Any]:
    artifact = render_agent_request(prompt, seed=seed, frames=frames, fps=fps)
    return display_render_artifact(device_url, artifact, stream_seconds=stream_seconds)


def display_catalog_app(
    device_url: str,
    app_id: str,
    seed: int | None = None,
    frames: int = 24,
    fps: int = 12,
    stream_seconds: int = 24,
    weather_location: str = "Miami, FL",
    message: str | None = None,
) -> dict[str, Any]:
    base = _normalize_device_url(device_url)
    app = get_app(app_id)

    if app.kind == "builtin_mode":
        _cancel_stream(base)
        _set_mode(base, app.mode or "clock_fun", app.params)
        return {
            "ok": True,
            "displayed": True,
            "app_id": app.id,
            "title": app.title,
            "kind": "builtin",
            "mode": app.mode,
            "params": app.params,
        }

    if app.kind == "weather":
        weather = get_weather_fun(location=weather_location, units="imperial")
        if not weather.get("ok"):
            raise RuntimeError("weather_fetch_failed")
        _cancel_stream(base)
        _set_mode(base, "weather_fun")
        current = weather.get("current", {})
        _set_params(base, {"tempF": current.get("temp"), "condition": current.get("condition", "Clear"), "variant": 1})
        return {
            "ok": True,
            "displayed": True,
            "app_id": app.id,
            "title": app.title,
            "kind": "weather",
            "weather": weather,
        }

    if app.kind == "text":
        params = dict(app.params)
        params["text"] = (message or params.get("text") or app.title)[:256]
        _cancel_stream(base)
        _set_mode(base, "text_scroll")
        _set_params(base, params)
        return {
            "ok": True,
            "displayed": True,
            "app_id": app.id,
            "title": app.title,
            "kind": "text",
            "params": params,
        }

    prompt = message or app.prompt or app.title
    result = display_agent_prompt(
        base,
        prompt=prompt,
        seed=seed,
        frames=frames,
        fps=fps,
        stream_seconds=stream_seconds,
    )
    result["app_id"] = app.id
    result["title"] = app.title
    result["catalog_kind"] = app.kind
    return result
