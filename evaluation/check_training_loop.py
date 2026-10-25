# Checks ORDER=training in evaluate.mjs against training itself: plays the
# trained model with the training runner (NeuroRunner, one agent), drawing
# random numbers from the website's sfc32 stream, and prints each game's death
# frame and score. The runner writes training_log.csv and TensorBoard logs into
# its working directory, so run it on a copy of pydino/, neurodino/ and
# best_brain.pkl:
#   python evaluation/check_training_loop.py <copy> <first seed> <last seed> <max frames>
import math, os, random, sys, types
from pathlib import Path

SANDBOX = Path(sys.argv[1]).resolve()
FIRST, LAST, MAX_FRAMES = int(sys.argv[2]), int(sys.argv[3]), int(sys.argv[4])
os.environ["SDL_VIDEODRIVER"] = "dummy"
os.environ["SDL_AUDIODRIVER"] = "dummy"
os.chdir(SANDBOX)                      # anything the runner writes lands here
sys.path.insert(0, str(SANDBOX))
sys.path.append(str(SANDBOX / "pydino"))

M = 0xFFFFFFFF
class Sfc32:
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

# No TensorBoard files: the runner only needs add_scalar/add_histogram.
class _Writer:
    def __init__(self, *a, **k): pass
    def __getattr__(self, name): return lambda *a, **k: None
sys.modules["tensorboardX"] = types.SimpleNamespace(SummaryWriter=_Writer)

import pygame
pygame.init()
import horizon_line, pydino.horizon_line
for module in (horizon_line, pydino.horizon_line):
    # The website's ground draws its cosmetic bumpy/flat choice from the random
    # stream; draw it the same way so both engines see the same numbers.
    module.HorizonLine.getRandomType = (
        lambda self: self.dimensions[0] if random.random() > self.bumpThreshold else 0)
from dimensions import Dimensions
from neurodino.neuro_runner import NeuroRunner

class GenerationOver(Exception):
    pass
def stop(self):
    raise GenerationOver()
NeuroRunner.start_next_generation = stop   # never evolves, saves or logs

import builtins
_print = builtins.print
builtins.print = lambda *a, **k: None
screen = pygame.display.set_mode((600, 650))
for seed in range(FIRST, LAST + 1):
    stream.__init__(seed)
    runner = NeuroRunner(screen, Dimensions(width=600, height=150), pop_size=1, target_fps=60)
    runner.set_rendering(False)
    runner.start()
    result = ("alive", MAX_FRAMES, None)
    try:
        for frame in range(MAX_FRAMES):
            runner.update()
    except GenerationOver:
        result = ("died", frame, int(runner.population[0].fitness * 0.025))
    _print(seed, *result, flush=True)
