// pydino/constants.py + the Config dataclass from pydino/runner.py.

export const FPS = 60;
export const GAME_WIDTH = 600;
export const GAME_HEIGHT = 150;

export const CONFIG = {
  bottomPad: 10,
  clearTime: 3000,
  invertFadeDuration: 12000,
  maxObstacleDuplication: 2,
  acceleration: 0.001,
  gapCoefficient: 0.6,
  invertDistance: 700,
  maxSpeed: 13.0,
  speed: 6.0,
} as const;
