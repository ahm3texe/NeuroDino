# constants.py
# 1:1 port of Chrome Dino constants.ts for a pygame project.

from __future__ import annotations
import os
import sys
from dimensions import Dimensions  # width, height dataclass

# Browser-only bayrakların pygame eşleniği:
# - IS_IOS / IS_MOBILE: masaüstünde genelde False. İstersen ENV ile zorlayabilirsin.
# - IS_HIDPI: tarayıcıdaki devicePixelRatio yerine ENV kullanıyoruz (varsayılan False).
# - IS_RTL: DOM yok; ister ENV ile ayarla, ister sabit False kalsın.

def _env_flag(name: str, default: bool = False) -> bool:
    val = os.environ.get(name)
    if val is None:
        return default
    return val.strip().lower() in ("1", "true", "yes", "on")

# TODO(salg): Use preprocessor to filter IOS code at build time.  (TS notunu koruyoruz)
IS_IOS: bool = _env_flag("NEURODINO_IOS", default=("ios" in sys.platform))
IS_HIDPI: bool = _env_flag("NEURODINO_HIDPI", default=False)
IS_MOBILE: bool = _env_flag(
    "NEURODINO_MOBILE",
    default=("android" in sys.platform or IS_IOS),
)
IS_RTL: bool = _env_flag("NEURODINO_RTL", default=False)

# Frames per second.
FPS: int = 60

# Default logical dimensions of the game surface.
DEFAULT_DIMENSIONS: Dimensions = Dimensions(width=600, height=150)