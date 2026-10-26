# Draws the paper's evaluation figure from the games in evaluation/data. Run
# from the repository root; --en draws the English paper's copy
# (evaluation-en.pdf):
#   python paper/scripts/evaluation_figure.py [--en]
import json
import sys
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.ticker
import numpy as np

ROOT = Path(__file__).resolve().parents[2]
DATA = ROOT / "evaluation" / "data"

BLUE, ORANGE, AQUA = "#2a78d6", "#eb6834", "#1baf7a"
INK, MUTED, GRID = "#0b0b0b", "#52514e", "#e4e3df"
TOP_SPEED_SCORE = 1662  # speed reaches 13 at frame 7000
EN = "--en" in sys.argv


def t(turkish, english):
    return english if EN else turkish


def number(v, digits=0):
    """v in the paper's language: 1.662 and 99,0 in Turkish, 1,662 and 99.0 in English."""
    text = f"{v:,.{digits}f}"
    return text if EN else text.replace(",", "_").replace(".", ",").replace("_", ".")

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


def survival(name):
    games = [json.loads(line) for line in (DATA / name).open()]
    end = max(g["score"] for g in games)
    deaths = sorted(g["score"] for g in games if g["died"])
    x = [100] + [s for s in deaths] + [end]
    y = [100] + [100 * (len(games) - k - 1) / len(games) for k in range(len(deaths))]
    y.append(y[-1])
    return np.array(x), np.array(y), end


fig, ax = plt.subplots(figsize=(6.3, 3.3))
# Where each end value goes: beside its dot, above it or below it, clear of
# the other labels and lines.
LEFT, ABOVE, BELOW = ((-7, 0), "right", "center"), ((0, 6), "center", "bottom"), ((0, -6), "center", "top")
for name, color, style, label, place in (
        ("v1-training-loop.jsonl", BLUE, "-", t("v1, eğitim koşulları: eğitimdeki döngü, normal boşluklar (4 saat)",
                                                "v1, training conditions: training loop, normal gaps (4 h)"), LEFT),
        ("v1-website-loop.jsonl", ORANGE, "-", t("v1, web sitesi koşulları: izleme döngüsü, normal boşluklar (4 saat)",
                                                 "v1, website conditions: watch loop, normal gaps (4 h)"), ABOVE),
        ("v1-website-loop-doubled-gaps.jsonl", AQUA, "-",
         t("v1, demo koşulları: izleme döngüsü, iki kat boşluklar (30 dakika)",
           "v1, demo conditions: watch loop, doubled gaps (30 min)"), ABOVE),
        ("v2-test.jsonl", MUTED, (0, (4, 2)), t("v2, web sitesi koşulları (4 saat)", "v2, website conditions (4 h)"), BELOW),
        ("v3-test.jsonl", INK, "-", t("v3, web sitesi koşulları (4 saat)", "v3, website conditions (4 h)"), ABOVE)):
    x, y, end = survival(name)
    ax.step(x, y, where="post", color=color, linestyle=style, label=label)
    ax.plot([end], [y[-1]], marker="o", markersize=4, color=color)
    offset, ha, va = place
    ax.annotate(f"{number(y[-1], 1)}%" if EN else f"%{number(y[-1], 1)}", (end, y[-1]), xytext=offset,
                textcoords="offset points", ha=ha, va=va, fontsize=7.5, color=INK)
ax.axvline(TOP_SPEED_SCORE, color=MUTED, linewidth=0.6, linestyle=(0, (3, 2)))
ax.annotate(t("Maksimum hız", "Top speed") + f"\n({number(TOP_SPEED_SCORE)} " + t("puan)", "points)"),
            (TOP_SPEED_SCORE, 92), xytext=(5, 0),
            textcoords="offset points", fontsize=7.5, color=INK, va="top")
ax.set_xscale("log")
ax.set_xlim(100, 4e5)
ax.set_ylim(0, 104)
ax.xaxis.set_major_formatter(matplotlib.ticker.FuncFormatter(lambda v, _: number(v)))
ax.set_xlabel(t("Skor (log)", "Score (log)"))
ax.set_ylabel(t("Süren oyunlar (%)", "Games still running (%)"))
ax.legend(loc="lower left")
fig.savefig(ROOT / "paper" / "figures" / ("evaluation-en.pdf" if EN else "evaluation.pdf"), bbox_inches="tight")
