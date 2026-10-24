// Ports of pydino/horizon_line.py, cloud.py and night_mode.py.

import {FPS} from './config.js';
import {rng} from '../determinism.js';
import {LDPI} from './sprites.js';
import type {LineConf, SpritePos} from './sprites.js';
import {capture, restore} from './state.js';
import type {State} from './state.js';
import type {Surface} from './surface.js';
import {pyInt, pyRound, randint} from '../py.js';

export class HorizonLine {
  private readonly yPos: number;
  private readonly spritePos: SpritePos;
  private readonly width: number;
  private readonly height: number;
  private readonly sourceXPos: [number, number];
  private readonly xPos: [number, number];
  private readonly bumpThreshold = 0.5;

  constructor(
      private readonly canvas: Surface, line: LineConf,
      private readonly sprite: CanvasImageSource) {
    this.yPos = line.yPos;
    this.spritePos = {x: line.sourceX, y: line.sourceY};
    this.width = line.width;
    this.height = line.height;
    this.sourceXPos = [this.spritePos.x, this.spritePos.x + this.width];
    this.xPos = [0, this.width];
    this.draw();
  }

  private getRandomType(): number {
    // pydino uses (ticks % 1000) / 1000 here, i.e. a coin flip off the clock.
    return rng.random() > this.bumpThreshold ? this.width : 0;
  }

  private draw() {
    for (const i of [0, 1] as const) {
      this.canvas.blit(
          this.sprite, this.sourceXPos[i], this.spritePos.y, this.width,
          this.height, this.xPos[i], this.yPos);
    }
  }

  private updateXPos(pos: 0|1, increment: number) {
    const line1 = pos;
    const line2 = (1 - pos) as 0|1;

    this.xPos[line1] -= increment;
    this.xPos[line2] = this.xPos[line1] + this.width;

    if (this.xPos[line1] <= -this.width) {
      this.xPos[line1] += this.width * 2;
      this.xPos[line2] = this.xPos[line1] - this.width;
      this.sourceXPos[line1] = this.getRandomType() + this.spritePos.x;
    }
  }

  update(deltaTime: number, speed: number) {
    const increment = pyInt(speed * (FPS / 1000.0) * deltaTime);
    this.updateXPos(this.xPos[0] <= 0 ? 0 : 1, increment);
    this.draw();
  }

  reset() {
    this.xPos[0] = 0;
    this.xPos[1] = this.width;
  }

  save(): State {
    return capture(this, ['sourceXPos', 'xPos']);
  }

  load(state: State) {
    restore(this, state, ['sourceXPos', 'xPos']);
  }
}

const CLOUD = {
  HEIGHT: 14,
  MAX_CLOUD_GAP: 400,
  MAX_SKY_LEVEL: 30,
  MIN_CLOUD_GAP: 100,
  MIN_SKY_LEVEL: 71,
  WIDTH: 46,
};

export class Cloud {
  gap: number;
  xPos: number;
  remove = false;
  private yPos = 0.0;

  constructor(
      private readonly canvas: Surface, private readonly spritePos: SpritePos,
      containerWidth: number, private readonly sprite: CanvasImageSource) {
    this.xPos = containerWidth;
    this.gap = randint(CLOUD.MIN_CLOUD_GAP, CLOUD.MAX_CLOUD_GAP);
    this.yPos = randint(CLOUD.MAX_SKY_LEVEL, CLOUD.MIN_SKY_LEVEL);
    this.draw();
  }

  private draw() {
    this.canvas.blit(
        this.sprite, this.spritePos.x, this.spritePos.y, CLOUD.WIDTH,
        CLOUD.HEIGHT, pyInt(this.xPos), pyInt(this.yPos));
  }

  update(speed: number) {
    if (!this.remove) {
      this.xPos -= Math.ceil(speed);
      this.draw();
      if (!this.isVisible()) {
        this.remove = true;
      }
    }
  }

  isVisible(): boolean {
    return (this.xPos + CLOUD.WIDTH) > 0;
  }

  private static readonly STATE_KEYS = ['gap', 'xPos', 'remove', 'yPos'];

  save(): State {
    return capture(this, Cloud.STATE_KEYS);
  }

  static fromState(
      canvas: Surface, spritePos: SpritePos, sprite: CanvasImageSource,
      state: State): Cloud {
    const cloud = Object.create(Cloud.prototype) as Cloud;
    Object.assign(cloud, {canvas, spritePos, sprite});
    restore(cloud, state, Cloud.STATE_KEYS);
    return cloud;
  }
}

const PHASES = [140, 120, 100, 60, 40, 20, 0];

const NIGHT = {
  FADE_SPEED: 0.035,
  HEIGHT: 40,
  MOON_SPEED: 0.25,
  NUM_STARS: 2,
  STAR_SIZE: 9,
  STAR_SPEED: 0.3,
  STAR_MAX_Y: 70,
  WIDTH: 20,
};

export class NightMode {
  private xPos = 0.0;
  private readonly yPos = 30.0;
  private currentPhase = 0;
  private opacity = 0.0;
  private drawStars = false;
  private readonly stars =
      Array.from({length: NIGHT.NUM_STARS}, () => ({x: 0.0, y: 0.0, sourceY: 0.0}));

  constructor(
      private readonly canvas: Surface, private readonly spritePos: SpritePos,
      private readonly containerWidth: number,
      private readonly sprite: CanvasImageSource) {
    this.placeStars();
  }

  update(activated: boolean) {
    if (activated && this.opacity === 0) {
      this.currentPhase += 1;
      if (this.currentPhase >= PHASES.length) {
        this.currentPhase = 0;
      }
    }

    if (activated && (this.opacity < 1 || this.opacity === 0)) {
      this.opacity += NIGHT.FADE_SPEED;
      if (this.opacity > 1) this.opacity = 1;
    } else if (this.opacity > 0) {
      this.opacity -= NIGHT.FADE_SPEED;
      if (this.opacity < 0) this.opacity = 0;
    }

    if (this.opacity > 0) {
      this.xPos = this.updateXPos(this.xPos, NIGHT.MOON_SPEED);
      if (this.drawStars) {
        for (const star of this.stars) {
          star.x = this.updateXPos(star.x, NIGHT.STAR_SPEED);
        }
      }
      this.draw();
    } else {
      this.placeStars();
    }

    this.drawStars = true;
  }

  reset() {
    this.currentPhase = 0;
    this.opacity = 0;
    this.update(false);
  }

  private static readonly STATE_KEYS =
      ['xPos', 'currentPhase', 'opacity', 'drawStars', 'stars'];

  save(): State {
    return capture(this, NightMode.STATE_KEYS);
  }

  load(state: State) {
    restore(this, state, NightMode.STATE_KEYS);
  }

  private updateXPos(current: number, speed: number): number {
    if (current < -NIGHT.WIDTH) return this.containerWidth;
    return current - speed;
  }

  private draw() {
    const moonSrcW = NIGHT.WIDTH * (this.currentPhase === 3 ? 2 : 1);
    const moonSrcX = this.spritePos.x + PHASES[this.currentPhase]!;
    const alpha = pyInt(Math.max(0, Math.min(255, this.opacity * 255)));
    if (alpha <= 0) return;

    for (const star of this.stars) {
      this.canvas.blit(
          this.sprite, LDPI.star.x, pyInt(star.sourceY), NIGHT.STAR_SIZE,
          NIGHT.STAR_SIZE, pyInt(star.x), pyInt(star.y), alpha);
    }

    this.canvas.blit(
        this.sprite, moonSrcX, this.spritePos.y, moonSrcW, NIGHT.HEIGHT,
        pyInt(this.xPos), pyInt(this.yPos), alpha);
  }

  private placeStars() {
    const segment = Math.max(1, pyRound(this.containerWidth / NIGHT.NUM_STARS));
    for (let i = 0; i < NIGHT.NUM_STARS; i++) {
      const star = this.stars[i]!;
      star.x = randint(segment * i, segment * (i + 1));
      star.y = randint(0, NIGHT.STAR_MAX_Y);
      star.sourceY = LDPI.star.y + NIGHT.STAR_SIZE * i;
    }
  }
}
