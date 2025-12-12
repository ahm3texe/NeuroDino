# debug_overlay.py
import pygame

def _get(obj, name, default=None):
    """Safe attribute/key getter: works with objects or dicts."""
    if hasattr(obj, name):
        return getattr(obj, name)
    if isinstance(obj, dict):
        return obj.get(name, default)
    return default

class CollisionDebugOverlay:
    def __init__(self):
        # Varsayılan kapalı; F3 ile toggle
        self.enabled = False

    def draw(self, screen: pygame.Surface, trex, obstacles: list):
        if not self.enabled or trex is None:
            return

        # --- T-Rex ana hitbox
        tw = int(_get(trex.config, "width", 44))
        th = int(_get(trex.config, "height", 47))
        t_rect = pygame.Rect(
            int(trex.xPos) + 1,
            int(trex.yPos) + 1,
            max(1, tw - 2),
            max(1, th - 2),
        )
        pygame.draw.rect(screen, (0, 255, 0), t_rect, 1)

        # --- T-Rex parçalı kutular
        for b in trex.getCollisionBoxes():
            r = pygame.Rect(
                int(trex.xPos) + 1 + int(b.x),
                int(trex.yPos) + 1 + int(b.y),
                int(b.width),
                int(b.height),
            )
            pygame.draw.rect(screen, (0, 200, 0), r, 1)

        if not obstacles:
            return

        # --- İlk engelin ana hitbox'ı (istersen tümünü dolaşabilirsin)
        ob = obstacles[0]
        ow = int(_get(ob.typeConfig, "width", 0))
        oh = int(_get(ob.typeConfig, "height", 0))
        o_rect = pygame.Rect(
            int(ob.xPos) + 1,
            int(ob.yPos) + 1,
            max(1, ow * int(getattr(ob, "size", 1)) - 2),
            max(1, oh - 2),
        )
        pygame.draw.rect(screen, (255, 0, 0), o_rect, 1)

        # --- Engelin parçalı kutuları
        for b in getattr(ob, "collisionBoxes", []):
            r = pygame.Rect(
                int(ob.xPos) + 1 + int(b.x),
                int(ob.yPos) + 1 + int(b.y),
                int(b.width),
                int(b.height),
            )
            pygame.draw.rect(screen, (200, 0, 0), r, 1)