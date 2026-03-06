from __future__ import annotations

import base64
import math
import os
import random
from array import array
from dataclasses import dataclass
from typing import Literal

from PIL import Image, ImageChops, ImageDraw, ImageEnhance, ImageFilter, ImageOps

from .providers.base import Provider
from .providers.openai_image import OpenAIImageProvider
from .providers.procedural import ProceduralProvider
from .providers.replicate_image import ReplicateImageProvider


TARGET_W, TARGET_H = 64, 32
PANEL_PALETTE_COLORS = 64
ANIMATION_HINTS = {
    "animate",
    "animation",
    "loop",
    "looping",
    "moving",
    "motion",
    "flying",
    "running",
    "spinning",
    "orbit",
    "orbiting",
    "breathing fire",
    "breathing",
    "flames",
    "fire",
    "rain",
    "falling",
    "storm",
    "wave",
    "waving",
    "spark",
    "sparks",
    "twinkling",
    "twinkle",
    "pulse",
    "scrolling",
    "drifting",
    "glowing beam",
    "warp",
}
MotionStyle = Literal["fire", "rain", "snow", "warp", "underwater", "aurora", "synthwave", "generic"]


@dataclass
class RenderArtifact:
    kind: Literal["image", "anim"]
    provider: str
    prompt_rewrite: str
    fps: int
    frame_b64: str | None = None
    frames_b64: list[str] | None = None


def _available_providers() -> list[Provider]:
    providers: list[Provider] = []
    replicate = ReplicateImageProvider.from_env()
    openai = OpenAIImageProvider.from_env()
    procedural = ProceduralProvider()

    requested = os.getenv("GODDARD_RENDER_PROVIDER", "auto").strip().lower()
    if requested in {"auto", "replicate"} and replicate:
        providers.append(replicate)
    if requested in {"auto", "openai"} and openai:
        providers.append(openai)
    if requested == "procedural":
        providers = [procedural]
    elif procedural not in providers:
        providers.append(procedural)
    return providers


_PROVIDER_CHAIN = _available_providers()
_PRIMARY_PROVIDER = _PROVIDER_CHAIN[0]


def provider_status() -> dict[str, object]:
    primary_name = _provider_name(_PRIMARY_PROVIDER)
    return {
        "provider": primary_name,
        "mode": "remote_ai" if primary_name.startswith(("replicate:", "openai:")) else "fallback",
        "replicate_ready": bool(ReplicateImageProvider.from_env()),
        "openai_ready": bool(OpenAIImageProvider.from_env()),
        "provider_chain": [_provider_name(provider) for provider in _PROVIDER_CHAIN],
        "anim_strategy": os.getenv("GODDARD_ANIM_STRATEGY", "hero_loop"),
    }


def _provider_name(provider: Provider) -> str:
    if hasattr(provider, "provider_name"):
        return str(getattr(provider, "provider_name"))
    return getattr(provider, "provider_id", provider.__class__.__name__.lower())


def _render_image_source(prompt: str, seed: int | None = None) -> tuple[Image.Image, str]:
    last_error: Exception | None = None
    for provider in _PROVIDER_CHAIN:
        try:
            return provider.image(prompt, seed=seed), _provider_name(provider)
        except Exception as exc:  # pragma: no cover
            last_error = exc
    raise last_error or RuntimeError("render_image_failed")


def _render_anim_source(prompt: str, frames: int, seed: int | None = None) -> tuple[list[Image.Image], str]:
    last_error: Exception | None = None
    for provider in _PROVIDER_CHAIN:
        try:
            return provider.animation(prompt, frames=frames, seed=seed), _provider_name(provider)
        except Exception as exc:  # pragma: no cover
            last_error = exc
    raise last_error or RuntimeError("render_anim_failed")


def infer_render_kind(prompt: str) -> Literal["image", "anim"]:
    lowered = prompt.lower()
    if any(hint in lowered for hint in ANIMATION_HINTS):
        return "anim"
    return "image"


def classify_motion_style(prompt: str) -> MotionStyle:
    lowered = prompt.lower()
    if any(word in lowered for word in ("dragon", "fire", "flame", "forge", "embers")):
        return "fire"
    if any(word in lowered for word in ("rain", "storm", "thunder", "lighthouse", "neon alley")):
        return "rain"
    if any(word in lowered for word in ("snow", "blizzard", "winter")):
        return "snow"
    if any(word in lowered for word in ("warp", "starfield", "spaceship", "space tunnel")):
        return "warp"
    if any(word in lowered for word in ("jellyfish", "ocean", "underwater", "deep water", "koi")):
        return "underwater"
    if "aurora" in lowered:
        return "aurora"
    if any(word in lowered for word in ("synthwave", "sunset", "arcade racer", "highway", "scanline")):
        return "synthwave"
    return "generic"


def _normalize_prompt(prompt: str) -> str:
    return " ".join(prompt.strip().split())


def _build_image_prompt(prompt: str) -> str:
    clean = _normalize_prompt(prompt)
    return (
        "Create premium pixel art for a small LED wall display. "
        f"Scene request: {clean}. "
        "Requirements: wide horizontal composition, one dominant focal subject, large readable silhouette, "
        "clean layering, bold negative space, strong color separation, vivid but disciplined palette, "
        "cinematic lighting, no text, no captions, no watermark, no borders, no UI, no tiny clutter, "
        "and no letters, digits, or signage anywhere in the artwork. "
        "The art must survive extreme downscaling and remain legible from across a room. "
        "Aim for sophisticated modern pixel art, not photorealism."
    )


def _build_storyboard_prompt(prompt: str, keyframes: int) -> str:
    clean = _normalize_prompt(prompt)
    grid_words = "three by two" if keyframes >= 6 else "two by two"
    return (
        "Create a premium pixel-art storyboard sprite sheet for a looping LED-wall animation. "
        f"Scene request: {clean}. "
        f"Layout: an exact {grid_words} grid, edge-to-edge panels, no gutters, no borders, no text, no captions, and no numerals. "
        "Every panel must keep the same camera framing, same main subject, and smooth motion continuity from panel to panel. "
        "Use large readable forms, clear silhouette, strong value contrast, limited background clutter, and a stable palette. "
        "Think like high-end 16-bit key art designed to be sliced into a clean repeating loop."
    )


def _build_loop_image_prompt(prompt: str, motion_style: MotionStyle) -> str:
    clean = _normalize_prompt(prompt)
    composition_notes = {
        "fire": "Place the main subject on the left third, action extending to the right, with open negative space for flames and sparks.",
        "rain": "Use strong depth, reflective surfaces, and clear vertical silhouettes with room for falling rain in the foreground.",
        "snow": "Keep the subject large and centered with dark shapes behind it so snowfall remains readable.",
        "warp": "Use a strong central vanishing point and bold luminous streaks that radiate outward.",
        "underwater": "Center the main glowing subject with open surrounding space for drifting particles and water motion.",
        "aurora": "Reserve the upper half for wide sky motion and keep the lower edge as a dark stable horizon silhouette.",
        "synthwave": "Use a central horizon or road perspective with clean geometry and open space for scanline or light motion.",
        "generic": "Keep the subject dominant and leave enough negative space for subtle ambient motion overlays.",
    }
    return (
        "Create premium pixel art for a looping LED display animation. "
        f"Scene request: {clean}. "
        f"Composition guidance: {composition_notes[motion_style]} "
        "Requirements: wide horizontal composition, one dominant subject, large readable silhouette, clear foreground and background separation, "
        "strong lighting, no text, no watermark, no UI, no borders, no letters, no digits, and no dense fine detail. "
        "This image will be animated after generation, so keep the scene coherent, stable, and readable from across a room."
    )


def _smart_fit(img: Image.Image) -> Image.Image:
    img = img.convert("RGB")
    w, h = img.size
    target_ratio = TARGET_W / TARGET_H
    cur_ratio = w / h
    if cur_ratio > target_ratio:
        new_w = int(h * target_ratio)
        left = max(0, (w - new_w) // 2)
        img = img.crop((left, 0, left + new_w, h))
    else:
        new_h = int(w / target_ratio)
        top = max(0, (h - new_h) // 2)
        img = img.crop((0, top, w, top + new_h))
    return img


def _panel_resize(img: Image.Image) -> Image.Image:
    img = _smart_fit(img)
    img = ImageOps.autocontrast(img, cutoff=1)
    img = ImageEnhance.Color(img).enhance(1.14)
    img = ImageEnhance.Contrast(img).enhance(1.1)
    img = img.filter(ImageFilter.UnsharpMask(radius=1.8, percent=200, threshold=2))
    img = img.resize((TARGET_W * 5, TARGET_H * 5), resample=Image.Resampling.LANCZOS)
    img = img.resize((TARGET_W * 2, TARGET_H * 2), resample=Image.Resampling.BOX)
    img = img.resize((TARGET_W, TARGET_H), resample=Image.Resampling.BOX)
    return img.convert("RGB")


def _build_palette_reference(images: list[Image.Image]) -> Image.Image:
    strip = Image.new("RGB", (TARGET_W * len(images), TARGET_H))
    for idx, img in enumerate(images):
        strip.paste(img, (idx * TARGET_W, 0))
    return strip.quantize(colors=PANEL_PALETTE_COLORS, method=Image.Quantize.MEDIANCUT)


def _apply_palette(panel: Image.Image, palette_reference: Image.Image | None = None) -> Image.Image:
    if palette_reference is None:
        palette_reference = panel.quantize(colors=PANEL_PALETTE_COLORS, method=Image.Quantize.MEDIANCUT)
    quantized = panel.quantize(palette=palette_reference, dither=Image.Dither.FLOYDSTEINBERG)
    return quantized.convert("RGB")


def _pixel_art_downscale(img: Image.Image, palette_reference: Image.Image | None = None) -> Image.Image:
    panel = _panel_resize(img)
    panel = ImageEnhance.Sharpness(panel).enhance(1.12)
    return _apply_palette(panel, palette_reference)


def _rgb888_to_rgb565_bytes(img: Image.Image) -> bytes:
    rgb = img.convert("RGB")
    packed = array("H")
    for r, g, b in rgb.getdata():
        packed.append(((r & 0xF8) << 8) | ((g & 0xFC) << 3) | (b >> 3))
    return packed.tobytes()


def rgb565_b64(img: Image.Image) -> str:
    raw = _rgb888_to_rgb565_bytes(img)
    return base64.b64encode(raw).decode("ascii")


def _camera_frame(base: Image.Image, phase: float, motion_style: MotionStyle) -> Image.Image:
    x_amp = 1 if motion_style not in {"warp", "synthwave"} else 0
    y_amp = 1 if motion_style not in {"warp"} else 0
    dx = int(round(math.sin(phase * math.tau) * x_amp))
    dy = int(round(math.cos(phase * math.tau * 1.3) * y_amp))
    shifted = ImageChops.offset(base, dx, dy)
    if motion_style in {"underwater", "aurora"}:
        tint = Image.new("RGB", shifted.size, (8, 18, 28) if motion_style == "underwater" else (12, 16, 22))
        shifted = Image.blend(shifted, tint, 0.04)
    return shifted


def _overlay_fire(img: Image.Image, phase: float, seed: int, dragon_mode: bool) -> Image.Image:
    rgba = img.convert("RGBA")
    draw = ImageDraw.Draw(rgba, "RGBA")
    origin_x = 18 if dragon_mode else 26
    origin_y = 13 if dragon_mode else 20
    plume_len = 26 if dragon_mode else 18
    flare = 0.55 + 0.45 * math.sin(phase * math.tau)

    for layer, (color, width, amp) in enumerate((
        ((255, 210, 120, 150), 7, 3.5),
        ((255, 150, 50, 180), 5, 2.5),
        ((255, 80, 16, 220), 3, 1.8),
    )):
        points: list[tuple[float, float]] = []
        for step in range(7):
            x = origin_x + (plume_len * step / 6)
            y = origin_y + math.sin(phase * math.tau * 2 + step * 0.7 + layer) * amp
            y += math.cos(phase * math.tau + step * 0.35 + layer) * (amp * 0.6)
            points.append((x, y))
        draw.line(points, fill=color, width=width)

    draw.ellipse((origin_x - 2, origin_y - 3, origin_x + 6, origin_y + 5), fill=(255, 180, 90, 140))
    draw.polygon(
        [
            (origin_x + 2, origin_y - 4),
            (origin_x + plume_len + 6, origin_y - 6 - 5 * flare),
            (origin_x + plume_len + 10, origin_y + 1),
            (origin_x + plume_len + 2, origin_y + 7 + 5 * flare),
            (origin_x + 2, origin_y + 4),
        ],
        fill=(255, 120, 32, 48),
    )

    for idx in range(12):
        spark_phase = (phase + idx / 12) % 1.0
        px = origin_x + 6 + int(spark_phase * (plume_len + 10))
        py = origin_y + int(math.sin((seed + idx) * 0.47 + spark_phase * math.tau * 2) * 4)
        size = 1 if idx % 3 else 2
        draw.ellipse((px, py, px + size, py + size), fill=(255, 220, 130, 190))

    return rgba.convert("RGB")


def _overlay_rain(img: Image.Image, phase: float, seed: int, storm_mode: bool) -> Image.Image:
    rgba = img.convert("RGBA")
    draw = ImageDraw.Draw(rgba, "RGBA")
    density = 34 if storm_mode else 24
    for idx in range(density):
        x = (idx * 11 + seed * 3 + int(phase * TARGET_W * 1.5)) % (TARGET_W + 10) - 5
        y = (idx * 7 + int(phase * TARGET_H * 6)) % (TARGET_H + 10) - 5
        draw.line((x, y, x - 2, y + 6), fill=(170, 205, 255, 110 if storm_mode else 90), width=1)
    if storm_mode and 0.18 < phase < 0.24:
        flash = Image.new("RGB", rgba.size, (200, 220, 255))
        rgba = Image.blend(rgba.convert("RGB"), flash, 0.22).convert("RGBA")
        draw = ImageDraw.Draw(rgba, "RGBA")
    for idx in range(10):
        rx = (idx * 9 + seed + int(phase * 24)) % TARGET_W
        draw.line((rx, TARGET_H - 5, min(TARGET_W - 1, rx + 6), TARGET_H - 5), fill=(120, 170, 255, 55), width=1)
    return rgba.convert("RGB")


def _overlay_snow(img: Image.Image, phase: float, seed: int) -> Image.Image:
    rgba = img.convert("RGBA")
    draw = ImageDraw.Draw(rgba, "RGBA")
    for idx in range(26):
        x = (idx * 13 + seed + int(phase * 16)) % TARGET_W
        y = (idx * 5 + int(phase * TARGET_H * 10)) % (TARGET_H + 6) - 3
        size = 2 if idx % 5 == 0 else 1
        draw.ellipse((x, y, x + size, y + size), fill=(245, 248, 255, 170))
    return rgba.convert("RGB")


def _overlay_warp(img: Image.Image, phase: float, seed: int) -> Image.Image:
    rgba = img.convert("RGBA")
    draw = ImageDraw.Draw(rgba, "RGBA")
    cx, cy = TARGET_W // 2, TARGET_H // 2
    for idx in range(26):
        angle = ((idx * 37 + seed * 5) % 360) * math.pi / 180.0
        radius = ((phase + idx / 26) % 1.0) * 26
        inner = max(0.0, radius - 6)
        x0 = cx + math.cos(angle) * inner
        y0 = cy + math.sin(angle) * inner * 0.65
        x1 = cx + math.cos(angle) * radius
        y1 = cy + math.sin(angle) * radius * 0.65
        draw.line((x0, y0, x1, y1), fill=(180, 220, 255, 160), width=1)
    return rgba.convert("RGB")


def _overlay_underwater(img: Image.Image, phase: float, seed: int) -> Image.Image:
    rgba = img.convert("RGBA")
    draw = ImageDraw.Draw(rgba, "RGBA")
    glow = Image.new("RGBA", rgba.size, (20, 90, 130, 0))
    glow_draw = ImageDraw.Draw(glow, "RGBA")
    for idx in range(10):
        x = (idx * 9 + seed * 2 + int(phase * 12)) % TARGET_W
        y = TARGET_H - ((idx * 7 + int(phase * TARGET_H * 8)) % (TARGET_H + 8))
        draw.ellipse((x, y, x + 1, y + 1), fill=(220, 255, 255, 120))
    band_y = 10 + math.sin(phase * math.tau) * 2
    glow_draw.rectangle((0, band_y, TARGET_W, band_y + 8), fill=(60, 190, 220, 24))
    rgba = Image.alpha_composite(rgba, glow)
    return rgba.convert("RGB")


def _overlay_aurora(img: Image.Image, phase: float, seed: int) -> Image.Image:
    rgba = img.convert("RGBA")
    draw = ImageDraw.Draw(rgba, "RGBA")
    colors = ((110, 255, 190, 38), (110, 180, 255, 28), (180, 110, 255, 20))
    for band, color in enumerate(colors):
        points = []
        for x in range(0, TARGET_W + 2, 4):
            y = 4 + band * 3 + math.sin(phase * math.tau + x * 0.18 + band) * 2
            points.append((x, y))
        draw.line(points, fill=color, width=6 - band)
    return rgba.convert("RGB")


def _overlay_synthwave(img: Image.Image, phase: float, seed: int) -> Image.Image:
    rgba = img.convert("RGBA")
    draw = ImageDraw.Draw(rgba, "RGBA")
    horizon = TARGET_H // 2 + 3
    for y in range(0, TARGET_H, 3):
        alpha = 12 if ((y + int(phase * 10)) % 6 == 0) else 0
        if alpha:
            draw.line((0, y, TARGET_W, y), fill=(255, 120, 220, alpha), width=1)
    pulse = int((math.sin(phase * math.tau) + 1) * 18)
    draw.line((0, horizon, TARGET_W, horizon), fill=(255, 180, 110, 60 + pulse), width=2)
    draw.line((TARGET_W // 2, horizon - 2, TARGET_W // 2, TARGET_H), fill=(120, 220, 255, 40), width=1)
    return rgba.convert("RGB")


def _overlay_generic(img: Image.Image, phase: float, seed: int) -> Image.Image:
    rgba = img.convert("RGBA")
    draw = ImageDraw.Draw(rgba, "RGBA")
    for idx in range(8):
        x = (idx * 17 + seed + int(phase * 10)) % TARGET_W
        y = (idx * 9 + int(phase * 8)) % TARGET_H
        draw.point((x, y), fill=(255, 255, 255, 110))
    return rgba.convert("RGB")


def _animate_master_image(base: Image.Image, prompt: str, frames: int, seed: int | None = None) -> list[Image.Image]:
    frames = max(2, frames)
    motion_style = classify_motion_style(prompt)
    seed_value = seed if seed is not None else 0
    dragon_mode = "dragon" in prompt.lower()
    storm_mode = any(word in prompt.lower() for word in ("storm", "thunder", "lighthouse"))

    out: list[Image.Image] = []
    for idx in range(frames):
        phase = idx / frames
        frame = _camera_frame(base, phase, motion_style)
        if motion_style == "fire":
            frame = _overlay_fire(frame, phase, seed_value, dragon_mode=dragon_mode)
        elif motion_style == "rain":
            frame = _overlay_rain(frame, phase, seed_value, storm_mode=storm_mode)
        elif motion_style == "snow":
            frame = _overlay_snow(frame, phase, seed_value)
        elif motion_style == "warp":
            frame = _overlay_warp(frame, phase, seed_value)
        elif motion_style == "underwater":
            frame = _overlay_underwater(frame, phase, seed_value)
        elif motion_style == "aurora":
            frame = _overlay_aurora(frame, phase, seed_value)
        elif motion_style == "synthwave":
            frame = _overlay_synthwave(frame, phase, seed_value)
        else:
            frame = _overlay_generic(frame, phase, seed_value)
        out.append(frame)
    return out


def render_prompt_to_frame(prompt: str, style: str = "pixel_art", seed: int | None = None) -> str:
    del style
    return render_image_artifact(prompt, seed=seed).frame_b64 or ""


def render_prompt_to_anim(
    prompt: str,
    style: str = "pixel_anim",
    seed: int | None = None,
    frames: int = 16,
    fps: int = 12,
) -> list[str]:
    del style
    return render_anim_artifact(prompt, seed=seed, frames=frames, fps=fps).frames_b64 or []


def render_image_artifact(prompt: str, seed: int | None = None, fps: int = 12) -> RenderArtifact:
    prompt_rewrite = _build_image_prompt(prompt)
    img, provider_name = _render_image_source(prompt_rewrite, seed=seed)
    pix = _pixel_art_downscale(img)
    return RenderArtifact(
        kind="image",
        provider=provider_name,
        prompt_rewrite=prompt_rewrite,
        fps=fps,
        frame_b64=rgb565_b64(pix),
    )


def render_anim_artifact(prompt: str, seed: int | None = None, frames: int = 16, fps: int = 12) -> RenderArtifact:
    strategy = os.getenv("GODDARD_ANIM_STRATEGY", "hero_loop").strip().lower()
    if strategy == "storyboard":
        keyframes = 6 if frames >= 18 else 4
        prompt_rewrite = _build_storyboard_prompt(prompt, keyframes=keyframes)
        imgs, provider_name = _render_anim_source(prompt_rewrite, frames=frames, seed=seed)
        resized = [_panel_resize(im) for im in imgs]
        palette_reference = _build_palette_reference(resized[: min(len(resized), 6)])
        output_frames = [rgb565_b64(_apply_palette(im, palette_reference=palette_reference)) for im in resized]
        return RenderArtifact(
            kind="anim",
            provider=provider_name,
            prompt_rewrite=prompt_rewrite,
            fps=fps,
            frames_b64=output_frames,
        )

    motion_style = classify_motion_style(prompt)
    prompt_rewrite = _build_loop_image_prompt(prompt, motion_style)
    image, provider_name = _render_image_source(prompt_rewrite, seed=seed)
    base = _panel_resize(image)
    frames_rgb = _animate_master_image(base, prompt, frames=frames, seed=seed)
    palette_reference = _build_palette_reference(frames_rgb[: min(len(frames_rgb), 6)])
    output_frames = [rgb565_b64(_apply_palette(im, palette_reference=palette_reference)) for im in frames_rgb]
    return RenderArtifact(
        kind="anim",
        provider=provider_name,
        prompt_rewrite=prompt_rewrite,
        fps=fps,
        frames_b64=output_frames,
    )


def render_agent_request(
    prompt: str,
    seed: int | None = None,
    frames: int = 24,
    fps: int = 12,
) -> RenderArtifact:
    kind = infer_render_kind(prompt)
    if kind == "anim":
        return render_anim_artifact(prompt, seed=seed, frames=frames, fps=fps)
    return render_image_artifact(prompt, seed=seed, fps=fps)
