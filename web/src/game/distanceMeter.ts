// Port of pydino/distance_meter.py (the parts watch_model.py exercises; the
// watcher never sets a high score, so the HI display is left out).

import type {SpritePos} from './sprites.js';
import {capture, restore} from './state.js';
import type {State} from './state.js';
import type {Surface} from './surface.js';
import {pyRound} from '../py.js';

const WIDTH = 10;
const HEIGHT = 13;
const DEST_WIDTH = 11;

const MAX_DISTANCE_UNITS = 5;
const ACHIEVEMENT_DISTANCE = 100;
const COEFFICIENT = 0.025;
const FLASH_DURATION = 1000 / 4;
const FLASH_ITERATIONS = 3;

export class DistanceMeter {
  achievement = false;
  private x = 0;
  private readonly y = 5;
  private maxScore = 0;
  private digits: string[] = [];
  private defaultString = '';
  private flashTimer = 0.0;
  private flashIterations = 0;
  private maxScoreUnits = MAX_DISTANCE_UNITS;

  constructor(
      private readonly canvas: Surface, private readonly spritePos: SpritePos,
      canvasWidth: number, private readonly sprite: CanvasImageSource) {
    let maxDistanceStr = '';
    this.x = canvasWidth - (DEST_WIDTH * (this.maxScoreUnits + 1));
    this.maxScore = this.maxScoreUnits;
    for (let i = 0; i < this.maxScoreUnits; i++) {
      this.draw(i, 0);
      this.defaultString += '0';
      maxDistanceStr += '9';
    }
    this.maxScore = parseInt(maxDistanceStr, 10);
  }

  private draw(digitPos: number, value: number) {
    this.canvas.blit(
        this.sprite, WIDTH * value + this.spritePos.x, this.spritePos.y, WIDTH,
        HEIGHT, this.x + digitPos * DEST_WIDTH, this.y);
  }

  getActualDistance(distance: number): number {
    return distance ? pyRound(distance * COEFFICIENT) : 0;
  }

  update(deltaTime: number, distance: number): boolean {
    let paint = true;
    let playSound = false;

    if (!this.achievement) {
      const distanceReal = this.getActualDistance(distance);

      if (distanceReal > this.maxScore &&
          this.maxScoreUnits === MAX_DISTANCE_UNITS) {
        this.maxScoreUnits += 1;
        this.maxScore = parseInt(`${this.maxScore}9`, 10);
      }

      if (distanceReal > 0) {
        if (distanceReal % ACHIEVEMENT_DISTANCE === 0) {
          this.achievement = true;
          this.flashTimer = 0.0;
          playSound = true;
        }
        const s = (this.defaultString + String(distanceReal))
                      .slice(-this.maxScoreUnits);
        this.digits = [...s];
      } else {
        this.digits = [...this.defaultString];
      }
    } else if (this.flashIterations <= FLASH_ITERATIONS) {
      this.flashTimer += deltaTime;
      if (this.flashTimer < FLASH_DURATION) {
        paint = false;
      } else if (this.flashTimer > FLASH_DURATION * 2) {
        this.flashTimer = 0.0;
        this.flashIterations += 1;
      }
    } else {
      this.achievement = false;
      this.flashIterations = 0;
      this.flashTimer = 0.0;
    }

    if (paint) {
      for (let i = this.digits.length - 1; i >= 0; i--) {
        this.draw(i, Number(this.digits[i]));
      }
    }

    return playSound;
  }

  reset() {
    this.update(0, 0);
    this.achievement = false;
  }

  private static readonly STATE_KEYS = [
    'achievement', 'x', 'maxScore', 'digits', 'defaultString', 'flashTimer',
    'flashIterations', 'maxScoreUnits',
  ];

  save(): State {
    return capture(this, DistanceMeter.STATE_KEYS);
  }

  load(state: State) {
    restore(this, state, DistanceMeter.STATE_KEYS);
  }
}
