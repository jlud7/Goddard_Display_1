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
    rgb565_b64: str

class AnimResponse(BaseModel):
    w: int
    h: int
    format: str
    fps: int
    frames_b64: list[str]
