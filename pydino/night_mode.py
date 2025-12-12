# night_mode.py
# Pygame port of night_mode.ts (dict/attr uyumlu)

from __future__ import annotations
from typing import Any, Dict, List, TypedDict
import pygame

try:
    from constants import IS_HIDPI
except ImportError:
    from .constants import IS_HIDPI
from offline_sprite_definitions import sprite_definition_by_type
from utils import get_random_num

# Ay fazlarının spritesheet içindeki x-pozisyonları (ldpi referansı)
PHASES: List[int] = [140, 120, 100, 60, 40, 20, 0]

class _Cfg:
    FADE_SPEED = 0.035
    HEIGHT = 40
    MOON_SPEED = 0.25
    NUM_STARS = 2
    STAR_SIZE = 9
    STAR_SPEED = 0.3
    STAR_MAX_Y = 70
    WIDTH = 20

class NightMode:
    def __init__(
        self,
        canvas: pygame.Surface,
        sprite_pos: Dict[str, int],   # {"x": int, "y": int}
        container_width: int,
        image_sprite_provider
    ) -> None:
        self.canvas = canvas
        self.canvasCtx = canvas
        self.sprite_pos = sprite_pos
        self.provider = image_sprite_provider

        self.container_width = container_width

        self.xPos: float = 0.0
        self.yPos: float = 30.0
        self.currentPhase: int = 0
        self.opacity: float = 0.0
        self.drawStars: bool = False

        # yıldızlar: x,y, sourceY
        self.stars: List[Dict[str, float]] = [dict(x=0.0, y=0.0, sourceY=0.0) for _ in range(_Cfg.NUM_STARS)]

        self._place_stars()

    def update(self, activated: bool) -> None:
        # Ay fazı geçişi yalnızca görünür olmaya başlarken değişsin
        if activated and self.opacity == 0:
            self.currentPhase += 1
            if self.currentPhase >= len(PHASES):
                self.currentPhase = 0

        # Fade in / out
        if activated and (self.opacity < 1 or self.opacity == 0):
            self.opacity += _Cfg.FADE_SPEED
            if self.opacity > 1:
                self.opacity = 1
        elif self.opacity > 0:
            self.opacity -= _Cfg.FADE_SPEED
            if self.opacity < 0:
                self.opacity = 0

        # Pozisyon güncelle / çiz
        if self.opacity > 0:
            self.xPos = self._update_xpos(self.xPos, _Cfg.MOON_SPEED)
            if self.drawStars:
                for s in self.stars:
                    s["x"] = self._update_xpos(float(s["x"]), _Cfg.STAR_SPEED)
            self._draw()
        else:
            # Görünür değilken yıldızları yeniden yerleştir
            self._place_stars()

        self.drawStars = True

    def reset(self) -> None:
        self.currentPhase = 0
        self.opacity = 0
        self.update(False)

    # ---- iç yardımcılar ----
    def _update_xpos(self, current: float, speed: float) -> float:
        if current < -_Cfg.WIDTH:
            return float(self.container_width)
        return current - speed

    def _draw(self) -> None:
        # Ay kaynak dikdörtgeni
        moon_src_w = _Cfg.WIDTH * (2 if self.currentPhase == 3 else 1)
        moon_src_h = _Cfg.HEIGHT
        phase_offset = PHASES[self.currentPhase]
        moon_src_x = self.sprite_pos["x"] + phase_offset
        moon_src_y = self.sprite_pos["y"]

        # HiDPI düzeltmeleri (spritesheet 2x ise kaynak boyutları 2x)
        star_src_size = _Cfg.STAR_SIZE
        star_sheet = sprite_definition_by_type["original"]["ldpi"]["star"]
        if IS_HIDPI:
            moon_src_w *= 2
            moon_src_h *= 2
            moon_src_x = self.sprite_pos["x"] + (phase_offset * 2)
            star_src_size *= 2
            star_sheet = sprite_definition_by_type["original"]["hdpi"]["star"]

        # Kaynak görsel (orijinal sheet)
        runner_orig = self.provider.getOrigImageSprite()
        assert runner_orig is not None

        # --- YENI: opacity'den alpha hesapla ve fade'i gerçekten uygula ---
        alpha = int(max(0, min(255, self.opacity * 255)))
        if alpha <= 0:
            return  # görünmezken çizme

        # Yıldızlar
        for s in self.stars:
            src_rect = pygame.Rect(star_sheet["x"], int(s["sourceY"]), star_src_size, star_src_size)
            # subsurface -> copy -> alpha uygula
            star_tile = runner_orig.subsurface(src_rect).copy()
            star_tile.set_alpha(alpha)
            self.canvasCtx.blit(star_tile, (int(s["x"]), int(s["y"])))

        # Ay
        moon_src_rect = pygame.Rect(moon_src_x, moon_src_y, moon_src_w, moon_src_h)
        moon_tile = runner_orig.subsurface(moon_src_rect).copy()
        moon_tile.set_alpha(alpha)
        self.canvasCtx.blit(moon_tile, (int(self.xPos), int(self.yPos)))

    def _place_stars(self) -> None:
        # ldpi/hdpi y bazları
        if IS_HIDPI:
            star_y_base = sprite_definition_by_type["original"]["hdpi"]["star"]["y"]
            step = _Cfg.STAR_SIZE * 2
        else:
            star_y_base = sprite_definition_by_type["original"]["ldpi"]["star"]["y"]
            step = _Cfg.STAR_SIZE

        segment = max(1, round(self.container_width / _Cfg.NUM_STARS))
        for i in range(_Cfg.NUM_STARS):
            self.stars[i]["x"] = float(get_random_num(segment * i, segment * (i + 1)))
            self.stars[i]["y"] = float(get_random_num(0, _Cfg.STAR_MAX_Y))
            self.stars[i]["sourceY"] = float(star_y_base + step * i)