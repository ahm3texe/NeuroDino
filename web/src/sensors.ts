// What the network sees, drawn over the game: the distance to the next two
// obstacles and the dino's height, with the input values they produce.

import type {Brain} from './brain.js';
import {GAME_HEIGHT, GAME_WIDTH} from './game/config.js';
import type {Obstacle} from './game/obstacle.js';
import type {Trex} from './game/trex.js';
import type {ModelWatcher} from './watcher.js';

interface Box {
  x: number;
  y: number;
  width: number;
  height: number;
}

/**
 * Where the dino and the next two obstacles are. Read from the watcher's
 * private fields on purpose: watcher.ts is part of the checkpoint fingerprint
 * (scripts/checkpoint.ts), and changing it would restart the shared game.
 */
function sensorGeometry(watcher: ModelWatcher): {dino: Box, obstacles: Box[]} {
  const {dino, horizon} =
      watcher as unknown as {dino: Trex, horizon: {obstacles: Obstacle[]}};
  const config = dino.config;
  const obstacles = horizon.obstacles.filter(o => o.xPos > dino.xPos)
                        .sort((a, b) => a.xPos - b.xPos)
                        .slice(0, 2)
                        .map(o => ({x: o.xPos, y: o.yPos, width: o.width, height: o.typeConfig.height}));
  // The ducking sprite is drawn full height; its body is the lower part.
  const box = dino.ducking ? {
    x: dino.xPos,
    y: dino.yPos + config.height - config.heightDuck,
    width: config.widthDuck,
    height: config.heightDuck,
  } : {x: dino.xPos, y: dino.yPos, width: config.width, height: config.height};
  return {dino: box, obstacles};
}

const FONT = "8px 'PressStart2P'";

export class SensorOverlay {
  enabled = true;
  private readonly ctx: CanvasRenderingContext2D;
  private near = '';
  private far = '';
  private tagBackground = '';

  constructor(private readonly canvas: HTMLCanvasElement) {
    this.ctx = canvas.getContext('2d')!;
    this.refreshColors();
  }

  /** Reads the theme's colours; call after switching light and dark mode. */
  refreshColors() {
    const style = getComputedStyle(document.documentElement);
    this.near = style.getPropertyValue('--pos').trim();
    this.far = style.getPropertyValue('--sensor-far').trim();
    this.tagBackground = style.getPropertyValue('--tag-bg').trim();
  }

  draw(watcher: ModelWatcher, brain: Brain) {
    const canvas = this.canvas;
    const dpr = window.devicePixelRatio || 1;
    const width = Math.round(canvas.clientWidth * dpr);
    const height = Math.round(canvas.clientHeight * dpr);
    if (canvas.width !== width) canvas.width = width;
    if (canvas.height !== height) canvas.height = height;
    const ctx = this.ctx;
    ctx.setTransform(1, 0, 0, 1, 0, 0);
    ctx.clearRect(0, 0, width, height);
    if (!this.enabled) return;

    // Game coordinates (600×150) to canvas pixels.
    const sx = width / GAME_WIDTH;
    const sy = height / GAME_HEIGHT;
    const box = (b: Box) => ({x: b.x * sx, y: b.y * sy, w: b.width * sx, h: b.height * sy});
    const inputs = brain.lastInputs;
    const {dino, obstacles} = sensorGeometry(watcher);
    const d = box(dino);
    ctx.font = FONT.replace('8px', `${8 * dpr}px`);
    ctx.textBaseline = 'middle';

    const ray = (from: number, to: ReturnType<typeof box>, y: number, color: string,
                 label: string) => {
      ctx.strokeStyle = color;
      ctx.lineWidth = dpr;
      ctx.setLineDash([4 * dpr, 3 * dpr]);
      ctx.beginPath();
      ctx.moveTo(from, y);
      ctx.lineTo(to.x, y);
      ctx.stroke();
      ctx.strokeRect(to.x, to.y, to.w, to.h);
      ctx.setLineDash([]);
      ctx.fillStyle = color;
      ctx.fillRect(to.x - 2 * dpr, y - 2 * dpr, 4 * dpr, 4 * dpr);
      // Below the line while the DinoY tag sits above the dino.
      this.tag(label, (from + to.x) / 2, y + (airborne ? 12 : -12) * dpr, color, dpr);
    };

    const airborne = inputs[10]! > 0;
    const eyeY = d.y + d.h * 0.3;
    if (obstacles[0]) {
      const o1 = box(obstacles[0]);
      ray(d.x + d.w, o1, eyeY, this.near, `Obj1 Dist ${inputs[0]!.toFixed(2)}`);
      if (obstacles[1]) {
        const o2 = box(obstacles[1]);
        ray(o1.x + o1.w, o2, Math.min(eyeY, o2.y + o2.h / 2), this.far,
            `Obj2 Dist ${inputs[3]!.toFixed(2)}`);
      }
    }
    if (airborne) {
      this.tag(`DinoY ${inputs[8]!.toFixed(2)}`, d.x + d.w / 2, d.y - 10 * dpr, this.near, dpr);
    }
  }

  /** A small labelled box, kept inside the canvas. */
  private tag(text: string, x: number, y: number, color: string, dpr: number) {
    const ctx = this.ctx;
    const pad = 4 * dpr;
    const w = ctx.measureText(text).width + pad * 2;
    const h = 14 * dpr;
    const left = Math.max(2 * dpr, Math.min(this.canvas.width - w - 2 * dpr, x - w / 2));
    const top = Math.max(2 * dpr, y - h / 2);
    ctx.fillStyle = this.tagBackground;
    ctx.fillRect(left, top, w, h);
    ctx.strokeStyle = color;
    ctx.lineWidth = dpr;
    ctx.strokeRect(left, top, w, h);
    ctx.fillStyle = color;
    ctx.textAlign = 'left';
    ctx.fillText(text, left + pad, top + h / 2 + dpr);
  }
}
