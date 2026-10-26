# v3

v2 never ducks. About once in a hundred hours at top speed it is still in the
air when the next obstacle needs a jump, and crashes; a duck in the air drops
the dino fast, and in every such crash there was a moment when it would have
saved it. v3 is v2 plus 8 hidden neurons that drive only duck, trained on
when to drop. Everything else of v2 is kept, so every jump is exactly v2's.

The scripts run on the website's engine (TypeScript, built with esbuild like
`evaluation/evaluate.ts`) except `learn.py`.

1. **`mine.ts`** plays v2 on 4,000 games of up to four hours (seeds 100001–104000)
   and saves the game's state 45, 60, 90 and 120 frames before each of its 156
   crashes at top speed, and at one tight moment per game.
2. **`sample.ts`** records what v2 sees and does in 200 ordinary games (seeds
   500001–500200), every fourth frame.
3. **`labels.ts`** labels frames in the air by playing 150 frames on from them
   twice, once with a duck now and once without (and no other duck until the
   dino lands): "must duck" if only the duck survives, "must not duck" if
   only the other does, "either" if both do. It labels every fifth frame in
   the air of 100 ordinary games (seeds 600001–600100) and every frame in the
   air after the crash moments, except those of every fifth crashed game,
   which are held out.
4. **`learn.py`** adds the 8 neurons and trains them and duck's output row by
   gradient descent: duck where it must, nowhere else in the air ("either"
   counts as "must not") and never on the ground. Then it lowers duck's bias
   by 1, which on the saved moments (`hard.ts`) kept the ducks that save and
   dropped the ones that do not.

```bash
for f in mine sample labels hard; do
  web/node_modules/.bin/esbuild training/$f.ts --bundle --platform=node --format=esm --outfile=training/$f.mjs
done
python export_best_brain.py --input runs/v2/best_brain.pkl --output v2.json
node training/mine.mjs v2.json 100001 4000 864000 mined.jsonl
node training/sample.mjs v2.json 500001 200 108000 4 normal
node training/labels.mjs v2.json games 600001 100 108000 5 150 games
node training/labels.mjs v2.json moments mined.jsonl 0 1 150 moments
python training/learn.py v2.json --ground normal --air games moments --out v3.json
```

Each script also splits into parts by seed range (or part and parts for
`labels.mjs moments` and `hard.mjs`) to run in parallel; the result is the
same. With these defaults `learn.py` reproduces v3 exactly: run again from
v2, the whole pipeline gave the same data and a bit-identical v3.

On an Apple M4 (10 cores), with each step split into 10 parallel processes,
it takes about 37 minutes: `mine` 31 minutes, `sample` 13 seconds, `labels`
3 minutes and `learn.py` 2 minutes. Validating a candidate on 1,000
four-hour games (`evaluation/evaluate.ts`) takes 8 more minutes.

On the saved moments, v3 survives 406 of the 500 crash moments it trained on
and 103 of the 124 held out (v2: none), and all 4,000 tight moments. What
counts is long play: see `evaluation/`.

## What did not work

A genetic algorithm scoring networks on the saved moments stalled: v2's duck
output is far below the others, and small mutations almost never make it win,
so selection has nothing to work with. Training the whole network, or adding
inputs for the time to landing, fitted the labels well but changed a few
decisions elsewhere, and in long play those cost far more crashes than the
ducks saved.
