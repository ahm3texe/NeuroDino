# NeuroDino

A neural network that learned to play Chrome's T-Rex game through a genetic
algorithm, and a website where everyone watches it play the same game, live,
with its network drawn next to it: **[huggingface.co/spaces/ahm3texe/neurodino](https://huggingface.co/spaces/ahm3texe/neurodino)**.

## Repository

| Path | What it is |
| --- | --- |
| `pydino/` | Chrome's T-Rex runner ported to Python and Pygame from Chromium's [`dino_game`](https://source.chromium.org/chromium/chromium/src/+/main:components/neterror/resources/dino_game/) |
| `neurodino/` | The network (`brain.py`), the genetic algorithm (`genetics.py`) and the training runner that plays 50 networks at once (`neuro_runner.py`) |
| `main_train.py` | Trains, resuming from `best_brain.pkl` and `training_log.csv` if they exist |
| `watch_model.py` | Plays a saved model in a window, or with `--silent` without one |
| `export_best_brain.py` | Exports `best_brain.pkl` to the website's JSON format |
| `app.py`, `neurodino/web-ui/` | The original Gradio dashboard |
| `best_brain.pkl`, `training_log.csv`, `runs/`, `backups/` | The trained model, its training log, its TensorBoard logs and every record-setting model |
| `web/` | The website: the game, the model and the visualizer ported to TypeScript, see [`web/README.md`](web/README.md) |

## Run

Python 3.13:

```bash
pip install -r requirements.txt
python watch_model.py
```

Training appends to `training_log.csv` and replaces `best_brain.pkl` when it
sets a record, so move those aside to start from scratch:

```bash
python main_train.py --headless
```

Without `--headless` it opens a window; press `S` to cycle the speed. The
TensorBoard logs need `pip install tensorboard`, then
`tensorboard --logdir runs`.

The website:

```bash
cd web
npm install
npm run dev
```

## The network

12 inputs → 48 hidden neurons (tanh) → 3 outputs (softmax: jump, duck, run),
771 parameters. The inputs describe the next two obstacles (time to impact,
width, whether it is the highest bird), the game speed, the gap between the
obstacles and the dino's own height, vertical speed and whether it is in the
air or ducking.

Each generation 50 networks play the same game at once; a network's fitness is
the distance it ran. The best two carry over unchanged, the rest are bred by
tournament selection (3), uniform crossover and Gaussian mutation whose rate
falls with the generation and the best score.

## Results

The model in this repository came from a single 6.5-hour run of 83
generations. Its record, 547,287 points, was set in generation 77.

Played on fresh games with the website's engine:

- once it reaches top speed it is very robust: in 26 four-hour runs that got
  there, it never crashed;
- before that it is not: 56% of 200 games ended while the game was still
  speeding up, at a score below 1,600;
- it never ducks; it jumps over every bird.

## Credits and license

The game in `pydino/` and `web/src/game/`, with its sprites and sounds, is
ported from Chromium's T-Rex runner, © The Chromium Authors, under the
BSD-3-Clause license in [`LICENSE-chromium`](LICENSE-chromium). Not affiliated
with Google.

The pixel font is Press Start 2P, © 2012 The Press Start 2P Project Authors,
under the SIL Open Font License 1.1.

Everything else is under the MIT license in [`LICENSE`](LICENSE).
