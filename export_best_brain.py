#!/usr/bin/env python3
import argparse
import json
import pickle
import sys
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from neurodino.brain import Brain  # noqa: E402


def _matrix_rows(values: Any) -> list[list[float]]:
    return [[float(item) for item in row] for row in values.tolist()]


def _vector(values: Any) -> list[float]:
    return [float(item) for item in values.reshape(-1).tolist()]


def _load_brain(path: Path) -> tuple[Brain, int | None]:
    with path.open("rb") as fh:
        loaded = pickle.load(fh)

    if isinstance(loaded, tuple):
        if not loaded:
            raise ValueError("Pickle tuple is empty.")
        brain = loaded[0]
        score = int(loaded[1]) if len(loaded) > 1 and loaded[1] is not None else None
    else:
        brain = loaded
        score = None

    if not isinstance(brain, Brain):
        raise TypeError(f"Expected Brain or (Brain, score), got {type(brain)!r}")

    return brain, score


def export_brain(input_path: Path, output_path: Path) -> dict[str, Any]:
    brain, score = _load_brain(input_path)

    payload = {
        "input_nodes": int(brain.input_nodes),
        "hidden_nodes": int(brain.hidden_nodes),
        "output_nodes": int(brain.output_nodes),
        "weights_ih": _matrix_rows(brain.weights_ih),
        "weights_ho": _matrix_rows(brain.weights_ho),
        "bias_h": _vector(brain.bias_h),
        "bias_o": _vector(brain.bias_o),
        "training_score": score,
    }

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    return payload


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Export best_brain.pkl into the WebDino JSON runtime format."
    )
    parser.add_argument(
        "--input",
        default=str(ROOT / "best_brain.pkl"),
        help="Path to the source pickle file.",
    )
    parser.add_argument(
        "--output",
        default=str(ROOT / "web" / "src" / "assets" / "best-brain.json"),
        help="Path to the output JSON file.",
    )
    args = parser.parse_args()

    input_path = Path(args.input).resolve()
    output_path = Path(args.output).resolve()

    payload = export_brain(input_path, output_path)
    print(
        f"Exported {input_path.name} -> {output_path} "
        f"({payload['input_nodes']}->{payload['hidden_nodes']}->{payload['output_nodes']})"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
