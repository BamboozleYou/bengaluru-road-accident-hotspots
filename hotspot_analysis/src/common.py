"""Shared paths, plot style and helpers used by all four member modules.

Road Accident Hotspot Analysis - Bengaluru (Data Exploration & Visualization, 23CS5PCDEV)
"""
import contextlib
import io
import json
import sys
import warnings
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import seaborn as sns

warnings.filterwarnings("ignore")
pd.set_option("display.width", 150)
pd.set_option("display.max_columns", 20)
pd.set_option("display.max_colwidth", 40)

PROJECT = Path(__file__).resolve().parents[1]          # hotspot_analysis/
RAW = PROJECT.parent / "data" / "raw"                   # raw CSVs downloaded from OpenCity
INTERIM = PROJECT / "outputs" / "interim"              # pickles passed between modules
TABLES = PROJECT / "outputs" / "tables"                # CSV tables used in the report
FIG = PROJECT / "outputs" / "figures"                  # charts
CONSOLE = PROJECT / "outputs" / "console"              # captured printed output per step
for _d in (INTERIM, TABLES, FIG, CONSOLE):
    _d.mkdir(parents=True, exist_ok=True)

# ---------------------------------------------------------------- colours
# Categorical slots in fixed order (validated CVD-safe for adjacent use).
ZONE_ORDER = ["North", "East", "West", "South"]
ZONE_COL = {"North": "#2a78d6", "East": "#eb6834", "West": "#1baf7a", "South": "#eda100"}
ZONE_MARK = {"North": "o", "East": "s", "West": "D", "South": "^"}  # secondary encoding
BLUE, ORANGE, GREY, INK, INK2, MUTED = "#2a78d6", "#eb6834", "#c3c2b7", "#0b0b0b", "#52514e", "#898781"
SEQ = matplotlib.colors.LinearSegmentedColormap.from_list(
    "seq_blue", ["#f4f8fd", "#cde2fb", "#86b6ef", "#3987e5", "#256abf", "#184f95", "#0d366b"])
DIV = matplotlib.colors.LinearSegmentedColormap.from_list(
    "div_blue_red", ["#2a78d6", "#86b6ef", "#f0efec", "#ef9a99", "#e34948"])

sns.set_theme(style="white", font="Times New Roman")
plt.rcParams.update({
    "figure.facecolor": "white", "axes.facecolor": "white",
    "axes.edgecolor": "#c3c2b7", "axes.labelcolor": INK2, "axes.titlecolor": INK,
    "xtick.color": INK2, "ytick.color": INK2, "axes.titleweight": "bold", "axes.titlesize": 12,
    "axes.labelsize": 10.5, "xtick.labelsize": 9.5, "ytick.labelsize": 9.5,
    "axes.spines.top": False, "axes.spines.right": False,
    "axes.grid": True, "axes.grid.axis": "y", "grid.color": "#e1e0d9", "grid.linewidth": 0.6,
    "legend.frameon": False, "legend.fontsize": 9, "lines.linewidth": 2,
})


def savefig(name):
    """Save the current figure as outputs/figures/<name>.png."""
    plt.tight_layout()
    plt.savefig(FIG / f"{name}.png", dpi=200, bbox_inches="tight")
    plt.close("all")


class _Tee(io.TextIOBase):
    def __init__(self, *streams):
        self.streams = streams

    def write(self, s):
        for st in self.streams:
            st.write(s)
        return len(s)


@contextlib.contextmanager
def step(name):
    """Run a block, echo its printed output and keep a copy for the report screenshots."""
    buf = io.StringIO()
    old = sys.stdout
    sys.stdout = _Tee(old, buf)
    try:
        yield
    finally:
        sys.stdout = old
        (CONSOLE / f"{name}.txt").write_text(buf.getvalue())


def save(obj, name):
    pd.to_pickle(obj, INTERIM / f"{name}.pkl")


def load(name):
    return pd.read_pickle(INTERIM / f"{name}.pkl")


def record(**kv):
    """Collect headline numbers in outputs/results.json (quoted in the report)."""
    path = PROJECT / "outputs" / "results.json"
    res = json.loads(path.read_text()) if path.exists() else {}
    res.update(json.loads(json.dumps(kv, default=lambda o: o.item() if hasattr(o, "item") else str(o))))
    path.write_text(json.dumps(res, indent=1))


def zone_legend(ax, **kw):
    from matplotlib.lines import Line2D
    handles = [Line2D([], [], marker=ZONE_MARK[z], ls="", color=ZONE_COL[z], markersize=8,
                      markeredgecolor="white", label=z) for z in ZONE_ORDER]
    ax.legend(handles=handles, title="Zone", **kw)
