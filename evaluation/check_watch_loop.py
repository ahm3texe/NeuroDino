# Checks the website's engine against the Python one: plays the trained model
# with watch_model.ModelWatcher (the loop the website copies), drawing random
# numbers from the website's sfc32 stream, and prints each game's death frame
# and score, to compare with evaluate.mjs on the same seeds.
#   python evaluation/check_watch_loop.py <repo> <first seed> <last seed> <max frames> [doubled]
import math
import os
import pickle
import random
import sys
from pathlib import Path

ROOT = Path(sys.argv[1])
FIRST, LAST, MAX_FRAMES = int(sys.argv[2]), int(sys.argv[3]), int(sys.argv[4])
DOUBLED = len(sys.argv) > 5 and sys.argv[5] == 'doubled'
os.environ["SDL_VIDEODRIVER"] = "dummy"
os.environ["SDL_AUDIODRIVER"] = "dummy"
os.chdir(ROOT)
sys.path.insert(0, str(ROOT))
sys.path.append(str(ROOT / "pydino"))

M = 0xFFFFFFFF


class Sfc32:
    """web/src/determinism.ts Rng, in Python."""

    def __init__(self, seed):
        self.a, self.b, self.c, self.d = 0x9E3779B9, 0x243F6A88, 0xB7E15162, seed & M
        for _ in range(16):
            self.next()

    def next(self):
        t = (self.a + self.b + self.d) & M
        self.d = (self.d + 1) & M
        self.a = self.b ^ (self.b >> 9)
        self.b = (self.c + (self.c << 3)) & M
        self.c = ((self.c << 21) | (self.c >> 11)) & M
        self.c = (self.c + t) & M
        return t

    def random(self):
        return self.next() / 4294967296


stream = Sfc32(1)
random.random = lambda: stream.random()
random.randint = lambda a, b: math.floor(stream.random() * (b - a + 1)) + a

import pygame  # noqa: E402

pygame.init()
from dimensions import Dimensions  # noqa: E402
from watch_model import ModelWatcher  # noqa: E402
import horizon_line  # noqa: E402
import pydino.horizon_line  # noqa: E402

# The website draws the ground's bumpy/flat choice from the game's random
# stream; pydino uses the wall clock. It is cosmetic, but it moves the stream,
# so draw it the website's way to keep both engines on the same numbers.
for module in (horizon_line, pydino.horizon_line):
    module.HorizonLine.getRandomType = (
        lambda self: self.dimensions[0] if random.random() > self.bumpThreshold else 0)

screen = pygame.display.set_mode((900, 850))
loaded = pickle.load(open(ROOT / "best_brain.pkl", "rb"))
brain = loaded[0] if isinstance(loaded, tuple) else loaded

import builtins  # noqa: E402
builtins.print, _print = (lambda *a, **k: None), builtins.print
for seed in range(FIRST, LAST + 1):
    stream.__init__(seed)
    w = ModelWatcher(pygame.Surface((600, 150)), Dimensions(width=600, height=150), brain, silent=True)
    w._has_audio_cues = DOUBLED
    w.start()
    result = ("alive", MAX_FRAMES, None)
    for frame in range(MAX_FRAMES):
        w.update()
        if w.crashed:
            result = ("died", frame, w.score)
            break
    _print(seed, *result, flush=True)
