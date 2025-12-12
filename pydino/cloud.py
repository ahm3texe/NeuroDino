# cloud.py
# 1:1 pygame port of Chrome Dino cloud.ts

from __future__ import annotations

import math
from typing import Any, Dict

import pygame

try:
    from constants import IS_HIDPI
    from utils import get_random_num
except ImportError:
    from .constants import IS_HIDPI
    from .utils import get_random_num


class CloudConfig:
    HEIGHT = 14
    MAX_CLOUD_GAP = 400
    MAX_SKY_LEVEL = 30
    MIN_CLOUD_GAP = 100
    MIN_SKY_LEVEL = 71
    WIDTH = 46


def _pos(obj: Dict[str, int] | Any, key: str) -> int:
    """Accept both dict-like {'x':...} and attr-like .x."""
    if isinstance(obj, dict):
        return int(obj[key])
    return int(getattr(obj, key))


class Cloud:
    """Cloud background item.
    Obstacle'a benzer ama çarpışma kutusu yok.
    """

    # TS: public fields
    gap: int
    xPos: float
    remove: bool = False

    # TS: private yPos/canvasCtx/spritePos/imageSpriteProvider
    _yPos: float
    _canvas: pygame.Surface
    _spritePos: Dict[str, int] | Any
    _imageSpriteProvider: Any

    def __init__(
        self,
        canvas: pygame.Surface,
        sprite_pos: Dict[str, int] | Any,
        container_width: int,
        image_sprite_provider: Any,  # ImageSpriteProvider
    ) -> None:
        self._canvas = canvas
        self._spritePos = sprite_pos
        self._imageSpriteProvider = image_sprite_provider

        self.xPos = float(container_width)
        self.gap = get_random_num(CloudConfig.MIN_CLOUD_GAP, CloudConfig.MAX_CLOUD_GAP)
        self.remove = False
        self._yPos = 0.0

        self.init()

    # ------------------------------------------------------------------ #
    # TS: init() — bulutun yüksekliğini belirle ve çiz
    # ------------------------------------------------------------------ #
    def init(self) -> None:
        self._yPos = float(
            get_random_num(CloudConfig.MAX_SKY_LEVEL, CloudConfig.MIN_SKY_LEVEL)
        )
        self.draw()

    # ------------------------------------------------------------------ #
    # TS: draw()
    # ------------------------------------------------------------------ #
    def draw(self) -> None:
        runner_image_sprite: pygame.Surface = self._imageSpriteProvider.getRunnerImageSprite()
        assert runner_image_sprite is not None, "Runner image sprite is required"

        source_w = CloudConfig.WIDTH
        source_h = CloudConfig.HEIGHT
        output_w = source_w
        output_h = source_h

        # HiDPI ise kaynak 2x
        if IS_HIDPI:
            source_w *= 2
            source_h *= 2

        src_x = _pos(self._spritePos, "x")
        src_y = _pos(self._spritePos, "y")

        src_rect = pygame.Rect(src_x, src_y, source_w, source_h)
        frame = runner_image_sprite.subsurface(src_rect).copy()
        if frame.get_size() != (output_w, output_h):
            frame = pygame.transform.scale(frame, (output_w, output_h))

        self._canvas.blit(frame, (int(self.xPos), int(self._yPos)))

    # ------------------------------------------------------------------ #
    # TS: update(speed)
    # ------------------------------------------------------------------ #
    def update(self, speed: float) -> None:
        if not self.remove:
            self.xPos -= math.ceil(speed)
            self.draw()

            if not self.isVisible():
                self.remove = True

    # ------------------------------------------------------------------ #
    # TS: isVisible()
    # ------------------------------------------------------------------ #
    def isVisible(self) -> bool:
        return (self.xPos + CloudConfig.WIDTH) > 0