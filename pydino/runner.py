from __future__ import annotations
import math
import os
import pygame
from dataclasses import dataclass

from typing import Dict, Optional, List, Any

# Debug overlay (optional)
try:
    from debug_overlay import CollisionDebugOverlay
except Exception:
    CollisionDebugOverlay = None  # overlay is optional; keep game running if missing

# NumPy import'unu en başta yapıyoruz
try:
    import numpy as np
    import pygame.surfarray as sarr
    NUMPY_AVAILABLE = True
except ImportError:
    NUMPY_AVAILABLE = False
    
# ==== USER PATHS (dynamic) ==================================================
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
ASSETS_DIR = os.path.join(BASE_DIR, "assets")
SOUNDS_DIR = os.path.join(BASE_DIR, "sounds")

SPRITE_PATH = os.path.join(ASSETS_DIR, "100-offline-sprite.png")
SND_BUTTON  = os.path.join(SOUNDS_DIR, "button-press.mp3")
SND_HIT     = os.path.join(SOUNDS_DIR, "hit.mp3")
SND_SCORE   = os.path.join(SOUNDS_DIR, "score-reached.mp3")
# ============================================================================

# ==== Imports from your ported modules ======================================
# ==== Imports from your ported modules ======================================
try:
    from constants import FPS
    from dimensions import Dimensions
    from horizon import Horizon
    from distance_meter import DistanceMeter
    from game_over_panel import GameOverPanel
    from trex import Trex, Status as TrexStatus
    from offline_sprite_definitions import (
        sprite_definition_by_type,    
        CollisionBox, GAME_TYPE
    )
except ImportError:
    from .constants import FPS
    from .dimensions import Dimensions
    from .horizon import Horizon
    from .distance_meter import DistanceMeter
    from .game_over_panel import GameOverPanel
    from .trex import Trex, Status as TrexStatus
    from .offline_sprite_definitions import (
        sprite_definition_by_type,    
        CollisionBox, GAME_TYPE
    )
    print("Lütfen tüm .py dosyalarının aynı dizinde olduğundan emin olun.")
    raise SystemExit(1)

# ==== Configs (merged from defaultBaseConfig + normalModeConfig) =============
@dataclass 
class Config:
    # defaultBaseConfig
    audiocueProximityThreshold: int = 190
    audiocueProximityThresholdMobileA11y: int = 250
    bgCloudSpeed: float = 0.2
    bottomPad: int = 10
    canvasInViewOffset: int = -10
    clearTime: int = 3000
    cloudFrequency: float = 0.5
    fadeDuration: float = 1
    flashDuration: int = 1000
    gameoverClearTime: int = 1200
    initialJumpVelocity: float = 12
    invertFadeDuration: int = 12000
    maxBlinkCount: int = 3
    maxClouds: int = 6
    maxObstacleLength: int = 3
    maxObstacleDuplication: int = 2
    resourceTemplateId: str = "audio-resources"
    speedDropCoefficient: float = 3
    arcadeModeInitialTopPosition: int = 35
    arcadeModeTopPositionPercent: float = 0.1
    # normalModeConfig
    acceleration: float = 0.001
    gapCoefficient: float = 0.6
    invertDistance: int = 700
    maxSpeed: float = 13.0
    mobileSpeedCoefficient: float = 1.2
    speed: float = 6.0


# ==== Utility (canvas scaling / collisions) ==================================
def create_adjusted_box(box: CollisionBox, adj: CollisionBox) -> CollisionBox:
    return CollisionBox(box.x + adj.x, box.y + adj.y, box.width, box.height)

def box_intersect(a: CollisionBox, b: CollisionBox) -> bool:
    return (
        a.x < b.x + b.width and
        a.x + a.width > b.x and
        a.y < b.y + b.height and
        a.height + a.y > b.y
    )

def _get(obj, name, default=None):
    """dict / obje uyumlu alan okuma"""
    if hasattr(obj, name):
        return getattr(obj, name)
    if isinstance(obj, dict):
        return obj.get(name, default)
    return default


# ==== Runner =================================================================
class Runner:
    """
    Pygame orchestrator matching Chrome Dino Runner logic.
    Provides ImageSpriteProvider, GameStateProvider, ConfigProvider interfaces.
    """
    # Key map
    KEY_JUMP = (pygame.K_UP, pygame.K_SPACE)
    KEY_DUCK = (pygame.K_DOWN,)
    KEY_RESTART = (pygame.K_RETURN,)
    
    # Yeni sabitler
    NIGHT_ALPHA_MAX = 180
    VISUAL_INVERT_MS = 1000
    
    def _get_visual_invert_ms(self) -> int:
        ms = self.VISUAL_INVERT_MS
        if self._invert_mode_pixels:
            ms = int(ms * 0.75)
        return max(120, ms)

    def _ease_in_out_cubic(self, t: float) -> float:
        """CSS-like ease-in-out (cubic) for more natural fade perception."""
        if t <= 0.0:
            return 0.0
        if t >= 1.0:
            return 1.0
        if t < 0.5:
            return 4.0 * t * t * t
        return 1.0 - ((-2.0 * t + 2.0) ** 3) / 2.0

    def __init__(self, screen: pygame.Surface, dimensions: Dimensions,
                 use_audio: bool = True) -> None:
        self.screen = screen
        self.dimensions = dimensions
        self.config = Config()
        self.ms_per_frame = 1000.0 / FPS

        # provider state
        self._has_slowdown = False
        self._has_audio_cues = use_audio
        self._alt_game_mode_active = False
        self._alt_game_assets_failed = False
        self._game_type: Optional[str] = None

        # spritesheet (LDPI by default)
        self.sprite_image: Optional[pygame.Surface] = None
        self.sprite_alt_game_image: Optional[pygame.Surface] = None 
        self.sprite_alt_common_image: Optional[pygame.Surface] = None 

        # sprite positions (ldpi)
        self.sprite_def = sprite_definition_by_type["original"]["ldpi"]

        # Components
        self.horizon: Optional[Horizon] = None
        self.distance_meter: Optional[DistanceMeter] = None
        self.trex: Optional[Trex] = None
        self.game_over_panel: Optional[GameOverPanel] = None

        # Game flow flags/state
        self.activated = False
        self.playing = False
        self.playing_intro = False
        self.crashed = False
        self.paused = False
        self.inverted = False
        self.is_dark_mode = False
        self.update_pending = False

        # Intro zamanlayıcı
        self.intro_start_time = 0
        self.INTRO_DURATION = 400  # 400ms
        self.intro_start_width = 44
        # Intro sadece ilk açılışta oynasın
        self.did_intro = False
        
        # Gece modu overlay yüzeyi ve bayrakları
        self._night_overlay = pygame.Surface((self.dimensions.width, self.dimensions.height), pygame.SRCALPHA)
        self._invert_mode_pixels = NUMPY_AVAILABLE 
        # Debug overlay instance (may be None if import failed)
        self.debug = CollisionDebugOverlay() if CollisionDebugOverlay else None

        # Timers & numeric state
        self.time_ms = pygame.time.get_ticks()
        self.distance_ran = 0.0
        self.running_time = 0.0
        self.current_speed = self.config.speed
        self.invert_timer = 0.0
        self.invert_trigger = False
        self.fade_in_timer = 0.0
        self.alt_game_mode_flash_timer: Optional[float] = None
        # Game over bekleme süresi için damga
        self.game_over_time: Optional[int] = None

        # Night-mode state machine
        self._inv_phase = "day"
        self._inv_progress = 0.0
        self._next_invert_score = self.config.invertDistance

        # High score
        self.highest_score = 0
        self.sync_highest_score = False

        # Sounds
        self.snd_button = None
        self.snd_hit = None
        self.snd_score = None
        if self._has_audio_cues:
            self._load_sounds()

        # Load images & init components
        self._load_images()
        self._init_components()

        # Intro başlangıç genişliği (Trex oluştuktan sonra)
        assert self.trex is not None
        trex_width = _get(self.trex.config, "width", 44)
        self.intro_start_width = self.trex.xPos + trex_width

    # ========== Provider interfaces ==========
    @property
    def hasSlowdown(self) -> bool:
        return self._has_slowdown

    @property
    def hasAudioCues(self) -> bool:
        return self._has_audio_cues

    def isAltGameModeEnabled(self) -> bool:
        return False if self._alt_game_assets_failed else False

    def getSpriteDefinition(self) -> Dict[str, Any]:
        return sprite_definition_by_type["original"]

    def getOrigImageSprite(self) -> pygame.Surface:
        assert self.sprite_image is not None
        return self.sprite_image

    def getRunnerImageSprite(self) -> pygame.Surface:
        assert self.sprite_image is not None
        return self.sprite_image

    def getRunnerAltGameImageSprite(self) -> Optional[pygame.Surface]:
        return self.sprite_alt_game_image

    def getAltCommonImageSprite(self) -> Optional[pygame.Surface]:
        return self.sprite_alt_common_image

    def getConfig(self) -> Config:
        return self.config

    # ========== Asset loading ==========
    def _load_images(self) -> None:
        try:
            img = pygame.image.load(SPRITE_PATH).convert_alpha()
            self.sprite_image = img
            self.sprite_def = sprite_definition_by_type["original"]["ldpi"]
        except pygame.error as e:
            print(f"HATA: Sprite dosyası yüklenemedi: {SPRITE_PATH}")
            print(f"Detay: {e}")
            raise e

    def _load_sounds(self) -> None:
        try:
            # Daha stabil/düşük gecikme ve yeterli kanal
            pygame.mixer.pre_init(44100, -16, 2, 512)
            pygame.mixer.init()
            pygame.mixer.set_num_channels(8)

            def _try_load_sound(path: str) -> pygame.mixer.Sound:
                try:
                    return pygame.mixer.Sound(path)
                except Exception:
                    # Yedek uzantıları dene (.wav/.ogg)
                    base, _ = os.path.splitext(path)
                    for ext in ('.wav', '.ogg'):
                        alt = base + ext
                        if os.path.exists(alt):
                            try:
                                return pygame.mixer.Sound(alt)
                            except Exception:
                                continue
                    raise

            self.snd_button = _try_load_sound(SND_BUTTON)
            self.snd_hit    = _try_load_sound(SND_HIT)
            self.snd_score  = _try_load_sound(SND_SCORE)

            # Varsayılan ses seviyeleri
            try:
                self.snd_button.set_volume(0.6)
                self.snd_hit.set_volume(0.8)
                self.snd_score.set_volume(0.7)
            except Exception:
                pass

            self._has_audio_cues = True
        except Exception:
            self._has_audio_cues = False
            self.snd_button = self.snd_hit = self.snd_score = None
            print("Uyarı: Ses dosyaları yüklenemedi, sesler devre dışı bırakıldı.")

    # ========== Init components ==========
    def _init_components(self) -> None:
        self.screen.fill((247, 247, 247))
        self.horizon = Horizon(
            self.screen, self.sprite_def, self.dimensions,
            self.config.gapCoefficient, self
        )
        self.distance_meter = DistanceMeter(
            self.screen, self.sprite_def["textSprite"],
            self.dimensions.width, self
        )
        self.trex = Trex(self.screen, self.sprite_def["tRex"], self)
        
    # ========== Public controls ==========
    def start(self) -> None:
        self.playing = True
        self.paused = False
        
    def stop(self) -> None:
        self.playing = False
        self.paused = True

    def restart(self) -> None:
        assert self.horizon and self.trex and self.distance_meter
        self.playing = True
        self.paused = False
        self.crashed = False
        # Restart'ta intro yok; direkt aktif başla
        self.activated = True
        self.playing_intro = False
        if self.trex:
            self.trex.playing_intro = False
        self.distance_ran = 0.0
        self.running_time = 0.0
        self.current_speed = self.config.speed
        self.time_ms = pygame.time.get_ticks()
        self.horizon.reset()
        self.trex.reset()
        self.distance_meter.reset()
        self._play_sound(self.snd_button)

        # Game over panel reset
        if self.game_over_panel:
            self.game_over_panel.reset()

        # Game-over zamanı sıfırla
        self.game_over_time = None
            
        self.invert(reset=True)

    # ========== Event handling ==========
    def handle_event(self, e: pygame.event.Event) -> None:
        if e.type == pygame.KEYDOWN:
            # CRASH SONRASI:
            #   Enter  -> anında restart
            #   Space/Up -> 1200 ms bekleme kuralı
            if self.crashed:
                if e.key in self.KEY_RESTART:           # Enter
                    self._on_restart(force=True)
                    return
                if e.key in self.KEY_JUMP:              # Space veya Up
                    self._on_restart(force=False)
                    return
            if e.key in self.KEY_JUMP:
                self._on_jump_down()
            elif e.key in self.KEY_DUCK:
                self._on_duck_down()
            elif e.key == pygame.K_F3 and self.debug is not None:
                # Toggle collision debug visualization
                self.debug.enabled = not self.debug.enabled

        elif e.type == pygame.KEYUP:
            if e.key in self.KEY_JUMP:
                self._on_jump_up()
            elif e.key in self.KEY_DUCK:
                self._on_duck_up()
        elif e.type == pygame.WINDOWFOCUSLOST:
            pass

    def _on_jump_down(self) -> None:
        assert self.trex
        if not self.playing and not self.crashed:
            self.start()
        # Havada değil ve eğilmiyorken: zıpla + ses
        if not self.trex.jumping and not self.trex.ducking:
            self._play_sound(self.snd_button)
            self.trex.startJump(self.current_speed)

    def _on_duck_down(self) -> None:
        assert self.trex
        if self.playing:
            if self.trex.jumping:
                self.trex.setSpeedDrop()
            elif not self.trex.ducking:
                self.trex.setDuck(True)

    def _on_jump_up(self) -> None:
        assert self.trex
        if self.playing:
            self.trex.endJump()
        elif self.crashed:
            self._on_restart()

    def _on_duck_up(self) -> None:
        assert self.trex
        self.trex.speedDrop = False
        self.trex.setDuck(False)

    def _on_restart(self, force: bool = False) -> None:
        # force=True ise (Enter), beklemeden anında başlat
        if force:
            self.restart()
            return

        # Space/Up için: gameoverClearTime (1200 ms) bekleme kuralı
        now = pygame.time.get_ticks()
        t0 = self.game_over_time if self.game_over_time is not None else self.time_ms
        if now - t0 >= self.config.gameoverClearTime:
            self.restart()

    # ========== Update loop ==========
    def update(self) -> None:
        """Call this once per frame from your game loop."""
        assert self.trex and self.horizon and self.distance_meter
        now = pygame.time.get_ticks()
        delta = now - self.time_ms
        self.time_ms = now

        # Alt game flash timer
        if self.alt_game_mode_flash_timer is not None:
            if self.alt_game_mode_flash_timer <= 0:
                self.alt_game_mode_flash_timer = None
                self.trex.setFlashing(False)
            else:
                self.alt_game_mode_flash_timer -= delta
                self.trex.update(delta)
                delta = 0

        # 1. EKRANI TEMİZLE
        self.screen.fill((247, 247, 247)) 

        # 2. GÜNCELLEMELER (FİZİK/ZAMANLAMA)
        if self.playing and self.trex.jumping:
            self.trex.updateJump(delta)

        if self.playing:
            self.running_time += delta
            
        has_obstacles = self.running_time > self.config.clearTime

        clip_rect = None # Varsayılan klip
        horizon_delta = delta 
        horizon_speed = self.current_speed 
        show_night_mode = (self.is_dark_mode != self.inverted)
        
        # 3. INTRO DURUM KONTROLÜ VE KLİP HESAPLAMA
        # Intro sadece ilk açılışta, ilk zıplamada tetiklensin
        if (not self.did_intro) and self.trex.jumpCount == 1 and not self.playing_intro and not self.activated:
            self.playing_intro = True
            self.trex.playing_intro = True
            self.intro_start_time = pygame.time.get_ticks()
            self.activated = True

        if not self.activated:
            tx = int(getattr(self.trex, "xPos", 0))
            tw = int(_get(self.trex.config, "width", 44))
            ideal = tx + tw
            if ideal > self.intro_start_width:
                self.intro_start_width = min(self.dimensions.width, ideal)

            clip_rect = pygame.Rect(0, 0, self.intro_start_width, self.dimensions.height)
            horizon_delta = 0
            show_night_mode = False

        elif self.playing_intro:
            elapsed_time = pygame.time.get_ticks() - self.intro_start_time
            if elapsed_time >= self.INTRO_DURATION:
                self.playing_intro = False
                self.trex.playing_intro = False
                self.running_time = 0
                self.did_intro = True  # bir kez oynatıldı
            else:
                progress = self._ease_in_out_cubic(elapsed_time / self.INTRO_DURATION)
                end_width = self.dimensions.width
                start_width = self.intro_start_width 
                current_width = start_width + (end_width - start_width) * progress
                clip_rect = pygame.Rect(0, 0, int(current_width), self.dimensions.height)
                horizon_delta = 0
                show_night_mode = False

        elif self.crashed:
            horizon_delta = 0  # Zemin durmalı

        # 4. KLİP AYARLAMA
        self.screen.set_clip(clip_rect)  # None ise tüm ekranı kullanır

        # 5. KLİPLİ ÇİZİM
        # Crashed olsa bile horizon'ı son durumuyla çiz (donmuş arka plan)
        if (self.playing and not self.crashed) or not self.activated or self.crashed:
            self.horizon.update(horizon_delta, horizon_speed, has_obstacles, show_night_mode)

        # DistanceMeter (sadece oynarken güncelle)
        play_achievement = False
        if self.playing:
            play_achievement = self.distance_meter.update(delta, math.ceil(self.distance_ran))
        elif self.crashed:
            # Kaza anında skor tablosunu ekranda tut
            self.distance_meter.update(0, math.ceil(self.distance_ran))
        
        # Trex
        self.trex.update(delta) 
        if not self.playing and not self.activated and hasattr(self.trex, "draw"):
            self.trex.draw(0, 0)

        # 6. KLİP KALDIR
        self.screen.set_clip(None)

        # 7. OYUN MANTIĞI
        if self.playing and not self.playing_intro and not self.crashed:
            first_obstacle = self.horizon.obstacles[0] if self.horizon.obstacles else None
            collision = False
            if has_obstacles and first_obstacle:
                collision_result = self._check_for_collision(first_obstacle, self.trex)
                if collision_result:
                    collision = True
            
            if not collision:
                self.distance_ran += self.current_speed * (delta / self.ms_per_frame)
                if self.current_speed < self.config.maxSpeed:
                    self.current_speed += self.config.acceleration
            else:
                self._game_over()
            
            if play_achievement and self._has_audio_cues:
                self._play_sound(self.snd_score)

            # Gece modu
            actual = self.distance_meter.getActualDistance(math.ceil(self.distance_ran))
            if not self.isAltGameModeEnabled():
                if self.invert_timer > self.config.invertFadeDuration:
                    self.invert_timer = 0
                    self.invert_trigger = False
                    self.invert(reset=False)
                elif self.invert_timer:
                    self.invert_timer += delta
                else:
                    if actual > 0 and (actual % self.config.invertDistance == 0) and not self.invert_trigger:
                        self.invert_timer += delta
                        self.invert(reset=False)
                        self.invert_trigger = True
                    elif (actual % self.config.invertDistance) != 0:
                        self.invert_trigger = False

            T = self.config.invertFadeDuration
            t = self.invert_timer
            vis = self._get_visual_invert_ms()

            inv_factor = 0.0
            if self.inverted: 
                if t == 0:
                    inv_factor = 1.0 
                elif t < vis:
                    inv_factor = self._ease_in_out_cubic(t / vis)
                elif t <= (T - vis):
                    inv_factor = 1.0
                else:
                    inv_factor = self._ease_in_out_cubic(1.0 - ((t - (T - vis)) / vis))
            else: 
                if t > 0:
                    if t > (T - vis):
                         inv_factor = self._ease_in_out_cubic(1.0 - ((t - (T - vis)) / vis))
            
            # 8. OVERLAY
            if inv_factor > 0:
                if self._invert_mode_pixels:
                    self._apply_invert_pixels(inv_factor)
                else:
                    self._apply_night_overlay_fallback(inv_factor)
        
        # 9. GAME OVER PANELİ
        if self.crashed and self.game_over_panel:
            self.game_over_panel.draw(self._alt_game_mode_active, self.trex)

        # 10. DEBUG OVERLAY (draw last so it sits on top)
        if self.debug is not None and self.debug.enabled:
            self.debug.draw(self.screen, self.trex, self.horizon.obstacles if self.horizon else [])

    # ========== Game over ==========
    def _game_over(self) -> None:
        assert self.distance_meter and self.trex
        self._play_sound(self.snd_hit)
        self.stop()
        self.crashed = True
        self.distance_meter.achievement = False
        self.trex.update(100, TrexStatus.CRASHED)
        if self.game_over_panel is None:
            orig_def = sprite_definition_by_type["original"]["ldpi"]
            self.game_over_panel = GameOverPanel(
                self.screen, orig_def["textSprite"], orig_def["restart"],
                self.dimensions, self
            )
        
        if self.distance_ran > self.highest_score:
            self.highest_score = int(math.ceil(self.distance_ran))
            self.distance_meter.setHighScore(self.highest_score)

        # Skoru/HI'ı çöküş karesinde de çizer (delta=0 ile donmuş)
        self.distance_meter.update(0, math.ceil(self.distance_ran))

        # Game over anını damgala (restart bekleme için)
        self.game_over_time = pygame.time.get_ticks()
        self.time_ms = self.game_over_time

    # ========== Helpers ==========
    def invert(self, reset: bool) -> None:
        if reset:
            self.invert_timer = 0
            self.inverted = False
        else:
            self.inverted = not self.inverted
    
    def _get_invert_fade_factor(self) -> float:
        if self.invert_timer == 0:
            return 0.0 if not self.inverted else 1.0
        
        current_factor = min(1.0, self.invert_timer / self.config.invertFadeDuration)
        return current_factor if self.inverted else (1.0 - current_factor)

    def _apply_invert_pixels(self, fade_factor: float):
        if fade_factor <= 0.0:
            return
        try:
            src = sarr.pixels3d(self.screen).copy().astype(np.float32)
            out = src * (1.0 - fade_factor) + (255.0 - src) * fade_factor
            np.rint(out, out=out)
            sarr.blit_array(self.screen, out.astype(np.uint8))
        except Exception:
            self._apply_night_overlay_fallback(fade_factor)

    def _apply_night_overlay_fallback(self, fade_factor: float):
        a = int(self.NIGHT_ALPHA_MAX * fade_factor)
        if a > 0:
            self._night_overlay.fill((0, 0, 0, a))
            self.screen.blit(self._night_overlay, (0, 0))

    def _play_sound(self, snd: Optional[pygame.mixer.Sound]) -> None:
        if snd is not None and self._has_audio_cues:
            try:
                ch = pygame.mixer.find_channel(True)  # boş kanal bul, yoksa yarat
                if ch is not None:
                    ch.play(snd)
                else:
                    snd.play()
            except Exception:
                pass

    # Collision port
    def _check_for_collision(self, obstacle, trex: Trex) -> Optional[List[CollisionBox]]:
        t_width = _get(trex.config, "width")
        t_height = _get(trex.config, "height")
        tbox = CollisionBox(
            trex.xPos + 1,
            trex.yPos + 1,
            int(t_width) - 2,
            int(t_height) - 2,
        )

        o_width = _get(obstacle.typeConfig, "width")
        o_height = _get(obstacle.typeConfig, "height")
        obox = CollisionBox(
            obstacle.xPos + 1,
            obstacle.yPos + 1,
            int(o_width) * obstacle.size - 2,
            int(o_height) - 2,
        )

        if not (
            tbox.x < obox.x + obox.width and
            tbox.x + tbox.width > obox.x and
            tbox.y < obox.y + obox.height and
            tbox.height + tbox.y > obox.y
        ):
            return None

        if self.isAltGameModeEnabled():
            runner_sprite_def = self.getSpriteDefinition()
            tboxes = _get(_get(runner_sprite_def, "tRex", {}), "collisionBoxes", []) or []
            norm = []
            for b in tboxes:
                if isinstance(b, CollisionBox):
                    norm.append(b)
                else:
                    norm.append(
                        CollisionBox(
                            int(_get(b, "x", 0)),
                            int(_get(b, "y", 0)),
                            int(_get(b, "width", 0)),
                            int(_get(b, "height", 0)),
                        )
                    )
            tboxes = norm
        else:
            tboxes = trex.getCollisionBoxes()

        for tb in tboxes:
            for ob in obstacle.collisionBoxes:
                adj_t = create_adjusted_box(tb, tbox)
                adj_o = create_adjusted_box(ob, obox)
                if (
                    adj_t.x < adj_o.x + adj_o.width and
                    adj_t.x + adj_t.width > adj_o.x and
                    adj_t.y < adj_o.y + adj_o.height and
                    adj_t.height + adj_o.y > adj_o.y
                ):
                    return [adj_t, adj_o]
        return None


# ==== Optional standalone run for smoke test =================
if __name__ == "__main__":
    # Ses için mixer’i init’ten önce yapılandır
    pygame.mixer.pre_init(44100, -16, 2, 512)
    pygame.init()
    pygame.display.set_caption("NeuroDino — Runner (pygame)")
    dims = Dimensions(width=600, height=150)
    screen = pygame.display.set_mode((dims.width, dims.height))
    clock = pygame.time.Clock()
    
    try:
        runner = Runner(screen, dims, use_audio=True)
    except Exception as e:
        print(f"Oyun başlatılırken kritik bir hata oluştu: {e}")
        pygame.quit()
        raise SystemExit(1)

    running = True
    while running:
        clock.tick(FPS)

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            if event.type == pygame.WINDOWFOCUSLOST:
                continue
            runner.handle_event(event)

        runner.update()
        pygame.display.flip()

    pygame.quit()