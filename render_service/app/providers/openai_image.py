import base64
import io
import math
import os

import requests
from PIL import Image

from .base import Provider


class OpenAIImageProvider(Provider):
    provider_id = "openai"

    def __init__(
        self,
        api_key: str,
        model: str = "gpt-image-1.5",
        base_url: str = "https://api.openai.com/v1",
        quality: str = "high",
        timeout_seconds: int = 90,
    ) -> None:
        self.api_key = api_key
        self.model = model
        self.base_url = base_url.rstrip("/")
        self.quality = quality
        self.timeout_seconds = timeout_seconds

    @classmethod
    def from_env(cls) -> "OpenAIImageProvider | None":
        api_key = os.getenv("GODDARD_OPENAI_API_KEY") or os.getenv("OPENAI_API_KEY")
        if not api_key:
            return None
        model = os.getenv("GODDARD_OPENAI_IMAGE_MODEL", "gpt-image-1.5")
        base_url = os.getenv("GODDARD_OPENAI_BASE_URL", "https://api.openai.com/v1")
        quality = os.getenv("GODDARD_OPENAI_IMAGE_QUALITY", "high")
        timeout_seconds = int(os.getenv("GODDARD_OPENAI_TIMEOUT_SECONDS", "90"))
        return cls(
            api_key=api_key,
            model=model,
            base_url=base_url,
            quality=quality,
            timeout_seconds=timeout_seconds,
        )

    @property
    def provider_name(self) -> str:
        return f"{self.provider_id}:{self.model}"

    def image(self, prompt: str, seed: int | None = None) -> Image.Image:
        del seed
        return self._generate(prompt=prompt, size="1536x1024")

    def animation(self, prompt: str, frames: int, seed: int | None = None) -> list[Image.Image]:
        del seed
        keyframes = 6 if frames >= 18 else 4
        cols, rows = (3, 2) if keyframes == 6 else (2, 2)
        size = "1536x1024" if keyframes == 6 else "1024x1024"
        sheet = self._generate(prompt=prompt, size=size)
        keyframe_images = self._split_storyboard(sheet, cols=cols, rows=rows)[:keyframes]
        if len(keyframe_images) < 2:
            return [sheet.copy() for _ in range(max(frames, 2))]
        return self._expand_keyframes(keyframe_images, target_frames=frames)

    def _generate(self, prompt: str, size: str) -> Image.Image:
        payload = {
            "model": self.model,
            "prompt": prompt,
            "size": size,
            "quality": self.quality,
            "output_format": "png",
        }
        response = requests.post(
            f"{self.base_url}/images/generations",
            headers={
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
            },
            json=payload,
            timeout=self.timeout_seconds,
        )
        response.raise_for_status()
        body = response.json()
        b64 = body["data"][0]["b64_json"]
        raw = base64.b64decode(b64)
        return Image.open(io.BytesIO(raw)).convert("RGB")

    @staticmethod
    def _split_storyboard(sheet: Image.Image, cols: int, rows: int) -> list[Image.Image]:
        tile_w = sheet.width // cols
        tile_h = sheet.height // rows
        frames: list[Image.Image] = []
        for row in range(rows):
            for col in range(cols):
                left = col * tile_w
                top = row * tile_h
                frames.append(sheet.crop((left, top, left + tile_w, top + tile_h)).copy())
        return frames

    @staticmethod
    def _expand_keyframes(keyframes: list[Image.Image], target_frames: int) -> list[Image.Image]:
        if target_frames <= len(keyframes):
            step = len(keyframes) / max(target_frames, 1)
            return [keyframes[min(len(keyframes) - 1, int(i * step))].copy() for i in range(target_frames)]

        cycle = keyframes + keyframes[-2:0:-1]
        cycle_len = len(cycle)
        if cycle_len < 2:
            return [keyframes[0].copy() for _ in range(target_frames)]

        expanded: list[Image.Image] = []
        for i in range(target_frames):
            pos = (i / target_frames) * cycle_len
            idx0 = int(math.floor(pos)) % cycle_len
            idx1 = (idx0 + 1) % cycle_len
            alpha = pos - math.floor(pos)
            expanded.append(
                Image.blend(cycle[idx0].convert("RGBA"), cycle[idx1].convert("RGBA"), alpha).convert("RGB")
            )
        return expanded
