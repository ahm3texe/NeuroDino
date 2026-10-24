// Port of pydino/trex.py (normal jump config, no alt game mode).

import {CONFIG, FPS, GAME_HEIGHT} from './config.js';
import type {CollisionBox, SpritePos} from './sprites.js';
import {capture, restore} from './state.js';
import type {State} from './state.js';
import type {Surface} from './surface.js';
import {pyRound, randint} from '../py.js';

export enum Status {
  CRASHED = 0,
  DUCKING = 1,
  JUMPING = 2,
  RUNNING = 3,
  WAITING = 4,
}

const TREX_CONFIG = {
  dropVelocity: -5,
  height: 47,
  heightDuck: 25,
  introDuration: 1500,
  speedDropCoefficient: 3,
  startXPos: 10,
  width: 44,
  widthDuck: 59,
  gravity: 0.6,
  maxJumpHeight: 30,
  minJumpHeight: 30,
  initialJumpVelocity: -10,
};

const COLLISION_BOXES: Record<'ducking'|'running', CollisionBox[]> = {
  ducking: [{x: 1, y: 18, width: 55, height: 25}],
  running: [
    {x: 22, y: 0, width: 17, height: 16},
    {x: 1, y: 18, width: 30, height: 9},
    {x: 10, y: 35, width: 14, height: 8},
    {x: 1, y: 24, width: 29, height: 5},
    {x: 5, y: 30, width: 21, height: 4},
    {x: 9, y: 34, width: 15, height: 4},
  ],
};

const BLINK_TIMING = 7000;
const BLINK_CLOSED_MS = 120;

const ANIM_FRAMES: Record<Status, {frames: number[], msPerFrame: number}> = {
  [Status.WAITING]: {frames: [0, 44], msPerFrame: 1000 / 3},
  [Status.RUNNING]: {frames: [88, 132], msPerFrame: 1000 / 12},
  [Status.CRASHED]: {frames: [220], msPerFrame: 1000 / 60},
  [Status.JUMPING]: {frames: [0], msPerFrame: 1000 / 60},
  [Status.DUCKING]: {frames: [264, 323], msPerFrame: 1000 / 8},
};

export class Trex {
  readonly config = {...TREX_CONFIG};
  /** NeuroTrex only draws once it has been made visible. */
  visible = true;

  playingIntro = false;
  xPos = 0;
  yPos = 0;
  xInitialPos: number;
  groundYPos: number;
  jumpCount = 0;
  ducking = false;
  blinkCount = 0;
  jumping = false;
  speedDrop = false;
  status: Status = Status.WAITING;
  reachedMinHeight = false;

  currentFrameIndex = 0;
  currentAnimFrames: number[] = [];
  blinkDelay = 0;
  animStartTime = 0;
  timer = 0.0;
  msPerFrame = 1000.0 / FPS;

  jumpVelocity = 0.0;
  minJumpHeight: number;

  constructor(
      private readonly canvas: Surface, private readonly spritePos: SpritePos,
      private readonly sprite: CanvasImageSource, visible = true) {
    this.visible = visible;
    this.xInitialPos = this.config.startXPos;
    this.groundYPos = GAME_HEIGHT - this.config.height - CONFIG.bottomPad;
    this.yPos = this.groundYPos;
    this.minJumpHeight = this.groundYPos - this.config.minJumpHeight;
    this.xPos = this.xInitialPos;
    this.update(0, Status.WAITING);
  }

  update(deltaTime: number, status?: Status) {
    this.timer += deltaTime;

    if (status !== undefined && this.status !== status) {
      this.status = status;
      this.currentFrameIndex = 0;
      this.msPerFrame = ANIM_FRAMES[status].msPerFrame;
      this.currentAnimFrames = ANIM_FRAMES[status].frames;
      this.timer = 0;
      if (status === Status.WAITING) {
        this.animStartTime = 0;
        this.setBlinkDelay();
      }
    }

    if (this.playingIntro && this.xPos < this.config.startXPos) {
      this.xPos += pyRound(
          (this.config.startXPos / this.config.introDuration) * deltaTime);
    }

    if (this.status === Status.WAITING) {
      // pydino passes the wall clock; the watcher's dino never waits, so a
      // fixed time keeps the state the same for every viewer.
      this.blink(0);
    } else {
      this.draw(this.currentAnimFrames[this.currentFrameIndex]!, 0);
      if (this.timer >= this.msPerFrame) {
        if (this.status === Status.RUNNING || this.status === Status.DUCKING) {
          this.currentFrameIndex =
              (this.currentFrameIndex + 1) % this.currentAnimFrames.length;
        }
        this.timer = 0;
      }
    }

    if (this.speedDrop && this.yPos === this.groundYPos) {
      this.speedDrop = false;
      this.setDuck(true);
    }
  }

  draw(x: number, y: number) {
    if (!this.visible) return;

    if (this.status === Status.WAITING) {
      const waitFrames = ANIM_FRAMES[Status.WAITING].frames;
      x = waitFrames[this.currentFrameIndex % waitFrames.length]!;
    }

    const ducking = this.ducking && this.status !== Status.CRASHED;
    const sourceWidth = ducking ? this.config.widthDuck : this.config.width;
    const sourceHeight = this.config.height;

    const sx = Math.trunc(this.spritePos.x + x);
    const sy = Math.trunc(this.spritePos.y + y);
    const imgW = (this.sprite as HTMLCanvasElement).width;
    const imgH = (this.sprite as HTMLCanvasElement).height;
    if (sx < 0 || sy < 0 || sx + sourceWidth > imgW || sy + sourceHeight > imgH) {
      return;
    }

    this.canvas.blit(
        this.sprite, sx, sy, sourceWidth, sourceHeight, Math.trunc(this.xPos),
        Math.trunc(this.yPos));
  }

  private setBlinkDelay() {
    this.blinkDelay = randint(1, BLINK_TIMING);
  }

  private blink(timeMs: number) {
    const deltaTime = timeMs - this.animStartTime;
    const waitFrames = ANIM_FRAMES[Status.WAITING].frames;
    this.draw(waitFrames[this.currentFrameIndex]!, 0);

    if (this.currentFrameIndex === 0 && deltaTime >= this.blinkDelay) {
      this.currentFrameIndex = 1;
      this.animStartTime = timeMs;
    } else if (this.currentFrameIndex === 1 && deltaTime >= BLINK_CLOSED_MS) {
      this.currentFrameIndex = 0;
      this.setBlinkDelay();
      this.animStartTime = timeMs;
      this.blinkCount += 1;
    }
  }

  startJump(speed: number) {
    if (!this.jumping) {
      this.status = Status.JUMPING;
      this.currentFrameIndex = 0;
      this.timer = 0;
      this.msPerFrame = ANIM_FRAMES[Status.JUMPING].msPerFrame;
      this.currentAnimFrames = ANIM_FRAMES[Status.JUMPING].frames;

      this.jumpVelocity = this.config.initialJumpVelocity - (speed / 10.0);
      this.jumping = true;
      this.reachedMinHeight = false;
      this.speedDrop = false;
    }
  }

  endJump() {
    if (this.reachedMinHeight && this.jumpVelocity < this.config.dropVelocity) {
      this.jumpVelocity = this.config.dropVelocity;
    }
  }

  updateJump(deltaTime: number) {
    const msPerFrame = ANIM_FRAMES[Status.JUMPING].msPerFrame;
    const framesElapsed = msPerFrame > 0 ? deltaTime / msPerFrame : 1.0;

    if (this.speedDrop) {
      this.yPos += pyRound(
          this.jumpVelocity * this.config.speedDropCoefficient * framesElapsed);
    } else {
      this.yPos += pyRound(this.jumpVelocity * framesElapsed);
    }

    this.jumpVelocity += this.config.gravity * framesElapsed;

    if (this.yPos < this.minJumpHeight || this.speedDrop) {
      this.reachedMinHeight = true;
    }

    if (this.yPos < this.config.maxJumpHeight || this.speedDrop) {
      this.endJump();
    }

    if (this.yPos > this.groundYPos) {
      this.reset();
      this.jumpCount += 1;
    }
  }

  setSpeedDrop() {
    this.speedDrop = true;
    this.jumpVelocity = 1;
  }

  setDuck(isDucking: boolean) {
    if (isDucking && this.status !== Status.DUCKING) {
      this.status = Status.DUCKING;
      this.currentFrameIndex = 0;
      this.timer = 0;
      this.msPerFrame = ANIM_FRAMES[Status.DUCKING].msPerFrame;
      this.currentAnimFrames = ANIM_FRAMES[Status.DUCKING].frames;
      this.ducking = true;
    } else if (this.status === Status.DUCKING && !isDucking) {
      this.status = Status.RUNNING;
      this.currentFrameIndex = 0;
      this.timer = 0;
      this.msPerFrame = ANIM_FRAMES[Status.RUNNING].msPerFrame;
      this.currentAnimFrames = ANIM_FRAMES[Status.RUNNING].frames;
      this.ducking = false;
    }
  }

  reset() {
    this.xPos = this.xInitialPos;
    this.yPos = this.groundYPos;
    this.jumpVelocity = 0;
    this.jumping = false;
    this.ducking = false;

    this.status = Status.RUNNING;
    this.currentFrameIndex = 0;
    this.timer = 0;
    this.currentAnimFrames = ANIM_FRAMES[Status.RUNNING].frames;
    this.msPerFrame = ANIM_FRAMES[Status.RUNNING].msPerFrame;

    this.speedDrop = false;
    this.jumpCount = 0;
  }

  private static readonly STATE_KEYS = [
    'visible', 'playingIntro', 'xPos', 'yPos', 'xInitialPos', 'groundYPos',
    'jumpCount', 'ducking', 'blinkCount', 'jumping', 'speedDrop', 'status',
    'reachedMinHeight', 'currentFrameIndex', 'currentAnimFrames', 'blinkDelay',
    'animStartTime', 'timer', 'msPerFrame', 'jumpVelocity', 'minJumpHeight',
  ];

  save(): State {
    return capture(this, Trex.STATE_KEYS);
  }

  load(state: State) {
    restore(this, state, Trex.STATE_KEYS);
  }

  getCollisionBoxes(): CollisionBox[] {
    return this.ducking ? COLLISION_BOXES.ducking : COLLISION_BOXES.running;
  }

  /**
   * neuro_trex.py NeuroTrex.act: 0 = jump, 1 = duck / fast drop, 2 = run.
   */
  act(action: number, currentSpeed: number) {
    if (this.status === Status.CRASHED) return;

    if (action === 0) {
      if (!this.jumping && !this.ducking) this.startJump(currentSpeed);
    } else if (action === 1) {
      if (this.jumping) {
        this.setSpeedDrop();
      } else if (!this.ducking) {
        this.setDuck(true);
      }
    } else if (this.ducking) {
      this.setDuck(false);
    }
  }
}
