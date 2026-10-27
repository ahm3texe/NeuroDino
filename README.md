# NeuroDino

[![Paper: English](https://img.shields.io/badge/Paper-English%20PDF-b31b1b)](paper/neurodino-en.pdf)
[![Makale: Türkçe](https://img.shields.io/badge/Makale-T%C3%BCrk%C3%A7e%20PDF-b31b1b)](paper/neurodino.pdf)
[![Live demo](https://img.shields.io/badge/Live%20demo-Hugging%20Face%20Space-ffcc4d)](https://huggingface.co/spaces/ahm3texe/neurodino)
[![Model](https://img.shields.io/badge/Model-Hugging%20Face-ffcc4d)](https://huggingface.co/ahm3texe/neurodino)

A neural network that learned to play Chrome's T-Rex game through a genetic
algorithm, and a website where everyone watches it play the same game, live,
with its network drawn next to it: **[huggingface.co/spaces/ahm3texe/neurodino](https://huggingface.co/spaces/ahm3texe/neurodino)**.

## Repository

| Path | What it is |
| --- | --- |
| `pydino/` | Chrome's T-Rex runner ported to Python and Pygame from Chromium's [`dino_game`](https://source.chromium.org/chromium/chromium/src/+/main:components/neterror/resources/dino_game/) |
| `neurodino/` | The network (`brain.py`), its inputs (`sensors.py`), the genetic algorithm (`genetics.py`) and a game played by many networks at once (`episode.py`); `neuro_runner.py` is the runner the first model was trained with |
| `main_train.py` | Trains, by default starting from `best_brain.pkl` |
| `watch_model.py` | Plays a saved model in a window, or with `--silent` without one |
| `export_best_brain.py` | Exports `best_brain.pkl` to the website's JSON format |
| `app.py`, `neurodino/web-ui/` | The original Gradio dashboard |
| `best_brain.pkl` | The model (v3) |
| `training_log.csv`, `runs/dino-full-train/`, `backups/` | The first training run: its log, its TensorBoard logs and every record-setting model; v1 is `backups/brain_score_547287.pkl` |
| `runs/v2/` | The second run's log, validation and model (v2) |
| `training/` | How v3 was made from v2, see [`training/README.md`](training/README.md) |
| `evaluation/` | How the models were tested, with every test game, see [`evaluation/README.md`](evaluation/README.md) |
| `paper/` | The paper: [`paper/neurodino-en.pdf`](paper/neurodino-en.pdf) in English, translated from the Turkish original [`paper/neurodino.pdf`](paper/neurodino.pdf); their LaTeX sources, figures and the scripts that draw them |
| `web/` | The website: the game, the model and the visualizer ported to TypeScript, see [`web/README.md`](web/README.md) |

## Run

Python 3.13:

```bash
pip install -r requirements.txt
python watch_model.py
```

Training plays every network of a generation on the same few games, in
parallel, and writes its log, the best network of each generation and the
network that does best on separate validation games to `runs/train/`. v2
came from (v3 then came from v2, see [`training/`](training/README.md)):

```bash
python main_train.py --start backups/brain_score_547287.pkl --generations 40 --games 10 --minutes 60 --mutation 0.02 --shock 0
```

`--start random` starts from scratch. The first run's TensorBoard logs need
`pip install tensorboard`, then `tensorboard --logdir runs`.

The website:

```bash
cd web
npm install
npm run dev
```

## The network

12 inputs → 56 hidden neurons (tanh) → 3 outputs (softmax: jump, duck, run),
899 parameters. The inputs describe the next two obstacles (time to impact,
width, whether it is the highest bird), the game speed, the gap between the
obstacles and the dino's own height, vertical speed and whether it is in the
air or ducking.

Most of it was trained by a genetic algorithm, in two runs. Each generation
has 50 networks; the best two carry over unchanged, the rest are bred by
tournament selection (3), uniform crossover and Gaussian mutation.

- **First run (v1):** 83 generations, 6.5 hours, from random weights. Each
  generation played a single game and a network's fitness was the distance
  it ran. Its record, 547,287 points, was set in generation 77.
- **Second run (v2):** 40 generations, 1 hour, starting from v1. Every network
  played the same 10 games of up to an hour each generation, new games every
  generation, and its fitness was its mean score; mutation was gentler. The
  best network of each generation was then scored on 100 validation games, and
  the best of those is v2. v2 has 48 hidden neurons and never ducks.
- **v3:** v2 plus 8 hidden neurons that drive only duck. v2 crashed about once
  in a hundred hours at top speed, nearly always still in the air when the
  next obstacle needed a jump; a duck in the air drops the dino fast and would
  have saved it. Trying both choices in the game found when it saves, and the
  new neurons learned that by gradient descent. Every jump is still v2's.

The first run's runner let the networks decide before the obstacles moved
each frame, so v1 learned to act on what it saw a frame earlier. The website,
`watch_model.py` and the Gradio app move the obstacles first, and so does the
second run.

## Results

Each model played 200 fresh games (seeds 1–200) with the website's engine, up
to four hours each; v2 and v3 had never played them before.

| | Ended before top speed | Lasted 4 hours | Crashes at top speed |
| --- | --- | --- | --- |
| v1, website loop | 113 | 85 | 1 every ~170 h |
| v1, its training loop | 5 | 110 | 1 every ~7 h |
| v2, website loop | 0 | 190 | 1 every ~80 h |
| **v3, website loop** | **0** | **198** | 1 every ~390 h |

On 1,000 more games that no model had played (seeds 900001–901000, four hours
each), v2 crashed 40 times and v3 3 times: about once in 100 and once in 1,300
hours at top speed.

In the website's loop v1 jumps a frame early: at intermediate speeds it lands
on obstacles, while at top speed that frame happens to help. v2 reaches top
speed in every game, also with the doubled gaps of the Gradio app. Neither
v1 nor v2 ever ducks: one input marks only the highest bird, which needs no action, so
a bird to duck under looks the same as a low one to jump over, and both jump.
v3 ducks only in the air, to drop fast. The models are on Hugging Face as
safetensors, with a model card:
[huggingface.co/ahm3texe/neurodino](https://huggingface.co/ahm3texe/neurodino).
Details and every game are in [`evaluation/`](evaluation/README.md). The paper
([`paper/neurodino-en.pdf`](paper/neurodino-en.pdf); Turkish original:
[`paper/neurodino.pdf`](paper/neurodino.pdf)) describes all three models and
how they were tested.

## Credits and license

The game in `pydino/` and `web/src/game/`, with its sprites and sounds, is
ported from Chromium's T-Rex runner, © The Chromium Authors, under the
BSD-3-Clause license in [`LICENSE-chromium`](LICENSE-chromium). Not affiliated
with Google.

The pixel font is Press Start 2P, © 2012 The Press Start 2P Project Authors,
under the SIL Open Font License 1.1.

Everything else is under the MIT license in [`LICENSE`](LICENSE).
