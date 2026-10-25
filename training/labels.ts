// Labels frames in the air by trying both choices: from the frame, play once
// with a duck now (a fast drop) and once without, then let the model decide
// for `horizon` frames, and see which of the two crash.
//   0: ducking now crashes and not ducking does not: must not duck
//   1: not ducking crashes and ducking does not:     must duck
//   2: neither crashes:                              either is fine
//   3: both crash                                    (left out)
// Frames come from ordinary games (every `every`-th frame in the air, seeds
// from `first`) or, with "moments", from the 300 frames after each crash
// moment of mine.ts, except the held-out ones. Writes <out>.inputs (float32 × 12) and <out>.labels (uint8).
//
//   node labels.mjs <model.json> games <first seed> <games> <max frames> <every> <horizon> <out>
//   node labels.mjs <model.json> moments <mined.jsonl> <part> <parts> <horizon> <out>

import fs from 'node:fs';

import {Brain} from '../web/src/brain.js';
import {ModelWatcher} from '../web/src/watcher.js';

import {readModel} from './common.js';
import type {Game, State} from './common.js';

const sheet = {width: 1233, height: 100} as unknown as HTMLCanvasElement;
const sprites = {alpha: sheet, keyed: sheet} as never;
const args = process.argv.slice(2);
const model = readModel(args[0]!);

type Dino = {jumping: boolean};
function start(state: State|{seed: number}, force?: () => number|null) {
  const brain = Brain.fromJSON(model);
  const watcher = new ModelWatcher(brain, sprites,
      'seed' in state ? state as {seed: number} : {checkpoint: structuredClone(state as State)});
  watcher.screen.muted = true;
  if (force) {
    const predict = brain.predict.bind(brain);
    brain.predict = (x: number[]) => {
      const p = predict(x);
      const a = force();
      return a === null ? p : [0, 1, 2].map(i => (i === a ? 1 : 0));
    };
  }
  return {brain, game: watcher as unknown as Game & {dino: Dino}};
}

/**
 * True if a game from `state` survives `frames` frames, ducking on the first
 * one if `duck`. Either way it does not duck again until it lands, so that
 * the two games differ only in this one choice; after landing the model plays.
 */
function survives(state: State, frames: number, duck: boolean): boolean {
  let first = true, landed = false;
  const {brain, game} = start(state);
  const predict = brain.predict.bind(brain);
  brain.predict = (x: number[]) => {
    const p = predict(x);
    landed ||= !game.dino.jumping;
    if (first) {
      first = false;
      if (duck) return [0, 1, 0];
    }
    if (landed || p.indexOf(Math.max(...p)) !== 1) return p;
    return p[0]! >= p[2]! ? [1, 0, 0] : [0, 0, 1];   // the best of jump and run
  };
  for (let f = 0; f < frames; f++) {
    game.update();
    if (game.crashed) return false;
  }
  return true;
}

const inputs: number[] = [], labels: number[] = [];
const counts = [0, 0, 0, 0];

/** Labels the next frame of `game`, whose state is `state`, if the dino is in the air. */
function label(state: State, x: number[], horizon: number) {
  const ducked = survives(state, horizon, true);
  const kept = survives(state, horizon, false);
  const l = ducked && kept ? 2 : ducked ? 1 : kept ? 0 : 3;
  counts[l]!++;
  if (l === 3) return;
  inputs.push(...x);
  labels.push(l);
}

// Plays `game` and labels every `every`-th frame in the air.
function walk(begin: State|{seed: number}, frames: number, every: number, horizon: number) {
  const {brain, game} = start(begin);
  const predict = brain.predict.bind(brain);
  let x: number[] = [];
  brain.predict = (v: number[]) => {
    x = v;
    return predict(v);
  };
  for (let f = 0; f < frames; f++) {
    // The state before this frame's update; its inputs are computed inside it.
    if (game.dino.jumping && f % every === 0) {
      const state = game.save();
      game.update();
      label(state, x, horizon);
    } else {
      game.update();
    }
    if (game.crashed) return;
  }
}

if (args[1] === 'games') {
  const [first, games, maxFrames, every, horizon] = args.slice(2, 7).map(Number);
  for (let seed = first!; seed < first! + games!; seed++) walk({seed}, maxFrames!, every!, horizon!);
} else {
  const [file, part, parts, horizon] = [args[2]!, Number(args[3]), Number(args[4]), Number(args[5])];
  const moments = fs.readFileSync(file, 'utf8').trim().split('\n').map(line => JSON.parse(line));
  // Leave out every fifth crashed game, as train.ts, learn.py and hard.ts do.
  const crashed = [...new Set(moments.filter(m => m.kind === 'death').map(m => m.seed as number))].sort((a, b) => a - b);
  const held = new Set(crashed.filter((_, i) => i % 5 === 4));
  moments.forEach((m, i) => {
    if (i % parts !== part || m.kind !== 'death' || held.has(m.seed)) return;
    walk(m.state, 300, 1, horizon);
  });
}
const out = args[args.length - 1]!;
fs.writeFileSync(`${out}.inputs`, Buffer.from(Float32Array.from(inputs).buffer));
fs.writeFileSync(`${out}.labels`, Uint8Array.from(labels));
console.error(`${out}: must not duck ${counts[0]}, must duck ${counts[1]}, either ${counts[2]}, both crash ${counts[3]}`);
