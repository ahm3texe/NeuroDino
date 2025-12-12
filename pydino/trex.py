# trex.py
# pygame port of Chrome Dino trex.ts (config fixed to avoid dataclass issues)

from __future__ import annotations
from typing import Dict, List, Optional, Any
import random # Göz kırpma için random import edildi

import pygame

def _blit_region_alpha(dst: pygame.Surface,
                       src: pygame.Surface,
                       src_rect: pygame.Rect,
                       dest_xy: tuple[int, int],
                       dest_wh: tuple[int, int] | None = None,
                       overall_alpha: int | None = None) -> None:
    """
    Sprite sheet'ten bir dikdörtgeni per‑pixel alpha veya colorkey ile çizer.
    Colorkey ve convert() kullanarak siyah arka planı kaldırır.
    """
    try:
        # Alt yüzey al, colorkey uygula ve convert et.
        frame = src.subsurface(src_rect).copy() 
        frame.set_colorkey((0, 0, 0)) # Siyah rengi transparan anahtar olarak ayarla
        frame = frame.convert() # Convert (alpha değil) çağırarak colorkey'i etkinleştir.

        if dest_wh is not None and (frame.get_width(), frame.get_height()) != dest_wh:
            # Ölçeklemede alpha kullanılmadığı için scale kullanmak daha iyi olabilir
            frame = pygame.transform.scale(frame, dest_wh)
            # Ölçekleme sonrası yeni yüzeye colorkey ayarını tekrar uygulayın
            frame.set_colorkey((0, 0, 0)) 

        # Alpha ayarı (Colorkey kullanıldığı için bu satırlar büyük ihtimalle etkisiz kalacaktır)
        if overall_alpha is not None:
            frame.set_alpha(overall_alpha)
        else:
            frame.set_alpha(None) # Alpha'yı kaldırır (varsayılan opaklık)
            
        dst.blit(frame, dest_xy)
    except ValueError:
        # Subsurface koordinatları hatalıysa görmezden gel (geçici çözüm)
        # print(f"Uyarı: Geçersiz subsurface rect: {src_rect}")
        pass


try:
    from constants import DEFAULT_DIMENSIONS, FPS
    from offline_sprite_definitions import CollisionBox
except ImportError:
    from .constants import DEFAULT_DIMENSIONS, FPS
    from .offline_sprite_definitions import CollisionBox

# utils.get_time_stamp -> getTimeStamp fallback to pygame time
try:
    from utils import get_time_stamp as getTimeStamp
except Exception:  # fallback
    def getTimeStamp() -> int:
        return pygame.time.get_ticks()


# ---------------- Config helper (dict + attribute access) ------------------
class TrexConfigDict(dict):
    """Allow both dict-style and attribute-style access."""
    def __getattr__(self, key):
        try:
            return self[key]
        except KeyError as e:
            raise AttributeError(key) from e
    def __setattr__(self, key, value):
        self[key] = value


# Default base config and jump configs (mirrors trex.ts)
DEFAULT_TREX_BASE: Dict[str, Any] = {
    "dropVelocity": -5,
    "flashOff": 175,
    "flashOn": 100,
    "height": 47, 
    "heightDuck": 25,
    "introDuration": 1500,
    "speedDropCoefficient": 3,
    "spriteWidth": 262,
    "startXPos": 10, # <--- Başlangıç X pozisyonunu tanımla
    "width": 44,
    "widthDuck": 59,
    "invertJump": False,
    # Optional widths used in alt game states
    "widthCrashed": None,
    "widthJump": None,
}

SLOW_JUMP: Dict[str, Any] = {
    "gravity": 0.25,
    "maxJumpHeight": 50,
    "minJumpHeight": 45,
    "initialJumpVelocity": -20,
}

NORMAL_JUMP: Dict[str, Any] = {
    "gravity": 0.6,
    "maxJumpHeight": 30,
    "minJumpHeight": 30,
    "initialJumpVelocity": -10,
}


# ---------------- Collision boxes ------------------
collisionBoxes_trex: Dict[str, List[CollisionBox]] = {
    "ducking": [CollisionBox(1, 18, 55, 25)],
    "running": [
        CollisionBox(22, 0, 17, 16),
        CollisionBox(1, 18, 30, 9),
        CollisionBox(10, 35, 14, 8),
        CollisionBox(1, 24, 29, 5),
        CollisionBox(5, 30, 21, 4),
        CollisionBox(9, 34, 15, 4),
    ],
}


# ---------------- Status enum ------------------
class Status:
    CRASHED = 0
    DUCKING = 1
    JUMPING = 2
    RUNNING = 3
    WAITING = 4


# Animation frames (pixels from sprite origin)
BLINK_TIMING = 7000
# Gözün kapalı kalacağı (ms) — orijinale göre daha kısa
BLINK_CLOSED_MS = 120
FrameInfo = Dict[str, Any]

# DÜZELTME: Orijinal TS kodundaki gibi, WAITING için Göz Açık (ilk frame 0), Göz Kapalı (ikinci frame 44)
animFrames: Dict[int, FrameInfo] = {
    Status.WAITING: {"frames": [0, 44], "msPerFrame": 1000 / 3},
    Status.RUNNING: {"frames": [88, 132], "msPerFrame": 1000 / 12},
    Status.CRASHED: {"frames": [220], "msPerFrame": 1000 / 60},
    Status.JUMPING: {"frames": [0], "msPerFrame": 1000 / 60},
    Status.DUCKING: {"frames": [264, 323], "msPerFrame": 1000 / 8},
}


class Trex:
    # resourceProvider: ConfigProvider & GameStateProvider & ImageSpriteProvider & (opt) GeneratedSoundFxProvider

    def __init__(self, canvas: pygame.Surface, spritePos: Dict[str, int], resourceProvider: Any):
        self.canvasCtx: pygame.Surface = canvas
        self.spritePos: Dict[str, int] = spritePos
        self.resourceProvider = resourceProvider

        # Config (dict-like) : default base + normal jump
        self.config = TrexConfigDict(**{**DEFAULT_TREX_BASE, **NORMAL_JUMP})

        # Position / state
        self.playingIntro: bool = False
        self.xPos: int = 0 
        self.yPos: int = 0
        self.xInitialPos: int = self.config.startXPos 
        self.groundYPos: int = 0
        self.jumpCount: int = 0
        self.ducking: bool = False
        self.blinkCount: int = 0
        self.jumping: bool = False
        self.speedDrop: bool = False
        self.status: int = Status.WAITING
        self.reachedMinHeight: bool = False
        self.altGameModeEnabled: bool = False
        self.flashing: bool = False

        # Animation / time
        self.currentFrameIndex: int = 0 # frame index (0 or 1 for WAITING/RUNNING/DUCKING)
        self.currentAnimFrames: List[int] = [] # x coordinates from sprite sheet
        self.blinkDelay: int = 0
        self.animStartTime: int = 0 # Used for blink timing
        self.timer: float = 0.0 # Used for general frame advancement
        self.msPerFrame: float = 1000.0 / FPS

        # Motion / jump
        self.jumpVelocity: float = 0.0
        self.minJumpHeight: int = 0

        # Ground position
        runnerDefaultDimensions = DEFAULT_DIMENSIONS
        runnerBottomPadding = self.resourceProvider.getConfig().bottomPad
        assert runnerBottomPadding is not None
        self.groundYPos = runnerDefaultDimensions.height - self.config.height - int(runnerBottomPadding)
        self.yPos = self.groundYPos
        self.minJumpHeight = self.groundYPos - self.config.minJumpHeight
        self.xPos = self.xInitialPos 

        # İlk update WAITING olarak çağrılacak
        self.update(0, Status.WAITING)

    # ---------------- Speed / config ------------------
    def enableSlowConfig(self):
        jump = SLOW_JUMP if getattr(self.resourceProvider, "hasSlowdown", False) else NORMAL_JUMP
        for k, v in jump.items():
            self.config[k] = v
        self.adjustAltGameConfigForSlowSpeed()

    def enableAltGameMode(self, spritePos: Dict[str, int]):
        self.altGameModeEnabled = True
        self.spritePos = spritePos
        spriteDefinition = self.resourceProvider.getSpriteDefinition()
        # Adjust bottom placement
        self.groundYPos = DEFAULT_DIMENSIONS.height - self.config.height - spriteDefinition.get("bottomPad", 10)
        self.yPos = self.groundYPos
        self.reset()

    def adjustAltGameConfigForSlowSpeed(self, gravityValue: Optional[float] = None):
        if getattr(self.resourceProvider, "hasSlowdown", False):
            if gravityValue is not None:
                self.config["gravity"] = gravityValue / 1.5
            self.config["minJumpHeight"] = int(self.config["minJumpHeight"] * 1.5)
            self.config["maxJumpHeight"] = int(self.config["maxJumpHeight"] * 1.5)
            self.config["initialJumpVelocity"] *= 1.5

    # ---------------- Visual / state ------------------
    def setFlashing(self, status: bool):
        self.flashing = status

    def setJumpVelocity(self, setting: float):
        self.config["initialJumpVelocity"] = -setting
        self.config["dropVelocity"] = -setting / 2.0

    # <--- === GÜNCELLENMİŞ UPDATE FONKSİYONU (Orijinal TS Mantığına Daha Yakın) === --->
    def update(self, deltaTime: float, status: Optional[int] = None):
        self.timer += deltaTime # Genel zamanlayıcıyı ilerlet

        # Update the status if changed
        if status is not None and self.status != status:
            self.status = status
            self.currentFrameIndex = 0
            self.msPerFrame = animFrames[status]["msPerFrame"]
            self.currentAnimFrames = animFrames[status]["frames"]
            self.timer = 0 # Reset general timer only when status changes
            if status == Status.WAITING:
                self.animStartTime = getTimeStamp()
                self._setBlinkDelay()
        
        # Game intro animation
        if self.playingIntro and self.xPos < self.config.startXPos:
            self.xPos += round((self.config.startXPos / self.config.introDuration) * deltaTime)

        # --- Drawing and Animation Frame Logic ---
        if self.status == Status.WAITING:
            self._blink(getTimeStamp()) # Blink handles its own drawing and timing
        else:
            # Draw current frame for non-WAITING states
            sprite_x_to_draw = self.currentAnimFrames[self.currentFrameIndex]
            self.draw(sprite_x_to_draw, 0)

            # Advance frame based on timer for RUNNING and DUCKING
            # Orijinal TS'deki gibi, yanıp sönme durumunda da kare ilerler
            # Sadece çizim sırasında alpha değişir.
            if self.timer >= self.msPerFrame:
                 if self.status in [Status.RUNNING, Status.DUCKING]:
                     self.currentFrameIndex = (self.currentFrameIndex + 1) % len(self.currentAnimFrames)
                 self.timer = 0 # Reset general timer after frame change

        # Speed drop becomes duck once on ground
        if self.speedDrop and self.yPos == self.groundYPos:
            self.speedDrop = False
            self.setDuck(True)
    # <--- === UPDATE BİTİŞ === --->

    def draw(self, x: int, y: int):
        # Force WAITING state to always use the blink frame, regardless of caller.
        if self.status == Status.WAITING:
            wait_frames = animFrames[Status.WAITING]["frames"]
            if wait_frames:
                idx = self.currentFrameIndex % len(wait_frames)
                x = wait_frames[idx]
        runnerImageSprite: pygame.Surface = self.resourceProvider.getRunnerImageSprite()
        assert runnerImageSprite is not None

        sourceX = x
        sourceY = y
        sourceWidth = self.config.widthDuck if (self.ducking and self.status != Status.CRASHED) else self.config.width
        sourceHeight = self.config.height

        outputHeight = sourceHeight
        outputWidth = self.config.width if self.status != Status.CRASHED else (self.config.widthCrashed or self.config.width)

        # Alt-mode width adjustments
        if self.altGameModeEnabled:
            if self.jumping and self.status != Status.CRASHED and self.config.widthJump:
                sourceWidth = self.config.widthJump
            elif self.status == Status.CRASHED and self.config.widthCrashed:
                sourceWidth = self.config.widthCrashed

        # Pygame'de HIDPI yönetimi farklıdır, scale faktörünü doğrudan kullanmıyoruz
        # Sprite tanımındaki x,y,w,h değerlerini doğrudan kullanacağız
        # IS_HIDPI kontrolü kaldırıldı
        scale = 1 # Varsayılan ölçek

        sx = int(self.spritePos["x"] + sourceX) # * scale kaldırıldı
        sy = int(self.spritePos["y"] + sourceY) # * scale kaldırıldı
        sw = int(sourceWidth)                   # * scale kaldırıldı
        sh = int(sourceHeight)                  # * scale kaldırıldı
        
        # Koordinatların geçerli olup olmadığını kontrol et
        img_w, img_h = runnerImageSprite.get_size()
        # spritePos genellikle LDPI içindir, HDPI sprite kullanıyorsak düzeltme gerekebilir
        # Şimdilik LDPI varsayalım
        if sx < 0 or sy < 0 or sx + sw > img_w or sy + sh > img_h:
             # print(f"Uyarı: Geçersiz kaynak koordinatları: Rect({sx}, {sy}, {sw}, {sh}), Img Size: ({img_w}, {img_h})")
             return 

        src_rect = pygame.Rect(sx, sy, sw, sh)

        # Target size (logical output) - Ölçekleme yoksa kaynakla aynı
        dw = int(sourceWidth) # Output width düzeltmesi
        dh = int(sourceHeight) # Output height düzeltmesi

        # Hedef boyutları config'den al (ducking durumu için)
        dw_config = self.config.widthDuck if (self.ducking and self.status != Status.CRASHED) else outputWidth
        dh_config = outputHeight
        dw = int(dw_config)
        dh = int(dh_config)


        # Alt jump xOffset (optional in sprite definition)
        dx = self.xPos
        if self.altGameModeEnabled and self.jumping and self.status != Status.CRASHED:
            # Alt game mode desteklenmiyor, bu bloğu yoksayabiliriz şimdilik
            pass 
            # spriteDefinition = self.resourceProvider.getSpriteDefinition()
            # tRexDef = spriteDefinition.get("tRex")
            # if tRexDef and isinstance(tRexDef, dict):
            #     xo = tRexDef.get("jumping", {}).get("xOffset", 0)
            #     dx = self.xPos - xo # scale kaldırıldı

        # Flashing alpha kontrolü
        overall_alpha = None
        if self.flashing:
            # Orijinal TS mantığına daha yakın: Genel zamanlayıcıyı kullan
            flash_timer_check = self.timer % (self.config.flashOn + self.config.flashOff)
            if flash_timer_check < self.config.flashOn:
                overall_alpha = 128 # Yarı saydam
            # else: Tam opak (alpha=None) - _blit_region_alpha bunu halleder
        
        # Per-pixel alpha safe blit (prevents black boxes)
        _blit_region_alpha(
            dst=self.canvasCtx,
            src=runnerImageSprite,
            src_rect=src_rect,
            dest_xy=(int(dx), int(self.yPos)), 
            dest_wh=(dw, dh), # Hedef boyutları kullan
            overall_alpha=overall_alpha,
        )

    def _setBlinkDelay(self):
        # Orijinal TS Math.ceil(Math.random() * BLINK_TIMING) -> 1 ile BLINK_TIMING arası
        self.blinkDelay = random.randint(1, BLINK_TIMING) 

    # <--- === GÜNCELLENMİŞ BLINK FONKSİYONU (Orijinal TS Mantığına Daha Yakın) === --->
    def _blink(self, time_ms: int):
        """Make t-rex blink at random intervals."""
        deltaTime = time_ms - self.animStartTime

        # WAITING animasyon bilgilerini al
        wait_anim = animFrames[Status.WAITING]
        wait_frames = wait_anim["frames"] # [Göz Açık X, Göz Kapalı X]
        closed_eye_duration = BLINK_CLOSED_MS  # Gözün kapalı kalma süresi (ms)

        # Geçerli sprite X koordinatını belirle
        sprite_x_to_draw = wait_frames[self.currentFrameIndex]

        # Dinozoru çiz
        self.draw(sprite_x_to_draw, 0)

        # Zamanlamayı kontrol et ve kareyi değiştir (Orijinal TS Mantığı)
        # Eğer göz kırpma zamanı geldiyse (ve şu an göz açıksa - index 0)
        if self.currentFrameIndex == 0 and deltaTime >= self.blinkDelay:
             self.currentFrameIndex = 1 # Göz kapalı kareye geç (index 1)
             self.animStartTime = time_ms # Gözün kapalı kalma süresini başlat
        
        # Eğer göz kapalıysa (index 1) ve kapalı kalma süresi dolduysa
        elif self.currentFrameIndex == 1 and deltaTime >= closed_eye_duration:
             self.currentFrameIndex = 0 # Göz açık kareye geç (index 0)
             self._setBlinkDelay()      # Yeni bir blink zamanı ayarla
             self.animStartTime = time_ms # Gözün açık kalma süresini başlat
             self.blinkCount += 1
    # <--- === BLINK BİTİŞ === --->

    # ---------------- Jump / motion (DEĞİŞİKLİK YOK) ------------------
    def startJump(self, speed: float):
        if not self.jumping:
            # self.update(0, Status.JUMPING) # update'i direkt çağırma, state'i ayarla
            self.status = Status.JUMPING
            self.currentFrameIndex = 0
            self.timer = 0
            self.msPerFrame = animFrames[Status.JUMPING]["msPerFrame"]
            self.currentAnimFrames = animFrames[Status.JUMPING]["frames"]
            
            self.jumpVelocity = self.config.initialJumpVelocity - (speed / 10.0)
            self.jumping = True
            self.reachedMinHeight = False
            self.speedDrop = False
            if self.config.invertJump:
                self.minJumpHeight = self.groundYPos + self.config.minJumpHeight

    def endJump(self):
        if self.reachedMinHeight and self.jumpVelocity < self.config.dropVelocity:
            self.jumpVelocity = self.config.dropVelocity

    def updateJump(self, deltaTime: float):
        # msPerFrame JUMPING durumundan alınmalı
        msPerFrame = animFrames[Status.JUMPING]["msPerFrame"]
        framesElapsed = (deltaTime / msPerFrame) if msPerFrame > 0 else 1.0

        if self.speedDrop:
            self.yPos += round(self.jumpVelocity * self.config.speedDropCoefficient * framesElapsed)
        elif self.config.invertJump:
            self.yPos -= round(self.jumpVelocity * framesElapsed)
        else:
            self.yPos += round(self.jumpVelocity * framesElapsed)

        self.jumpVelocity += self.config.gravity * framesElapsed

        # Min height reached?
        if (self.config.invertJump and (self.yPos > self.minJumpHeight)) or \
           ((not self.config.invertJump) and (self.yPos < self.minJumpHeight)) or \
           self.speedDrop:
            self.reachedMinHeight = True

        # Max height logic
        if (self.config.invertJump and (self.yPos > -self.config.maxJumpHeight)) or \
           ((not self.config.invertJump) and (self.yPos < self.config.maxJumpHeight)) or \
           self.speedDrop:
            self.endJump()

        # Back down at ground level. Jump completed.
        if (self.config.invertJump and (self.yPos < self.groundYPos)) or \
           ((not self.config.invertJump) and (self.yPos > self.groundYPos)):
            self.reset()
            self.jumpCount += 1
            if getattr(self.resourceProvider, "hasAudioCues", False):
                if hasattr(self.resourceProvider, "getGeneratedSoundFx"):
                    try:
                        self.resourceProvider.getGeneratedSoundFx().loopFootSteps()
                    except Exception:
                        pass

    def setSpeedDrop(self):
        self.speedDrop = True
        self.jumpVelocity = 1

    def setDuck(self, isDucking: bool):
        if isDucking and self.status != Status.DUCKING:
            # self.update(0, Status.DUCKING) # update'i çağırma
            self.status = Status.DUCKING
            self.currentFrameIndex = 0
            self.timer = 0
            self.msPerFrame = animFrames[Status.DUCKING]["msPerFrame"]
            self.currentAnimFrames = animFrames[Status.DUCKING]["frames"]
            self.ducking = True
        elif self.status == Status.DUCKING and not isDucking: 
            # self.update(0, Status.RUNNING) # update'i çağırma
            self.status = Status.RUNNING
            self.currentFrameIndex = 0
            self.timer = 0
            self.msPerFrame = animFrames[Status.RUNNING]["msPerFrame"]
            self.currentAnimFrames = animFrames[Status.RUNNING]["frames"]
            self.ducking = False

    def reset(self):
        self.xPos = self.xInitialPos # reset'te xInitialPos'a dönmeli
        self.yPos = self.groundYPos
        self.jumpVelocity = 0
        self.jumping = False
        self.ducking = False
        
        self.status = Status.RUNNING # Sadece durumu ayarla
        self.currentFrameIndex = 0   # Animasyonu sıfırla
        self.timer = 0               # Zamanlayıcıyı sıfırla
        self.currentAnimFrames = animFrames[Status.RUNNING]["frames"] # Kareleri ayarla
        self.msPerFrame = animFrames[Status.RUNNING]["msPerFrame"] # Hızı ayarla

        self.speedDrop = False
        self.jumpCount = 0

    def getCollisionBoxes(self) -> List[CollisionBox]:
        return collisionBoxes_trex["ducking"] if self.ducking else collisionBoxes_trex["running"]

