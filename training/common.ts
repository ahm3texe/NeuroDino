// Shared by the v3 training scripts: games on the website's engine, started
// from a seed or from a saved moment.

import fs from 'node:fs';

import {Brain} from '../web/src/brain.js';
import type {SerializedBrain} from '../web/src/brain.js';
import type {State} from '../web/src/game/state.js';
import {ModelWatcher} from '../web/src/watcher.js';

export type {SerializedBrain, State};

export const TOP_SPEED_FRAME = 7000;   // speed reaches 13 here in every game

// The engine draws nothing we read; a stub sprite sheet is enough.
const sheet = {width: 1233, height: 100} as unknown as HTMLCanvasElement;
const sprites = {alpha: sheet, keyed: sheet} as never;

export interface Obstacle {
  xPos: number;
  yPos: number;
  width: number;
  size: number;
  typeConfig: {type: string};
}

export interface Game {
  update(): void;
  save(): State;
  crashed: boolean;
  score: number;
  currentSpeed: number;
  horizon: {obstacles: Obstacle[]};
  dino: {xPos: number, config: {width: number}};
}

export function readModel(path: string): SerializedBrain {
  return JSON.parse(fs.readFileSync(path, 'utf8')) as SerializedBrain;
}

export function newGame(model: SerializedBrain, start: {seed: number}|{checkpoint: State}): Game {
  const watcher = new ModelWatcher(Brain.fromJSON(model), sprites,
      'checkpoint' in start ? {checkpoint: structuredClone(start.checkpoint)} : start);
  watcher.screen.muted = true;
  return watcher as unknown as Game;
}

/** Plays up to `frames` frames; returns the frame it crashed on (-1 if it did not). */
export function play(game: Game, frames: number): number {
  for (let f = 0; f < frames; f++) {
    game.update();
    if (game.crashed) return f;
  }
  return -1;
}
