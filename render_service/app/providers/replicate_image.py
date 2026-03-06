from __future__ import annotations

import io
import math
import os
import time
from typing import Any
from urllib.parse import quote

import requests
from PIL import Image

from .base import Provider


class ReplicateImageProvider(Provider):
    provider_id = "replicate"

    def __init__(
        self,
        api_token: str,
        model_ref: str = "prunaai/z-image-turbo",
        base_url: str = "https://api.replicate.com/v1",
        height: int = 768,
        timeout_seconds: int = 120,
        wait_seconds: int = 60,
    ) -> None:
        self.api_token = api_token
        self.model_ref = model_ref
        self.base_url = base_url.rstrip("/")
        self.height = height
        self.timeout_seconds = timeout_seconds
        self.wait_seconds = wait_seconds

    @classmethod
    def from_env(cls) -> "ReplicateImageProvider | None":
        api_token = os.getenv("GODDARD_REPLICATE_API_TOKEN") or os.getenv("REPLICATE_API_TOKEN")
        if not api_token:
            return None
        return cls(
            api_token=api_token,
            model_ref=os.getenv("GODDARD_REPLICATE_MODEL", "prunaai/z-image-turbo"),
            base_url=os.getenv("GODDARD_REPLICATE_BASE_URL", "https://api.replicate.com/v1"),
            height=int(os.getenv("GODDARD_REPLICATE_HEIGHT", "768")),
            timeout_seconds=int(os.getenv("GODDARD_REPLICATE_TIMEOUT_SECONDS", "120")),
            wait_seconds=int(os.getenv("GODDARD_REPLICATE_WAIT_SECONDS", "60")),
        )

    @property
    def provider_name(self) -> str:
        return f"{self.provider_id}:{self.model_ref}"

    def image(self, prompt: str, seed: int | None = None) -> Image.Image:
        return self._generate(prompt=prompt, aspect_ratio="2:1", seed=seed)

    def animation(self, prompt: str, frames: int, seed: int | None = None) -> list[Image.Image]:
        keyframes = 6 if frames >= 18 else 4
        cols, rows = (3, 2) if keyframes == 6 else (2, 2)
        aspect_ratio = "3:2" if keyframes == 6 else "1:1"
        sheet = self._generate(prompt=prompt, aspect_ratio=aspect_ratio, seed=seed)
        keyframe_images = self._split_storyboard(sheet, cols=cols, rows=rows)[:keyframes]
        if len(keyframe_images) < 2:
            return [sheet.copy() for _ in range(max(frames, 2))]
        return self._expand_keyframes(keyframe_images, target_frames=frames)

    def _generate(self, prompt: str, aspect_ratio: str, seed: int | None = None) -> Image.Image:
        payload: dict[str, Any] = {
            "input": {
                "prompt": prompt,
                "height": self.height,
                "aspect_ratio": aspect_ratio,
            }
        }
        if seed is not None:
            payload["input"]["seed"] = int(seed)

        encoded_model = "/".join(quote(part, safe="") for part in self.model_ref.split("/"))
        response = requests.post(
            f"{self.base_url}/models/{encoded_model}/predictions",
            headers={
                "Authorization": f"Bearer {self.api_token}",
                "Content-Type": "application/json",
                "Prefer": f"wait={self.wait_seconds}",
            },
            json=payload,
            timeout=self.wait_seconds + 15,
        )
        response.raise_for_status()
        prediction = self._wait_for_prediction(response.json())

        if prediction.get("status") != "succeeded":
            raise RuntimeError(prediction.get("error") or f"replicate_prediction_{prediction.get('status', 'unknown')}")

        output = prediction.get("output")
        if isinstance(output, list):
            output = output[0] if output else None
        if isinstance(output, dict):
            output = output.get("url")
        if not isinstance(output, str) or not output:
            raise RuntimeError("replicate_missing_output_url")

        image_response = requests.get(output, timeout=self.timeout_seconds)
        image_response.raise_for_status()
        return Image.open(io.BytesIO(image_response.content)).convert("RGB")

    def _wait_for_prediction(self, prediction: dict[str, Any]) -> dict[str, Any]:
        status = str(prediction.get("status", ""))
        if status in {"succeeded", "failed", "canceled"}:
            return prediction

        poll_url = prediction.get("urls", {}).get("get")
        if not poll_url:
            return prediction

        deadline = time.monotonic() + self.timeout_seconds
        while time.monotonic() < deadline:
            time.sleep(1.2)
            poll = requests.get(
                poll_url,
                headers={"Authorization": f"Bearer {self.api_token}"},
                timeout=20,
            )
            poll.raise_for_status()
            prediction = poll.json()
            status = str(prediction.get("status", ""))
            if status in {"succeeded", "failed", "canceled"}:
                return prediction
        raise TimeoutError("replicate_prediction_timeout")

    @staticmethod
    def _split_storyboard(sheet: Image.Image, cols: int, rows: int) -> list[Image.Image]:
        tile_w = max(1, sheet.width // cols)
        tile_h = max(1, sheet.height // rows)
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
