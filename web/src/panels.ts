// The cards around the game: live stats, the current decision with its recent
// history, and the training curve from training_log.csv.

import trainingLog from './assets/training-log.csv?raw';
import type {ModelWatcher} from './watcher.js';

// CSS colours, so they follow light and dark mode.
export const ACTIONS = [
  {name: 'JUMP', color: 'var(--jump)'},
  {name: 'DUCK', color: 'var(--duck)'},
  {name: 'RUN', color: 'var(--run)'},
];

const numberFormat = new Intl.NumberFormat('en-US');
const HISTORY = 75;

const byId = (id: string) => document.getElementById(id)!;
const setText = (el: HTMLElement, text: string) => {
  if (el.textContent !== text) el.textContent = text;
};

/** "22d 04h 13m", "4h 13m 09s" or "13m 09s". */
function formatDuration(ms: number): string {
  const s = Math.floor(ms / 1000);
  const pad = (n: number) => String(n).padStart(2, '0');
  const [d, h, m, sec] = [Math.floor(s / 86400), Math.floor(s / 3600) % 24, Math.floor(s / 60) % 60, s % 60];
  if (d > 0) return `${d}d ${pad(h)}h ${pad(m)}m`;
  if (h > 0) return `${h}h ${pad(m)}m ${pad(sec)}s`;
  return `${m}m ${pad(sec)}s`;
}

/** Score, best score, deaths and time since the last death, under the game. */
export class Stats {
  private readonly score = byId('stat-score');
  private readonly best = byId('stat-best');
  private readonly deaths = byId('stat-deaths');
  private readonly alive = byId('stat-alive');

  update(watcher: ModelWatcher) {
    setText(this.score, numberFormat.format(Math.floor(watcher.score)));
    setText(this.best, numberFormat.format(Math.floor(Math.max(watcher.bestScore, watcher.score))));
    // gameNumber is 1 for the first game and +1 after every crash.
    setText(this.deaths, numberFormat.format(watcher.gameNumber - 1));
    // Game time since the last restart, in ms. Read from the private field on
    // purpose: watcher.ts is part of the checkpoint fingerprint.
    const {runningTime} = watcher as unknown as {runningTime: number};
    setText(this.alive, formatDuration(runningTime));
  }
}

/** The chosen action, the three probabilities and the last 75 choices. */
export class Decision {
  private readonly now = byId('now-action');
  private readonly confidence = byId('now-confidence');
  private readonly frame = byId('decision-frame');
  private readonly rows = [...document.querySelectorAll<HTMLElement>('.decision-row')];
  private readonly cells: HTMLElement[] = [];
  private readonly history: number[] = [];

  constructor() {
    const strip = byId('decision-strip');
    for (let i = 0; i < HISTORY; i++) {
      const cell = document.createElement('span');
      strip.appendChild(cell);
      this.cells.push(cell);
    }
  }

  update(outputs: number[], frame: number) {
    const chosen = outputs.indexOf(Math.max(...outputs));
    const action = ACTIONS[chosen]!;
    setText(this.now, action.name);
    this.now.style.color = action.color;
    setText(this.confidence, `${Math.round(outputs[chosen]! * 100)}%`);
    setText(this.frame, `frame ${numberFormat.format(frame)}`);

    this.rows.forEach((row, i) => {
      const p = outputs[i] ?? 0;
      row.classList.toggle('chosen', i === chosen);
      row.querySelector<HTMLElement>('.decision-fill')!.style.width = `${(p * 100).toFixed(1)}%`;
      setText(row.querySelector<HTMLElement>('.decision-value')!, `${Math.round(p * 100)}%`);
    });

    this.history.push(chosen);
    if (this.history.length > HISTORY) this.history.shift();
    const offset = HISTORY - this.history.length;
    this.cells.forEach((cell, i) => {
      const a = this.history[i - offset];
      cell.style.background = a === undefined ? '' : ACTIONS[a]!.color;
    });
  }
}

interface Generation {
  generation: number;
  best: number;
  average: number;
  bestSoFar: number;
}

function parseLog(csv: string): Generation[] {
  return csv.trim().split('\n').slice(1).map(line => {
    const [generation, best, average, bestSoFar] = line.split(',').map(Number);
    return {generation: generation!, best: best!, average: average!, bestSoFar: bestSoFar!};
  });
}

/**
 * Record, best and average score of every generation, on a log scale: the
 * scores run from tens to hundreds of thousands. Pointing at the chart (or
 * touching it) reads out that generation below it; otherwise it shows the
 * generation that set the record, whose best network plays on the page.
 */
export function drawTrainingChart() {
  const log = parseLog(trainingLog);
  const last = log[log.length - 1]!;
  const record = log.find(g => g.best === last.bestSoFar)!;
  setText(byId('train-generations'), String(last.generation));

  const width = 300;
  const height = 130;
  const left = 34;
  const right = 8;
  const top = 8;
  const bottom = 18;
  const [lo, hi] = [1, 6];  // 10 .. 1,000,000
  const x = (g: number) => left + (g - 1) / (last.generation - 1) * (width - left - right);
  const y = (v: number) =>
      top + (1 - (Math.log10(Math.max(10, v)) - lo) / (hi - lo)) * (height - top - bottom);
  const line = (pick: (g: Generation) => number) =>
      log.map(g => `${x(g.generation).toFixed(1)},${y(pick(g)).toFixed(1)}`).join(' ');

  const grid = [2, 3, 4, 5, 6].map(p => {
    const label = p === 6 ? '1M' : p >= 3 ? `${10 ** (p - 3)}K` : '100';
    return `<line x1="${left}" x2="${width - right}" y1="${y(10 ** p)}" y2="${y(10 ** p)}" class="grid"/>` +
        `<text x="${left - 5}" y="${y(10 ** p) + 3}" text-anchor="end">${label}</text>`;
  }).join('');
  const ticks = [1, 20, 40, 60, last.generation]
      .map(g => `<text x="${x(g)}" y="${height - 4}" text-anchor="middle">${g}</text>`).join('');

  const chart = byId('training-chart');
  chart.innerHTML = `
    <svg viewBox="0 0 ${width} ${height}" role="img"
         aria-label="Record, best and average score per generation, generations 1 to ${last.generation}">
      ${grid}${ticks}
      <polyline points="${line(g => g.average)}" class="avg"/>
      <polyline points="${line(g => g.best)}" class="best"/>
      <polyline points="${line(g => g.bestSoFar)}" class="record"/>
      <line class="cursor" y1="${top}" y2="${height - bottom}"/>
      <circle r="2.5" class="cursor-dot avg"/>
      <circle r="2.5" class="cursor-dot best"/>
      <circle r="3" class="cursor-dot record"/>
    </svg>`;

  const svg = chart.querySelector('svg')!;
  const cursor = svg.querySelector('.cursor')!;
  const dots = {
    average: svg.querySelector('.cursor-dot.avg')!,
    best: svg.querySelector('.cursor-dot.best')!,
    bestSoFar: svg.querySelector('.cursor-dot.record')!,
  };
  const readout = [...byId('chart-readout').querySelectorAll<HTMLElement>('dd')];

  const show = (g: Generation) => {
    const cx = x(g.generation).toFixed(1);
    cursor.setAttribute('x1', cx);
    cursor.setAttribute('x2', cx);
    for (const [key, dot] of Object.entries(dots)) {
      dot.setAttribute('cx', cx);
      dot.setAttribute('cy', y(g[key as keyof Generation]).toFixed(1));
    }
    for (const dd of readout) {
      const key = dd.dataset['key'] as keyof Generation;
      setText(dd, key === 'generation' ? String(g.generation) : numberFormat.format(g[key]));
    }
  };
  const at = (e: PointerEvent) => {
    const rect = svg.getBoundingClientRect();
    const vx = (e.clientX - rect.left) / rect.width * width;
    const gen = Math.round((vx - left) / (width - left - right) * (last.generation - 1)) + 1;
    return log[Math.min(log.length, Math.max(1, gen)) - 1]!;
  };
  svg.addEventListener('pointermove', e => show(at(e)));
  svg.addEventListener('pointerdown', e => show(at(e)));
  // A mouse that leaves goes back to the record; a finger's last pick stays.
  svg.addEventListener('pointerleave', e => {
    if (e.pointerType === 'mouse') show(record);
  });
  show(record);
}
