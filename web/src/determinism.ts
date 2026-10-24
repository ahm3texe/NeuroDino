// Everything every viewer's browser must compute bit-for-bit identically, so
// that all of them show the same game: a seeded RNG instead of Math.random,
// and exp/tanh built from + - * / only (Math.exp/Math.tanh are allowed to
// differ in the last bit between browser engines).

/** sfc32: small, fast, 32-bit integer only, so identical on every engine. */
export class Rng {
  private a: number;
  private b: number;
  private c: number;
  private d: number;

  constructor(seed: number) {
    this.a = 0x9e3779b9;
    this.b = 0x243f6a88;
    this.c = 0xb7e15162;
    this.d = seed >>> 0;
    for (let i = 0; i < 16; i++) this.next();
  }

  private next(): number {
    const t = (((this.a + this.b) | 0) + this.d) | 0;
    this.d = (this.d + 1) | 0;
    this.a = this.b ^ (this.b >>> 9);
    this.b = (this.c + (this.c << 3)) | 0;
    this.c = (this.c << 21) | (this.c >>> 11);
    this.c = (this.c + t) | 0;
    return t >>> 0;
  }

  /** Uniform in [0, 1), like Math.random(). */
  random(): number {
    return this.next() / 4294967296;
  }

  getState(): [number, number, number, number] {
    return [this.a, this.b, this.c, this.d];
  }

  setState([a, b, c, d]: readonly number[]) {
    this.a = a! | 0;
    this.b = b! | 0;
    this.c = c! | 0;
    this.d = d! | 0;
  }
}

/** The game's single random stream. Seeded and restored by the timeline. */
export const rng = new Rng(1);

const LN2_HI = 6.93147180369123816490e-01;
const LN2_LO = 1.90821492927058770002e-10;
const INV_LN2 = 1.44269504088896338700e+00;

/** exp(x) to ~1 ulp, using only operations IEEE 754 defines exactly. */
export function exp(x: number): number {
  if (x !== x) return NaN;
  if (x > 709.78) return Infinity;
  if (x < -745.13) return 0;

  const k = Math.round(x * INV_LN2);
  const r = (x - k * LN2_HI) - k * LN2_LO;

  // Taylor series of e^r for |r| <= ln2/2, Horner form.
  let p = 1.0;
  for (let n = 17; n >= 1; n--) {
    p = 1.0 + (r * p) / n;
  }

  // Multiply by 2^k with exact power-of-two steps.
  let scale = 1.0;
  let base = k < 0 ? 0.5 : 2.0;
  let n = Math.abs(k);
  while (n > 0) {
    if (n & 1) scale *= base;
    base *= base;
    n >>>= 1;
  }
  return p * scale;
}

export function tanh(x: number): number {
  if (x !== x) return NaN;
  const ax = Math.abs(x);
  if (ax > 22) return x > 0 ? 1 : -1;
  const e = exp(-2 * ax);
  const t = (1 - e) / (1 + e);
  return x < 0 ? -t : t;
}
