# obstacle.py
# 1:1 pygame port of obstacle.ts

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Optional

import pygame

try:
    from constants import FPS, IS_HIDPI, IS_MOBILE
    from utils import get_random_num
except ImportError:
    from .constants import FPS, IS_HIDPI, IS_MOBILE
    from .utils import get_random_num
from offline_sprite_definitions import CollisionBox  # your py version


# -----------------------------------------------------------------------------
# Global tunables (match TS module-level state)
# -----------------------------------------------------------------------------
max_gap_coefficient: float = 1.5
max_obstacle_length: int = 3


def set_max_gap_coefficient(coefficient: float) -> None:
    global max_gap_coefficient
    max_gap_coefficient = coefficient


def set_max_obstacle_length(length: int) -> None:
    global max_obstacle_length
    max_obstacle_length = int(length)


# TS-compatible aliases (so imports like setMaxGapCoefficient work)
setMaxGapCoefficient = set_max_gap_coefficient
setMaxObstacleLength = set_max_obstacle_length


# -----------------------------------------------------------------------------
# Helpers
# -----------------------------------------------------------------------------
def _get(obj: Any, name: str, default: Any = None) -> Any:
    """Support both dataclass/attr objects and dict-like configs."""
    if hasattr(obj, name):
        return getattr(obj, name)
    if isinstance(obj, dict):
        return obj.get(name, default)
    return default


def _blit_region(
    dst_surface: pygame.Surface,
    src_surface: pygame.Surface,
    src_rect: pygame.Rect,
    dest_xy: tuple[int, int],
    dest_wh: tuple[int, int],
) -> None:
    sub = src_surface.subsurface(src_rect)
    if sub.get_width() != dest_wh[0] or sub.get_height() != dest_wh[1]:
        sub = pygame.transform.scale(sub, dest_wh)
    dst_surface.blit(sub, dest_xy)


# -----------------------------------------------------------------------------
# Obstacle
# -----------------------------------------------------------------------------
class Obstacle:
    # Public fields (match TS names exactly)
    collisionBoxes: list[CollisionBox]
    followingObstacleCreated: bool
    gap: int
    jumpAlerted: bool
    remove: bool
    size: int
    width: int
    xPos: int
    yPos: int
    typeConfig: Any  # ObstacleType in TS

    # private-ish
    _canvas: pygame.Surface
    _sprite_pos: Any  # SpritePosition (expects .x, .y)
    _gap_coefficient: float
    _speed_offset: float
    _alt_game_mode_active: bool
    _image_sprite: pygame.Surface
    _current_frame: int
    _timer: float
    _resource_provider: Any  # ImageSpriteProvider & GameStateProvider

    def __init__(
        self,
        canvas_ctx: pygame.Surface,
        type_config: Any,          # ObstacleType (dataclass/dict)
        sprite_img_pos: Any,       # SpritePosition (.x, .y)
        dimensions: Any,           # Dimensions (width, height)
        gap_coefficient: float,
        speed: float,
        x_offset: float = 0,
        resource_provider: Any = None,  # provides image sprites & state flags
        is_alt_game_mode: bool = False,
    ) -> None:
        self._canvas = canvas_ctx
        self._sprite_pos = sprite_img_pos
        self.typeConfig = type_config
        self._resource_provider = resource_provider

        has_slowdown = bool(getattr(resource_provider, "hasSlowdown", False))
        self._gap_coefficient = gap_coefficient * 2 if has_slowdown else gap_coefficient

        self.size = get_random_num(1, max_obstacle_length)
        self.xPos = int(_get(dimensions, "width", 600) + x_offset)
        self.yPos = 0

        self.followingObstacleCreated = False
        self.gap = 0
        self.jumpAlerted = False
        self.remove = False
        self.width = 0

        self._alt_game_mode_active = bool(is_alt_game_mode)
        self._speed_offset = 0.0
        self._current_frame = 0
        self._timer = 0.0

        # Pick correct sprite sheet surface
        img_surface: Optional[pygame.Surface]
        t_type = _get(self.typeConfig, "type")
        if t_type == "collectable":
            img_surface = getattr(resource_provider, "getAltCommonImageSprite")()
        elif self._alt_game_mode_active:
            img_surface = getattr(resource_provider, "getRunnerAltGameImageSprite")()
        else:
            img_surface = getattr(resource_provider, "getRunnerImageSprite")()
        assert img_surface is not None, "Image sprite surface could not be loaded."
        self._image_sprite = img_surface

        # Finish setup
        self._init(speed)

    # -------------------------------------------------------------------------
    # TS private init()
    # -------------------------------------------------------------------------
    def _init(self, speed: float) -> None:
        self.cloneCollisionBoxes()

        # Only allow sizing if at the right speed.
        multiple_speed = float(_get(self.typeConfig, "multipleSpeed", 9999))
        if self.size > 1 and multiple_speed > speed:
            self.size = 1

        base_width = int(_get(self.typeConfig, "width", 0))
        base_height = int(_get(self.typeConfig, "height", 0))
        self.width = base_width * self.size

        # yPos can be an int or a list (with optional yPosMobile)
        y_pos = _get(self.typeConfig, "yPos")
        if isinstance(y_pos, (list, tuple)):
            y_mobile = _get(self.typeConfig, "yPosMobile", y_pos)
            selectable = y_mobile if IS_MOBILE else y_pos
            idx = get_random_num(0, len(selectable) - 1)
            self.yPos = int(selectable[idx])
        else:
            self.yPos = int(y_pos)

        # Initial draw
        self._draw()

        # Adjust collision boxes for size > 1
        if self.size > 1 and len(self.collisionBoxes) >= 3:
            # center box width spans total width minus side boxes
            left = self.collisionBoxes[0]
            center = self.collisionBoxes[1]
            right = self.collisionBoxes[2]
            center.width = self.width - left.width - right.width
            right.x = self.width - right.width

        # speedOffset
        speed_offset = _get(self.typeConfig, "speedOffset")
        if speed_offset:
            self._speed_offset = float(speed_offset if (get_random_num(0, 1) == 1) else -speed_offset)

        # gap
        self.gap = self.getGap(self._gap_coefficient, speed)

        # Increase gap if audio cues enabled
        if bool(getattr(self._resource_provider, "hasAudioCues", False)):
            self.gap *= 2

    # -------------------------------------------------------------------------
    # TS private draw()
    # -------------------------------------------------------------------------
    def _draw(self) -> None:
        source_w = int(_get(self.typeConfig, "width", 0))
        source_h = int(_get(self.typeConfig, "height", 0))

        # HIDPI ise kaynaktan 2x alan oku
        src_w_px = source_w * (2 if IS_HIDPI else 1)
        src_h_px = source_h * (2 if IS_HIDPI else 1)

        # Sprite sheet üzerindeki başlangıç X konumu:
        # (sourceWidth * size) * (0.5 * (size - 1)) + spritePos.x
        base = (src_w_px * self.size) * (0.5 * (self.size - 1))

        # sprite_pos hem dict hem obje olabilir — güvenli oku
        pos_x = int(_get(self._sprite_pos, "x", 0))
        pos_y = int(_get(self._sprite_pos, "y", 0))

        src_x = int(base + pos_x)
        src_y = pos_y

        # Animasyon çerçevesi ofseti
        if self._current_frame > 0:
            src_x += src_w_px * self._current_frame

        # Kaynak dikdörtgen ve hedef boyut (mantıksal ölçekte)
        src_rect = pygame.Rect(src_x, src_y, src_w_px * self.size, src_h_px)
        dest_wh = (source_w * self.size, source_h)

        _blit_region(
            self._canvas,
            self._image_sprite,
            src_rect,
            (int(self.xPos), int(self.yPos)),
            dest_wh,
        )

    # -------------------------------------------------------------------------
    # TS update(deltaTime, speed)
    # -------------------------------------------------------------------------
    def update(self, delta_time: float, speed: float) -> None:
        if self.remove:
            return

        # Per-obstacle speed offset
        if _get(self.typeConfig, "speedOffset"):
            speed = float(speed) + self._speed_offset

        # Move left
        self.xPos -= int((speed * (FPS / 1000.0)) * delta_time)

        # Animated obstacles
        num_frames = _get(self.typeConfig, "numFrames")
        if num_frames:
            frame_rate = float(_get(self.typeConfig, "frameRate", 0))
            self._timer += delta_time
            if self._timer >= frame_rate:
                self._current_frame = 0 if self._current_frame >= int(num_frames) - 1 else self._current_frame + 1
                self._timer = 0.0

        # Draw current frame
        self._draw()

        # Cull when off-screen
        if not self.isVisible():
            self.remove = True

    # -------------------------------------------------------------------------
    # TS getGap(...)
    # -------------------------------------------------------------------------
    def getGap(self, gap_coefficient: float, speed: float) -> int:
        min_gap = int(round(self.width * speed + _get(self.typeConfig, "minGap", 0) * gap_coefficient))
        max_gap = int(round(min_gap * max_gap_coefficient))
        return get_random_num(min_gap, max_gap)

    # -------------------------------------------------------------------------
    # TS isVisible()
    # -------------------------------------------------------------------------
    def isVisible(self) -> bool:
        return (self.xPos + self.width) > 0

    # Pythonic alias
    def is_visible(self) -> bool:
        return self.isVisible()

    # -------------------------------------------------------------------------
    # TS cloneCollisionBoxes()
    # -------------------------------------------------------------------------
    def cloneCollisionBoxes(self) -> None:
        self.collisionBoxes = []
        boxes = _get(self.typeConfig, "collisionBoxes", []) or []
        for b in boxes:
            # b may be dict or CollisionBox-like
            self.collisionBoxes.append(
                CollisionBox(
                    x=int(_get(b, "x", 0)),
                    y=int(_get(b, "y", 0)),
                    width=int(_get(b, "width", 0)),
                    height=int(_get(b, "height", 0)),
                )
            )