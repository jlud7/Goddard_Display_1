import base64
from PIL import Image, ImageOps, ImageFilter
import numpy as np
from .providers.procedural import ProceduralProvider

_PROVIDER = ProceduralProvider()

TARGET_W, TARGET_H = 64, 32

def _smart_fit(img: Image.Image) -> Image.Image:
    # Fit to 2:1 with center crop, preserving important content
    img = img.convert("RGB")
    w, h = img.size
    target_ratio = TARGET_W / TARGET_H
    cur_ratio = w / h
    if cur_ratio > target_ratio:
        # too wide; crop width
        new_w = int(h * target_ratio)
        left = (w - new_w)//2
        img = img.crop((left, 0, left+new_w, h))
    else:
        # too tall; crop height
        new_h = int(w / target_ratio)
        top = (h - new_h)//2
        img = img.crop((0, top, w, top+new_h))
    return img

def _pixel_art_downscale(img: Image.Image) -> Image.Image:
    # High quality: pre-sharpen, then area downscale, then palette quantize + ordered dither.
    img = _smart_fit(img)
    img = img.filter(ImageFilter.UnsharpMask(radius=2, percent=140, threshold=2))
    img = img.resize((TARGET_W, TARGET_H), resample=Image.Resampling.BOX)

    # Reduce colors to read well on LED: adaptive palette
    # Use Floyd-Steinberg or ordered; ordered gives more stable low-res.
    pal = img.convert("P", palette=Image.Palette.ADAPTIVE, colors=96)
    pal = pal.convert("RGB")
    return pal

def _rgb888_to_rgb565_bytes(img: Image.Image) -> bytes:
    arr = np.array(img.convert("RGB"), dtype=np.uint8)
    r = arr[:,:,0].astype(np.uint16)
    g = arr[:,:,1].astype(np.uint16)
    b = arr[:,:,2].astype(np.uint16)
    rgb565 = ((r & 0xF8) << 8) | ((g & 0xFC) << 3) | (b >> 3)
    # little-endian uint16 stream
    out = rgb565.astype('<u2').tobytes()
    return out

def rgb565_b64(img: Image.Image) -> str:
    raw = _rgb888_to_rgb565_bytes(img)
    return base64.b64encode(raw).decode("ascii")

def render_prompt_to_frame(prompt: str, style: str = "pixel_art", seed: int | None = None) -> str:
    img = _PROVIDER.image(prompt, seed=seed)
    pix = _pixel_art_downscale(img)
    return rgb565_b64(pix)

def render_prompt_to_anim(prompt: str, style: str = "pixel_anim", seed: int | None = None, frames: int = 16, fps: int = 12) -> list[str]:
    imgs = _PROVIDER.animation(prompt, frames=frames, seed=seed)
    out = []
    for im in imgs:
        pix = _pixel_art_downscale(im)
        out.append(rgb565_b64(pix))
    return out
