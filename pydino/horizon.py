# horizon.py
# Pygame port of horizon.ts (dict/attr uyumlu, 1:1 mantık)

from __future__ import annotations

import random
from dataclasses import dataclass
from typing import Any, Callable, List, Optional

import pygame

try:
    # Senin utils.py farklı isimde olabilir.
    from utils import get_random_num as getRandomNum
except Exception:
    from utils import getRandomNum  # type: ignore

from background_el import (
    BackgroundEl,
    get_global_config as getBackgroundElGlobalConfig,
    set_global_config as setBackgroundElGlobalConfig,
)
from cloud import Cloud
from dimensions import Dimensions
from horizon_line import HorizonLine
from image_sprite_provider import ImageSpriteProvider
from night_mode import NightMode
from obstacle import (
    Obstacle,
    set_max_gap_coefficient as setMaxObstacleGapCoefficient,
    set_max_obstacle_length as setMaxObstacleLength,
)
from offline_sprite_definitions import sprite_definition_by_type


__all__ = ["Horizon"]  # dışa açık isim

def _get(container: Any, key: str, default: Any = None) -> Any:
    """dict / obj uyumlu erişim."""
    if hasattr(container, key):
        return getattr(container, key)
    if isinstance(container, dict):
        return container.get(key, default)
    return default


@dataclass(frozen=True)
class HorizonConfig:
    BG_CLOUD_SPEED: float
    BUMPY_THRESHOLD: float
    CLOUD_FREQUENCY: float
    HORIZON_HEIGHT: int
    MAX_CLOUDS: int


horizonConfig = HorizonConfig(
    BG_CLOUD_SPEED=0.2,
    BUMPY_THRESHOLD=0.3,
    CLOUD_FREQUENCY=0.5,
    HORIZON_HEIGHT=16,
    MAX_CLOUDS=6,
)


class Horizon:
    obstacles: List[Obstacle]

    def __init__(
        self,
        canvas: pygame.Surface,
        spritePos: dict,           # SpritePositions (dict)
        dimensions: Dimensions,
        gapCoefficient: float,
        resourceProvider: ImageSpriteProvider,  # + getConfig(), hasSlowdown, hasAudioCues
    ) -> None:
        self.obstacles = []
        self.canvas = canvas
        self.canvasCtx = canvas  # pygame Surface
        self.config = horizonConfig
        self.dimensions = dimensions
        self.gapCoefficient = gapCoefficient
        self.resourceProvider = resourceProvider

        self.obstacleHistory: List[str] = []
        self.cloudFrequency = self.config.CLOUD_FREQUENCY
        self.spritePos = spritePos
        self.cloudSpeed = self.config.BG_CLOUD_SPEED

        self.altGameModeActive: bool = False
        self.obstacleTypes: List[dict] = []

        # Collections
        self.clouds: List[Cloud] = []
        self.backgroundEls: List[BackgroundEl] = []
        self.lastEl: Optional[str] = None
        self.horizonLines: List[HorizonLine] = []

        # Başlangıç tanımları
        self.obstacleTypes = list(sprite_definition_by_type["original"]["obstacles"])
        self.addCloud()

        runnerSpriteDefinition = self.resourceProvider.getSpriteDefinition()
        assert runnerSpriteDefinition is not None

        for lineDef in runnerSpriteDefinition["lines"]:
            self.horizonLines.append(
                HorizonLine(self.canvas, lineDef, self.resourceProvider)
            )

        self.nightMode = NightMode(
            self.canvas, _get(self.spritePos, "moon"), self.dimensions.width, self.resourceProvider
        )

    # -------- helpers --------
    def adjustObstacleSpeed(self) -> None:
        """Slow mode için obstacle tanımlarını ayarla."""
        if not getattr(self.resourceProvider, "hasSlowdown", False):
            return
        for ob in self.obstacleTypes:
            # Güvenli okuma: yoksa değiştirmiyoruz
            if "multipleSpeed" in ob and isinstance(ob["multipleSpeed"], (int, float)):
                ob["multipleSpeed"] = ob["multipleSpeed"] / 2
            if "minGap" in ob and isinstance(ob["minGap"], (int, float)):
                ob["minGap"] = ob["minGap"] * 1.5
            if "minSpeed" in ob and isinstance(ob["minSpeed"], (int, float)):
                ob["minSpeed"] = ob["minSpeed"] / 2
            yPos = ob.get("yPos")
            if isinstance(yPos, list) and len(yPos) > 1:
                ob["yPos"] = yPos[0]

    def enableAltGameMode(self, spritePos: dict) -> None:
        runnerSpriteDefinition = self.resourceProvider.getSpriteDefinition()
        assert runnerSpriteDefinition is not None

        # temizle
        self.clouds = []
        self.backgroundEls = []

        self.altGameModeActive = True
        self.spritePos = spritePos

        self.obstacleTypes = list(runnerSpriteDefinition["obstacles"])
        self.adjustObstacleSpeed()

        setMaxObstacleGapCoefficient(runnerSpriteDefinition["maxGapCoefficient"])
        setMaxObstacleLength(runnerSpriteDefinition["maxObstacleLength"])
        setBackgroundElGlobalConfig(runnerSpriteDefinition["backgroundElConfig"])

        self.horizonLines = []
        for lineDef in runnerSpriteDefinition["lines"]:
            self.horizonLines.append(
                HorizonLine(self.canvas, lineDef, self.resourceProvider)
            )
        self.reset()

    # -------- frame update --------
    def update(
        self,
        deltaTime: float,
        currentSpeed: float,
        updateObstacles: bool,
        showNightMode: bool,
    ) -> None:
        runnerSpriteDefinition = self.resourceProvider.getSpriteDefinition()
        assert runnerSpriteDefinition is not None

        if self.altGameModeActive:
            self._updateBackgroundEls(deltaTime)

        for line in self.horizonLines:
            line.update(deltaTime, currentSpeed)

        if (not self.altGameModeActive) or runnerSpriteDefinition["hasClouds"]:
            self.nightMode.update(showNightMode)
            self._updateClouds(deltaTime, currentSpeed)

        if updateObstacles:
            self._updateObstacles(deltaTime, currentSpeed)

    # -------- background elements / clouds --------
    def _updateBackgroundEl(
        self,
        elSpeed: float,
        bgElArray: List[Cloud | BackgroundEl],
        maxBgEl: int,
        bgElAddFunction: Callable[[], None],
        frequency: float,
    ) -> None:
        numElements = len(bgElArray)

        if not numElements:
            bgElAddFunction()
            return

        for i in range(numElements - 1, -1, -1):
            bgElArray[i].update(elSpeed)

        lastEl = bgElArray[-1]

        if (
            numElements < maxBgEl
            and (self.dimensions.width - lastEl.xPos) > getattr(lastEl, "gap", 0)
            and frequency > random.random()
        ):
            bgElAddFunction()

    def _updateClouds(self, deltaTime: float, speed: float) -> None:
        elSpeed = self.cloudSpeed / 1000.0 * deltaTime * speed
        self._updateBackgroundEl(
            elSpeed, self.clouds, self.config.MAX_CLOUDS, self.addCloud, self.cloudFrequency
        )
        # temizle
        self.clouds = [c for c in self.clouds if not c.remove]

    def _updateBackgroundEls(self, deltaTime: float) -> None:
        self._updateBackgroundEl(
            deltaTime,
            self.backgroundEls,
            _get(getBackgroundElGlobalConfig(), "maxBgEls"),
            self.addBackgroundEl,
            self.cloudFrequency,
        )
        self.backgroundEls = [b for b in self.backgroundEls if not b.remove]

    # -------- obstacles --------
    def _updateObstacles(self, deltaTime: float, currentSpeed: float) -> None:
        updated = self.obstacles[:]
        for ob in self.obstacles:
            ob.update(deltaTime, currentSpeed)
            if ob.remove and updated:
                updated.pop(0)
        self.obstacles = updated

        if self.obstacles:
            last = self.obstacles[-1]
            if (
                last
                and not last.followingObstacleCreated
                and last.isVisible()
                and (last.xPos + last.width + last.gap) < self.dimensions.width
            ):
                self.addNewObstacle(currentSpeed)
                last.followingObstacleCreated = True
        else:
            self.addNewObstacle(currentSpeed)

    def removeFirstObstacle(self) -> None:
        if self.obstacles:
            self.obstacles.pop(0)

    def addNewObstacle(self, currentSpeed: float) -> None:
        if not self.obstacleTypes:
            return

        lastType = self.obstacleTypes[-1]
        lastTypeName = _get(lastType, "type")

        if (
            lastTypeName != "collectable"
            or (
                getattr(self.resourceProvider, "isAltGameModeEnabled", lambda: False)()
                and not self.altGameModeActive
            )
            or self.altGameModeActive
        ):
            obstacleCount = len(self.obstacleTypes) - 1
        else:
            obstacleCount = len(self.obstacleTypes) - 2

        idx = getRandomNum(0, obstacleCount) if obstacleCount > 0 else 0
        obstacleType = self.obstacleTypes[idx]
        obstacleTypeName = _get(obstacleType, "type")

        # tekrar & hız kontrol
        if (
            (obstacleCount > 0 and self.duplicateObstacleCheck(obstacleTypeName))
            or currentSpeed < float(_get(obstacleType, "minSpeed", 0))
        ):
            self.addNewObstacle(currentSpeed)
            return

        obstacleSpritePos = _get(self.spritePos, obstacleTypeName)

        self.obstacles.append(
            Obstacle(
                self.canvasCtx,
                obstacleType,
                obstacleSpritePos,
                self.dimensions,
                self.gapCoefficient,
                currentSpeed,
                int(_get(obstacleType, "width", 0)),
                self.resourceProvider,   # ImageSpriteProvider & GameStateProvider
                self.altGameModeActive,
            )
        )

        self.obstacleHistory.insert(0, obstacleTypeName)
        if len(self.obstacleHistory) > 1:
            maxDup = _get(self.resourceProvider.getConfig(), "maxObstacleDuplication", 2)
            del self.obstacleHistory[int(maxDup):]

    def duplicateObstacleCheck(self, nextType: str) -> bool:
        dup = 0
        for t in self.obstacleHistory:
            if t == nextType:
                dup += 1
            else:
                dup = 0
        maxDup = _get(self.resourceProvider.getConfig(), "maxObstacleDuplication", 2)
        return dup >= maxDup

    # -------- misc --------
    def reset(self) -> None:
        self.obstacles = []
        for line in self.horizonLines:
            line.reset()
        self.nightMode.reset()

    def resize(self, width: int, height: int) -> None:
        # pygame Surface boyutu display.set_mode ile ayarlanır; burada no-op
        pass

    def addCloud(self) -> None:
        self.clouds.append(
            Cloud(self.canvas, _get(self.spritePos, "cloud"), self.dimensions.width, self.resourceProvider)
        )

    def addBackgroundEl(self) -> None:
        runnerSpriteDefinition = self.resourceProvider.getSpriteDefinition()
        assert runnerSpriteDefinition is not None
        backgroundElDict = runnerSpriteDefinition["backgroundEl"]
        backgroundElTypes = list(backgroundElDict.keys())
        if not backgroundElTypes:
            return

        index = getRandomNum(0, len(backgroundElTypes) - 1)
        elType = backgroundElTypes[index]
        while elType == self.lastEl and len(backgroundElTypes) > 1:
            index = getRandomNum(0, len(backgroundElTypes) - 1)
            elType = backgroundElTypes[index]

        self.lastEl = elType
        self.backgroundEls.append(
            BackgroundEl(
                self.canvas,
                _get(self.spritePos, "backgroundEl"),
                self.dimensions.width,
                elType,
                self.resourceProvider,
            )
        )