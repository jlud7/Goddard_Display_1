from abc import ABC, abstractmethod
from PIL import Image

class Provider(ABC):
    @abstractmethod
    def image(self, prompt: str, seed: int | None = None) -> Image.Image:
        raise NotImplementedError

    @abstractmethod
    def animation(self, prompt: str, frames: int, seed: int | None = None) -> list[Image.Image]:
        raise NotImplementedError
