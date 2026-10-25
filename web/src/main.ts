// Every viewer runs the same game: the state at the bundled checkpoint is
// advanced to the current time, then one step per 1/60 s of wall-clock time.
// Everything (model, sprites, font, visualizer, training log) is inside the
// bundle, so
// nothing can fail to load once the page is open.

import './style.css';
import './controls.css';

import fontUrl from './assets/PressStart2P-Regular.ttf?inline';
import spriteUrl from './assets/100-offline-sprite.png?inline';
import model from './assets/best-brain.json';
import {Brain} from './brain.js';
import type {SerializedBrain} from './brain.js';
import {LDPI, loadSpriteSheet} from './game/sprites.js';
import type {SpriteSheet} from './game/sprites.js';
import {Decision, drawTrainingChart, Stats} from './panels.js';
import {SensorOverlay} from './sensors.js';
import {NeuronTooltip} from './tooltip.js';
import checkpointData from './timeline/checkpoint.json';
import {frameAt, timeOfFrame} from './timeline/timeline.js';
import type {Checkpoint} from './timeline/timeline.js';
import visualizerSource from './vendor/visualizer.js?raw';
import {ModelWatcher} from './watcher.js';

declare global {
  interface Window {
    NEURO_WEIGHTS: {ih: number[][], ho: number[][], bh: number[], bo: number[]};
    toggleNeuroCheck: (elemId: string, globalVar: string) => void;
    useVerticalLayout: boolean;
    isDragging: boolean;
    layerSpacing: number;
    smoothLayerSpacing: number;
    activeNode: unknown;
    drawBrain?: (data: {inputs: number[], hidden: number[], outputs: number[]}) => void;
    vizScale: number;
    panX: number;
    panY: number;
    useWeightColor: boolean;
    useNodeActivationColor: boolean;
    toggleNeuroGroup: (groupId: string, arrowId: string) => void;
    /** Height of the drawing itself, set by visualizer.js every frame. */
    neuroContentHeight?: number;
    /** Distance between the top and bottom node centres, likewise. */
    neuroNodeSpan?: number;
    /** Whether the canvas fills its card instead of fitting its content. */
    neuroFillParent: boolean;
  }
}

const checkpoint = checkpointData as unknown as Checkpoint;

// Catching up runs without drawing; check the clock every this many steps.
const CATCH_UP_BATCH = 256;
const FRAME_BUDGET_MS = 12;
const INITIAL_BUDGET_MS = 3000;

// How far the drawing reaches beyond the input/output layers: input names on
// the left, output names on the right.
const LABEL_EXTENT = [165, 115] as const;
// The vertical layout's extent around the centre line, layer names included.
const VERTICAL_EXTENT = [300, 490] as const;
// Auto layer spacing range; wider spreads the layers too far apart to follow.
// The panel's "Layer spacing" slider goes 50-800.
const MIN_LAYER_SPACING = 180;
const MAX_LAYER_SPACING = 340;
const SIDE_MARGIN = 24;
const VERTICAL_LAYER_SPACING = 290;
// visualizer.js's canvas height before its first frame has sized it.
const DEFAULT_CANVAS_HEIGHT = 700;
const COMPACT_SCALE = 0.6;
// Next to the game the network is scaled up to fill the card, up to this.
const MAX_FILL_SCALE = 1.6;
// In the horizontal layout the drawing reaches this far beyond the top and
// bottom node centres: a node's radius above, the layer names below.
const DRAWING_ABOVE = 8;
const DRAWING_BELOW = 44;
const FILL_MARGIN = 12;

// Matches the side-by-side layout in style.css.
const sideBySide = window.matchMedia('(min-width: 1200px)');
const gameCanvas = document.querySelector<HTMLCanvasElement>('#game')!;
const brainContainer = document.querySelector<HTMLElement>('#canvas-container')!;
const brainCanvas = document.querySelector<HTMLCanvasElement>('#brainCanvas')!;

/**
 * Viewers' clocks are usually NTP-synced; one that is clearly off is corrected
 * from the server's Date header so it still shows the same moment.
 */
async function clockOffset(): Promise<number> {
  try {
    const controller = new AbortController();
    const timer = setTimeout(() => controller.abort(), 2000);
    const sent = Date.now();
    const response = await fetch(location.href, {
      method: 'HEAD',
      cache: 'no-store',
      signal: controller.signal,
    });
    const received = Date.now();
    clearTimeout(timer);
    const header = response.headers.get('date');
    if (!header) return 0;
    // The header has one-second resolution; assume the middle of that second.
    const offset = Date.parse(header) + 500 - (sent + received) / 2;
    return Math.abs(offset) > 2000 ? offset : 0;
  } catch {
    return 0;
  }
}

/** The standing T-rex from the sprite sheet as the tab and header icon. */
function setFavicon(sprites: SpriteSheet) {
  const canvas = document.createElement('canvas');
  canvas.width = 44;
  canvas.height = 47;
  canvas.getContext('2d')!.drawImage(
      sprites.keyed, LDPI.tRex.x, LDPI.tRex.y, 44, 47, 0, 0, 44, 47);
  document.querySelector<HTMLCanvasElement>('#brand-icon')
      ?.getContext('2d')!.drawImage(canvas, 0, 0);
  const icon = document.createElement('link');
  icon.rel = 'icon';
  icon.href = canvas.toDataURL('image/png');
  document.head.appendChild(icon);
}

/** The two pairs of +/- colour pickers set the same colours; keep them in step. */
function syncColorPickers() {
  const pickers = [...document.querySelectorAll<HTMLInputElement>('.neuro-color')];
  for (const picker of pickers) {
    const target = picker.getAttribute('oninput')?.match(/'(\w+)'/)?.[1];
    picker.addEventListener('input', () => {
      for (const other of pickers) {
        if (other !== picker && other.getAttribute('oninput')?.includes(`'${target}'`)) {
          other.value = picker.value;
        }
      }
    });
  }
}

/** The panel's headers and checkboxes are plain divs; make them keyboard-usable. */
function makeControlsAccessible() {
  const controls = document.querySelectorAll<HTMLElement>(
      '#neuro-custom-controls .neuro-header, #neuro-custom-controls .neuro-checkbox-wrapper');
  const syncChecked = () => {
    for (const el of controls) {
      const box = el.querySelector('.neuro-checkbox');
      if (box) el.setAttribute('aria-checked', String(box.classList.contains('checked')));
    }
  };
  for (const el of controls) {
    const isCheckbox = el.classList.contains('neuro-checkbox-wrapper');
    el.tabIndex = 0;
    el.setAttribute('role', isCheckbox ? 'checkbox' : 'button');
    el.addEventListener('keydown', e => {
      if (e.key === 'Enter' || e.key === ' ') {
        e.preventDefault();
        el.click();
      }
    });
    el.addEventListener('click', () => setTimeout(syncChecked));
  }
  syncChecked();
}

/**
 * The visualizer starts with the Space's plain grey edges; 720 of them at full
 * opacity read as a dark mass. Start with what the panel's checkboxes show
 * instead: grey Bézier edges for only the signal flowing right now (weight ×
 * activation), pixel neurons, no bias dots. The smooth factors are set too, so
 * nothing animates on load.
 */
function applyDefaultView() {
  Object.assign(window, {
    useBezier: true,
    smoothBezierFactor: 1,
    vSpacingInput: 40,
    smoothVSpacingInput: 40,
    useProportionalOpacity: true,
    smoothPropOpacityFactor: 1,
    showActiveEdgesOnly: true,
    smoothActiveFactor: 1,
    edgeWidth: 1,
    smoothEdgeWidth: 1,
    usePixelNodes: true,
    showBiases: false,
    edgeOpacity: 0.5,
    smoothEdgeOpacity: 0.5,
  });
}

const THEME_KEY = 'neurodino-theme';
const prefersDark = window.matchMedia('(prefers-color-scheme: dark)');

/** A saved choice (data-theme, set in index.html) wins over the system's. */
function isDark(): boolean {
  const theme = document.documentElement.dataset['theme'];
  return theme ? theme === 'dark' : prefersDark.matches;
}

// The visualizer draws with these; the panel's colour pickers show them.
const VISUALIZER_COLORS = {
  light: {
    labelColor: '#535353', defaultEdgeColor: '#505050', nodeColor: '#ffffff',
    nodeBorderColor: '#535353', posColor: '#2563eb', negColor: '#e5484d',
    activationInk: '0, 0, 0',
  },
  dark: {
    labelColor: '#e8eaed', defaultEdgeColor: '#c4c7c5', nodeColor: '#292a2d',
    nodeBorderColor: '#e8eaed', posColor: '#8ab4f8', negColor: '#f28b82',
    activationInk: '232, 234, 237',
  },
};

/** Points the canvases and the panel at the current theme's colours. */
function applyTheme(sensors: SensorOverlay) {
  const dark = isDark();
  document.documentElement.classList.toggle('dark', dark);
  const colors = VISUALIZER_COLORS[dark ? 'dark' : 'light'];
  Object.assign(window, colors);
  for (const picker of document.querySelectorAll<HTMLInputElement>('.neuro-color')) {
    const target = picker.getAttribute('oninput')?.match(/'(\w+)'/)?.[1];
    if (target && target in colors) picker.value = colors[target as keyof typeof colors];
  }
  sensors.refreshColors();
  const label = dark ? 'Switch to light mode' : 'Switch to dark mode';
  const button = document.querySelector<HTMLButtonElement>('#theme-toggle')!;
  button.setAttribute('aria-label', label);
  button.title = label;
}

/** The header's moon/sun button; the choice is remembered in this browser. */
function bindTheme(sensors: SensorOverlay) {
  document.querySelector('#theme-toggle')!.addEventListener('click', () => {
    const theme = isDark() ? 'light' : 'dark';
    document.documentElement.dataset['theme'] = theme;
    try {
      localStorage.setItem(THEME_KEY, theme);
    } catch {
      // Storage blocked (private window): the choice lasts until reload.
    }
    applyTheme(sensors);
  });
  prefersDark.addEventListener('change', () => applyTheme(sensors));
  applyTheme(sensors);
}

/** The canvas is 150px tall until visualizer.js sizes it on its first frame. */
function brainCanvasHeight(): number {
  return brainCanvas.style.height ? brainCanvas.clientHeight : DEFAULT_CANVAS_HEIGHT;
}

/** Height of the drawing, which can differ from the canvas when it fills its card. */
function brainContentHeight(): number {
  return window.neuroContentHeight ?? brainCanvasHeight();
}

/** The legend only applies while edges or nodes are coloured by sign. */
function updateLegend() {
  const legend = document.querySelector<HTMLElement>('.network-card .legend')!;
  legend.hidden = !window.useWeightColor && !window.useNodeActivationColor;
}

// Until the viewer moves the "Layer spacing" slider, the layer spacing follows
// the available width.
let autoLayerSpacing = true;

function layerSpacingSlider(): HTMLInputElement|null {
  return document.querySelector<HTMLInputElement>('input[oninput*="layerSpacing"]');
}

/** Sets the layer spacing without animating, and shows it on the slider. */
function setLayerSpacing(spacing: number) {
  window.layerSpacing = spacing;
  window.smoothLayerSpacing = spacing;
  const slider = layerSpacingSlider();
  if (slider) slider.value = String(spacing);
  const label = document.getElementById('val_spacing');
  if (label) label.textContent = String(spacing);
}

/**
 * Lays the network out for its card. Next to the game the card is as tall as
 * the viewport and the drawing is scaled to fill its height, with the layers
 * spread over the width that leaves. Elsewhere it is drawn at full size and
 * scaled down only when it does not fit; on phones the container shrinks with
 * it instead of leaving a tall empty canvas.
 */
function fitBrainView() {
  const width = brainContainer.clientWidth;
  const canvasHeight = brainCanvasHeight();
  const fillHeight = sideBySide.matches;
  window.neuroFillParent = fillHeight;
  // Fill the card with the nodes and layer names, not the canvas's padding.
  const nodeFill = fillHeight && !window.useVerticalLayout && window.neuroNodeSpan !== undefined;
  const drawingHeight = nodeFill ? window.neuroNodeSpan! + DRAWING_ABOVE + DRAWING_BELOW
                                 : brainContentHeight();
  const available = brainContainer.clientHeight - (nodeFill ? 2 * FILL_MARGIN : 0);
  const heightScale = fillHeight ? Math.min(MAX_FILL_SCALE, available / drawingHeight) : 1;
  // How far below the canvas centre the drawing's centre is (world units).
  const centreOffset = nodeFill ? (DRAWING_BELOW - DRAWING_ABOVE) / 2 : 0;
  // The width the layers can spread over once the drawing is scaled down.
  const logicalWidth = width / heightScale;
  let left: number;
  let right: number;

  if (window.useVerticalLayout) {
    // The vertical layout stacks the layers, so the spacing is bounded by the
    // canvas height, not the width: keep the Space's 290.
    if (autoLayerSpacing) setLayerSpacing(VERTICAL_LAYER_SPACING);
    [left, right] = VERTICAL_EXTENT;
  } else {
    let spacing = window.layerSpacing;
    if (autoLayerSpacing) {
      const room = (logicalWidth - LABEL_EXTENT[0] - LABEL_EXTENT[1] - 2 * SIDE_MARGIN) / 2;
      spacing = Math.round(Math.min(MAX_LAYER_SPACING, Math.max(MIN_LAYER_SPACING, room)));
      setLayerSpacing(spacing);
    }
    left = spacing + LABEL_EXTENT[0];
    right = spacing + LABEL_EXTENT[1];
  }

  const content = left + right;
  const scale = Math.min(heightScale, width / (content + 2 * SIDE_MARGIN));
  const contentLeft = width / 2 - left;
  window.vizScale = scale;
  window.panX = (width - scale * content) / 2 - scale * contentLeft;

  if (!fillHeight && scale < COMPACT_SCALE) {
    brainContainer.style.height = `${Math.round(canvasHeight * scale + 20)}px`;
    brainContainer.style.minHeight = '0';
    brainContainer.style.overflow = 'hidden';
    window.panY = 10;
  } else {
    brainContainer.style.removeProperty('height');
    brainContainer.style.removeProperty('min-height');
    brainContainer.style.removeProperty('overflow');
    window.panY = canvasHeight / 2 - scale * (canvasHeight / 2 + centreOffset);
  }
}

/**
 * visualizer.js opens a group to its height at that moment, so showing the
 * colour pickers inside it later would be cut off. Once open, let it grow;
 * before closing, pin the height again so the close still animates.
 */
function letOpenGroupsGrow() {
  const toggle = window.toggleNeuroGroup;
  window.toggleNeuroGroup = (groupId, arrowId) => {
    const group = document.getElementById(groupId)!;
    if (group.style.maxHeight === 'none') {
      group.style.maxHeight = `${group.scrollHeight}px`;
      void group.offsetHeight;
    }
    toggle(groupId, arrowId);
    if (group.style.maxHeight !== '0px') {
      setTimeout(() => {
        if (group.style.maxHeight !== '0px') group.style.maxHeight = 'none';
      }, 350);
    }
  };
}

/** The Settings button opens the visualizer's panel over the network. */
function bindSettings() {
  const button = document.querySelector<HTMLButtonElement>('#settings-toggle')!;
  const popover = document.querySelector<HTMLElement>('#settings-popover')!;
  const head = document.querySelector<HTMLElement>('.network-card .card-head')!;
  const setOpen = (open: boolean) => {
    popover.hidden = !open;
    button.setAttribute('aria-expanded', String(open));
    button.textContent = open ? 'Settings ▲' : 'Settings ▼';
    // Just under the card's head, whose height depends on the width, and
    // never past the card's bottom (it scrolls instead).
    if (open) {
      const top = head.offsetHeight + 8;
      const card = head.parentElement!;
      popover.style.top = `${top}px`;
      popover.style.maxHeight = `${card.clientHeight - top - 12}px`;
    }
  };
  button.addEventListener('click', () => setOpen(popover.hidden));
  document.addEventListener('pointerdown', e => {
    const target = e.target as Node;
    if (!popover.hidden && !popover.contains(target) && !button.contains(target)) setOpen(false);
  });
  document.addEventListener('keydown', e => {
    if (e.key === 'Escape' && !popover.hidden) {
      setOpen(false);
      button.focus();
    }
  });
}

function bindSensorToggle(overlay: SensorOverlay) {
  const toggle = document.querySelector<HTMLButtonElement>('#sensor-toggle')!;
  toggle.addEventListener('click', () => {
    overlay.enabled = !overlay.enabled;
    toggle.setAttribute('aria-pressed', String(overlay.enabled));
  });
}

async function boot() {
  const pixelFont = new FontFace('PressStart2P', `url(${fontUrl})`);
  const [sprites, offset] = await Promise.all([
    loadSpriteSheet(spriteUrl),
    clockOffset(),
    pixelFont.load().then(font => document.fonts.add(font)),
  ]);
  setFavicon(sprites);

  // Never run behind the checkpoint, even on a clock that is far off.
  const lag = timeOfFrame(checkpoint, checkpoint.frame) - (Date.now() + offset);
  const correctedOffset = lag > 0 ? offset + lag : offset;
  const now = () => Date.now() + correctedOffset;

  const brain = Brain.fromJSON(model as unknown as SerializedBrain);
  const watcher =
      new ModelWatcher(brain, sprites, {checkpoint: checkpoint.state}, gameCanvas);

  window.NEURO_WEIGHTS = {
    ih: brain.weightsIH,
    ho: brain.weightsHO,
    bh: brain.biasH,
    bo: brain.biasO,
  };
  const setupNeuroDino =
      new Function(`${visualizerSource}\nreturn setupNeuroDino;`)() as () => void;
  setupNeuroDino();
  applyDefaultView();
  syncColorPickers();
  makeControlsAccessible();
  bindSettings();
  letOpenGroupsGrow();
  updateLegend();
  const tooltip = new NeuronTooltip(brain, brainCanvas, brainContainer);

  let userMovedView = false;
  brainCanvas.addEventListener('pointermove', () => {
    if (window.isDragging) userMovedView = true;
  });
  // A touch that turns into a page scroll never sends pointerup.
  window.addEventListener('pointercancel', () => {
    window.isDragging = false;
    window.activeNode = null;
  });
  const toggleNeuroCheck = window.toggleNeuroCheck;
  window.toggleNeuroCheck = (elemId, globalVar) => {
    toggleNeuroCheck(elemId, globalVar);
    updateLegend();
    if (elemId === 'vertical_check') {
      userMovedView = false;
      fitBrainView();
    }
  };
  brainCanvas.addEventListener('wheel', e => {
    if (e.ctrlKey || e.metaKey) userMovedView = true;
  });
  brainCanvas.addEventListener('dblclick', () => {
    userMovedView = false;
    fitBrainView();
  });
  layerSpacingSlider()?.addEventListener('input', () => {
    autoLayerSpacing = false;
    if (!userMovedView) fitBrainView();
  });
  fitBrainView();
  window.addEventListener('resize', () => {
    if (!userMovedView) fitBrainView();
  });

  const sensors = new SensorOverlay(document.querySelector<HTMLCanvasElement>('#sensors')!);
  bindTheme(sensors);
  const stats = new Stats();
  const decision = new Decision();
  bindSensorToggle(sensors);
  drawTrainingChart();

  /**
   * Runs the frames up to the current time. Only the last one is drawn; the
   * rest are never on screen.
   */
  const advance = (budgetMs: number) => {
    const target = frameAt(checkpoint, now());
    if (watcher.frame >= target) return;

    const deadline = performance.now() + budgetMs;
    watcher.screen.muted = true;
    while (watcher.frame < target - 1) {
      const batchEnd = Math.min(target - 1, watcher.frame + CATCH_UP_BATCH);
      while (watcher.frame < batchEnd) watcher.tick();
      if (performance.now() > deadline) break;
    }
    watcher.screen.muted = false;
    if (watcher.frame === target - 1) watcher.tick();
  };

  advance(INITIAL_BUDGET_MS);

  // The canvas height follows the layout (first frame, vertical layout,
  // spacing sliders); keep the view fitted to it.
  let fittedHeights = '';
  // The stats change every frame; a few updates a second stay legible.
  let statsFrame = 0;

  const frame = () => {
    requestAnimationFrame(frame);
    advance(FRAME_BUDGET_MS);
    // Everything below shows the same frame as the game.
    window.drawBrain?.({
      inputs: brain.lastInputs,
      hidden: brain.lastHidden,
      outputs: brain.lastOutputs,
    });
    tooltip.update();
    sensors.draw(watcher, brain);
    decision.update(brain.lastOutputs, watcher.frame);
    if (statsFrame++ % 6 === 0) stats.update(watcher);
    const heights = `${brainCanvasHeight()}:${brainContentHeight()}`;
    if (heights !== fittedHeights) {
      fittedHeights = heights;
      if (!userMovedView) fitBrainView();
    }
  };
  requestAnimationFrame(frame);
}

void boot();
