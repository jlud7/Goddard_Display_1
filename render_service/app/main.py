from fastapi import FastAPI, Query
from fastapi.middleware.cors import CORSMiddleware
from .schemas import RenderImageRequest, RenderAnimRequest, RenderResponse, AnimResponse
from .pipeline import render_prompt_to_frame, render_prompt_to_anim
from .weather import get_weather_fun

app = FastAPI(
    title="Goddard Display Render Service",
    version="2.0.0",
    description="Converts prompts and data into 64x32 pixel-art frames for HUB75 LED panels",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
def health():
    return {"ok": True, "version": "2.0.0"}


@app.post("/render/image", response_model=RenderResponse)
def render_image(req: RenderImageRequest):
    frame = render_prompt_to_frame(req.prompt, req.style, req.seed)
    return {"w": 64, "h": 32, "format": "rgb565", "rgb565_b64": frame}


@app.post("/render/anim", response_model=AnimResponse)
def render_anim(req: RenderAnimRequest):
    anim = render_prompt_to_anim(req.prompt, req.style, req.seed, req.frames, req.fps)
    return {"w": 64, "h": 32, "format": "rgb565", "fps": req.fps, "frames_b64": anim}


@app.get("/weather")
def weather(
    location: str = Query("Miami,FL"),
    units: str = Query("imperial"),
):
    return get_weather_fun(location=location, units=units)


@app.get("/prompts")
def prompt_suggestions():
    """Return a list of known working prompts for the procedural provider."""
    return {
        "images": [
            "dragon breathing fire",
            "mario pixel sprite",
            "metroid floating orb",
            "zelda triforce sword",
            "random pokemon",
            "neon abstract shapes",
            "sunset landscape",
            "space galaxy",
            "fire flames",
            "mountain landscape",
        ],
        "animations": [
            "dragon breathing fire",
            "rain falling city",
            "time orbiting clock",
            "fire flames burning",
            "neon pulse shapes",
            "starfield warp speed",
        ],
    }
