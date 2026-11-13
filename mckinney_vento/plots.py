"""Matplotlib chart helpers with a consistent, accessible house style.

Palette: validated categorical slots 1-3 (blue, orange, aqua) for the three districts,
fixed per district so colors never shift between charts; NC statewide is neutral gray.
"""

from __future__ import annotations

from pathlib import Path

import matplotlib.pyplot as plt
import matplotlib.ticker as mticker
import pandas as pd

from .config import COVID_YEARS, DISTRICTS, FIGURES_DIR

SURFACE = "#fcfcfb"
TEXT = "#0b0b0b"
TEXT_2 = "#52514e"
GRID = "#e4e3df"
STATE_GRAY = "#8a8984"
COVID_FILL = "#f1f0ec"

# Color follows the entity, never its rank.
DISTRICT_COLORS = dict(zip([v["short"] for v in DISTRICTS.values()],
                           ["#2a78d6", "#eb6834", "#1baf7a"]))
MARKERS = dict(zip(DISTRICT_COLORS, ["o", "s", "D"]))   # secondary encoding, not color-alone
RESIDENCE_COLORS = {                                     # slots 1-4, adjacent-validated order
    "Doubled-up": "#2a78d6",
    "Hotels / motels": "#eb6834",
    "Shelters / transitional housing": "#1baf7a",
    "Unsheltered": "#eda100",
}

SOURCE_NOTE = ("Source: U.S. Dept. of Education, ED Data Express (EDFacts FS 118); "
               "enrollment: NCES CCD via Urban Institute.")


def use_style() -> None:
    plt.rcParams.update({
        "figure.facecolor": SURFACE, "axes.facecolor": SURFACE, "savefig.facecolor": SURFACE,
        "figure.dpi": 110, "savefig.dpi": 200, "savefig.bbox": "tight",
        "font.size": 10, "axes.titlesize": 13, "axes.titleweight": "bold", "axes.titlelocation": "left",
        "axes.edgecolor": GRID, "axes.labelcolor": TEXT_2, "text.color": TEXT,
        "xtick.color": TEXT_2, "ytick.color": TEXT_2,
        "axes.spines.top": False, "axes.spines.right": False, "axes.spines.left": False,
        "axes.grid": True, "axes.grid.axis": "y", "grid.color": GRID, "grid.linewidth": 0.8,
        "axes.axisbelow": True, "lines.linewidth": 2, "lines.markersize": 5.5,
        "legend.frameon": False,
    })


def _short_year(sy: str) -> str:
    return f"{sy[2:4]}–{sy[7:9]}"   # "2022-2023" -> "22–23"


def _shade_covid(ax, years: list[str]) -> None:
    idx = [i for i, y in enumerate(years) if y in COVID_YEARS]
    if idx:
        ax.axvspan(min(idx) - 0.5, max(idx) + 0.5, color=COVID_FILL, zorder=0, lw=0)
        ax.text((min(idx) + max(idx)) / 2, 1.0, "COVID-affected", transform=ax.get_xaxis_transform(),
                ha="center", va="bottom", fontsize=8, color=TEXT_2)


def _finish(fig, ax, years, title, subtitle, ylabel, save_as):
    ax.set_xticks(range(len(years)), [_short_year(y) for y in years])
    ax.set_xlim(-0.5, len(years) - 0.5)
    ax.set_ylim(bottom=0)
    ax.set_ylabel(ylabel)
    ax.set_xlabel("School year")
    ax.yaxis.set_major_formatter(mticker.FuncFormatter(lambda v, _: f"{v:,.0f}"))
    ax.set_title(title, pad=34)
    ax.text(0, 1.075, subtitle, transform=ax.transAxes, fontsize=9.5, color=TEXT_2)
    ax.legend(loc="upper left", bbox_to_anchor=(1.0, 1.0))
    fig.text(0, -0.02, SOURCE_NOTE, fontsize=7.5, color=TEXT_2)
    if save_as:
        FIGURES_DIR.mkdir(parents=True, exist_ok=True)
        path = Path(FIGURES_DIR) / save_as
        fig.savefig(path)
        print(f"saved {path}")
    return fig, ax


def district_lines(panel: pd.DataFrame, value: str, *, title: str, subtitle: str, ylabel: str,
                   state: pd.DataFrame | None = None, save_as: str | None = None,
                   label_fmt: str = "{:,.0f}"):
    """One line per district over time; optional NC statewide reference line."""
    use_style()
    years = sorted(panel["school_year"].unique())
    pos = {y: i for i, y in enumerate(years)}
    fig, ax = plt.subplots(figsize=(9, 4.8))
    _shade_covid(ax, years)

    if state is not None and value in state:
        s = state[state["school_year"].isin(years)].sort_values("school_year")
        ax.plot(s["school_year"].map(pos), s[value], color=STATE_GRAY, ls="--", lw=1.5,
                label="North Carolina (statewide)", zorder=2)

    for name, g in panel.groupby("district", observed=True):
        g = g.sort_values("school_year")
        x, y = g["school_year"].map(pos), g[value]
        ax.plot(x, y, color=DISTRICT_COLORS[name], marker=MARKERS[name], label=name, zorder=3,
                markeredgecolor=SURFACE, markeredgewidth=1.2)
        last = g.dropna(subset=[value]).iloc[-1:]   # direct label at the last point only
        for _, r in last.iterrows():
            ax.annotate(label_fmt.format(r[value]), (pos[r["school_year"]], r[value]),
                        xytext=(6, 0), textcoords="offset points", va="center", fontsize=8.5, color=TEXT)
    return _finish(fig, ax, years, title, subtitle, ylabel, save_as)


def line_panel(ax, panel: pd.DataFrame, value: str, years: list[str], *, title: str,
               state: pd.DataFrame | None = None, label_fmt: str = "{:,.0f}", ylabel: str = "",
               legend: bool = False) -> None:
    """Draw one small-multiple panel (no legend by default; the report has a shared one)."""
    pos = {y: i for i, y in enumerate(years)}
    _shade_covid(ax, years)
    ends = []   # (value, label text, color) for de-collided end labels
    if state is not None and value in state:
        s = state[state["school_year"].isin(years)].sort_values("school_year")
        ax.plot(s["school_year"].map(pos), s[value], color=STATE_GRAY, ls="--", lw=1.5,
                label="North Carolina (statewide)", zorder=2)
        last = s.dropna(subset=[value]).iloc[-1]
        ends.append((last[value], f"NC {label_fmt.format(last[value])}", TEXT_2))
    for name, g in panel.groupby("district", observed=True):
        g = g.sort_values("school_year")
        ax.plot(g["school_year"].map(pos), g[value], color=DISTRICT_COLORS[name], marker=MARKERS[name],
                label=name, zorder=3, markeredgecolor=SURFACE, markeredgewidth=1.0, markersize=4.5)
        last = g.dropna(subset=[value]).iloc[-1]
        ends.append((last[value], label_fmt.format(last[value]), TEXT))
    # Direct end labels, nudged apart so they don't collide.
    ends.sort(key=lambda e: e[0])
    lo, hi = ax.get_ylim()
    min_gap = (max(hi, max(e[0] for e in ends)) - min(0, lo)) * 0.065
    placed = []
    for v, text, color in ends:
        y = v if not placed else max(v, placed[-1] + min_gap)
        placed.append(y)
        ax.text(len(years) - 1 + 0.25, y, text, va="center", fontsize=8.5, color=color)
    ax.set_xticks(range(len(years)), [_short_year(y) for y in years], fontsize=8)
    ax.set_xlim(-0.5, len(years) + 0.9)
    ax.set_ylim(bottom=0)
    ax.yaxis.set_major_formatter(mticker.FuncFormatter(lambda v, _: f"{v:,.0f}"))
    ax.set_ylabel(ylabel, fontsize=8.5)
    ax.set_title(title, fontsize=11.5, pad=14)
    if legend:
        ax.legend(loc="upper left", fontsize=8)


def residence_stacked(res: pd.DataFrame, *, save_as: str | None = None):
    """Statewide homeless students by primary nighttime residence (stacked bars)."""
    use_style()
    wide = (res.groupby(["school_year", "residence"])["students"].sum(min_count=1)
               .unstack().reindex(columns=list(RESIDENCE_COLORS)).fillna(0).sort_index())
    years = list(wide.index)
    fig, ax = plt.subplots(figsize=(9, 4.8))
    _shade_covid(ax, years)
    bottom = pd.Series(0.0, index=wide.index)
    for col, color in RESIDENCE_COLORS.items():
        ax.bar(range(len(years)), wide[col], bottom=bottom, color=color, width=0.62, label=col,
               edgecolor=SURFACE, linewidth=1.5)   # surface gap between stacked segments
        bottom += wide[col]
    for i, tot in enumerate(bottom):
        ax.text(i, tot, f"{tot / 1000:.1f}k", ha="center", va="bottom", fontsize=8, color=TEXT_2)
    return _finish(fig, ax, years, "Where NC's homeless students sleep at night",
                   "Statewide count by primary nighttime residence — district-level breakdown is not published",
                   "Students", save_as)
