// Plain-data snapshots of engine objects, for checkpoints.

export type State = Record<string, unknown>;

function clone<T>(value: T): T {
  return JSON.parse(JSON.stringify(value)) as T;
}

export function capture(obj: object, keys: readonly string[]): State {
  const out: State = {};
  for (const key of keys) out[key] = (obj as State)[key];
  return clone(out);
}

export function restore(obj: object, state: State, keys: readonly string[]) {
  for (const key of keys) {
    if (!(key in state)) throw new Error(`Checkpoint is missing "${key}"`);
    (obj as State)[key] = clone(state[key]);
  }
}
