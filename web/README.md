# NeuroDino Web

A neural network trained with a genetic algorithm plays the Chrome Dino game,
with its network drawn live. Everyone who opens the page watches the same game,
in sync, with nothing streamed: each browser computes it.

## How everyone sees the same game

- The game is a TypeScript port of `pydino/` and `watch_model.py`, with
  Chrome's normal obstacle gaps as in training (`watch_model.py` and the old
  Gradio demo doubled them, as Chrome does only in its audio-cue mode). It is
  fully deterministic: a seeded RNG (`src/determinism.ts`) replaces
  `Math.random`, and `exp`/`tanh` use only basic arithmetic, so every browser
  engine produces bit-identical frames (checked on V8 and JavaScriptCore).
- Frame N of the shared game belongs to wall-clock time `epoch + N / 60 s`.
- `src/timeline/checkpoint.json` holds the full game state at a recent frame.
  A viewer loads it, simulates the time since then (under a second for an
  hour), and from there steps once per 1/60 s of real time.
- `../.github/workflows/deploy.yml` runs every hour: it downloads the live
  checkpoint from the Hugging Face Space, advances it to the current time
  (`npm run checkpoint`), rebuilds the site and uploads it to the Space with
  `space/README.md` as its README, so checkpoints stay fresh. It squashes the
  Space's history once a day, since every upload adds a new bundle.
- If the model or engine sources change, the checkpoint's fingerprint no longer
  matches and a new shared game starts. To carry the current game over an engine
  change instead, advance the live checkpoint with the old engine, then write
  the new fingerprint into it (done when the gaps went back to normal).

The model, sprites, font, visualizer and training log are all inside the JS
bundle, so
nothing can fail to load once the page is open.

## Interface

A dashboard in the game's own look: its grey (#535353) and off-white, square
2px lines and the PressStart2P pixel font. It follows the system's light or dark
mode; the moon/sun button in the header switches it and the choice is
remembered in the browser. In dark mode the game is shown inverted, as Chrome
does in its own dark theme.

- **Game** with a sensor overlay (toggle "Sensors"): the rays to the next two
  obstacles and the dino's height, labelled with the input values they give
  (`src/sensors.ts`). Below it: total score, best, deaths and how long the dino has been
  alive since its last death (game time).
- **Neural network**: the Hugging Face Space's visualizer
  (`src/vendor/visualizer.js`, from `neurodino/web-ui/`); its control panel
  opens over it from the card's "Settings" button, its groups closed. It
  starts with grey Bézier edges in live-signal mode: an edge shows weight ×
  activation (the Positive/Negative legend appears once a colour mode is on).
  Next to the game the nodes and layer names fill the card's height, with the
  layers up to 340 apart (the slider goes to 800); elsewhere the network is
  drawn at full size and only scaled down when it does not fit; drag pans, Ctrl/Cmd + wheel (or a pinch) zooms, a plain
  wheel scrolls the page, double-click fits it again, and holding a neuron
  shows only its connections. Hovering a neuron explains it (`src/tooltip.ts`):
  an input's value and what it measures, a hidden neuron's activation,
  strongest input and the action it pushes up or down, an output's strongest
  supporter.
- **Decision**: the chosen action and its probability, the three bars and the
  last 75 frames' choices (`src/panels.ts`). Everything is drawn from the same
  frame as the game; the visualizer no longer eases between values, which the
  Space did because it only received a few updates a second.
- **Model Information**: 12 → 48 (tanh) → 3 (softmax), 771 parameters.
- **Training**: best and average score of each generation from
  `src/assets/training-log.csv` (a copy of `training_log.csv`), on a log scale.
  The page plays the record holder, from generation 77 (547,287).

On screens 1200px and wider the game and the cards sit next to the network,
which fills the viewport's height and stays in view, so the dino and the
signals it causes are always seen together. There is no speed or pause
control, since everyone watches the same game.

The sensor overlay reads the dino and obstacle positions from the watcher
without changing `src/watcher.ts`, which is part of the checkpoint fingerprint.

Changes to the Space's `visualizer.js`:

- weights come from `window.NEURO_WEIGHTS` instead of a Python placeholder;
- holding a neuron to isolate its connections never worked (node positions
  were never recorded); it works with mouse, pen and touch now;
- a plain mouse wheel scrolls the page instead of zooming;
- nothing animates on load, and values are not eased between frames;
- the canvas is as tall as its content (the vertical layout keeps room for its
  rotated labels) and is only reallocated when its size changes;
- labels use the pixel font; layer names read "HIDDEN · 48", as the font has
  no ∈ℝ or superscripts.

## Run

```bash
npm install
npm run dev
```

`npm run build` advances the checkpoint and writes the static site to `dist/`.

The link preview image, `public/og-image.png`, is drawn by
`scripts/og_image.py` from the sprite sheet, the font and the model; the page's
Open Graph tags and the Space's `thumbnail` point to its copy on GitHub, which
is served without the redirect the Space's file store adds.

The site is live at https://huggingface.co/spaces/ahm3texe/neurodino. The
workflow uploads with Hugging Face Trusted Publishers: the Space's settings
trust this repository's `main` branch and `deploy.yml`, so no token is
stored.

## Updating the model

After training a new `best_brain.pkl`, export it from the project root:

```bash
python export_best_brain.py --output web/src/assets/best-brain.json
```

and copy its training log, for the Training card:

```bash
cp training_log.csv web/src/assets/training-log.csv
```

The record generation in the Training card's text and in "How it works" is
written in `index.html`; update it too.

## Credits

The game (engine, sprites and rules) is ported, through `pydino/`, from
Chromium's T-Rex runner,
[`components/neterror/resources/dino_game`](https://source.chromium.org/chromium/chromium/src/+/main:components/neterror/resources/dino_game/).
© The Chromium Authors, BSD-3-Clause: the license text is in
`public/LICENSE-chromium.txt` and is published with the site. The page credits
it in its footer. Not affiliated with Google.

The pixel font is Press Start 2P, © 2012 The Press Start 2P Project Authors,
SIL Open Font License 1.1 (`public/OFL-PressStart2P.txt`, also published with
the site).
