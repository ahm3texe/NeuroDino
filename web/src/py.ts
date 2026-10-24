import {rng} from './determinism.js';

// Python semantics the original pygame code relies on. Using JS defaults
// (Math.round, toFixed, ...) would change gameplay or labels in edge cases.

/** Python `round(x)`: ties go to the nearest even integer. */
export function pyRound(x: number): number {
  const floor = Math.floor(x);
  const diff = x - floor;
  if (diff > 0.5) return floor + 1;
  if (diff < 0.5) return floor;
  return floor % 2 === 0 ? floor : floor + 1;
}

/** Python `int(x)` on a float: truncates toward zero. */
export const pyInt = Math.trunc;

/** Python `random.randint(a, b)`: inclusive on both ends. */
export function randint(min: number, max: number): number {
  return Math.floor(rng.random() * (max - min + 1)) + min;
}
