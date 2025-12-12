# horizon_line.py
# Pygame port of horizon_line.ts (dict/attr uyumlu)

from __future__ import annotations

from typing import Any, Dict, Tuple
import pygame

try:
    from constants import FPS, IS_HIDPI
except ImportError:
    from .constants import FPS, IS_HIDPI
from image_sprite_provider import ImageSpriteProvider

SpritePosition = Dict[str, int]  # {"x": int, "y": int}

def _get(container: Any, key: str, default=None):
    if isinstance(container, dict):
        return container.get(key, default)
    return getattr(container, key, default)

class HorizonLine:
    def __init__(
        self,
        canvas: pygame.Surface,
        line_config: Dict[str, int] | Any,
        image_sprite_provider: ImageSpriteProvider,
    ) -> None:
        # Kaynak konumları (sprite sheet içindeki yatay 2 parça)
        source_x = _get(line_config, "sourceX")
        source_y = _get(line_config, "sourceY")
        width = _get(line_config, "width")
        height = _get(line_config, "height")
        self.yPos = _get(line_config, "yPos")

        if source_x is None or source_y is None or width is None or height is None:
            raise ValueError("HorizonLine: line_config eksik alan içeriyor.")

        if IS_HIDPI:
            source_x *= 2
            source_y *= 2

        # Canvas & provider
        self.canvas = canvas
        self.canvasCtx = canvas  # pygame Surface
        self.imageSpriteProvider = image_sprite_provider

        # Sprite sheet üzerindeki başlangıç x’leri
        self.spritePos: SpritePosition = {"x": source_x, "y": source_y}
        self.dimensions: Tuple[int, int] = (width, height)

        # İki parça halinde zemin çizgisi
        self.sourceXPos = [self.spritePos["x"], self.spritePos["x"] + width]
        self.xPos = [0, width]

        # Kesilecek kaynak boyutları (HiDPI’de 2x)
        self.sourceDimensions = {
            "width": width * (2 if IS_HIDPI else 1),
            "height": height * (2 if IS_HIDPI else 1),
        }

        self.bumpThreshold = 0.5  # bumpy/flat geçiş olasılığı
        self.draw()

    def getRandomType(self) -> int:
        """Bumpy/flat seçimi: ikinci parçanın kaynak offset’i."""
        return self.dimensions[0] if (pygame.time.get_ticks() % 1000) / 1000.0 > self.bumpThreshold else 0

    def draw(self) -> None:
        runner_image = self.image_sprite_provider_image()
        sw = self.sourceDimensions["width"]
        sh = self.sourceDimensions["height"]
        dw, dh = self.dimensions

        # parça 1
        self.canvasCtx.blit(
            runner_image,
            (self.xPos[0], self.yPos),
            (self.sourceXPos[0], self.spritePos["y"], sw, sh),
        )
        # parça 2
        self.canvasCtx.blit(
            runner_image,
            (self.xPos[1], self.yPos),
            (self.sourceXPos[1], self.spritePos["y"], sw, sh),
        )

    def updatexPos(self, pos: int, increment: int) -> None:
        line1 = pos
        line2 = 1 - pos

        self.xPos[line1] -= increment
        self.xPos[line2] = self.xPos[line1] + self.dimensions[0]

        if self.xPos[line1] <= -self.dimensions[0]:
            self.xPos[line1] += self.dimensions[0] * 2
            self.xPos[line2] = self.xPos[line1] - self.dimensions[0]
            # bumpy/flat seçimi: ikinci “kaynak x” başlangıcı
            self.sourceXPos[line1] = self.getRandomType() + self.spritePos["x"]

    def update(self, deltaTime: float, speed: float) -> None:
        increment = int(speed * (FPS / 1000.0) * deltaTime)
        self.updatexPos(0 if self.xPos[0] <= 0 else 1, increment)
        self.draw()

    def reset(self) -> None:
        self.xPos[0] = 0
        self.xPos[1] = self.dimensions[0]

    # ---- helpers ----
    def image_sprite_provider_image(self) -> pygame.Surface:
        img = self.imageSpriteProvider.getRunnerImageSprite()
        assert img is not None
        return img