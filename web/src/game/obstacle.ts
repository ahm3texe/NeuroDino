// Port of pydino/obstacle.py.

import {FPS} from './config.js';
import {MAX_GAP_COEFFICIENT, MAX_OBSTACLE_LENGTH, OBSTACLE_TYPES} from './sprites.js';
import type {CollisionBox, ObstacleType, SpritePos} from './sprites.js';
import {capture, restore} from './state.js';
import type {State} from './state.js';
import type {Surface} from './surface.js';
import {pyInt, pyRound, randint} from '../py.js';

export class Obstacle {
  collisionBoxes: CollisionBox[] = [];
  followingObstacleCreated = false;
  gap = 0;
  remove = false;
  size: number;
  width = 0;
  xPos: number;
  yPos = 0;

  private gapCoefficient: number;
  private speedOffset = 0.0;
  private currentFrame = 0;
  private timer = 0.0;

  constructor(
      private readonly canvas: Surface, readonly typeConfig: ObstacleType,
      private readonly spritePos: SpritePos, private readonly sprite: CanvasImageSource,
      containerWidth: number, gapCoefficient: number, speed: number, xOffset: number,
      private readonly hasAudioCues: boolean) {
    this.gapCoefficient = gapCoefficient;
    this.size = randint(1, MAX_OBSTACLE_LENGTH);
    this.xPos = pyInt(containerWidth + xOffset);
    this.init(speed);
  }

  private init(speed: number) {
    this.collisionBoxes = this.typeConfig.collisionBoxes.map(b => ({...b}));

    if (this.size > 1 && this.typeConfig.multipleSpeed > speed) {
      this.size = 1;
    }

    this.width = this.typeConfig.width * this.size;

    const yPos = this.typeConfig.yPos;
    if (Array.isArray(yPos)) {
      this.yPos = yPos[randint(0, yPos.length - 1)]!;
    } else {
      this.yPos = yPos;
    }

    this.draw();

    if (this.size > 1 && this.collisionBoxes.length >= 3) {
      const [left, center, right] = this.collisionBoxes as
          [CollisionBox, CollisionBox, CollisionBox];
      center.width = this.width - left.width - right.width;
      right.x = this.width - right.width;
    }

    const speedOffset = this.typeConfig.speedOffset;
    if (speedOffset) {
      this.speedOffset = randint(0, 1) === 1 ? speedOffset : -speedOffset;
    }

    this.gap = this.getGap(this.gapCoefficient, speed);

    // Chrome's audio-cue mode (Runner(use_audio=True)) doubles every gap.
    if (this.hasAudioCues) {
      this.gap *= 2;
    }
  }

  private draw() {
    const sourceW = this.typeConfig.width;
    const sourceH = this.typeConfig.height;
    const base = (sourceW * this.size) * (0.5 * (this.size - 1));

    let srcX = pyInt(base + this.spritePos.x);
    if (this.currentFrame > 0) {
      srcX += sourceW * this.currentFrame;
    }

    this.canvas.blit(
        this.sprite, srcX, this.spritePos.y, sourceW * this.size, sourceH,
        pyInt(this.xPos), pyInt(this.yPos));
  }

  update(deltaTime: number, speed: number) {
    if (this.remove) return;

    if (this.typeConfig.speedOffset) {
      speed = speed + this.speedOffset;
    }

    this.xPos -= pyInt((speed * (FPS / 1000.0)) * deltaTime);

    const numFrames = this.typeConfig.numFrames;
    if (numFrames) {
      const frameRate = this.typeConfig.frameRate ?? 0;
      this.timer += deltaTime;
      if (this.timer >= frameRate) {
        this.currentFrame =
            this.currentFrame >= numFrames - 1 ? 0 : this.currentFrame + 1;
        this.timer = 0.0;
      }
    }

    this.draw();

    if (!this.isVisible()) {
      this.remove = true;
    }
  }

  getGap(gapCoefficient: number, speed: number): number {
    const minGap =
        pyRound(this.width * speed + this.typeConfig.minGap * gapCoefficient);
    const maxGap = pyRound(minGap * MAX_GAP_COEFFICIENT);
    return randint(minGap, maxGap);
  }

  isVisible(): boolean {
    return (this.xPos + this.width) > 0;
  }

  private static readonly STATE_KEYS = [
    'collisionBoxes', 'followingObstacleCreated', 'gap', 'remove', 'size',
    'width', 'xPos', 'yPos', 'gapCoefficient', 'speedOffset', 'currentFrame',
    'timer',
  ];

  save(): State {
    return {type: this.typeConfig.type, ...capture(this, Obstacle.STATE_KEYS)};
  }

  /** Rebuilds a saved obstacle without re-rolling any of its random choices. */
  static fromState(
      canvas: Surface, spritePositions: Record<string, SpritePos>,
      sprite: CanvasImageSource, hasAudioCues: boolean, state: State): Obstacle {
    const typeConfig = OBSTACLE_TYPES.find(t => t.type === state['type']);
    if (!typeConfig) throw new Error(`Unknown obstacle type ${String(state['type'])}`);
    const obstacle = Object.create(Obstacle.prototype) as Obstacle;
    Object.assign(obstacle, {
      canvas,
      typeConfig,
      spritePos: spritePositions[typeConfig.type],
      sprite,
      hasAudioCues,
    });
    restore(obstacle, state, Obstacle.STATE_KEYS);
    return obstacle;
  }
}
