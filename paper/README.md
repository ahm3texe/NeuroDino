# Paper

`neurodino.tex` is the paper (in Turkish): how the network was trained, how
the run went and what the trained model does on 200 fresh games, with an
input ablation; then how v2 and v3 fixed what that showed. `neurodino.pdf` is
the compiled paper. It compiles with pdfLaTeX, XeLaTeX or Tectonic
(`tectonic paper/neurodino.tex`); the figures are in `figures/`.

## Reproducing the numbers

Every number in the paper comes from the repository: the first run's
`training_log.csv`, TensorBoard logs in `runs/` and record-setting models in
`backups/`; the second run's logs in `runs/v2/`; v3's pipeline in
`training/`; and every evaluation game in `evaluation/data/`, written by
`evaluation/evaluate.ts`. See
[`evaluation/README.md`](../evaluation/README.md) for how to play them again
and how the engine was checked against Python.

## Figures

```bash
python paper/scripts/training_figures.py
python paper/scripts/evaluation_figure.py
```

They need `numpy` and `matplotlib`. `figures/website.png` is a screenshot of
the live site.
