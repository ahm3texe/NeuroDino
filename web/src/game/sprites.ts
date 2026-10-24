// Port of pydino/offline_sprite_definitions.py (LDPI sheet only; pydino never
// enables HiDPI or the alt game mode).

export interface CollisionBox {
  x: number;
  y: number;
  width: number;
  height: number;
}

export interface SpritePos {
  x: number;
  y: number;
}

export interface ObstacleType {
  type: string;
  width: number;
  height: number;
  yPos: number|number[];
  multipleSpeed: number;
  minGap: number;
  minSpeed: number;
  collisionBoxes: CollisionBox[];
  yPosMobile?: number[];
  speedOffset?: number;
  numFrames?: number;
  frameRate?: number;
}

export interface LineConf {
  sourceX: number;
  sourceY: number;
  width: number;
  height: number;
  yPos: number;
}

export const LDPI = {
  backgroundEl: {x: 86, y: 2},
  cactusLarge: {x: 332, y: 2},
  cactusSmall: {x: 228, y: 2},
  obstacle2: {x: 332, y: 2},
  obstacle: {x: 228, y: 2},
  cloud: {x: 86, y: 2},
  horizon: {x: 2, y: 54},
  moon: {x: 484, y: 2},
  pterodactyl: {x: 134, y: 2},
  restart: {x: 2, y: 68},
  textSprite: {x: 655, y: 2},
  tRex: {x: 848, y: 2},
  star: {x: 645, y: 2},
  collectable: {x: 0, y: 0},
  altGameEnd: {x: 32, y: 0},
} satisfies Record<string, SpritePos>;

export type SpritePositions = typeof LDPI;

export const OBSTACLE_TYPES: readonly ObstacleType[] = [
  {
    type: 'cactusSmall',
    width: 17,
    height: 35,
    yPos: 105,
    multipleSpeed: 4,
    minGap: 120,
    minSpeed: 0,
    collisionBoxes: [
      {x: 0, y: 7, width: 5, height: 27},
      {x: 4, y: 0, width: 6, height: 34},
      {x: 10, y: 4, width: 7, height: 14},
    ],
  },
  {
    type: 'cactusLarge',
    width: 25,
    height: 50,
    yPos: 90,
    multipleSpeed: 7,
    minGap: 120,
    minSpeed: 0,
    collisionBoxes: [
      {x: 0, y: 12, width: 7, height: 38},
      {x: 8, y: 0, width: 7, height: 49},
      {x: 13, y: 10, width: 10, height: 38},
    ],
  },
  {
    type: 'pterodactyl',
    width: 46,
    height: 40,
    yPos: [100, 75, 50],
    yPosMobile: [100, 50],
    multipleSpeed: 999,
    minSpeed: 8.5,
    minGap: 150,
    collisionBoxes: [
      {x: 15, y: 15, width: 16, height: 5},
      {x: 18, y: 21, width: 24, height: 6},
      {x: 2, y: 14, width: 4, height: 3},
      {x: 6, y: 10, width: 4, height: 7},
      {x: 10, y: 8, width: 6, height: 9},
    ],
    numFrames: 2,
    frameRate: 1000.0 / 6.0,
    speedOffset: 0.8,
  },
  {
    type: 'collectable',
    width: 31,
    height: 24,
    yPos: 104,
    multipleSpeed: 1000,
    minGap: 9999,
    minSpeed: 0,
    collisionBoxes: [{x: 0, y: 0, width: 32, height: 25}],
  },
];

export const LINES: readonly LineConf[] = [
  {sourceX: 2, sourceY: 52, width: 600, height: 12, yPos: 127},
];

export const MAX_GAP_COEFFICIENT = 1.5;
export const MAX_OBSTACLE_LENGTH = 3;

/**
 * The sprite sheet in two flavours:
 * - `alpha`: per-pixel alpha, what most pydino components blit.
 * - `keyed`: what trex.py blits. It calls convert() + set_colorkey(black),
 *   which drops the alpha channel, so every non-transparent pixel is opaque.
 */
export interface SpriteSheet {
  alpha: HTMLCanvasElement;
  keyed: HTMLCanvasElement;
}

export async function loadSpriteSheet(url: string): Promise<SpriteSheet> {
  // The load event, not img.decode(): Chrome can hold decode() back until a
  // background tab becomes visible.
  const img = new Image();
  await new Promise<void>((resolve, reject) => {
    img.onload = () => resolve();
    img.onerror = () => reject(new Error('Sprite sheet could not be loaded'));
    img.src = url;
  });

  const alpha = document.createElement('canvas');
  alpha.width = img.naturalWidth;
  alpha.height = img.naturalHeight;
  const alphaCtx = alpha.getContext('2d')!;
  alphaCtx.drawImage(img, 0, 0);

  const keyed = document.createElement('canvas');
  keyed.width = alpha.width;
  keyed.height = alpha.height;
  const keyedCtx = keyed.getContext('2d')!;
  const pixels = alphaCtx.getImageData(0, 0, alpha.width, alpha.height);
  for (let i = 3; i < pixels.data.length; i += 4) {
    if (pixels.data[i]! > 0) pixels.data[i] = 255;
  }
  keyedCtx.putImageData(pixels, 0, 0);

  return {alpha, keyed};
}
