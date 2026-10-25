// Plays a model from every saved moment of mine.ts for 300 frames and counts
// how many it survives: crash moments used in training, held-out crash
// moments (every fifth crashed game, as in train.ts and learn.py) and tight
// moments.
//
//   node hard.mjs <model.json> <mined.jsonl> [part parts]

import fs from 'node:fs';

import {newGame, play, readModel} from './common.js';

const [modelPath, minedPath, partArg = '0', partsArg = '1'] = process.argv.slice(2);
const model = readModel(modelPath!);
const part = Number(partArg), parts = Number(partsArg);
const moments = fs.readFileSync(minedPath!, 'utf8').trim().split('\n').map(line => JSON.parse(line));
const crashed = [...new Set(moments.filter(m => m.kind === 'death').map(m => m.seed as number))].sort((a, b) => a - b);
const held = new Set(crashed.filter((_, i) => i % 5 === 4));

const counts: Record<string, [number, number]> = {training: [0, 0], 'held-out': [0, 0], tight: [0, 0]};
moments.forEach((m, i) => {
  if (i % parts !== part) return;
  const group = m.kind === 'tight' ? 'tight' : held.has(m.seed) ? 'held-out' : 'training';
  counts[group]![1]++;
  if (play(newGame(model, {checkpoint: m.state}), 300) < 0) counts[group]![0]++;
});
console.log(JSON.stringify(counts));
