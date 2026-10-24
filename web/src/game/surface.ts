// Minimal stand-in for pygame.Surface on top of a 2D canvas.

export type Rgb = readonly [number, number, number];

export class Surface {
  readonly canvas: HTMLCanvasElement|null;
  readonly ctx: CanvasRenderingContext2D|null;
  /**
   * When true every draw call is a no-op. Used for simulation steps whose
   * frame is never shown (pygame draws them anyway, but nobody sees them).
   */
  muted = false;

  constructor(readonly width: number, readonly height: number, canvas?: HTMLCanvasElement) {
    // Without a canvas (the Node checkpoint generator) nothing is drawn.
    this.canvas = canvas ?? null;
    this.ctx = null;
    if (this.canvas) {
      this.canvas.width = width;
      this.canvas.height = height;
      this.ctx = this.canvas.getContext('2d', {willReadFrequently: true});
      if (!this.ctx) throw new Error('2D canvas is not supported');
      this.ctx.imageSmoothingEnabled = false;
    }
  }

  fill([r, g, b]: Rgb) {
    if (this.muted || !this.ctx) return;
    this.ctx.fillStyle = `rgb(${r},${g},${b})`;
    this.ctx.fillRect(0, 0, this.width, this.height);
  }

  /** `dst.blit(src.subsurface(sx, sy, sw, sh), (dx, dy))` with optional set_alpha. */
  blit(
      src: CanvasImageSource, sx: number, sy: number, sw: number, sh: number,
      dx: number, dy: number, alpha = 255) {
    if (this.muted || !this.ctx || sw <= 0 || sh <= 0) return;
    this.ctx.globalAlpha = alpha / 255;
    this.ctx.drawImage(src, sx, sy, sw, sh, dx, dy, sw, sh);
    this.ctx.globalAlpha = 1;
  }

  /** watch_model._apply_night_overlay: blend every pixel toward its inverse. */
  invert(fadeFactor: number) {
    if (this.muted || !this.ctx) return;
    const image = this.ctx.getImageData(0, 0, this.width, this.height);
    const data = image.data;
    const keep = 1.0 - fadeFactor;
    for (let i = 0; i < data.length; i += 4) {
      for (let c = 0; c < 3; c++) {
        const v = data[i + c]!;
        data[i + c] = Math.trunc(v * keep + (255 - v) * fadeFactor);
      }
    }
    this.ctx.putImageData(image, 0, 0);
  }
}
