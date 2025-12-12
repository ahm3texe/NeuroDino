# distance_meter.py
# 1:1 pygame port of Chrome Dino distance_meter.ts

from __future__ import annotations

from typing import List, Optional, Tuple, Any

import pygame

try:
    from constants import IS_HIDPI, IS_RTL
except ImportError:
    from .constants import IS_HIDPI, IS_RTL
from offline_sprite_definitions import CollisionBox
# SpritePosition: dict-like {"x": int, "y": int}
from utils import getTimeStamp


# ---------------------------------------------------------------------------
# Dimensions / Config (TS'deki enum sabitleri)
# ---------------------------------------------------------------------------
class _Dim:
    WIDTH = 10        # tek rakam kaynağındaki genişlik
    HEIGHT = 13       # tek rakam kaynağındaki yükseklik
    DEST_WIDTH = 11   # hedefte rakamlar arası adım


class _Cfg:
    MAX_DISTANCE_UNITS = 5
    ACHIEVEMENT_DISTANCE = 100
    COEFFICIENT = 0.025
    FLASH_DURATION = 1000 / 4          # ms
    FLASH_ITERATIONS = 3
    HIGH_SCORE_HIT_AREA_PADDING = 4


class DistanceMeter:
    achievement: bool = False

    def __init__(self, canvas: pygame.Surface, spritePos: dict, canvasWidth: int,
                 imageSpriteProvider: Any) -> None:
        """Handles displaying the distance meter."""
        self.canvas = canvas
        self.canvasCtx = canvas  # pygame.Surface
        self.image: pygame.Surface = imageSpriteProvider.getRunnerImageSprite()
        self.spritePos = spritePos  # {"x": int, "y": int}

        self.x: int = 0
        self.y: int = 5
        self.maxScore: int = 0
        self.highScore: str = ""
        self._show_high_score: bool = False
        self.digits: List[str] = []
        self.defaultString: str = ""
        self.flashTimer: float = 0.0
        self.flashIterations: int = 0

        self.flashingRafId = None  # TS uyumu için placeholder
        self.highScoreBounds: Optional[CollisionBox] = None
        self.highScoreFlashing: bool = False
        self.maxScoreUnits: int = _Cfg.MAX_DISTANCE_UNITS
        self.canvasWidth: int = canvasWidth
        self.frameTimeStamp: Optional[int] = None

        self.init(canvasWidth)

    # -----------------------------------------------------------------------
    # TS parity methods
    # -----------------------------------------------------------------------
    def init(self, width: int) -> None:
        """Initialise the distance meter to '00000'."""
        maxDistanceStr = ""
        self.calcXpos(width)
        self.maxScore = self.maxScoreUnits
        for i in range(self.maxScoreUnits):
            self.draw(i, 0)
            self.defaultString += "0"
            maxDistanceStr += "9"
        self.maxScore = int(maxDistanceStr, 10)

    def calcXpos(self, canvasWidth: int) -> None:
        """Calculate the xPos in the canvas."""
        self.x = canvasWidth - (_Dim.DEST_WIDTH * (self.maxScoreUnits + 1))

    def _blit_sprite_digit(self, source_x: int, source_y: int, source_w: int, source_h: int,
                           dest_x: int, dest_y: int, dest_w: int, dest_h: int) -> None:
        """Helper: copy region from sprite sheet and blit to canvas, handling HiDPI."""
        scale = 2 if IS_HIDPI else 1
        sx = source_x * scale
        sy = source_y * scale
        sw = source_w * scale
        sh = source_h * scale

        src_rect = pygame.Rect(sx, sy, sw, sh)
        frame = self.image.subsurface(src_rect).copy()

        # hedef boyut (lo-dpi mantığı) sabit: WIDTH/HEIGHT
        if frame.get_width() != dest_w or frame.get_height() != dest_h:
            frame = pygame.transform.scale(frame, (dest_w, dest_h))

        self.canvasCtx.blit(frame, (dest_x, dest_y))

    def draw(self, digitPos: int, value: int, highScore: bool = False) -> None:
        """Draw a digit to canvas."""
        sourceWidth = _Dim.WIDTH
        sourceHeight = _Dim.HEIGHT
        sourceX = _Dim.WIDTH * value
        sourceY = 0

        # Hedefte rakamlar dEST_WIDTH ile yan yana
        targetX = digitPos * _Dim.DEST_WIDTH
        targetY = self.y
        targetWidth = _Dim.WIDTH
        targetHeight = _Dim.HEIGHT

        # Kaynak sprite sheet ofsetleri
        sourceX += int(self.spritePos["x"])
        sourceY += int(self.spritePos["y"])

        # RTL konumlama (TS'deki translate + scale yerine mutlak X hesaplıyoruz)
        if IS_RTL:
            if highScore:
                translateX = self.canvasWidth - (_Dim.WIDTH * (self.maxScoreUnits + 3))
            else:
                translateX = self.canvasWidth - _Dim.WIDTH
            dest_x = translateX - targetX  # ayna etkisi nedeniyle ters
        else:
            highScoreX = self.x - (self.maxScoreUnits * 2) * _Dim.WIDTH
            dest_base = highScoreX if highScore else self.x
            dest_x = dest_base + targetX

        dest_y = targetY

        self._blit_sprite_digit(sourceX, sourceY, sourceWidth, sourceHeight,
                                dest_x, dest_y, targetWidth, targetHeight)

    def getActualDistance(self, distance: float) -> int:
        """Convert pixel distance to a 'real' distance."""
        return int(round(distance * _Cfg.COEFFICIENT)) if distance else 0

    def update(self, deltaTime: float, distance: float) -> bool:
        """Update the distance meter. Returns whether achievement sound should play."""
        paint = True
        playSound = False

        if not self.achievement:
            distance_real = self.getActualDistance(distance)

            # Score genişlerse bir haneyi arttır
            if distance_real > self.maxScore and self.maxScoreUnits == _Cfg.MAX_DISTANCE_UNITS:
                self.maxScoreUnits += 1
                self.maxScore = int(f"{self.maxScore}9", 10)

            if distance_real > 0:
                # Achievement
                if distance_real % _Cfg.ACHIEVEMENT_DISTANCE == 0:
                    self.achievement = True
                    self.flashTimer = 0.0
                    playSound = True

                # '00042' gibi sol sıfırlarla dizgi
                s = (self.defaultString + str(distance_real))[-self.maxScoreUnits:]
                self.digits = list(s)
            else:
                self.digits = list(self.defaultString)
        else:
            # Achievement flashing
            if self.flashIterations <= _Cfg.FLASH_ITERATIONS:
                self.flashTimer += deltaTime
                if self.flashTimer < _Cfg.FLASH_DURATION:
                    paint = False
                elif self.flashTimer > _Cfg.FLASH_DURATION * 2:
                    self.flashTimer = 0.0
                    self.flashIterations += 1
            else:
                self.achievement = False
                self.flashIterations = 0
                self.flashTimer = 0.0

        # Draw digits
        if paint:
            for i in range(len(self.digits) - 1, -1, -1):
                self.draw(i, int(self.digits[i]))

        # High score daima üstüne çizilir
        self.drawHighScore()

        # (TS: flashHighScore ayrı rAF ile çalışır) — burada da ilerletelim:
        if self.highScoreFlashing:
            self._step_high_score_flash(deltaTime)

        return playSound

    def drawHighScore(self) -> None:
        if not getattr(self, "_show_high_score", False) or len(self.highScore) == 0:
            return

        # Yüksek skoru biraz saydam çiz
        # pygame: global alpha yok; yüzeyi geçici modla doldurmak yerine direkt çiziyoruz
        # (görsel eşleşme tam değil ama işlev aynı)
        for i in range(len(self.highScore) - 1, -1, -1):
            ch = self.highScore[i]
            # 0-9 normal; 'H'->10, 'I'->11
            if ch.isdigit():
                pos = int(ch)
            elif ch == "H":
                pos = 10
            elif ch == "I":
                pos = 11
            else:
                continue
            self.draw(i, pos, True)

    def setHighScore(self, distance: float) -> None:
        distance_real = self.getActualDistance(distance)
        s = (self.defaultString + str(distance_real))[-self.maxScoreUnits:]
        self.highScore = "HI " + s
        self._show_high_score = True

    # -----------------------------------------------------------------------
    # High score mouse/touch alanı ve flashing
    # -----------------------------------------------------------------------
    def hasClickedOnHighScore(self, e: Any) -> bool:
        """Pygame uyarlaması: e.pos veya (x,y) tuple bekler."""
        if isinstance(e, tuple) and len(e) == 2:
            x, y = e
        elif hasattr(e, "pos"):
            x, y = getattr(e, "pos")
        else:
            # Diğer event tipleri desteklenmiyor; dışarıdan (x,y) ile çağır.
            return False

        self.highScoreBounds = self.getHighScoreBounds()
        hb = self.highScoreBounds
        return (x >= hb.x and x <= hb.x + hb.width and
                y >= hb.y and y <= hb.y + hb.height)

    def getHighScoreBounds(self) -> CollisionBox:
        return CollisionBox(
            x=(self.x - (self.maxScoreUnits * 2) * _Dim.WIDTH) - _Cfg.HIGH_SCORE_HIT_AREA_PADDING,
            y=self.y,
            width=_Dim.WIDTH * (len(self.highScore) + 1) + _Cfg.HIGH_SCORE_HIT_AREA_PADDING,
            height=_Dim.HEIGHT + (_Cfg.HIGH_SCORE_HIT_AREA_PADDING * 2),
        )

    def _step_high_score_flash(self, deltaTime: float) -> None:
        """TS'deki requestAnimationFrame döngüsünü deltaTime ile taklit eder."""
        now = getTimeStamp()
        prev = self.frameTimeStamp or now
        self.frameTimeStamp = now

        # Reached max flashes?
        if self.flashIterations > _Cfg.FLASH_ITERATIONS * 2:
            self.cancelHighScoreFlashing()
            return

        paint = True
        self.flashTimer += (now - prev) if deltaTime == 0 else deltaTime
        if self.flashTimer < _Cfg.FLASH_DURATION:
            paint = False
        elif self.flashTimer > _Cfg.FLASH_DURATION * 2:
            self.flashTimer = 0.0
            self.flashIterations += 1

        if paint:
            self.drawHighScore()
        else:
            self.clearHighScoreBounds()

    def clearHighScoreBounds(self) -> None:
        if not self.highScoreBounds:
            self.highScoreBounds = self.getHighScoreBounds()
        hb = self.highScoreBounds
        rect = pygame.Rect(hb.x, hb.y, hb.width, hb.height)
        pygame.draw.rect(self.canvasCtx, (247, 247, 247), rect)

    def startHighScoreFlashing(self) -> None:
        self.highScoreFlashing = True
        # TS rAF yerine zaman damgası başlat
        self.frameTimeStamp = getTimeStamp()
        self.flashTimer = 0.0
        self.flashIterations = 0

    def isHighScoreFlashing(self) -> bool:
        return self.highScoreFlashing

    def cancelHighScoreFlashing(self) -> None:
        self.flashIterations = 0
        self.flashTimer = 0.0
        self.highScoreFlashing = False
        self.clearHighScoreBounds()
        self.drawHighScore()

    def resetHighScore(self) -> None:
        self.highScore = ""
        self._show_high_score = False
        self.cancelHighScoreFlashing()

    def reset(self) -> None:
        """Reset the distance meter back to '00000'."""
        self.update(0, 0)
        self.achievement = False