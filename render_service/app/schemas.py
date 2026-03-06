from __future__ import annotations

from pydantic import BaseModel, Field


class RenderImageRequest(BaseModel):
    prompt: str = Field(..., min_length=1, max_length=200)
    style: str = Field("pixel_art", max_length=32)
    seed: int | None = None


class RenderAnimRequest(BaseModel):
    prompt: str = Field(..., min_length=1, max_length=200)
    style: str = Field("pixel_anim", max_length=32)
    seed: int | None = None
    frames: int = Field(16, ge=2, le=96)
    fps: int = Field(12, ge=1, le=30)


class RenderResponse(BaseModel):
    w: int
    h: int
    format: str
    provider: str | None = None
    prompt_rewrite: str | None = None
    rgb565_b64: str


class AnimResponse(BaseModel):
    w: int
    h: int
    format: str
    fps: int
    provider: str | None = None
    prompt_rewrite: str | None = None
    frames_b64: list[str]


class AgentRenderRequest(BaseModel):
    prompt: str = Field(..., min_length=1, max_length=400)
    seed: int | None = None
    frames: int = Field(24, ge=2, le=96)
    fps: int = Field(12, ge=1, le=30)


class AgentRenderResponse(BaseModel):
    kind: str
    w: int
    h: int
    format: str
    fps: int
    provider: str | None = None
    prompt_rewrite: str | None = None
    rgb565_b64: str | None = None
    frames_b64: list[str] | None = None


class DisplayRenderRequest(BaseModel):
    prompt: str = Field(..., min_length=1, max_length=400)
    device_url: str = Field(..., min_length=1, max_length=200)
    seed: int | None = None
    frames: int = Field(24, ge=2, le=96)
    fps: int = Field(12, ge=1, le=30)
    stream_seconds: int = Field(24, ge=2, le=180)


class DisplayAppRequest(BaseModel):
    app_id: str = Field(..., min_length=1, max_length=64)
    device_url: str = Field(..., min_length=1, max_length=200)
    seed: int | None = None
    frames: int = Field(24, ge=2, le=96)
    fps: int = Field(12, ge=1, le=30)
    stream_seconds: int = Field(24, ge=2, le=180)
    weather_location: str = Field("Miami, FL", min_length=1, max_length=120)
    message: str | None = Field(default=None, max_length=256)
