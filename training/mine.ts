// Collects hard moments for v3's training: plays a model on seeded games up
// to `maxFrames` and saves the game's state
//   - before every crash at top speed, 45, 60, 90 and 120 frames earlier
//     ("death"), and
//   - at the first obstacle in each game that appears at top speed within
//     400 px of a single small cactus ("tight"): every v2 crash at top speed
//     began that way, and the dino usually gets through.
//
//   node mine.mjs <model.json> <first seed> <games> <max frames> <out.jsonl>

import fs from 'node:fs';

import {newGame, readModel, TOP_SPEED_FRAME} from './common.js';
import type {Obstacle} from './common.js';

const [modelPath, firstArg, gamesArg, maxArg, out] = process.argv.slice(2);
const model = readModel(modelPath!);
const first = Number(firstArg), games = Number(gamesArg), maxFrames = Number(maxArg);
const OFFSETS = [120, 90, 60, 45];
const TIGHT_GAP = 400;

fs.writeFileSync(out!, '');
let deaths = 0, tight = 0;
for (let seed = first; seed < first + games; seed++) {
  const game = newGame(model, {seed});
  const seen = new Set<Obstacle>();
  let savedTight = false;
  let crash = -1;
  for (let f = 0; f < maxFrames; f++) {
    game.update();
    if (game.crashed) {
      crash = f;
      break;
    }
    if (savedTight || f < TOP_SPEED_FRAME) continue;
    for (const o of game.horizon.obstacles) {
      if (seen.has(o)) continue;
      seen.add(o);
      const before = game.horizon.obstacles.filter(p => p !== o && p.xPos < o.xPos)
          .sort((a, b) => b.xPos - a.xPos)[0];
      if (before && before.typeConfig.type === 'cactusSmall' && before.size === 1 &&
          o.xPos - (before.xPos + before.width) <= TIGHT_GAP) {
        fs.appendFileSync(out!, JSON.stringify({kind: 'tight', seed, frame: f, state: game.save()}) + '\n');
        savedTight = true;
        tight++;
      }
    }
  }
  if (crash > TOP_SPEED_FRAME + OFFSETS[0]!) {
    // Play the same game again and save it on the way to the crash.
    const again = newGame(model, {seed});
    let f = 0;
    for (const offset of OFFSETS) {
      for (; f < crash - offset; f++) again.update();
      fs.appendFileSync(out!, JSON.stringify({kind: 'death', seed, frame: f, crash, state: again.save()}) + '\n');
    }
    deaths++;
  }
}
console.error(`seeds ${first}-${first + games - 1}: ${deaths} crashes at top speed, ${tight} tight moments`);
