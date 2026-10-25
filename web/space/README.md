---
title: NeuroDino
emoji: 🦖
colorFrom: green
colorTo: gray
sdk: static
app_file: index.html
pinned: false
license: mit
models:
  - ahm3texe/neurodino
short_description: An evolved neural network plays Chrome Dino, live
---

# NeuroDino

A neural network trained by a genetic algorithm plays Chrome's T-Rex game.
Everyone who opens the page watches the same game at the same moment, with the
network's inputs, hidden activations and decisions drawn next to it.

## How it works

- **Network:** 12 inputs (the next two obstacles, the game speed and the
  dino's own height and motion), 56 hidden neurons (tanh) and 3 outputs
  (jump, duck, run; softmax): 899 parameters, written from scratch.
- **Training:** a genetic algorithm with 50 networks per generation, the best
  two kept unchanged, tournament selection, uniform crossover and Gaussian
  mutation. A first run of 83 generations (6.5 hours) set a record of 547,287
  points, but each generation played a single game, in a loop that showed the
  network the obstacles a frame late; here it crashed before top speed in more
  than half of its games. A second run (40 generations, 1 hour) started from
  it in this page's loop and scored every network on the same 10 games of up
  to an hour. Its network still crashed about once in a hundred hours at top
  speed, still in the air when the next obstacle needed a jump; a duck in the
  air drops the dino fast and would have saved it, but it never ducked. 8
  neurons that drive only duck were added and trained by gradient descent on
  the moments a search over the game found. That network, v3, plays here: in
  1,000 new four-hour games it crashed 3 times, against 40 before.
- **Same game for everyone:** nothing is streamed. The game is a
  deterministic port of Chrome's T-Rex runner, so every browser computes the
  same frames; the page starts from a recent snapshot and fast-forwards to the
  current time.

## Credits

The game (engine, sprites and rules) is ported from Chromium's T-Rex runner,
© The Chromium Authors, BSD-3-Clause (`LICENSE-chromium.txt`). The pixel font
is Press Start 2P, SIL Open Font License 1.1 (`OFL-PressStart2P.txt`).
Everything else is MIT licensed. Not affiliated with Google.
