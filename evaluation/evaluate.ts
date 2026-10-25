// Plays the trained model on fresh seeded games with the website's engine
// (a port of the Python engine) and writes one JSON line per game.
//
//   [ORDER=training] [MODEL=brain.json] [FIRST_SEED=1] node evaluate.mjs <out.jsonl> <seeds> <maxFrames> [doubled|normal] [ablateIndex ablateValue]
//
// The website, like watch_model.py and the Gradio demo, moves the obstacles
// and then lets the network decide; training (NeuroRunner) decides first, on
// the previous frame's positions, and never turns on night mode. ORDER=training
// plays it the training way.
//
// Records how far each game got, what killed the dino and whether that
// obstacle was still in the network's view, the actions taken, how each
// pterodactyl height was handled and the mean of every input.

import fs from 'node:fs';
import path from 'node:path';

import {Brain} from '../web/src/brain.js';
import type {SerializedBrain} from '../web/src/brain.js';
import type {SpriteSheet} from '../web/src/game/sprites.js';
import {ModelWatcher} from '../web/src/watcher.js';

const WEB = path.resolve(import.meta.dirname, '../web');
// MODEL=<file> plays another exported network (export_best_brain.py) instead of the website's.
const model = JSON.parse(fs.readFileSync(
    process.env.MODEL ?? path.join(WEB, 'src/assets/best-brain.json'), 'utf8')) as SerializedBrain;
const sheet = {width: 1233, height: 100} as unknown as HTMLCanvasElement;
const sprites: SpriteSheet = {alpha: sheet, keyed: sheet};

const [out, seedsArg, maxArg, gaps = 'normal', ablateArg, valueArg] = process.argv.slice(2);
// The inputs as they were at the end of the previous frame are what training saw.
const TRAINING_ORDER = process.env.ORDER === 'training';
const SEEDS = Number(seedsArg);
const MAX_FRAMES = Number(maxArg);
const DOUBLED = gaps === 'doubled';
const ABLATE = ablateArg === undefined ? -1 : Number(ablateArg);
const ABLATE_VALUE = Number(valueArg ?? 0);

interface Obstacle { xPos: number; yPos: number; width: number; typeConfig: {type: string}; }
interface Dino { xPos: number; jumping: boolean; ducking: boolean; config: {width: number}; }
interface Internals {
  horizon: {hasAudioCues: boolean, obstacles: Obstacle[]};
  dino: Dino;
  crashed: boolean;
  update(): void;
}

fs.writeFileSync(out, '');
const started = Date.now();
let totalFrames = 0;
// FIRST_SEED moves the games away from the test seeds 1-200, e.g. for validation.
const FIRST_SEED = Number(process.env.FIRST_SEED ?? 1);
for (let seed = FIRST_SEED; seed < FIRST_SEED + SEEDS; seed++) {
  const brain = Brain.fromJSON(model);
  if (ABLATE >= 0) {
    const predict = brain.predict.bind(brain);
    brain.predict = (inputs: number[]) => {
      const x = [...inputs];
      x[ABLATE] = ABLATE_VALUE;
      return predict(x);
    };
  }
  const w = new ModelWatcher(brain, sprites, {seed});
  w.screen.muted = true;
  const g = w as unknown as Internals;
  g.horizon.hasAudioCues = DOUBLED;
  const internals = w as unknown as {getInputs(): number[]};
  const fresh = internals.getInputs.bind(w);
  let cached = fresh();
  if (TRAINING_ORDER) internals.getInputs = () => cached;

  const actions = [0, 0, 0];
  const inputSums = new Array(12).fill(0);
  const inputMax = new Array(12).fill(-Infinity);
  const inputMin = new Array(12).fill(Infinity);
  const inputNonzero = new Array(12).fill(0);
  const birds: Record<string, {n: number, jumped: number, ducked: number}> = {};
  const seen = new Map<Obstacle, {jumped: boolean, ducked: boolean}>();
  let topSpeedFrame = -1;
  let death: null | {score: number, frame: number, speed: number, killer: string, visible: boolean} = null;
  let frame = 0;
  const night = w as unknown as {inverted: boolean, invertTimer: number};
  for (; frame < MAX_FRAMES; frame++) {
    if (TRAINING_ORDER) {
      // Training never turns on night mode, and while the night is showing
      // the stars stop drawing random numbers; keep it off as in training.
      night.inverted = false;
      night.invertTimer = 0;
    }
    g.update();
    totalFrames++;
    if (TRAINING_ORDER) cached = fresh();
    const d = g.dino;
    const obstacles = g.horizon.obstacles;
    if (g.crashed) {
      const right = d.xPos + d.config.width;
      const hit = obstacles.filter(o => o.xPos < right && o.xPos + o.width > d.xPos)
                      .sort((a, b) => a.xPos - b.xPos)[0];
      death = {
        score: w.score, frame, speed: Number(w.currentSpeed.toFixed(3)),
        killer: hit ? `${hit.typeConfig.type}@${hit.yPos}` : 'unknown',
        visible: hit ? hit.xPos > d.xPos : false,
      };
      break;
    }
    if (topSpeedFrame < 0 && w.currentSpeed >= 13) topSpeedFrame = frame;
    const out = brain.lastOutputs;
    actions[out.indexOf(Math.max(...out))]!++;
    const x = brain.lastInputs;
    for (let i = 0; i < 12; i++) {
      inputSums[i] += x[i]!;
      inputMax[i] = Math.max(inputMax[i], x[i]!);
      inputMin[i] = Math.min(inputMin[i], x[i]!);
      if (x[i] !== 0) inputNonzero[i]++;
    }
    const next = obstacles.filter(o => o.xPos > d.xPos).sort((a, b) => a.xPos - b.xPos)[0];
    if (next && next.typeConfig.type === 'pterodactyl') {
      const r = seen.get(next) ?? {jumped: false, ducked: false};
      if (d.jumping) r.jumped = true;
      if (d.ducking) r.ducked = true;
      seen.set(next, r);
    }
  }
  for (const [o, r] of seen) {
    const k = String(o.yPos);
    birds[k] ??= {n: 0, jumped: 0, ducked: 0};
    birds[k]!.n++;
    if (r.jumped) birds[k]!.jumped++;
    if (r.ducked) birds[k]!.ducked++;
  }
  const frames = death ? death.frame : frame;
  fs.appendFileSync(out, JSON.stringify({
    seed, doubled: DOUBLED, ablate: ABLATE, ablateValue: ABLATE_VALUE,
    frames, score: death ? death.score : w.score, died: death !== null, death,
    topSpeedFrame, actions, birds, inputMeans: inputSums.map(s => s / Math.max(1, frames)), inputMax, inputMin, inputNonzero,
  }) + '\n');
}
const secs = (Date.now() - started) / 1000;
console.error(`${SEEDS} games, ${totalFrames} frames in ${secs.toFixed(1)} s (${Math.round(totalFrames / secs)} frames/s)`);
