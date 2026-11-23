"""Shared helpers for experiment scripts: stamped figures, JSON output, text tables."""
from __future__ import annotations
import json, os

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

from src.world import STAMP, ROOT  # noqa: E402

OUT = os.path.join(ROOT, "results")


def save_json(name: str, payload: dict) -> str:
    os.makedirs(OUT, exist_ok=True)
    path = os.path.join(OUT, name)
    with open(path, "w") as f:
        json.dump({"stamp": STAMP, **payload}, f, indent=2, default=str)
    return path


def save_fig(fig, name: str) -> str:
    """Every figure gets the group stamp in its footer."""
    fig.text(0.5, 0.01, STAMP, ha="center", fontsize=7.5, color="#333")
    fig.tight_layout(rect=(0, 0.04, 1, 1))
    path = os.path.join(OUT, name)
    fig.savefig(path, dpi=130)
    plt.close(fig)
    return path


def print_table(rows: list, cols: list, title: str = "") -> None:
    """Plain fixed-width console table (stamp is printed by each main())."""
    if title:
        print(f"\n{title}")
    widths = [max(len(c), *(len(str(r.get(c, ""))) for r in rows)) for c in cols]
    print("  ".join(c.rjust(w) for c, w in zip(cols, widths)))
    for r in rows:
        print("  ".join(str(r.get(c, "")).rjust(w) for c, w in zip(cols, widths)))
