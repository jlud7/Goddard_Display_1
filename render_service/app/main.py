from __future__ import annotations

import logging
from typing import Literal

from fastapi import FastAPI, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from .catalog import catalog_payload
from .display import display_agent_prompt, display_catalog_app
from .pipeline import (
    provider_status,
    render_agent_request,
    render_anim_artifact,
    render_image_artifact,
    render_prompt_to_anim,
    render_prompt_to_frame,
)
from .schemas import (
    AgentRenderRequest,
    AgentRenderResponse,
    AnimResponse,
    DisplayAppRequest,
    DisplayRenderRequest,
    RenderAnimRequest,
    RenderImageRequest,
    RenderResponse,
)
from .weather import get_weather_fun

VERSION = "2.2.0"

logger = logging.getLogger("goddard.render")

app = FastAPI(
    title="Goddard Display Render Service",
    version=VERSION,
    description="Converts prompts and data into 64x32 pixel-art frames for HUB75 LED panels",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
def health():
    return {"ok": True, "version": VERSION, **provider_status()}


@app.get("/catalog/apps")
def catalog_apps():
    return catalog_payload()


@app.post("/render/image", response_model=RenderResponse)
def render_image(req: RenderImageRequest):
    try:
        artifact = render_image_artifact(req.prompt, seed=req.seed)
        return {
            "w": 64,
            "h": 32,
            "format": "rgb565",
            "provider": artifact.provider,
            "prompt_rewrite": artifact.prompt_rewrite,
            "rgb565_b64": artifact.frame_b64,
        }
    except Exception:
        logger.exception("render_image failed for prompt=%s", req.prompt)
        return JSONResponse(status_code=500, content={"error": "render_failed"})


@app.post("/render/anim", response_model=AnimResponse)
def render_anim(req: RenderAnimRequest):
    try:
        artifact = render_anim_artifact(req.prompt, seed=req.seed, frames=req.frames, fps=req.fps)
        return {
            "w": 64,
            "h": 32,
            "format": "rgb565",
            "fps": req.fps,
            "provider": artifact.provider,
            "prompt_rewrite": artifact.prompt_rewrite,
            "frames_b64": artifact.frames_b64,
        }
    except Exception:
        logger.exception("render_anim failed for prompt=%s", req.prompt)
        return JSONResponse(status_code=500, content={"error": "render_failed"})


@app.post("/agent/render", response_model=AgentRenderResponse)
def agent_render(req: AgentRenderRequest):
    try:
        artifact = render_agent_request(req.prompt, seed=req.seed, frames=req.frames, fps=req.fps)
        return {
            "kind": artifact.kind,
            "w": 64,
            "h": 32,
            "format": "rgb565",
            "fps": artifact.fps,
            "provider": artifact.provider,
            "prompt_rewrite": artifact.prompt_rewrite,
            "rgb565_b64": artifact.frame_b64,
            "frames_b64": artifact.frames_b64,
        }
    except Exception:
        logger.exception("agent_render failed for prompt=%s", req.prompt)
        return JSONResponse(status_code=500, content={"error": "render_failed"})


@app.post("/display/render")
def display_render(req: DisplayRenderRequest):
    try:
        result = display_agent_prompt(
            device_url=req.device_url,
            prompt=req.prompt,
            seed=req.seed,
            frames=req.frames,
            fps=req.fps,
            stream_seconds=req.stream_seconds,
        )
        result.update({"w": 64, "h": 32, "format": "rgb565"})
        return result
    except Exception:
        logger.exception("display_render failed for prompt=%s device=%s", req.prompt, req.device_url)
        return JSONResponse(status_code=500, content={"error": "display_failed"})


@app.post("/display/app")
def display_app(req: DisplayAppRequest):
    try:
        result = display_catalog_app(
            device_url=req.device_url,
            app_id=req.app_id,
            seed=req.seed,
            frames=req.frames,
            fps=req.fps,
            stream_seconds=req.stream_seconds,
            weather_location=req.weather_location,
            message=req.message,
        )
        result.update({"w": 64, "h": 32, "format": "rgb565"})
        return result
    except Exception:
        logger.exception("display_app failed for app=%s device=%s", req.app_id, req.device_url)
        return JSONResponse(status_code=500, content={"error": "display_failed"})


@app.get("/weather")
def weather(
    location: str = Query("Miami,FL", max_length=200),
    units: Literal["imperial", "metric"] = Query("imperial"),
):
    return get_weather_fun(location=location, units=units)


@app.get("/prompts")
def prompt_suggestions():
    catalog = catalog_payload()
    ai_apps = [app for app in catalog["apps"] if app["kind"].startswith("ai_")]
    return {
        "images": [app["prompt"] for app in ai_apps if app["kind"] == "ai_image"][:8],
        "animations": [app["prompt"] for app in ai_apps if app["kind"] == "ai_anim"][:8],
    }
