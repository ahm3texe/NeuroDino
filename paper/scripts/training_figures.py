# Draws the paper's training figures from training_log.csv and the saved
# record-setting models. Run from the repository root; --en draws the English
# paper's copies (training-en.pdf, weights-en.pdf):
#   python paper/scripts/training_figures.py [--en]
import csv
import pickle
import sys
from pathlib import Path

import matplotlib
import matplotlib.ticker

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
OUT = ROOT / "paper" / "figures"
EN = "--en" in sys.argv
SUFFIX = "-en" if EN else ""


def t(turkish, english):
    return english if EN else turkish


def number(v, digits=0):
    """v in the paper's language: 1.247 and 0,05 in Turkish, 1,247 and 0.05 in English."""
    text = f"{v:,.{digits}f}"
    return text if EN else text.replace(",", "_").replace(".", ",").replace("_", ".")

BLUE, ORANGE, AQUA = "#2a78d6", "#eb6834", "#1baf7a"
INK, MUTED, GRID = "#0b0b0b", "#52514e", "#e4e3df"

plt.rcParams.update({
    "font.size": 8.5,
    "axes.edgecolor": MUTED,
    "axes.labelcolor": INK,
    "axes.spines.top": False,
    "axes.spines.right": False,
    "axes.grid": True,
    "grid.color": GRID,
    "grid.linewidth": 0.6,
    "xtick.color": MUTED,
    "ytick.color": MUTED,
    "legend.frameon": False,
    "lines.linewidth": 1.4,
    "pdf.fonttype": 42,
})


def decimal_ticks(ax, axis="y", digits=2):
    """Decimals on an axis's tick labels in the paper's language."""
    fmt = matplotlib.ticker.FuncFormatter(lambda v, _: number(v, digits))
    (ax.yaxis if axis == "y" else ax.xaxis).set_major_formatter(fmt)


rows = list(csv.DictReader((ROOT / "training_log.csv").open()))
gen = np.array([int(r["Generation"]) for r in rows])
best = np.array([int(r["Max_Score"]) for r in rows])
avg = np.array([int(r["Avg_Score"]) for r in rows])
record = np.array([int(r["Global_Best"]) for r in rows])

# The rate that bred generation g+1, computed after generation g as in
# Genetics.evolve_population; TensorBoard logged it with a 0.02 floor instead.
raw = 0.20 * 0.995 ** gen / (1 + record / 2000)
used = np.clip(raw, 0.05, 0.25)
logged = np.clip(raw, 0.02, 0.25)

fig, (top, bottom) = plt.subplots(2, 1, figsize=(6.3, 4.6), sharex=True,
                                  gridspec_kw={"height_ratios": [1.6, 1], "hspace": 0.12})
top.step(gen, record, where="post", color=INK, linestyle=(0, (4, 2)), linewidth=1.1, label=t("Rekor", "Record"))
top.plot(gen, best, color=BLUE, label=t("Neslin en iyisi", "Best of generation"))
top.plot(gen, avg, color=ORANGE, label=t("Neslin ortalaması", "Generation mean"))
top.set_yscale("log")
top.set_ylim(10, 2e6)
top.set_ylabel(t("Skor (log)", "Score (log)"))
top.legend(loc="upper left", ncol=3)
for g, text in ((42, t("42. nesil", "Generation 42") + f"\n{number(1247)} → {number(12643)}"),
                (77, t("77. nesil", "Generation 77") + f"\n{number(547287)}")):
    top.annotate(text, (g, best[g - 1]), xytext=(-6, 10), textcoords="offset points",
                 ha="right", va="bottom", color=INK, fontsize=7.5,
                 arrowprops={"arrowstyle": "-", "color": MUTED, "linewidth": 0.6})

bottom.step(gen, used, where="post", color=BLUE,
            label=t("Kullanılan oran (sınırlar: ", "Rate used (bounds: ") + f"{number(0.05, 2)}–{number(0.25, 2)})")
bottom.step(gen, logged, where="post", color=MUTED, linestyle=(0, (1, 1.5)), linewidth=1.1,
            label=t("TensorBoard'a yazılan (alt sınır ", "Logged to TensorBoard (floor ") + f"{number(0.02, 2)})")
bottom.axvline(41.5, color=MUTED, linewidth=0.6, linestyle=(0, (3, 2)))
bottom.annotate(t("41. nesilden sonra: ", "After generation 41: ") + number(0.1003, 4), (41.5, used[40]), xytext=(6, 4), textcoords="offset points",
                fontsize=7.5, color=INK)
bottom.set_ylim(0, 0.21)
bottom.set_ylabel(t("Mutasyon oranı", "Mutation rate"))
bottom.set_xlabel(t("Nesil (oran, o neslin ardından bir sonraki nesli üretmek için hesaplanır)",
                    "Generation (the rate is computed after a generation, to breed the next one)"))
bottom.set_xlim(1, 83)
bottom.set_xticks([1, 10, 20, 30, 42, 50, 60, 70, 77, 83])
decimal_ticks(bottom)
bottom.legend(loc="upper right")
fig.savefig(OUT / f"training{SUFFIX}.pdf", bbox_inches="tight")


def weights(score):
    loaded = pickle.load((ROOT / "backups" / f"brain_score_{score}.pkl").open("rb"))
    brain = loaded[0] if isinstance(loaded, tuple) else loaded
    return brain.weights_ih.ravel(), brain.weights_ho.ravel()


models = [(1, 102, BLUE), (42, 12643, ORANGE), (77, 547287, AQUA)]
fig, axes = plt.subplots(1, 2, figsize=(6.3, 2.4), gridspec_kw={"wspace": 0.28})
for title, ax, k in ((t("Giriş → gizli (576 ağırlık)", "Input → hidden (576 weights)"), axes[0], 0),
                     (t("Gizli → çıkış (144 ağırlık)", "Hidden → output (144 weights)"), axes[1], 1)):
    bins = np.linspace(-1.6, 1.6, 33)
    for g, score, color in models:
        w = weights(score)[k]
        ax.hist(w, bins=bins, histtype="step", color=color, linewidth=1.4, label=t(f"{g}. nesil", f"Generation {g}"))
    ax.set_title(title, fontsize=8.5, color=INK, loc="left")
    ax.set_xlabel(t("Ağırlık", "Weight"))
    decimal_ticks(ax, "x", 1)
axes[0].set_ylabel(t("Sayı", "Count"))
fig.legend(*axes[0].get_legend_handles_labels(), loc="lower center", ncol=3,
           bbox_to_anchor=(0.5, 0.98))
fig.savefig(OUT / f"weights{SUFFIX}.pdf", bbox_inches="tight")

for g, score, _ in models:
    ih, ho = weights(score)
    print(f"gen {g}: W_ih range [{ih.min():.3f}, {ih.max():.3f}] std {ih.std():.3f}; "
          f"W_ho range [{ho.min():.3f}, {ho.max():.3f}] std {ho.std():.3f}")
