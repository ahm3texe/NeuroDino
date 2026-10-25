// Records what a model sees and does in ordinary play, for v3's training to
// keep: every `every`-th frame of seeded games, as binary files
//   <out>.inputs (float32 × 12), <out>.actions (uint8), <out>.air (uint8).
//
//   node sample.mjs <model.json> <first seed> <games> <max frames> <every> <out>

import fs from 'node:fs';

import {Brain} from '../web/src/brain.js';
import {ModelWatcher} from '../web/src/watcher.js';

import {readModel} from './common.js';
import type {Game} from './common.js';

const [modelPath, firstArg, gamesArg, maxArg, everyArg, out] = process.argv.slice(2);
const model = readModel(modelPath!);
const first = Number(firstArg), games = Number(gamesArg), maxFrames = Number(maxArg), every = Number(everyArg);
const sheet = {width: 1233, height: 100} as unknown as HTMLCanvasElement;

const inputs: number[] = [], actions: number[] = [], air: number[] = [];
for (let seed = first; seed < first + games; seed++) {
  const brain = Brain.fromJSON(model);
  const watcher = new ModelWatcher(brain, {alpha: sheet, keyed: sheet} as never, {seed});
  watcher.screen.muted = true;
  const game = watcher as unknown as Game & {dino: {jumping: boolean}};
  const predict = brain.predict.bind(brain);
  let f = 0;
  brain.predict = (x: number[]) => {
    const p = predict(x);
    if (f % every === 0) {
      inputs.push(...x);
      actions.push(p.indexOf(Math.max(...p)));
      air.push(game.dino.jumping ? 1 : 0);
    }
    return p;
  };
  for (; f < maxFrames; f++) {
    game.update();
    if (game.crashed) break;
  }
}
fs.writeFileSync(`${out}.inputs`, Buffer.from(Float32Array.from(inputs).buffer));
fs.writeFileSync(`${out}.actions`, Uint8Array.from(actions));
fs.writeFileSync(`${out}.air`, Uint8Array.from(air));
console.error(`seeds ${first}-${first + games - 1}: ${actions.length} frames`);
