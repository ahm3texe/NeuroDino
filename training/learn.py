#!/usr/bin/env python3
"""Makes v3: v2 plus hidden neurons that feed only duck, taught when a duck in
the air (a fast drop) saves the dino.

v2 never ducks. It crashes about once in a hundred hours of top speed, nearly
always because it is still in the air when the next obstacle needs a jump;
dropping fast would have saved it. This adds --extra neurons that feed duck
alone and trains them, and duck's row, by gradient descent on
  - frames on the ground (sample.ts): duck must not win;
  - frames in the air (labels.ts): duck where only ducking survives, and
    nowhere else, since every needless fast drop is a new risk.
Everything else of v2 stays as it was, so jump and run, and with them every
jump, are exactly v2's. At the end duck's bias is lowered by --duck-offset,
which on the hard moments of mine.ts kept the ducks that save and dropped
the ones that do not.

    python training/learn.py <v2.json> --ground <prefix>... --air <prefix>... --out v3.json
"""
import argparse
import json
from pathlib import Path

import numpy as np

JUMP, DUCK, RUN = 0, 1, 2
MUST_NOT, MUST, EITHER = 0, 1, 2


def load_ground(prefixes):
    xs, ys = [], []
    for prefix in prefixes:
        y = np.fromfile(f"{prefix}.actions", dtype=np.uint8)
        x = np.fromfile(f"{prefix}.inputs", dtype=np.float32).reshape(len(y), -1)
        ground = np.fromfile(f"{prefix}.air", dtype=np.uint8) == 0
        xs.append(x[ground])
        ys.append(y[ground])
    return np.concatenate(xs).astype(np.float64), np.concatenate(ys)


def load_air(prefixes):
    xs, ys = [], []
    for prefix in prefixes:
        ys.append(np.fromfile(f"{prefix}.labels", dtype=np.uint8))
        xs.append(np.fromfile(f"{prefix}.inputs", dtype=np.float32).reshape(len(ys[-1]), -1))
    x, y = np.concatenate(xs).astype(np.float64), np.concatenate(ys)
    # Duck only where it has to: "either" counts as "must not".
    return x, np.where(y == EITHER, MUST_NOT, y)


def forward(params, x):
    w1, b1, w2, b2 = params
    h = np.tanh(x @ w1.T + b1)
    z = h @ w2.T + b2
    z = z - z.max(axis=1, keepdims=True)
    p = np.exp(z)
    p /= p.sum(axis=1, keepdims=True)
    return h, p


def grads(params, x, target, weight):
    """target: an action to choose, or -1 for "anything but duck"."""
    w1, b1, w2, b2 = params
    h, p = forward(params, x)
    dz = np.zeros_like(p)
    loss = np.zeros(len(x))
    exact = target >= 0
    i = np.where(exact)[0]
    loss[i] = -np.log(p[i, target[i]] + 1e-12)
    dz[i] = p[i]
    dz[i, target[i]] -= 1
    i = np.where(~exact)[0]
    q = 1 - p[i, DUCK]
    loss[i] = -np.log(q + 1e-12)
    dz[i] = -(p[i, DUCK] / (q + 1e-12))[:, None] * p[i]
    dz[i, DUCK] = p[i, DUCK]
    dz *= weight[:, None] / len(x)
    da = (dz @ w2) * (1 - h ** 2)
    return float((loss * weight).mean()), [da.T @ x, da.sum(axis=0), dz.T @ h, dz.sum(axis=0)]


def report(params, gx, gy, ax, ay):
    _, p = forward(params, gx)
    same = np.mean(p.argmax(axis=1) == gy)
    _, p = forward(params, ax)
    duck = p.argmax(axis=1) == DUCK
    print(f"  ground: same choice {same:.4%};  air: must duck chosen {np.mean(duck[ay == MUST]):.1%}, "
          f"must not duck kept {np.mean(~duck[ay == MUST_NOT]):.4%}")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("model")
    ap.add_argument("--ground", nargs="+", required=True)
    ap.add_argument("--air", nargs="+", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--extra", type=int, default=8, help="hidden neurons to add, feeding only duck")
    ap.add_argument("--steps", type=int, default=20000)
    ap.add_argument("--batch", type=int, default=16384)
    ap.add_argument("--lr", type=float, default=1e-3)
    ap.add_argument("--duck-weight", type=float, default=5.0, help="weight of \"must duck\"")
    ap.add_argument("--not-weight", type=float, default=5.0, help="weight of \"must not duck\"")
    ap.add_argument("--duck-offset", type=float, default=1.0, help="lowers duck's bias by this at the end")
    ap.add_argument("--seed", type=int, default=1)
    args = ap.parse_args()

    model = json.load(open(args.model))
    w1, b1 = np.array(model["weights_ih"], dtype=np.float64), np.array(model["bias_h"], dtype=np.float64).ravel()
    w2, b2 = np.array(model["weights_ho"], dtype=np.float64), np.array(model["bias_o"], dtype=np.float64).ravel()
    gx, gy = load_ground(args.ground)
    ax, ay = load_air(args.air)
    rng = np.random.default_rng(args.seed)
    original = len(b1)
    params = [np.vstack([w1, rng.normal(0, 1, (args.extra, w1.shape[1]))]),
              np.concatenate([b1, rng.normal(0, 1, args.extra)]),
              np.hstack([w2, np.zeros((3, args.extra))]), b2]
    # Only the new neurons and duck's row learn.
    learns = [np.zeros((original + args.extra, 1)), np.zeros((3, 1))]
    learns[0][original:] = 1
    learns[1][DUCK] = 1
    print(f"{len(gx):,} ground frames; in the air {int((ay == MUST).sum()):,} must duck, "
          f"{int((ay == MUST_NOT).sum()):,} must not")
    print("before:")
    report(params, gx, gy, ax, ay)

    m = [np.zeros_like(a) for a in params]
    v = [np.zeros_like(a) for a in params]
    half = args.batch // 2
    for step in range(1, args.steps + 1):
        i = rng.integers(0, len(gx), half)
        j = rng.integers(0, len(ax), args.batch - half)
        x = np.concatenate([gx[i], ax[j]])
        target = np.concatenate([gy[i].astype(int), np.where(ay[j] == MUST, DUCK, -1)])
        weight = np.concatenate([np.ones(half), np.where(ay[j] == MUST, args.duck_weight, args.not_weight)])
        loss, g = grads(params, x, target, weight)
        g = [g[0] * learns[0], g[1] * learns[0][:, 0], g[2] * learns[1], g[3] * learns[1][:, 0]]
        for k in range(4):   # Adam
            m[k] = 0.9 * m[k] + 0.1 * g[k]
            v[k] = 0.999 * v[k] + 0.001 * g[k] * g[k]
            params[k] -= args.lr * (m[k] / (1 - 0.9 ** step)) / (np.sqrt(v[k] / (1 - 0.999 ** step)) + 1e-8)
        if step % 5000 == 0:
            print(f"step {step}: loss {loss:.5f}")
    params[3][DUCK] -= args.duck_offset
    print("after:")
    report(params, gx, gy, ax, ay)

    w1, b1, w2, b2 = params
    Path(args.out).write_text(json.dumps({
        "input_nodes": w1.shape[1], "hidden_nodes": len(b1), "output_nodes": 3,
        "weights_ih": w1.tolist(), "weights_ho": w2.tolist(),
        "bias_h": b1.tolist(), "bias_o": b2.tolist(), "training_score": None}))


if __name__ == "__main__":
    main()
