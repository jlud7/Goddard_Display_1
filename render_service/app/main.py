import logging
from typing import Literal

from fastapi import FastAPI, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from .schemas import RenderImageRequest, RenderAnimRequest, RenderResponse, AnimResponse
from .pipeline import render_prompt_to_frame, render_prompt_to_anim
from .weather import get_weather_fun

VERSION = "2.1.0"

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
    return {"ok": True, "version": VERSION}


@app.post("/render/image", response_model=RenderResponse)
def render_image(req: RenderImageRequest):
    try:
        frame = render_prompt_to_frame(req.prompt, req.style, req.seed)
        return {"w": 64, "h": 32, "format": "rgb565", "rgb565_b64": frame}
    except Exception:
        logger.exception("render_image failed for prompt=%s", req.prompt)
        return JSONResponse(status_code=500, content={"error": "render_failed"})


@app.post("/render/anim", response_model=AnimResponse)
def render_anim(req: RenderAnimRequest):
    try:
        anim = render_prompt_to_anim(req.prompt, req.style, req.seed, req.frames, req.fps)
        return {"w": 64, "h": 32, "format": "rgb565", "fps": req.fps, "frames_b64": anim}
    except Exception:
        logger.exception("render_anim failed for prompt=%s", req.prompt)
        return JSONResponse(status_code=500, content={"error": "render_failed"})


@app.get("/weather")
def weather(
    location: str = Query("Miami,FL", max_length=200),
    units: Literal["imperial", "metric"] = Query("imperial"),
):
    return get_weather_fun(location=location, units=units)


@app.get("/prompts")
def prompt_suggestions():
    """Return a list of known working prompts for the procedural provider."""
    return {
        "images": [
            "charmander breathing fire",
            "pikachu in a field",
            "mario pixel sprite",
            "metroid floating orb",
            "zelda triforce sword",
            "pepperoni pizza",
            "cheeseburger",
            "sushi platter",
            "donut with sprinkles",
            "ramen bowl",
            "cute cat",
            "happy dog",
            "goldfish aquarium",
            "owl at night",
            "robot",
            "spooky ghost",
            "skull",
            "alien ufo",
            "mushroom 1up",
            "red heart",
            "gem diamond",
            "crown royal",
            "sword blade",
            "flower garden",
            "rocket spaceship",
            "house cottage",
            "car racing",
            "neon city",
            "sunset beach",
            "space galaxy",
            "ocean waves",
            "snowy winter",
            "cityscape night",
            "rainbow",
            "mountain landscape",
            "birthday cake",
            "ice cream cone",
            "coffee latte",
            "fire flames",
        ],
        "animations": [
            "charmander breathing fire",
            "dragon breathing fire",
            "rain falling city",
            "time orbiting clock",
            "fire flames burning",
            "neon pulse shapes",
            "starfield warp speed",
            "ocean waves rolling",
            "snow falling winter",
            "heart love pulsing",
            "rainbow shimmer",
        ],
    }
