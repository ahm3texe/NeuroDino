# Draws the paper's training figures from training_log.csv and the saved
# record-setting models. Run from the repository root:
#   python paper/scripts/training_figures.py
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


def decimal_comma(ax, axis="y", digits=2):
    """Turkish decimal commas on an axis's tick labels."""
    fmt = matplotlib.ticker.FuncFormatter(lambda v, _: f"{v:.{digits}f}".replace(".", ","))
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
top.step(gen, record, where="post", color=INK, linestyle=(0, (4, 2)), linewidth=1.1, label="Rekor")
top.plot(gen, best, color=BLUE, label="Neslin en iyisi")
top.plot(gen, avg, color=ORANGE, label="Neslin ortalaması")
top.set_yscale("log")
top.set_ylim(10, 2e6)
top.set_ylabel("Skor (log)")
top.legend(loc="upper left", ncol=3)
for g, text in ((42, "42. nesil\n1.247 → 12.643"), (77, "77. nesil\n547.287")):
    top.annotate(text, (g, best[g - 1]), xytext=(-6, 10), textcoords="offset points",
                 ha="right", va="bottom", color=INK, fontsize=7.5,
                 arrowprops={"arrowstyle": "-", "color": MUTED, "linewidth": 0.6})

bottom.step(gen, used, where="post", color=BLUE, label="Kullanılan oran (sınırlar: 0,05–0,25)")
bottom.step(gen, logged, where="post", color=MUTED, linestyle=(0, (1, 1.5)), linewidth=1.1,
            label="TensorBoard'a yazılan (alt sınır 0,02)")
bottom.axvline(41.5, color=MUTED, linewidth=0.6, linestyle=(0, (3, 2)))
bottom.annotate("41. nesilden sonra: 0,1003", (41.5, used[40]), xytext=(6, 4), textcoords="offset points",
                fontsize=7.5, color=INK)
bottom.set_ylim(0, 0.21)
bottom.set_ylabel("Mutasyon oranı")
bottom.set_xlabel("Nesil (oran, o neslin ardından bir sonraki nesli üretmek için hesaplanır)")
bottom.set_xlim(1, 83)
bottom.set_xticks([1, 10, 20, 30, 42, 50, 60, 70, 77, 83])
decimal_comma(bottom)
bottom.legend(loc="upper right")
fig.savefig(OUT / "training.pdf", bbox_inches="tight")


def weights(score):
    loaded = pickle.load((ROOT / "backups" / f"brain_score_{score}.pkl").open("rb"))
    brain = loaded[0] if isinstance(loaded, tuple) else loaded
    return brain.weights_ih.ravel(), brain.weights_ho.ravel()


models = [(1, 102, BLUE), (42, 12643, ORANGE), (77, 547287, AQUA)]
fig, axes = plt.subplots(1, 2, figsize=(6.3, 2.4), gridspec_kw={"wspace": 0.28})
for title, ax, k in (("Giriş → gizli (576 ağırlık)", axes[0], 0), ("Gizli → çıkış (144 ağırlık)", axes[1], 1)):
    bins = np.linspace(-1.6, 1.6, 33)
    for g, score, color in models:
        w = weights(score)[k]
        ax.hist(w, bins=bins, histtype="step", color=color, linewidth=1.4, label=f"{g}. nesil")
    ax.set_title(title, fontsize=8.5, color=INK, loc="left")
    ax.set_xlabel("Ağırlık")
    decimal_comma(ax, "x", 1)
axes[0].set_ylabel("Sayı")
fig.legend(*axes[0].get_legend_handles_labels(), loc="lower center", ncol=3,
           bbox_to_anchor=(0.5, 0.98))
fig.savefig(OUT / "weights.pdf", bbox_inches="tight")

for g, score, _ in models:
    ih, ho = weights(score)
    print(f"gen {g}: W_ih range [{ih.min():.3f}, {ih.max():.3f}] std {ih.std():.3f}; "
          f"W_ho range [{ho.min():.3f}, {ho.max():.3f}] std {ho.std():.3f}")
