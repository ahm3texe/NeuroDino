# background_el.py
# 1:1 pygame port of Chrome Dino background_el.ts

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional, Dict, Any

import pygame

try:
    from constants import IS_HIDPI
    from utils import get_random_num
except ImportError:
    from .constants import IS_HIDPI
    from .utils import get_random_num  # alias -> utils.get_random_num


# -----------------------------------------------------------------------------
# Config dataclasses (TS interface eşdeğerleri)
# -----------------------------------------------------------------------------
@dataclass
class BackgroundElSpriteConfig:
    height: int
    width: int
    offset: int
    xPos: int
    fixed: bool
    fixedXPos: Optional[int] = None
    fixedYPos1: Optional[int] = None
    fixedYPos2: Optional[int] = None


@dataclass
class BackgroundElConfig:
    maxBgEls: int
    maxGap: int
    minGap: int
    pos: int
    speed: float
    yPos: int
    msPerFrame: int = 0  # only needed when spriteConfig.fixed is true


# -----------------------------------------------------------------------------
# Global config (TS: module-level mutable)
# -----------------------------------------------------------------------------
_global_config = BackgroundElConfig(
    maxBgEls=0,
    maxGap=0,
    minGap=0,
    msPerFrame=0,
    pos=0,
    speed=0.0,
    yPos=0,
)


def get_global_config() -> BackgroundElConfig:
    return _global_config


def set_global_config(config: BackgroundElConfig) -> None:
    global _global_config
    _global_config = config


# TS-style aliases (opsiyonel)
getGlobalConfig = get_global_config
setGlobalConfig = set_global_config


# -----------------------------------------------------------------------------
# Background element
# -----------------------------------------------------------------------------
class BackgroundEl:
    gap: int
    xPos: float
    remove: bool

    def __init__(
        self,
        canvas: pygame.Surface,
        spritePos: Dict[str, int],  # SpritePosition {x,y}
        containerWidth: int,
        type_name: str,
        imageSpriteProvider: Any,  # ImageSpriteProvider
    ) -> None:
        """
        Background item. Similar to cloud, without random y position.
        """
        self.canvas: pygame.Surface = canvas
        self.canvasCtx: pygame.Surface = canvas
        self.spritePos = spritePos
        self.imageSpriteProvider = imageSpriteProvider

        self.xPos = float(containerWidth)
        self.type = type_name
        self.remove = False

        # Rastgele gap
        gc = get_global_config()
        self.gap = getRandomNum(gc.minGap, gc.maxGap)

        # Sprite config'i provider'dan al
        sprite_def = imageSpriteProvider.getSpriteDefinition()
        assert sprite_def is not None
        cfg_raw = sprite_def["backgroundEl"][self.type]
        # cfg_raw dict → dataclass'a sar
        self.spriteConfig = BackgroundElSpriteConfig(
            height=int(cfg_raw["height"]),
            width=int(cfg_raw["width"]),
            offset=int(cfg_raw["offset"]),
            xPos=int(cfg_raw["xPos"]),
            fixed=bool(cfg_raw["fixed"]),
            fixedXPos=cfg_raw.get("fixedXPos"),
            fixedYPos1=cfg_raw.get("fixedYPos1"),
            fixedYPos2=cfg_raw.get("fixedYPos2"),
        )

        # Y konumu / sabit x ayarı
        self.yPos: float = 0.0
        self.animTimer: float = 0.0
        self.switchFrames: bool = False

        self.init()

    # ------------------------------------------------------------------
    # TS parity methods
    # ------------------------------------------------------------------
    def init(self) -> None:
        if self.spriteConfig.fixed and self.spriteConfig.fixedXPos is not None:
            self.xPos = float(self.spriteConfig.fixedXPos)

        gc = get_global_config()
        # yPos = global.yPos - height + offset
        self.yPos = float(gc.yPos - self.spriteConfig.height + self.spriteConfig.offset)

        self.draw()

    def draw(self) -> None:
        imageSprite: pygame.Surface = self.imageSpriteProvider.getRunnerImageSprite()
        assert imageSprite is not None

        # Kaynak kare (sprite sheet üzerinde)
        sourceWidth = self.spriteConfig.width
        sourceHeight = self.spriteConfig.height
        sourceX = self.spriteConfig.xPos
        sourceY = self.spritePos["y"]

        scale = 2 if IS_HIDPI else 1
        sx = sourceX * scale
        sy = sourceY * scale
        sw = sourceWidth * scale
        sh = sourceHeight * scale

        src_rect = pygame.Rect(sx, sy, sw, sh)
        frame = imageSprite.subsurface(src_rect).copy()

        # Hedef boyut: lo-dpi mantıksal piksel (TS çizimde output=sourceWidth/Height;
        # pygame tarafında HiDPI için 2x örneklediğimiz kareyi mantıksal boyuta indiriyoruz)
        if frame.get_width() != sourceWidth or frame.get_height() != sourceHeight:
            frame = pygame.transform.scale(frame, (sourceWidth, sourceHeight))

        # Blit
        self.canvasCtx.blit(frame, (int(self.xPos), int(self.yPos)))

    def update(self, speed: float) -> None:
        if self.remove:
            return

        if self.spriteConfig.fixed:
            gc = get_global_config()
            # Animasyon zamanlayıcı (msPerFrame zorunlu)
            assert gc.msPerFrame is not None
            self.animTimer += speed
            if self.animTimer > gc.msPerFrame:
                self.animTimer = 0.0
                self.switchFrames = not self.switchFrames

            if self.spriteConfig.fixedYPos1 is not None and self.spriteConfig.fixedYPos2 is not None:
                self.yPos = float(self.spriteConfig.fixedYPos1 if self.switchFrames else self.spriteConfig.fixedYPos2)
        else:
            # Sabit hız (oyun hızından bağımsız)
            self.xPos -= get_global_config().speed

        self.draw()

        # Canvas dışında kaldı mı?
        if not self.isVisible():
            self.remove = True

    def isVisible(self) -> bool:
        # Sağ kenar > 0 ise görünür
        return (self.xPos + self.spriteConfig.width) > 0