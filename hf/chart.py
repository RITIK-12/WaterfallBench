"""Draw the leaderboard image for the Hugging Face card from site/data.json.

Bars: tasks fully resolved (primary), with a ±1 SE whisker. Dots: field accuracy (non-trivial fields).
Usage: python hf/chart.py OUT.png
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

REPO = Path(__file__).resolve().parents[1]
INK, MUTED, GRID, SURFACE = "#1c1c19", "#6d6b63", "#e3e0d6", "#ffffff"
BAR, DOT = "#2f7d3c", "#d97757"   # validated pair (dataviz validate_palette.js, light mode)


def main(out: str) -> None:
    d = json.loads((REPO / "site" / "data.json").read_text())
    ms = sorted(d["models"], key=lambda m: (m["fully_resolved"], m["nontrivial"], -m["cost"]))
    plt.rcParams.update({"font.family": "DejaVu Sans", "font.size": 11})
    fig, ax = plt.subplots(figsize=(10, 0.62 * len(ms) + 1.5), dpi=200)
    fig.patch.set_facecolor(SURFACE)
    ax.set_facecolor(SURFACE)
    y = range(len(ms))
    ax.barh(y, [m["fully_resolved"] for m in ms], height=0.5, color=BAR, zorder=2, label="Tasks fully resolved (±1 SE)")
    for i, m in enumerate(ms):
        lo, hi = max(0, m["fully_resolved"] - m["se"]), min(100, m["fully_resolved"] + m["se"])
        ax.plot([lo, hi], [i, i], color=INK, lw=1.2, alpha=.55, zorder=3, solid_capstyle="butt")
        ax.text(1.5, i, f"{m['fully_resolved']:.0f}%", va="center", ha="left", color=SURFACE,
                fontsize=10, fontweight="bold", zorder=5)
        ax.text(103, i, f"${m['cost']:.2f} / task", va="center", ha="left", color=MUTED, fontsize=10)
    ax.scatter([m["nontrivial"] for m in ms], list(y), s=70, color=DOT, edgecolor=SURFACE, linewidth=2, zorder=4,
               label="Field accuracy (non-trivial fields)")
    ax.set_yticks(list(y), [m["name"] for m in ms], color=INK)
    ax.set_xlim(0, 100)
    ax.set_xticks(range(0, 101, 20), [f"{v}%" for v in range(0, 101, 20)], color=MUTED)
    ax.grid(axis="x", color=GRID, lw=1, zorder=0)
    ax.tick_params(length=0)
    for s in ax.spines.values():
        s.set_visible(False)
    ax.set_title("WaterfallBench v1.0 · 20 first-distribution tasks · one call, reasoning effort high",
                 loc="left", color=INK, fontsize=12, pad=30)
    h, lab = ax.get_legend_handles_labels()
    order = [lab.index(x) for x in sorted(lab, key=lambda t: not t.startswith("Tasks"))]
    ax.legend([h[i] for i in order], [lab[i] for i in order], loc="lower left", bbox_to_anchor=(0, 1.0), ncol=2,
              frameon=False, fontsize=10, labelcolor=INK, handlelength=1.2, borderaxespad=0.2)
    fig.subplots_adjust(left=0.2, right=0.86, top=0.84, bottom=0.08)
    fig.savefig(out, facecolor=SURFACE)
    print(f"wrote {out}")


if __name__ == "__main__":
    main(sys.argv[1])
