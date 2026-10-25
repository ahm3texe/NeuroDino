// Hovering a neuron in the visualizer explains it: an input's value and what
// it measures, a hidden neuron's activation, strongest input and the action it
// pushes, an output's probability and its strongest supporter. Rebuilt every
// frame, so it follows the live values.

import type {Brain} from './brain.js';
import {ACTIONS} from './panels.js';

const INPUTS = [
  {name: 'Obj1 Dist', about: 'How close the next obstacle is (1 = about to hit)'},
  {name: 'Obj1 Act', about: '1 if the next obstacle is the highest bird, which flies over a running dino'},
  {name: 'Obj1 W', about: 'Width of the next obstacle'},
  {name: 'Obj2 Dist', about: 'How close the obstacle after it is'},
  {name: 'Obj2 Act', about: '1 if that one is the highest bird'},
  {name: 'Obj2 W', about: 'Width of the obstacle after it'},
  {name: 'Speed', about: 'Game speed (1 = top speed)'},
  {name: 'Gap', about: 'How close the two obstacles are to each other'},
  {name: 'DinoY', about: 'Height of the dino in a jump'},
  {name: 'DinoVel', about: 'Vertical velocity in a jump'},
  {name: 'Air', about: '1 while the dino is in the air'},
  {name: 'Duck', about: '1 while the dino is ducking'},
];

interface NodePosition {
  x: number;
  y: number;
  r: number;
  layer: 'input'|'hidden'|'output';
  index: number;
}

const signed = (v: number) => `${v >= 0 ? '+' : '-'}${Math.abs(v).toFixed(2)}`;

export class NeuronTooltip {
  private readonly tip: HTMLElement;
  private hovered: NodePosition|null = null;
  private pointer = {x: 0, y: 0};

  constructor(
      private readonly brain: Brain, private readonly canvas: HTMLCanvasElement,
      private readonly container: HTMLElement) {
    this.tip = document.createElement('div');
    this.tip.className = 'net-tip';
    this.tip.hidden = true;
    container.appendChild(this.tip);

    canvas.addEventListener('pointermove', e => {
      if (e.pointerType !== 'mouse') return;
      const rect = canvas.getBoundingClientRect();
      this.pointer = {x: e.clientX - rect.left, y: e.clientY - rect.top};
      this.hovered = window.isDragging ? null : this.hit(this.pointer.x, this.pointer.y);
    });
    canvas.addEventListener('pointerleave', () => {
      this.hovered = null;
    });
  }

  /** The visualizer's own hit test: node positions are in world coordinates. */
  private hit(x: number, y: number): NodePosition|null {
    const worldX = (x - window.panX) / window.vizScale;
    const worldY = (y - window.panY) / window.vizScale;
    const nodes = (window as unknown as {nodePositions: NodePosition[]}).nodePositions ?? [];
    return nodes.find(n => (worldX - n.x) ** 2 + (worldY - n.y) ** 2 < n.r * n.r) ?? null;
  }

  update() {
    const node = this.hovered;
    this.tip.hidden = !node;
    if (!node) return;

    const lines = this.describe(node);
    const html = lines.map(line => `<div>${line}</div>`).join('');
    if (this.tip.innerHTML !== html) this.tip.innerHTML = html;

    // Next to the pointer, kept inside the network card.
    const offsetX = this.canvas.offsetLeft;
    const offsetY = this.canvas.offsetTop;
    const width = this.tip.offsetWidth;
    const height = this.tip.offsetHeight;
    const maxX = this.container.clientWidth - width - 4;
    const maxY = this.container.clientHeight - height - 4;
    let left = this.pointer.x + offsetX + 16;
    if (left > maxX) left = this.pointer.x + offsetX - 16 - width;
    const top = Math.min(maxY, this.pointer.y + offsetY + 16);
    this.tip.style.left = `${Math.max(4, left)}px`;
    this.tip.style.top = `${Math.max(4, top)}px`;
  }

  private describe(node: NodePosition): string[] {
    const brain = this.brain;
    if (node.layer === 'input') {
      const input = INPUTS[node.index]!;
      return [`${input.name} = ${brain.lastInputs[node.index]!.toFixed(2)}`, input.about];
    }
    if (node.layer === 'hidden') {
      const j = node.index;
      const a = brain.lastHidden[j]!;
      const weights = brain.weightsIH[j]!;
      // The input that moves this neuron most right now; if all are zero, the
      // one it weighs most.
      const score = (i: number) => Math.abs(weights[i]! * brain.lastInputs[i]!);
      let best = 0;
      for (let i = 1; i < weights.length; i++) if (score(i) > score(best)) best = i;
      if (score(best) === 0) {
        for (let i = 1; i < weights.length; i++) {
          if (Math.abs(weights[i]!) > Math.abs(weights[best]!)) best = i;
        }
      }
      const pushes = brain.weightsHO.map(row => row[j]! * a);
      const up = pushes.indexOf(Math.max(...pushes));
      const down = pushes.indexOf(Math.min(...pushes));
      const effect = [
        pushes[up]! > 0.01 ? `${ACTIONS[up]!.name} ↑` : '',
        pushes[down]! < -0.01 ? `${ACTIONS[down]!.name} ↓` : '',
      ].filter(Boolean).join('  ');
      return [
        `Neuron #${j + 1}   a = ${signed(a)}`,
        `Strongest input: ${INPUTS[best]!.name} (w ${signed(weights[best]!)})`,
        effect ? `Pushes: ${effect}` : 'Pushes: nothing right now',
      ];
    }
    const k = node.index;
    const contributions = brain.lastHidden.map((h, j) => h * brain.weightsHO[k]![j]!);
    const top = contributions.indexOf(Math.max(...contributions));
    return [
      `${ACTIONS[k]!.name} ${Math.round(brain.lastOutputs[k]! * 100)}%`,
      `Most support: neuron #${top + 1} (${signed(contributions[top]!)})`,
    ];
  }
}
