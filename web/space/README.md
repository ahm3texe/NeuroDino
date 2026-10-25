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
  dino's own height and motion), 48 hidden neurons (tanh) and 3 outputs
  (jump, duck, run; softmax): 771 parameters, written from scratch.
- **Training:** a genetic algorithm with 50 networks per generation, the best
  two kept unchanged, tournament selection, uniform crossover and Gaussian
  mutation. A first run of 83 generations (6.5 hours) set a record of 547,287
  points, but each generation played a single game, in a loop that showed the
  network the obstacles a frame late; here it crashed before top speed in more
  than half of its games. A second run (40 generations, 1 hour) started from
  it in this page's loop and scored every network on the same 10 games of up
  to an hour. Its best network plays here: in 200 test games it always
  reached top speed, and 190 lasted four hours.
- **Same game for everyone:** nothing is streamed. The game is a
  deterministic port of Chrome's T-Rex runner, so every browser computes the
  same frames; the page starts from a recent snapshot and fast-forwards to the
  current time.

## Credits

The game (engine, sprites and rules) is ported from Chromium's T-Rex runner,
© The Chromium Authors, BSD-3-Clause (`LICENSE-chromium.txt`). The pixel font
is Press Start 2P, SIL Open Font License 1.1 (`OFL-PressStart2P.txt`).
Everything else is MIT licensed. Not affiliated with Google.
