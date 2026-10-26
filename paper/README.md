# Paper

The paper: how the network was trained, how the run went and what the
trained model does on 200 fresh games, with an input ablation; then how v2
and v3 fixed what that showed. It was written in Turkish (`neurodino.tex`,
`neurodino.pdf`); `neurodino-en.tex` and `neurodino-en.pdf` are its English
translation, sentence for sentence, with the same tables and numbers. Both
compile with pdfLaTeX, XeLaTeX or Tectonic (`tectonic paper/neurodino-en.tex`);
the figures are in `figures/`, the English copies ending in `-en`.

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

`--en` draws the English copies (`training-en.pdf`, `weights-en.pdf`,
`evaluation-en.pdf`).

They need `numpy` and `matplotlib`. `figures/website.png` is a screenshot of
the live site.
