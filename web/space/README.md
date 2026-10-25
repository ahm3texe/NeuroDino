---
title: NeuroDino
emoji: 🦖
colorFrom: green
colorTo: gray
sdk: static
app_file: index.html
pinned: false
license: mit
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
  mutation that shrinks as the scores grow. One 6.5-hour run of 83
  generations; the record, 547,287 points, was set in generation 77 by the
  network playing here.
- **Same game for everyone:** nothing is streamed. The game is a
  deterministic port of Chrome's T-Rex runner, so every browser computes the
  same frames; the page starts from a recent snapshot and fast-forwards to the
  current time.

## Credits

The game (engine, sprites and rules) is ported from Chromium's T-Rex runner,
© The Chromium Authors, BSD-3-Clause (`LICENSE-chromium.txt`). The pixel font
is Press Start 2P, SIL Open Font License 1.1 (`OFL-PressStart2P.txt`).
Everything else is MIT licensed. Not affiliated with Google.
