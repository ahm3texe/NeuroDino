# Evaluation

How the models were tested, and every game they were tested on.

`evaluate.ts` plays a model on fresh seeded games with the website's engine,
a TypeScript port of the Python one, and writes one JSON line per game: how
far it got, what killed the dino, the actions it took and its inputs. It plays
the website's model unless `MODEL` names another exported network. The
website's engine runs about ten times faster than Python, which makes
hundreds of four-hour games practical.

## Two game loops

The website, `watch_model.py` and the Gradio app move the obstacles and then
let the network decide. The runner that trained v1 (`neurodino/neuro_runner.py`)
let it decide first, on the previous frame's positions, and never turned on
night mode. v1 learned its timing in that loop, and that one frame changes
what it does: on the website it crashed before top speed in more than half of
its games. `ORDER=training` plays the v1 training loop. v2 was trained in the
website's loop (`main_train.py`, `neurodino/episode.py`), and v3 from v2 (see
[`training/`](../training/README.md)).

## Data

| File | Model | Loop | Gaps | Seeds | Up to |
| --- | --- | --- | --- | --- | --- |
| `v1-training-loop.jsonl` | v1 | v1 training | normal | 1–200 | 4 h |
| `v1-website-loop.jsonl` | v1 | website | normal | 1–200 | 4 h |
| `v1-website-loop-doubled-gaps.jsonl` | v1 | website | doubled | 1–200 | 30 min |
| `v1-ablation.json` | v1 | v1 training | normal | 1–200 | 30 min |
| `v2-validation.jsonl` | v2 | website | normal | 1001–1100 | 4 h |
| `v2-test.jsonl` | v2 | website | normal | 1–200 | 4 h |
| `v2-test-doubled-gaps.jsonl` | v2 | website | doubled | 1–200 | 30 min |
| `v2-fresh.jsonl` | v2 | website | normal | 900001–901000 | 4 h |
| `v3-validation.jsonl` | v3 | website | normal | 300001–301000 | 4 h |
| `v3-test.jsonl` | v3 | website | normal | 1–200 | 4 h |
| `v3-fresh.jsonl` | v3 | website | normal | 900001–901000 | 4 h |

Doubled gaps are Chrome's audio-cue mode, which `watch_model.py` and the
Gradio app use by default. Seeds 1–200 were kept as the test set: v2 and v3
were chosen on validation games before they ever played them. v3 was picked
among a few candidates on the 1,000 validation games, so it was also played
on 1,000 games none of them had seen, next to v2.

```bash
python evaluation/summarize.py evaluation/data/*.jsonl
```

## Reproducing

Build the script, then play. The arguments are the output file, the number of
games, the frame limit (60 frames a second) and the gaps; `FIRST_SEED` moves
the seeds.

```bash
web/node_modules/.bin/esbuild evaluation/evaluate.ts --bundle --platform=node --format=esm --outfile=evaluation/evaluate.mjs
node evaluation/evaluate.mjs v2-test.jsonl 200 864000 normal
```

v1 is in `backups/brain_score_547287.pkl` and v2 in `runs/v2/best_brain.pkl`:

```bash
python export_best_brain.py --input backups/brain_score_547287.pkl --output v1.json
MODEL=v1.json node evaluation/evaluate.mjs v1-website-loop.jsonl 200 864000 normal
MODEL=v1.json ORDER=training node evaluation/evaluate.mjs v1-training-loop.jsonl 200 864000 normal
```

Two more arguments hold one input at a value for the whole game, for the
ablation: its index (0–11) and the value.

## Checking the engine against Python

Both loops were checked game by game against the Python engine fed the same
random numbers: `check_watch_loop.py` plays the website loop with
`watch_model.py`, `check_training_loop.py` the v1 training loop with the v1
runner itself. Each plays `best_brain.pkl` from the directory it is given and
prints `seed died frame score` or `seed alive`. The v1 runner writes a log and
TensorBoard files, so give it a copy of the code:

```bash
python evaluation/check_watch_loop.py . 1 200 20000
mkdir /tmp/v1 && cp -R pydino neurodino /tmp/v1/ && cp backups/brain_score_547287.pkl /tmp/v1/best_brain.pkl
python evaluation/check_training_loop.py /tmp/v1 1 200 12000
```
