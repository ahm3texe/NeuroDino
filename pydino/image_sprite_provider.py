# image_sprite_provider.py
# 1:1 pygame port of image_sprite_provider.ts (interface + a simple impl)

from __future__ import annotations

from typing import Optional, Protocol

import pygame

from offline_sprite_definitions import SpriteDefinition, sprite_definition_by_type


class ImageSpriteProvider(Protocol):
    """Dino oyununda paylaşılan sprite sheet'lere erişim arayüzü."""

    def getOrigImageSprite(self) -> pygame.Surface: ...
    def getRunnerImageSprite(self) -> pygame.Surface: ...
    def getRunnerAltGameImageSprite(self) -> Optional[pygame.Surface]: ...
    def getAltCommonImageSprite(self) -> Optional[pygame.Surface]: ...
    def getSpriteDefinition(self) -> SpriteDefinition: ...


def _load_image(path: str) -> pygame.Surface:
    """Load image with guaranteed alpha preservation, even before display init."""
    if not pygame.get_init():
        pygame.init()
    if not pygame.display.get_init():
        pygame.display.init()
        pygame.display.set_mode((1, 1))
    surf = pygame.image.load(path)
    if surf.get_alpha() is not None:
        surf = surf.convert_alpha()
    else:
        surf = surf.convert()
        surf.set_colorkey((0, 0, 0))
    return surf


def _get_original_sprite_definition() -> SpriteDefinition:
    """TS tarafında spriteDefinitionByType.original vardı;
    Python port'unda dict/attr her iki olasılığı da destekle."""
    try:
        return sprite_definition_by_type["original"]  # dict tarzı
    except Exception:
        return getattr(sprite_definition_by_type, "original")  # attr tarzı


class PygameImageSpriteProvider(ImageSpriteProvider):
    """Basit bir sağlayıcı: tek bir sprite sheet kullanır (orig=runner).
    Alt oyun görselleri opsiyoneldir (None döner)."""

    def __init__(
        self,
        sprite_path: str,
        *,
        alt_game_path: Optional[str] = None,
        alt_common_path: Optional[str] = None,
    ) -> None:
        self._orig = _load_image(sprite_path)
        # Chrome dino'da orig ve runner aynı sheet olabilir; bire bir yapıyoruz.
        self._runner = self._orig
        self._alt_game = _load_image(alt_game_path) if alt_game_path else None
        self._alt_common = _load_image(alt_common_path) if alt_common_path else None
        self._sprite_def = _get_original_sprite_definition()

    # --- ImageSpriteProvider implementation ---
    def getOrigImageSprite(self) -> pygame.Surface:
        return self._orig

    def getRunnerImageSprite(self) -> pygame.Surface:
        return self._runner

    def getRunnerAltGameImageSprite(self) -> Optional[pygame.Surface]:
        return self._alt_game

    def getAltCommonImageSprite(self) -> Optional[pygame.Surface]:
        return self._alt_common

    def getSpriteDefinition(self) -> SpriteDefinition:
        return self._sprite_def