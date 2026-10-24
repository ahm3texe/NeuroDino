// Port of pydino/horizon.py (original game type only).

import {Cloud, HorizonLine, NightMode} from './background.js';
import {CONFIG} from './config.js';
import {Obstacle} from './obstacle.js';
import {LINES, OBSTACLE_TYPES} from './sprites.js';
import type {ObstacleType, SpritePositions} from './sprites.js';
import type {State} from './state.js';
import type {Surface} from './surface.js';
import {rng} from '../determinism.js';
import {randint} from '../py.js';

const BG_CLOUD_SPEED = 0.2;
const CLOUD_FREQUENCY = 0.5;
const MAX_CLOUDS = 6;

export class Horizon {
  obstacles: Obstacle[] = [];
  private obstacleHistory: string[] = [];
  private readonly obstacleTypes: readonly ObstacleType[] = OBSTACLE_TYPES;
  private clouds: Cloud[] = [];
  private readonly horizonLines: HorizonLine[] = [];
  private readonly nightMode: NightMode;

  constructor(
      private readonly canvas: Surface, private readonly spritePos: SpritePositions,
      private readonly containerWidth: number,
      private readonly gapCoefficient: number,
      private readonly sprite: CanvasImageSource,
      private readonly hasAudioCues: boolean) {
    this.addCloud();
    for (const line of LINES) {
      this.horizonLines.push(new HorizonLine(canvas, line, sprite));
    }
    this.nightMode =
        new NightMode(canvas, spritePos.moon, containerWidth, sprite);
  }

  update(
      deltaTime: number, currentSpeed: number, updateObstacles: boolean,
      showNightMode: boolean) {
    for (const line of this.horizonLines) {
      line.update(deltaTime, currentSpeed);
    }

    this.nightMode.update(showNightMode);
    this.updateClouds(deltaTime, currentSpeed);

    if (updateObstacles) {
      this.updateObstacles(deltaTime, currentSpeed);
    }
  }

  private updateClouds(deltaTime: number, speed: number) {
    const elSpeed = BG_CLOUD_SPEED / 1000.0 * deltaTime * speed;
    const numElements = this.clouds.length;

    if (!numElements) {
      this.addCloud();
    } else {
      for (let i = numElements - 1; i >= 0; i--) {
        this.clouds[i]!.update(elSpeed);
      }
      const lastEl = this.clouds[this.clouds.length - 1]!;
      if (numElements < MAX_CLOUDS &&
          (this.containerWidth - lastEl.xPos) > lastEl.gap &&
          CLOUD_FREQUENCY > rng.random()) {
        this.addCloud();
      }
    }

    this.clouds = this.clouds.filter(c => !c.remove);
  }

  private updateObstacles(deltaTime: number, currentSpeed: number) {
    // Mirrors horizon.py exactly, including popping the *first* entry when
    // any obstacle is flagged for removal.
    const updated = this.obstacles.slice();
    for (const ob of this.obstacles) {
      ob.update(deltaTime, currentSpeed);
      if (ob.remove && updated.length) {
        updated.shift();
      }
    }
    this.obstacles = updated;

    if (this.obstacles.length) {
      const last = this.obstacles[this.obstacles.length - 1]!;
      if (!last.followingObstacleCreated && last.isVisible() &&
          (last.xPos + last.width + last.gap) < this.containerWidth) {
        this.addNewObstacle(currentSpeed);
        last.followingObstacleCreated = true;
      }
    } else {
      this.addNewObstacle(currentSpeed);
    }
  }

  private addNewObstacle(currentSpeed: number) {
    // The last type is the alt-mode collectable, which is never spawned.
    const obstacleCount = this.obstacleTypes.length - 2;
    const obstacleType = this.obstacleTypes[randint(0, obstacleCount)]!;

    if (this.duplicateObstacleCheck(obstacleType.type) ||
        currentSpeed < obstacleType.minSpeed) {
      this.addNewObstacle(currentSpeed);
      return;
    }

    const spritePos =
        this.spritePos[obstacleType.type as keyof SpritePositions];
    this.obstacles.push(new Obstacle(
        this.canvas, obstacleType, spritePos, this.sprite, this.containerWidth,
        this.gapCoefficient, currentSpeed, obstacleType.width,
        this.hasAudioCues));

    this.obstacleHistory.unshift(obstacleType.type);
    if (this.obstacleHistory.length > 1) {
      this.obstacleHistory.length =
          Math.min(this.obstacleHistory.length, CONFIG.maxObstacleDuplication);
    }
  }

  private duplicateObstacleCheck(nextType: string): boolean {
    let dup = 0;
    for (const t of this.obstacleHistory) {
      dup = t === nextType ? dup + 1 : 0;
    }
    return dup >= CONFIG.maxObstacleDuplication;
  }

  reset() {
    this.obstacles = [];
    for (const line of this.horizonLines) {
      line.reset();
    }
    this.nightMode.reset();
  }

  save(): State {
    return {
      obstacleHistory: [...this.obstacleHistory],
      obstacles: this.obstacles.map(o => o.save()),
      clouds: this.clouds.map(c => c.save()),
      horizonLines: this.horizonLines.map(l => l.save()),
      nightMode: this.nightMode.save(),
    };
  }

  load(state: State) {
    this.obstacleHistory = [...state['obstacleHistory'] as string[]];
    this.obstacles = (state['obstacles'] as State[]).map(
        o => Obstacle.fromState(
            this.canvas, this.spritePos, this.sprite, this.hasAudioCues, o));
    this.clouds = (state['clouds'] as State[]).map(
        c => Cloud.fromState(this.canvas, this.spritePos.cloud, this.sprite, c));
    (state['horizonLines'] as State[]).forEach((l, i) => this.horizonLines[i]!.load(l));
    this.nightMode.load(state['nightMode'] as State);
  }

  private addCloud() {
    this.clouds.push(
        new Cloud(this.canvas, this.spritePos.cloud, this.containerWidth, this.sprite));
  }
}
