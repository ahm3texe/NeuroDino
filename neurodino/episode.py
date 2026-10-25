# neurodino/episode.py
"""One game played by many agents at once, the way the website plays it.

Each frame the obstacles move first and then every agent decides on their new
positions, as in watch_model.py, the Gradio demo and the website. (The v1
training runner, neuro_runner.py, let agents decide before the obstacles
moved, so the network learned to act one frame late.) Night mode is kept
because it changes which random numbers the game draws.

The obstacles do not depend on what the agents do, so every agent in an
episode plays exactly the game it would play alone with the same seed.
"""
from __future__ import annotations

import random
from typing import List, Tuple

import numpy as np
import pygame

from pydino.dimensions import Dimensions
from pydino.runner import Runner
from pydino.trex import Status

from .brain import Brain
from .neuro_trex import NeuroTrex
from .sensors import get_inputs

FRAME_MS = 1000.0 / 60


class Episode(Runner):
    def __init__(self, screen: pygame.Surface, brains: List[Brain]):
        # use_audio=False: normal obstacle gaps, as in Chrome without audio cues
        super().__init__(screen, Dimensions(width=600, height=150), use_audio=False)
        self.inverted = False
        self.invert_timer = 0.0
        self.invert_trigger = False
        self.agents: List[NeuroTrex] = []
        for brain in brains:
            dino = NeuroTrex(self.screen, self.sprite_def["tRex"], self)
            dino.brain = brain
            self.agents.append(dino)
        self.start()

    def update(self) -> None:
        """One frame of watch_model.ModelWatcher.update for every live agent."""
        if self.playing:
            self.running_time += FRAME_MS
        has_obstacles = self.running_time > self.config.clearTime

        show_night_mode = self.inverted
        if self.playing:
            actual_score = int(self.distance_ran * 0.025)
            if self.invert_timer > self.config.invertFadeDuration:
                self.invert_timer = 0
                self.invert_trigger = False
                self.inverted = not self.inverted
            elif self.invert_timer > 0:
                self.invert_timer += FRAME_MS
            elif (actual_score > 0 and actual_score % self.config.invertDistance == 0
                  and not self.invert_trigger):
                self.invert_timer += FRAME_MS
                self.inverted = not self.inverted
                self.invert_trigger = True
            elif actual_score % self.config.invertDistance != 0:
                self.invert_trigger = False

        self.horizon.update(FRAME_MS, self.current_speed, has_obstacles, show_night_mode)

        if not self.playing or self.crashed:
            return
        alive = [d for d in self.agents if d.status != Status.CRASHED]
        for dino in alive:
            dino.act(int(np.argmax(dino.brain.predict(get_inputs(self, dino)))))
            dino.update(FRAME_MS)
            if dino.jumping:
                dino.updateJump(FRAME_MS)

        if has_obstacles and self.horizon.obstacles:
            for dino in alive:
                for obstacle in self.horizon.obstacles:
                    if self._check_for_collision(obstacle, dino):
                        dino.update(100, Status.CRASHED)
                        dino.fitness = self.distance_ran
                        break

        if all(d.status == Status.CRASHED for d in self.agents):
            self.crashed = True
            return
        self.distance_ran += self.current_speed * (FRAME_MS / self.ms_per_frame)
        if self.current_speed < self.config.maxSpeed:
            self.current_speed += self.config.acceleration


def play(brains: List[Brain], seed: int, max_frames: int) -> List[Tuple[float, bool]]:
    """Plays one game with `seed`. Returns, for each agent, the distance it
    ran and whether it was still alive after `max_frames` frames."""
    random.seed(seed)
    episode = Episode(pygame.Surface((600, 150)), brains)
    for _ in range(max_frames):
        episode.update()
        if episode.crashed:
            break
    return [(d.fitness, False) if d.status == Status.CRASHED else (episode.distance_ran, True)
            for d in episode.agents]
