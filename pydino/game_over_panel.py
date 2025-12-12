# game_over_panel.py
# 1:1 pygame port of Chrome Dino game_over_panel.ts

from __future__ import annotations

from typing import Optional, Any, Dict

import pygame

try:
    from constants import IS_HIDPI, IS_RTL
except ImportError:
    from .constants import IS_HIDPI, IS_RTL
from dimensions import Dimensions
from offline_sprite_definitions import sprite_definition_by_type
from utils import getTimeStamp


RESTART_ANIM_DURATION: int = 875
LOGO_PAUSE_DURATION: int = 875
FLASH_ITERATIONS: int = 5


class _AnimConfig:
    frames = [0, 36, 72, 108, 144, 180, 216, 252]
    msPerFrame = RESTART_ANIM_DURATION / 8


class _DefaultPanelDims:
    # TS: GameOverPanelDimensions
    textX = 0
    textY = 13
    textWidth = 191
    textHeight = 11
    restartWidth = 36
    restartHeight = 32


class GameOverPanel:
    def __init__(
        self,
        canvas: pygame.Surface,
        text_img_pos: Dict[str, int],      # SpritePosition: {"x": int, "y": int}
        restart_img_pos: Dict[str, int],   # SpritePosition
        dimensions: Dimensions,
        image_sprite_provider: Any,
        alt_game_end_img_pos: Optional[Dict[str, int]] = None,  # SpritePosition
        alt_game_active: Optional[bool] = None,
    ) -> None:
        self.canvasCtx: pygame.Surface = canvas
        self.canvasDimensions: Dimensions = dimensions
        self.textImgPos = text_img_pos
        self.restartImgPos = restart_img_pos
        self.imageSpriteProvider = image_sprite_provider
        self.altGameEndImgPos = alt_game_end_img_pos
        self.altGameModeActive: bool = bool(alt_game_active)

        self.frameTimeStamp: int = 0
        self.animTimer: float = 0.0
        self.currentFrame: int = 0

        self.flashTimer: float = 0.0
        self.flashCounter: int = 0
        self.originalText: bool = True

    # ------------------------------------------------------------------ #
    # Public API                                                          #
    # ------------------------------------------------------------------ #
    def update_dimensions(self, width: int, height: Optional[int] = None) -> None:
        self.canvasDimensions.width = width
        if height is not None:
            self.canvasDimensions.height = height
        # Boyut değiştiğinde animasyonu son kareye ayarla
        self.currentFrame = len(_AnimConfig.frames) - 1

    def draw(self, alt_game_mode_active: Optional[bool] = None, t_rex: Optional[Any] = None) -> None:
        if alt_game_mode_active is not None:
            self.altGameModeActive = alt_game_mode_active

        # Metni (orijinal) çiz
        self._draw_game_over_text(_DefaultPanelDims, use_alt_text=False)
        # Restart butonu (mevcut frame)
        self._draw_restart_button()
        # Alt game öğeleri TRex üzerinde
        if t_rex is not None:
            self._draw_alt_game_elements(t_rex)

        # Zaman ve animasyon adımı
        self._step()

    def reset(self) -> None:
        self.animTimer = 0.0
        self.frameTimeStamp = 0
        self.currentFrame = 0
        self.flashTimer = 0.0
        self.flashCounter = 0
        self.originalText = True

    # ------------------------------------------------------------------ #
    # Internal                                                            #
    # ------------------------------------------------------------------ #
    def _draw_game_over_text(self, dims, use_alt_text: bool = False) -> None:
        centerX = self.canvasDimensions.width / 2

        textSourceX = dims.textX
        textSourceY = dims.textY
        textSourceWidth = dims.textWidth
        textSourceHeight = dims.textHeight

        textTargetX = round(centerX - (dims.textWidth / 2))
        textTargetY = round((self.canvasDimensions.height - 25) / 3)
        textTargetWidth = dims.textWidth
        textTargetHeight = dims.textHeight

        if IS_HIDPI:
            textSourceY *= 2
            textSourceX *= 2
            textSourceWidth *= 2
            textSourceHeight *= 2

        if not use_alt_text:
            textSourceX += int(self.textImgPos["x"])
            textSourceY += int(self.textImgPos["y"])

        spriteSource = (
            self.imageSpriteProvider.getAltCommonImageSprite()
            if use_alt_text
            else self.imageSpriteProvider.getOrigImageSprite()
        )
        assert spriteSource is not None

        # Kaynaktan bölge
        src_rect = pygame.Rect(textSourceX, textSourceY, textSourceWidth, textSourceHeight)
        frame = spriteSource.subsurface(src_rect).copy()
        if frame.get_size() != (textTargetWidth, textTargetHeight):
            frame = pygame.transform.scale(frame, (textTargetWidth, textTargetHeight))

        # RTL: ayna konumlandırma
        if IS_RTL:
            dest_x = self.canvasDimensions.width - textTargetX - textTargetWidth
        else:
            dest_x = textTargetX

        self.canvasCtx.blit(frame, (dest_x, textTargetY))

    def _draw_alt_game_elements(self, t_rex: Any) -> None:
        spriteDefinition = self.imageSpriteProvider.getSpriteDefinition()
        if self.altGameModeActive and spriteDefinition:
            assert self.altGameEndImgPos is not None
            alt_cfg = spriteDefinition.get("altGameEndConfig")
            assert alt_cfg is not None

            alt_w = int(alt_cfg["width"])
            alt_h = int(alt_cfg["height"])
            target_x = int(t_rex.xPos + alt_cfg["xOffset"])
            target_y = int(t_rex.yPos + alt_cfg["yOffset"])

            src_w = alt_w * (2 if IS_HIDPI else 1)
            src_h = alt_h * (2 if IS_HIDPI else 1)

            altCommon = self.imageSpriteProvider.getAltCommonImageSprite()
            assert altCommon is not None

            src_rect = pygame.Rect(self.altGameEndImgPos["x"], self.altGameEndImgPos["y"], src_w, src_h)
            frame = altCommon.subsurface(src_rect).copy()
            if frame.get_size() != (alt_w, alt_h):
                frame = pygame.transform.scale(frame, (alt_w, alt_h))

            # RTL: sadece x'i aynala
            if IS_RTL:
                dest_x = self.canvasDimensions.width - target_x - alt_w
            else:
                dest_x = target_x

            self.canvasCtx.blit(frame, (dest_x, target_y))

    def _draw_restart_button(self) -> None:
        dims = _DefaultPanelDims
        # Clamp frame index to avoid IndexError when animation steps past last frame
        frame_index = self.currentFrame
        if frame_index < 0:
            frame_index = 0
        max_idx = len(_AnimConfig.frames) - 1
        if frame_index > max_idx:
            frame_index = max_idx
            
        framePosX = _AnimConfig.frames[frame_index]
        src_w = dims.restartWidth
        src_h = dims.restartHeight

        target_x = int((self.canvasDimensions.width / 2) - (dims.restartWidth / 2))
        target_y = int(self.canvasDimensions.height / 2)

        if IS_HIDPI:
            src_w *= 2
            src_h *= 2
            framePosX *= 2

        origSprite = self.imageSpriteProvider.getOrigImageSprite()
        assert origSprite is not None

        src_rect = pygame.Rect(self.restartImgPos["x"] + framePosX, self.restartImgPos["y"], src_w, src_h)
        frame = origSprite.subsurface(src_rect).copy()
        if frame.get_size() != (dims.restartWidth, dims.restartHeight):
            frame = pygame.transform.scale(frame, (dims.restartWidth, dims.restartHeight))

        if IS_RTL:
            dest_x = self.canvasDimensions.width - target_x - dims.restartWidth
        else:
            dest_x = target_x

        self.canvasCtx.blit(frame, (dest_x, target_y))

    def _clear_game_over_text_bounds(self, dims=_DefaultPanelDims) -> None:
        # TS clearRect → pygame'de beyaz dolduruyoruz
        rect = pygame.Rect(
            round(self.canvasDimensions.width / 2 - (dims.textWidth / 2)),
            round((self.canvasDimensions.height - 25) / 3),
            dims.textWidth,
            dims.textHeight + 4,
        )
        # <--- DÜZELTME: Renk (255, 255, 255) yerine (247, 247, 247) olmalı
        pygame.draw.rect(self.canvasCtx, (247, 247, 247), rect)

    def _step(self) -> None:
        now = getTimeStamp()
        delta = now - (self.frameTimeStamp or now)
        self.frameTimeStamp = now
        self.animTimer += delta
        self.flashTimer += delta

        # Restart logosu animasyonu
        if self.currentFrame == 0 and self.animTimer > LOGO_PAUSE_DURATION:
            self.animTimer = 0
            self.currentFrame += 1
            # self._draw_restart_button() # <--- Çizim zaten draw() içinde yapılıyor
        # <--- === DÜZELTME 1: Animasyonun son karede durması için ===
        elif 0 < self.currentFrame < len(_AnimConfig.frames) - 1:
        # =========================================================
            if self.animTimer >= _AnimConfig.msPerFrame:
                self.currentFrame += 1
                # self._draw_restart_button() # <--- Çizim zaten draw() içinde yapılıyor

        # <--- === DÜZELTME 2: Döngüye neden olan bloğu kaldır ===
        # elif (not self.altGameModeActive) and self.currentFrame == len(_AnimConfig.frames):
        #     self.reset()
        #     return
        # =====================================================

        # Game Over yazısı (Alt game metni / flashing)
        altTextCfg = sprite_definition_by_type["original"].get("altGameOverTextConfig")
        if self.altGameModeActive and altTextCfg:
            if altTextCfg.get("flashing"):
                if self.flashCounter < FLASH_ITERATIONS and self.flashTimer > altTextCfg["flashDuration"]:
                    self.flashTimer = 0
                    self.originalText = not self.originalText
                    self._clear_game_over_text_bounds()
                    if self.originalText:
                        self._draw_game_over_text(_DefaultPanelDims, use_alt_text=False)
                        self.flashCounter += 1
                    else:
                        self._draw_game_over_text(altTextCfg, use_alt_text=True)
                elif self.flashCounter >= FLASH_ITERATIONS:
                    # <--- DÜZELTME 3: Döngüyü kaldır, sadece geç ===
                    # self.reset()
                    # return
                    pass
                    # ==============================================
            else:
                # flash yoksa, doğrudan alt metni bas
                self._clear_game_over_text_bounds(altTextCfg)
                self._draw_game_over_text(altTextCfg, use_alt_text=True)
