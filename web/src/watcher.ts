// Port of watch_model.py ModelWatcher, as app.py runs it on the Space: one
// trained brain plays and the 600x150 game surface is what the page shows.

import {argmax} from './brain.js';
import type {Brain} from './brain.js';
import {Rng, rng} from './determinism.js';
import {CONFIG, GAME_HEIGHT, GAME_WIDTH} from './game/config.js';
import {DistanceMeter} from './game/distanceMeter.js';
import {Horizon} from './game/horizon.js';
import type {Obstacle} from './game/obstacle.js';
import {LDPI} from './game/sprites.js';
import type {CollisionBox, SpriteSheet} from './game/sprites.js';
import {capture, restore} from './game/state.js';
import type {State} from './game/state.js';
import {Surface} from './game/surface.js';
import {Status, Trex} from './game/trex.js';
import {pyInt} from './py.js';

// Must match training (neuro_runner.py).
const MAX_OBSTACLE_WIDTH = 75;
const MAX_TTI_FRAMES = 50.0;
const DUCK_THRESHOLD_Y = 75;

const DELTA = 1000.0 / 60;
const VISUAL_INVERT_MS = 1000;
const BACKGROUND = [247, 247, 247] as const;

const STATE_KEYS = [
  'frame', 'score', 'crashed', 'playing', 'distanceRan', 'runningTime',
  'currentSpeed', 'inverted', 'invertTimer', 'invertTrigger', 'gameNumber',
  'bestScore',
];

export class ModelWatcher {
  readonly screen: Surface;
  /** Steps since the timeline started; frame N is shown at epoch + N/60 s. */
  frame = 0;
  score = 0;
  /** 1 for the first game of the timeline, +1 after every crash. */
  gameNumber = 1;
  bestScore = 0;
  crashed = false;
  private playing = false;

  private dino!: Trex;
  private readonly horizon: Horizon;
  private readonly distanceMeter: DistanceMeter;
  private distanceRan = 0.0;
  private runningTime = 0.0;
  currentSpeed: number = CONFIG.speed;
  private inverted = false;
  private invertTimer = 0;
  private invertTrigger = false;

  /**
   * Starts a fresh game from `seed` (frame 0), or rebuilds the one saved in
   * `checkpoint`. Either way the result is the same on every browser.
   */
  constructor(
      private readonly brain: Brain, private readonly sprites: SpriteSheet,
      start: {seed: number}|{checkpoint: State}, canvas?: HTMLCanvasElement) {
    rng.setState(new Rng('seed' in start ? start.seed : 0).getState());
    this.screen = new Surface(GAME_WIDTH, GAME_HEIGHT, canvas);
    this.screen.fill(BACKGROUND);
    // Runner(use_audio=True) => hasAudioCues, which doubles obstacle gaps.
    this.horizon = new Horizon(
        this.screen, LDPI, GAME_WIDTH, CONFIG.gapCoefficient, sprites.alpha, true);
    this.distanceMeter =
        new DistanceMeter(this.screen, LDPI.textSprite, GAME_WIDTH, sprites.alpha);
    this.setupNeuroTrex();
    this.playing = true;
    if ('checkpoint' in start) this.load(start.checkpoint);
  }

  private setupNeuroTrex() {
    // NeuroTrex: invisible while constructing, forced into RUNNING, then shown.
    this.dino = new Trex(this.screen, LDPI.tRex, this.sprites.keyed, false);
    this.dino.update(0, Status.RUNNING);
    this.dino.visible = true;
  }

  private getInputs(): number[] {
    const dino = this.dino;
    const speed = this.currentSpeed / CONFIG.maxSpeed;

    let dinoYNormalized = 0.0;
    if (dino.jumping) {
      const heightAboveGround = dino.groundYPos - dino.yPos;
      dinoYNormalized =
          Math.min(1.0, Math.max(0.0, heightAboveGround / dino.config.maxJumpHeight));
    }

    let dinoVelocity = 0.0;
    if (dino.jumping) {
      dinoVelocity = Math.max(-1.0, Math.min(1.0, dino.jumpVelocity / 10.0));
    }

    const isAirborne = dino.jumping ? 1.0 : 0.0;
    const isDucking = dino.ducking ? 1.0 : 0.0;

    let obs1Dist = 0.0;
    let obs1Action = 0.0;
    let obs1W = 0.0;
    let obs2Dist = 0.0;
    let obs2Action = 0.0;
    let obs2W = 0.0;
    let gap = 0.0;

    if (this.horizon.obstacles.length) {
      const future = this.horizon.obstacles.filter(o => o.xPos > dino.xPos)
                         .sort((a, b) => a.xPos - b.xPos);

      if (future.length > 0) {
        const o1 = future[0]!;
        const tti1 = (o1.xPos - dino.xPos) / Math.max(1.0, this.currentSpeed);
        obs1Dist = 1.0 - Math.min(1.0, tti1 / MAX_TTI_FRAMES);
        obs1Action = o1.yPos < DUCK_THRESHOLD_Y ? 1.0 : 0.0;
        obs1W = Math.min(1.0, o1.width / MAX_OBSTACLE_WIDTH);

        if (future.length > 1) {
          const o2 = future[1]!;
          const tti2 = (o2.xPos - dino.xPos) / Math.max(1.0, this.currentSpeed);
          obs2Dist = 1.0 - Math.min(1.0, tti2 / MAX_TTI_FRAMES);
          obs2Action = o2.yPos < DUCK_THRESHOLD_Y ? 1.0 : 0.0;
          obs2W = Math.min(1.0, o2.width / MAX_OBSTACLE_WIDTH);

          const rawGap = o2.xPos - (o1.xPos + o1.width);
          const timeGap = rawGap / Math.max(1.0, this.currentSpeed);
          gap = 1.0 - Math.min(1.0, timeGap / 15.0);
        }
      }
    }

    return [
      obs1Dist, obs1Action, obs1W,
      obs2Dist, obs2Action, obs2W,
      speed, gap,
      dinoYNormalized, dinoVelocity,
      isAirborne, isDucking,
    ];
  }

  /** One fixed 60 FPS physics step (watch_model.py ModelWatcher.update). */
  update() {
    this.screen.fill(BACKGROUND);

    if (this.playing) {
      this.runningTime += DELTA;
    }

    const hasObstacles = this.runningTime > CONFIG.clearTime;

    const showNightMode = this.inverted;
    if (this.playing) {
      const actualScore = pyInt(this.distanceRan * 0.025);

      if (this.invertTimer > CONFIG.invertFadeDuration) {
        this.invertTimer = 0;
        this.invertTrigger = false;
        this.inverted = !this.inverted;
      } else if (this.invertTimer > 0) {
        this.invertTimer += DELTA;
      } else if (actualScore > 0 &&
                 actualScore % CONFIG.invertDistance === 0 && !this.invertTrigger) {
        this.invertTimer += DELTA;
        this.inverted = !this.inverted;
        this.invertTrigger = true;
      } else if (actualScore % CONFIG.invertDistance !== 0) {
        this.invertTrigger = false;
      }
    }

    this.horizon.update(DELTA, this.currentSpeed, hasObstacles, showNightMode);

    if (this.playing && !this.crashed && this.dino.status !== Status.CRASHED) {
      const outputs = this.brain.predict(this.getInputs());
      this.dino.act(argmax(outputs), this.currentSpeed);
      this.dino.update(DELTA);
      if (this.dino.jumping) {
        this.dino.updateJump(DELTA);
      }
    }

    if (this.playing) {
      this.distanceMeter.update(DELTA, Math.ceil(this.distanceRan));
    }

    if (this.playing && !this.crashed) {
      if (hasObstacles && this.horizon.obstacles.length) {
        for (const obstacle of this.horizon.obstacles) {
          if (checkForCollision(obstacle, this.dino)) {
            this.dino.update(100, Status.CRASHED);
            this.crashed = true;
            break;
          }
        }
      }

      if (!this.crashed) {
        this.distanceRan += this.currentSpeed * (DELTA / (1000 / 60));
        this.score = pyInt(this.distanceRan * 0.025);
        if (this.currentSpeed < CONFIG.maxSpeed) {
          this.currentSpeed += CONFIG.acceleration;
        }
      }
    }

    const fadeFactor = this.getInvertFadeFactor();
    if (fadeFactor > 0) {
      this.screen.invert(fadeFactor);
    }
  }

  private getInvertFadeFactor(): number {
    const T = CONFIG.invertFadeDuration;
    const t = this.invertTimer;
    const vis = VISUAL_INVERT_MS;

    if (this.inverted) {
      if (t === 0) return 1.0;
      if (t < vis) return easeInOutCubic(t / vis);
      if (t <= T - vis) return 1.0;
      return easeInOutCubic(1.0 - ((t - (T - vis)) / vis));
    }
    if (t > 0 && t > T - vis) {
      return easeInOutCubic(1.0 - ((t - (T - vis)) / vis));
    }
    return 0.0;
  }

  /** One frame of app.py's loop: update, and on a crash restart straight away. */
  tick() {
    this.update();
    if (this.crashed) {
      this.bestScore = Math.max(this.bestScore, this.score);
      this.gameNumber++;
      this.restartGame();
    }
    this.frame++;
  }

  save(): State {
    return {
      ...capture(this, STATE_KEYS),
      rng: rng.getState(),
      dino: this.dino.save(),
      horizon: this.horizon.save(),
      distanceMeter: this.distanceMeter.save(),
      brain: {
        inputs: this.brain.lastInputs,
        hidden: this.brain.lastHidden,
        outputs: this.brain.lastOutputs,
      },
    };
  }

  private load(state: State) {
    restore(this, state, STATE_KEYS);
    this.dino.load(state['dino'] as State);
    this.horizon.load(state['horizon'] as State);
    this.distanceMeter.load(state['distanceMeter'] as State);
    const brain = state['brain'] as {inputs: number[], hidden: number[], outputs: number[]};
    this.brain.lastInputs = [...brain.inputs];
    this.brain.lastHidden = [...brain.hidden];
    this.brain.lastOutputs = [...brain.outputs];
    rng.setState(state['rng'] as number[]);
  }

  private restartGame() {
    this.crashed = false;
    this.playing = true;
    this.distanceRan = 0;
    this.score = 0;
    this.currentSpeed = CONFIG.speed;
    this.runningTime = 0;

    this.inverted = false;
    this.invertTimer = 0;
    this.invertTrigger = false;

    this.horizon.reset();
    this.distanceMeter.reset();

    this.setupNeuroTrex();
    this.dino.update(0, Status.RUNNING);
  }
}

/** pydino Runner._check_for_collision, including its quirks. */
function checkForCollision(obstacle: Obstacle, trex: Trex): boolean {
  const tbox: CollisionBox = {
    x: trex.xPos + 1,
    y: trex.yPos + 1,
    width: trex.config.width - 2,
    height: trex.config.height - 2,
  };
  const obox: CollisionBox = {
    x: obstacle.xPos + 1,
    y: obstacle.yPos + 1,
    width: obstacle.typeConfig.width * obstacle.size - 2,
    height: obstacle.typeConfig.height - 2,
  };

  if (!(tbox.x < obox.x + obox.width && tbox.x + tbox.width > obox.x &&
        tbox.y < obox.y + obox.height && tbox.height + tbox.y > obox.y)) {
    return false;
  }

  for (const tb of trex.getCollisionBoxes()) {
    for (const ob of obstacle.collisionBoxes) {
      const adjT = {x: tb.x + tbox.x, y: tb.y + tbox.y, width: tb.width, height: tb.height};
      const adjO = {x: ob.x + obox.x, y: ob.y + obox.y, width: ob.width, height: ob.height};
      // The last term compares adjO.y with itself in pydino; kept as-is
      // because the trained model was evaluated against this behaviour.
      if (adjT.x < adjO.x + adjO.width && adjT.x + adjT.width > adjO.x &&
          adjT.y < adjO.y + adjO.height && adjT.height + adjO.y > adjO.y) {
        return true;
      }
    }
  }
  return false;
}

function easeInOutCubic(t: number): number {
  if (t <= 0.0) return 0.0;
  if (t >= 1.0) return 1.0;
  if (t < 0.5) return 4.0 * t * t * t;
  const u = -2.0 * t + 2.0;
  return 1.0 - (u * u * u) / 2.0;
}
