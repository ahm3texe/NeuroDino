# offline_sprite_definitions.py
# 1:1 port of Chrome Dino offline_sprite_definitions.ts for pygame.

from __future__ import annotations
from dataclasses import dataclass
from typing import Dict, List, Optional, Union, TypedDict, Any

# --- helpers to allow both dict["x"] and obj.x access ----------------------
class _DotAccessDict(dict):
    def __getattr__(self, key):
        try:
            return self[key]
        except KeyError:
            raise AttributeError(key)

    def __setattr__(self, key, value):
        if key in ("__setstate__",):
            return super().__setattr__(key, value)
        self[key] = value

    def __delattr__(self, key):
        try:
            del self[key]
        except KeyError:
            raise AttributeError(key)

class SpritePos(_DotAccessDict):
    def __init__(self, x: int, y: int):
        super().__init__({"x": int(x), "y": int(y)})

class LineConf(_DotAccessDict):
    def __init__(self, sourceX: int, sourceY: int, width: int, height: int, yPos: int):
        super().__init__({
            "sourceX": int(sourceX),
            "sourceY": int(sourceY),
            "width": int(width),
            "height": int(height),
            "yPos": int(yPos),
        })

# ---------------------------------------------------------------------------
# Types (lightweight Python equivalents)
# ---------------------------------------------------------------------------

@dataclass
class CollisionBox:
    x: int
    y: int
    width: int
    height: int


@dataclass
class ObstacleType:
    # Keys mirror TS interface
    type: str
    width: int
    height: int
    yPos: Union[int, List[int]]
    multipleSpeed: float
    minGap: int
    minSpeed: float
    collisionBoxes: List[CollisionBox]
    # optional
    yPosMobile: Optional[List[int]] = None
    speedOffset: Optional[float] = None
    numFrames: Optional[int] = None
    frameRate: Optional[float] = None


class SpritePosition(TypedDict):
    x: int
    y: int


# SpritePositions in TS is an object with many sprite anchors.
SpritePositions = Dict[str, SpritePosition]

# Loosely typed containers for convenience (dict-like)
SpriteDefinition = Dict[str, Any]
SpriteDefinitionByType = Dict[str, SpriteDefinition]

# ---------------------------------------------------------------------------
# GAME_TYPE list (TS exports an empty list; keep parity)
# ---------------------------------------------------------------------------
GAME_TYPE: List[str] = []

# ---------------------------------------------------------------------------
# Sprite definitions (values copied 1:1 from TS)
# ---------------------------------------------------------------------------

_ldpi_positions: SpritePositions = {
    "backgroundEl": {"x": 86,  "y": 2},
    "cactusLarge":  {"x": 332, "y": 2},
    "cactusSmall":  {"x": 228, "y": 2},
    "obstacle2":    {"x": 332, "y": 2},
    "obstacle":     {"x": 228, "y": 2},
    "cloud":        {"x": 86,  "y": 2},
    "horizon":      {"x": 2,   "y": 54},
    "moon":         {"x": 484, "y": 2},
    "pterodactyl":  {"x": 134, "y": 2},
    "restart":      {"x": 2,   "y": 68},
    "textSprite":   {"x": 655, "y": 2},
    "tRex":         {"x": 848, "y": 2},
    "star":         {"x": 645, "y": 2},
    "collectable":  {"x": 0,   "y": 0},
    "altGameEnd":   {"x": 32,  "y": 0},
}

_hdpi_positions: SpritePositions = {
    "backgroundEl": {"x": 166,  "y": 2},
    "cactusLarge":  {"x": 652,  "y": 2},
    "cactusSmall":  {"x": 446,  "y": 2},
    "obstacle2":    {"x": 652,  "y": 2},
    "obstacle":     {"x": 446,  "y": 2},
    "cloud":        {"x": 166,  "y": 2},
    "horizon":      {"x": 2,    "y": 104},
    "moon":         {"x": 954,  "y": 2},
    "pterodactyl":  {"x": 260,  "y": 2},
    "restart":      {"x": 2,    "y": 130},
    "textSprite":   {"x": 1294, "y": 2},
    "tRex":         {"x": 1678, "y": 2},
    "star":         {"x": 1276, "y": 2},
    "collectable":  {"x": 0,    "y": 0},
    "altGameEnd":   {"x": 64,   "y": 0},
}

# Wrap sprite positions to support both ["x"] and .x usage
_ldpi_positions_wrapped: SpritePositions = {k: SpritePos(v["x"], v["y"]) for k, v in _ldpi_positions.items()}
_hdpi_positions_wrapped: SpritePositions = {k: SpritePos(v["x"], v["y"]) for k, v in _hdpi_positions.items()}

# Obstacles (dataclass instances for attribute access)
_obstacles: List[ObstacleType] = [
    ObstacleType(
        type="cactusSmall",
        width=17,
        height=35,
        yPos=105,
        multipleSpeed=4,
        minGap=120,
        minSpeed=0,
        collisionBoxes=[
            CollisionBox(x=0,  y=7,  width=5, height=27),
            CollisionBox(x=4,  y=0,  width=6, height=34),
            CollisionBox(x=10, y=4,  width=7, height=14),
        ],
    ),
    ObstacleType(
        type="cactusLarge",
        width=25,
        height=50,
        yPos=90,
        multipleSpeed=7,
        minGap=120,
        minSpeed=0,
        collisionBoxes=[
            CollisionBox(x=0,  y=12, width=7,  height=38),
            CollisionBox(x=8,  y=0,  width=7,  height=49),
            CollisionBox(x=13, y=10, width=10, height=38),
        ],
    ),
    ObstacleType(
        type="pterodactyl",
        width=46,
        height=40,
        yPos=[100, 75, 50],          # variable heights
        yPosMobile=[100, 50],
        multipleSpeed=999,
        minSpeed=8.5,
        minGap=150,
        collisionBoxes=[
            CollisionBox(x=15, y=15, width=16, height=5),
            CollisionBox(x=18, y=21, width=24, height=6),
            CollisionBox(x=2,  y=14, width=4,  height=3),
            CollisionBox(x=6,  y=10, width=4,  height=7),
            CollisionBox(x=10, y=8,  width=6,  height=9),
        ],
        numFrames=2,
        frameRate=1000.0 / 6.0,
        speedOffset=0.8,
    ),
    ObstacleType(
        type="collectable",
        width=31,
        height=24,
        yPos=104,
        multipleSpeed=1000,
        minGap=9999,
        minSpeed=0,
        collisionBoxes=[
            CollisionBox(x=0, y=0, width=32, height=25),
        ],
    ),
]

_background_el: Dict[str, Dict[str, Union[int, float, bool]]] = {
    "CLOUD": {
        "height": 14,
        "offset": 4,
        "width": 46,
        "xPos": 1,
        "fixed": False,
    },
}

_background_el_config: Dict[str, Union[int, float]] = {
    "maxBgEls": 1,
    "maxGap": 400,
    "minGap": 100,
    "pos": 0,
    "speed": 0.5,
    "yPos": 125,
}

_lines: List[Dict[str, int]] = [
    {"sourceX": 2, "sourceY": 52, "width": 600, "height": 12, "yPos": 127},
]

_lines_wrapped = [LineConf(**line) for line in _lines]

_alt_game_over_text_config: Dict[str, Union[int, float, bool]] = {
    "textX": 32,
    "textY": 0,
    "textWidth": 246,
    "textHeight": 17,
    "flashDuration": 1500,
    "flashing": False,
}

sprite_definition_by_type: SpriteDefinitionByType = {
    "original": {
        "ldpi": _ldpi_positions_wrapped,
        "hdpi": _hdpi_positions_wrapped,
        "maxGapCoefficient": 1.5,
        "maxObstacleLength": 3,
        "hasClouds": True,
        "bottomPad": 10,
        "obstacles": _obstacles,
        "backgroundEl": _background_el,
        "backgroundElConfig": _background_el_config,
        "lines": _lines_wrapped,
        "altGameOverTextConfig": _alt_game_over_text_config,
        # "altGameEndConfig": ...   # optional, not used in original
    }
}