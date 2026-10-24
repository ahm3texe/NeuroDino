// Port of neurodino/brain.py inference: input -> hidden (tanh) -> output (softmax).
// Weights come from export_best_brain.py (best_brain.pkl -> JSON).

import {exp, tanh} from './determinism.js';

export interface SerializedBrain {
  input_nodes: number;
  hidden_nodes: number;
  output_nodes: number;
  weights_ih: number[][];
  weights_ho: number[][];
  bias_h: number[];
  bias_o: number[];
  training_score: number|null;
}

export class Brain {
  lastInputs: number[];
  lastHidden: number[];
  lastOutputs: number[];

  private constructor(
      readonly inputNodes: number, readonly hiddenNodes: number,
      readonly outputNodes: number, readonly weightsIH: number[][],
      readonly weightsHO: number[][], readonly biasH: number[],
      readonly biasO: number[], readonly trainingScore: number|null) {
    this.lastInputs = new Array(inputNodes).fill(0);
    this.lastHidden = new Array(hiddenNodes).fill(0);
    this.lastOutputs = new Array(outputNodes).fill(0);
  }

  static fromJSON(data: SerializedBrain): Brain {
    return new Brain(
        data.input_nodes, data.hidden_nodes, data.output_nodes, data.weights_ih,
        data.weights_ho, data.bias_h.flat(), data.bias_o.flat(),
        data.training_score);
  }

  predict(inputs: number[]): number[] {
    this.lastInputs = inputs;

    this.lastHidden = this.weightsIH.map((row, j) => {
      let total = 0;
      for (let i = 0; i < row.length; i++) total += row[i]! * inputs[i]!;
      return tanh(total + this.biasH[j]!);
    });

    const logits = this.weightsHO.map((row, k) => {
      let total = 0;
      for (let j = 0; j < row.length; j++) total += row[j]! * this.lastHidden[j]!;
      return total + this.biasO[k]!;
    });

    const max = Math.max(...logits);
    const exps = logits.map(v => exp(v - max));
    const sum = exps.reduce((acc, v) => acc + v, 0);
    this.lastOutputs = exps.map(v => v / sum);
    return this.lastOutputs;
  }
}

/** np.argmax: index of the first maximum. */
export function argmax(values: number[]): number {
  let best = 0;
  for (let i = 1; i < values.length; i++) {
    if (values[i]! > values[best]!) best = i;
  }
  return best;
}
