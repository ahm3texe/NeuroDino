// Advances the shared game to the current time and saves it as
// src/timeline/checkpoint.json, which the site bundles. Run before every build
// (the scheduled deploy runs it every 30 minutes), so a viewer never has more
// than a few minutes of frames to catch up on.
//
// If the model or engine sources changed since the saved checkpoint, the old
// state is meaningless and a new timeline starts now.

import crypto from 'node:crypto';
import fs from 'node:fs';
import path from 'node:path';

import {Brain} from '../src/brain.js';
import type {SerializedBrain} from '../src/brain.js';
import type {SpriteSheet} from '../src/game/sprites.js';
import {frameAt} from '../src/timeline/timeline.js';
import type {Checkpoint} from '../src/timeline/timeline.js';
import {ModelWatcher} from '../src/watcher.js';

const ROOT = process.cwd();
const CHECKPOINT_PATH = path.join(ROOT, 'src/timeline/checkpoint.json');
const MODEL_PATH = path.join(ROOT, 'src/assets/best-brain.json');
const ENGINE_SOURCES = [
  'src/brain.ts', 'src/determinism.ts', 'src/py.ts', 'src/watcher.ts',
  ...fs.readdirSync(path.join(ROOT, 'src/game')).map(f => `src/game/${f}`),
].sort();

function fingerprint(): string {
  const hash = crypto.createHash('sha256');
  for (const file of [MODEL_PATH, ...ENGINE_SOURCES]) {
    hash.update(fs.readFileSync(path.resolve(ROOT, file)));
  }
  return hash.digest('hex').slice(0, 16);
}

function readCheckpoint(): Checkpoint|null {
  try {
    return JSON.parse(fs.readFileSync(CHECKPOINT_PATH, 'utf8')) as Checkpoint;
  } catch {
    return null;
  }
}

const model = JSON.parse(fs.readFileSync(MODEL_PATH, 'utf8')) as SerializedBrain;
const brain = Brain.fromJSON(model);
// Nothing is drawn in Node; the engine only needs the sheet's size.
const sheet = {width: 1233, height: 100} as unknown as HTMLCanvasElement;
const sprites: SpriteSheet = {alpha: sheet, keyed: sheet};

const print = fingerprint();
const previous = readCheckpoint();
let checkpoint: Checkpoint;
let watcher: ModelWatcher;

if (previous && previous.fingerprint === print) {
  checkpoint = previous;
  watcher = new ModelWatcher(brain, sprites, {checkpoint: previous.state});
} else {
  const seed = crypto.randomBytes(4).readUInt32LE(0);
  const epoch = Math.floor(Date.now() / 1000) * 1000;
  console.log(previous ? 'Model or engine changed: starting a new timeline.' :
                         'No checkpoint yet: starting a new timeline.');
  watcher = new ModelWatcher(brain, sprites, {seed});
  checkpoint = {version: 1, fingerprint: print, epoch, seed, frame: 0, state: {}};
}

const target = frameAt(checkpoint, Date.now());
const from = watcher.frame;
const started = performance.now();
while (watcher.frame < target) watcher.tick();
const seconds = (performance.now() - started) / 1000;

checkpoint = {...checkpoint, frame: watcher.frame, state: watcher.save()};
fs.writeFileSync(CHECKPOINT_PATH, JSON.stringify(checkpoint) + '\n');
console.log(
    `Checkpoint at frame ${watcher.frame} (score ${watcher.score}), ` +
    `simulated ${watcher.frame - from} frames in ${seconds.toFixed(2)}s.`);
