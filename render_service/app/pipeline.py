import base64
from PIL import Image, ImageOps, ImageFilter, ImageEnhance
import numpy as np
from .providers.procedural import ProceduralProvider

_PROVIDER = ProceduralProvider()

TARGET_W, TARGET_H = 64, 32


def _smart_fit(img: Image.Image) -> Image.Image:
    """Fit to 2:1 with center crop, preserving important content."""
    img = img.convert("RGB")
    w, h = img.size
    target_ratio = TARGET_W / TARGET_H
    cur_ratio = w / h
    if cur_ratio > target_ratio:
        new_w = int(h * target_ratio)
        left = (w - new_w) // 2
        img = img.crop((left, 0, left + new_w, h))
    else:
        new_h = int(w / target_ratio)
        top = (h - new_h) // 2
        img = img.crop((0, top, w, top + new_h))
    return img


def _pixel_art_downscale(img: Image.Image) -> Image.Image:
    """High-quality pixel art pipeline: sharpen → downscale → boost → quantize.

    Optimized for LED matrix readability at 64x32.
    """
    img = _smart_fit(img)

    # 1. Pre-sharpen at source resolution to preserve edges through downscale
    img = img.filter(ImageFilter.UnsharpMask(radius=1.5, percent=160, threshold=2))

    # 2. Two-stage downscale for better quality:
    #    First to 2x target with LANCZOS (preserves detail),
    #    then to target with BOX (clean pixel-art look).
    w, h = img.size
    if w > TARGET_W * 2 and h > TARGET_H * 2:
        img = img.resize((TARGET_W * 2, TARGET_H * 2), resample=Image.Resampling.LANCZOS)
    img = img.resize((TARGET_W, TARGET_H), resample=Image.Resampling.BOX)

    # 3. Boost saturation slightly — LEDs look washed out without it
    img = ImageEnhance.Color(img).enhance(1.15)

    # 4. Slight contrast boost for LED readability
    img = ImageEnhance.Contrast(img).enhance(1.1)

    # 5. Post-sharpen at pixel level to crisp up edges
    img = img.filter(ImageFilter.UnsharpMask(radius=0.5, percent=80, threshold=1))

    # 6. Adaptive palette quantization — 128 colors for richer gradients,
    #    then convert back to RGB for the RGB565 encoder
    pal = img.convert("P", palette=Image.Palette.ADAPTIVE, colors=128)
    return pal.convert("RGB")


def _rgb888_to_rgb565_bytes(img: Image.Image) -> bytes:
    arr = np.array(img.convert("RGB"), dtype=np.uint8)
    r = arr[:, :, 0].astype(np.uint16)
    g = arr[:, :, 1].astype(np.uint16)
    b = arr[:, :, 2].astype(np.uint16)
    rgb565 = ((r & 0xF8) << 8) | ((g & 0xFC) << 3) | (b >> 3)
    return rgb565.astype('<u2').tobytes()


def rgb565_b64(img: Image.Image) -> str:
    raw = _rgb888_to_rgb565_bytes(img)
    return base64.b64encode(raw).decode("ascii")


def render_prompt_to_frame(prompt: str, style: str = "pixel_art", seed: int | None = None) -> str:
    img = _PROVIDER.image(prompt, seed=seed)
    pix = _pixel_art_downscale(img)
    return rgb565_b64(pix)


def render_prompt_to_anim(prompt: str, style: str = "pixel_anim", seed: int | None = None, frames: int = 16, fps: int = 12) -> list[str]:
    imgs = _PROVIDER.animation(prompt, frames=frames, seed=seed)
    return [rgb565_b64(_pixel_art_downscale(im)) for im in imgs]
