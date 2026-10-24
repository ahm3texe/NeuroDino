// The shared timeline: frame N of the one game everybody watches is shown at
// epoch + N/60 s. A checkpoint is the full game state at some frame, so a
// viewer only simulates the frames since then.

import type {State} from '../game/state.js';

export const STEP_MS = 1000 / 60;

export interface Checkpoint {
  version: 1;
  /** Hash of the model and engine sources the state was produced with. */
  fingerprint: string;
  /** Wall-clock time (ms since 1970) of frame 0. */
  epoch: number;
  seed: number;
  frame: number;
  state: State;
}

export function frameAt(checkpoint: Checkpoint, timeMs: number): number {
  return Math.floor((timeMs - checkpoint.epoch) / STEP_MS);
}

export function timeOfFrame(checkpoint: Checkpoint, frame: number): number {
  return checkpoint.epoch + frame * STEP_MS;
}
