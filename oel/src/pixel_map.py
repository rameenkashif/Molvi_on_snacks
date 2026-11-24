"""Pixel-art renderer for the Streamlit UI (pure NumPy + matplotlib, no image files).

Every grid cell becomes a 16x16 pixel tile:
  road  -> asphalt with lane dashes toward neighbouring road cells and a light kerb
  grass -> green with speckles        mud -> brown dirt with clods
  ford  -> water with waves (dark, foaming water while flooded)
  blocked -> a pine tree or a rock on grass
Sprites (also 16x16) are drawn on top: tunnel portals, depot house, map pins for the stops
(red = to do, green = delivered, grey = stolen), the courier (agent) and the raccoon (rival).
Textures are seeded from the instance id, so the map looks the same every run.
"""
from __future__ import annotations
import hashlib

import numpy as np
import matplotlib.pyplot as plt
from matplotlib import patheffects

from src.world import STAMP

T = 16  # pixels per cell


def _rgb(h: str) -> np.ndarray:
    h = h.lstrip("#")
    return np.array([int(h[i:i + 2], 16) / 255 for i in (0, 2, 4)])


PAL = {k: _rgb(v) for k, v in {
    "k": "#1b1b1f", "r": "#e23b3b", "R": "#ff7a7a", "w": "#ffffff", "g": "#5fb85f", "G": "#2f7d32",
    "b": "#7a4a24", "L": "#9a9a9a", "l": "#c8c8c8", "D": "#666666", "W": "#f3e6c4", "c": "#7fc4ff",
    "d": "#8a5a2b", "B": "#2a62c9", "s": "#f6c9a0", "O": "#f08a24", "y": "#d9a95b", "P": "#3b3b55",
    "A": "#8a8a8a", "V": "#d0d0d0", "e": "#f7e26b", "E": "#3cb043", "Q": "#9e9e9e"}.items()}

SPRITES = {
    "pin": ["......kkkk......", "....kkrrrrkk....", "...krrRRrrrrk...", "..krRRrrrrrrrk..",
            "..krRrrwwrrrrk..", "..krrrwwwwrrrk..", "..krrrwwwwrrrk..", "..krrrrwwrrrrk..",
            "...krrrrrrrrk...", "...krrrrrrrrk...", "....krrrrrrk....", ".....krrrrk.....",
            "......krrk......", ".......kk.......", "................", "................"],
    "tree": [".......kk.......", "......kGGk......", ".....kGgGGk.....", "....kGGgGGGk....",
             ".....kGGGGk.....", "....kGgGGGGk....", "...kGGGgGGGGk...", "....kGGGGGGk....",
             "...kGGgGGGGGk...", "..kGGGGGgGGGGk..", "..kkkkkkkkkkkk..", ".......bb.......",
             ".......bb.......", "......kbbk......", "................", "................"],
    "rock": ["................", "................", "................", "................",
             "................", ".....kkkkk......", "....kLLLLLk.....", "...kLLlLLLLk....",
             "..kLLLLLLlLLk...", "..kLlLLLLLLDk...", ".kLLLLLDLLLDDk..", ".kLLLLLLLDDDDk..",
             ".kDDLLLDDDDDDk..", "..kkkkkkkkkkk...", "................", "................"],
    "house": ["................", ".......kk.......", "......krrk......", ".....krrrrk.....",
              "....krrrrrrk....", "...krrrrrrrrk...", "..kkkkkkkkkkkk..", "...kWWWWWWWWk...",
              "...kWccWWccWWk..", "...kWccWWccWk...", "...kWWWWWWWWk...", "...kWWWddWWWk...",
              "...kWWWddWWWk...", "...kkkkkkkkkk...", "................", "................"],
    "agent": ["................", ".....kkkkk......", "....kBBBBBk.....", "...kBBBBBBBk....",
              "....kssssk......", "....kskskk......", "....ksssk.......", "...kOOOOOk......",
              "..kOOOOOOkyyyk..", "..ksOOOOOkyyyk..", "...kOOOOOkyyyk..", "...kPPkPPkkkkk..",
              "...kPPkPPk......", "...kkk.kkk......", "................", "................"],
    "rival": ["................", "...kk......kk...", "..kAAk....kAAk..", "..kAAAkkkkAAAk..",
              "..kAAAAAAAAAAk..", ".kAkkkAAAAkkkAk.", ".kkwkkkAAkkwkkk.", ".kAkkkAAAAkkkAk.",
              "..kAAAAkkAAAAk..", "...kAVVVVVVAk...", "....kAAAAAAk....", "...kAAAAAAAAk...",
              "..kAAkAAAAkAAk..", "..kkk.kkkk.kkk..", "................", "................"],
    "check": ["................"] * 4 + ["..........kk....", ".........kEEk...", "..kk....kEEk....",
              ".kEEk..kEEk.....", "..kEEkkEEk......", "...kEEEEk.......", "....kEEk........",
              ".....kk........."] + ["................"] * 4,
}


def _blit(img, name, r, c, recolor=None):
    """Draw sprite `name` into cell (r, c). recolor maps palette chars to other chars."""
    rows = SPRITES[name]
    for i, line in enumerate(rows):
        for j, ch in enumerate(line):
            if ch == ".":
                continue
            ch = (recolor or {}).get(ch, ch)
            img[r * T + i, c * T + j] = PAL[ch]


def sprite_image(name, recolor=None, bg="#6abe30") -> np.ndarray:
    """A single 16x16 sprite on a plain background (for the legend)."""
    img = np.tile(_rgb(bg), (T, T, 1))
    _blit(img, name, 0, 0, recolor)
    return img


def _noise(rng, base, spread, k=0.08):
    """Tile of `base` colour with a few lighter/darker pixels."""
    tile = np.tile(base, (T, T, 1))
    m = rng.random((T, T))
    tile[m < k] = np.clip(base + spread, 0, 1)
    tile[m > 1 - k] = np.clip(base - spread, 0, 1)
    return tile


def render_tiles(w, flooded: bool = False) -> np.ndarray:
    """Background image (terrain + obstacles + portals + depot), no moving pieces."""
    seed = int(hashlib.sha256(("pixel|" + w.inst["instance_id"]).encode()).hexdigest()[:8], 16)
    rng = np.random.default_rng(seed)
    n = w.n
    img = np.zeros((n * T, n * T, 3))
    grass, road, mud = _rgb("#6abe30"), _rgb("#3d3d46"), _rgb("#8f563b")
    water, flood = _rgb("#4f9be0"), _rgb("#1f3f80")
    for r in range(n):
        for c in range(n):
            code = int(w.grid[r, c])
            y, x = r * T, c * T
            if code == 0:                                   # road
                tile = _noise(rng, road, 0.05, 0.05)
                for k, (dr, dc) in enumerate(((-1, 0), (1, 0), (0, -1), (0, 1))):
                    rr, cc = r + dr, c + dc
                    same = 0 <= rr < n and 0 <= cc < n and w.grid[rr, cc] == 0
                    if same:                                # lane dash toward the neighbour
                        if dr:
                            ys = range(0, 6) if dr < 0 else range(10, 16)
                            for yy in ys:
                                if yy % 4 < 2:
                                    tile[yy, 7:9] = _rgb("#e8e8e8")
                        else:
                            xs = range(0, 6) if dc < 0 else range(10, 16)
                            for xx in xs:
                                if xx % 4 < 2:
                                    tile[7:9, xx] = _rgb("#e8e8e8")
                    else:                                   # kerb on edges facing non-road
                        kerb = _rgb("#9aa0a6")
                        if dr < 0: tile[0, :] = kerb
                        if dr > 0: tile[-1, :] = kerb
                        if dc < 0: tile[:, 0] = kerb
                        if dc > 0: tile[:, -1] = kerb
            elif code == 2:                                 # mud
                tile = _noise(rng, mud, 0.08, 0.12)
                for _ in range(3):
                    a, b = rng.integers(2, 13, 2)
                    tile[a:a + 2, b:b + 3] = _rgb("#6e3f28")
            elif code == 3:                                 # ford / water
                base = flood if flooded else water
                tile = np.tile(base, (T, T, 1))
                wave = _rgb("#ffffff") if flooded else _rgb("#a9d4ff")
                for row in (3, 8, 13):
                    off = int(rng.integers(0, 4))
                    for xx in range(off, T - 3, 6):
                        tile[row, xx:xx + 3] = wave
                        tile[row - 1, xx + 1] = wave
            else:                                           # grass (and grass under obstacles)
                tile = _noise(rng, grass, 0.07, 0.10)
                if rng.random() < 0.35:                     # little grass tuft
                    a, b = rng.integers(3, 12, 2)
                    tile[a, b] = tile[a - 1, b + 1] = tile[a, b + 2] = _rgb("#3f8f2a")
            img[y:y + T, x:x + T] = tile
            if code < 0:
                _blit(img, "tree" if rng.random() < 0.7 else "rock", r, c)
    for m in w.tunnels:                                     # portals: concentric purple rings
        yy, xx = np.mgrid[0:T, 0:T]
        d = np.hypot(yy - 7.5, xx - 7.5)
        tile = img[m[0] * T:(m[0] + 1) * T, m[1] * T:(m[1] + 1) * T]
        tile[(d < 7.5)] = _rgb("#1b1b1f")
        tile[(d < 6.5)] = _rgb("#7b2cbf")
        tile[(d < 4.5)] = _rgb("#c77dff")
        tile[(d < 2.5)] = _rgb("#240046")
    _blit(img, "house", *w.start)
    return img


def draw_map(w, s, route=None, plan=None, trail=None, rival=True, title=None):
    """Full game view. route / plan / trail are lists of (row, col) cells."""
    n = w.n
    img = render_tiles(w, flooded=s.flood_left > 0)
    for i, st in enumerate(w.stops):
        if s.delivered >> i & 1:
            _blit(img, "pin", *st, recolor={"r": "E", "R": "g"})
        elif s.stolen >> i & 1:
            _blit(img, "pin", *st, recolor={"r": "Q", "R": "l"})
        else:
            _blit(img, "pin", *st)
    if rival:
        _blit(img, "rival", *s.rival)
    _blit(img, "agent", *s.agent)

    fig, ax = plt.subplots(figsize=(7.4, 7.6), facecolor="#3f8f2a")
    ax.imshow(img, extent=(-0.5, n - 0.5, n - 0.5, -0.5), interpolation="nearest")
    outline = [patheffects.withStroke(linewidth=4, foreground="#1b1b1f")]
    for a, b in {tuple(sorted(x)) for x in w.tunnels.items()}:
        ax.plot([a[1], b[1]], [a[0], b[0]], ":", c="#e0aaff", lw=1.2, alpha=.8)
    if trail and len(trail) > 1:
        ax.plot([c for _, c in trail], [r for r, _ in trail], "-", c="#1565c0", lw=2, alpha=.55)
    for cells, col, ls in ((route, "#ffd60a", "--"), (plan, "#ff4d6d", "-")):
        if cells and len(cells) > 1:
            ax.plot([c for _, c in cells], [r for r, _ in cells], ls, c=col, lw=2.6,
                    path_effects=outline, alpha=.95)
    box = dict(boxstyle="square,pad=0.25", fc="#e9e5dc", ec="#8d8d8d", lw=2)
    for i, st in enumerate(w.stops):
        label = f"S{i + 1}" + (" ✓" if s.delivered >> i & 1 else " ✗" if s.stolen >> i & 1 else "")
        above = st[0] >= 2                                  # top-row labels go below the pin
        ax.text(st[1], st[0] - 0.95 if above else st[0] + 0.75, label, ha="center",
                va="bottom" if above else "top", fontsize=8.5,
                family="monospace", weight="bold", color="#1b1b1f", bbox=box, zorder=6)
    ax.text(w.start[1], w.start[0] + 0.75, "DEPOT", ha="center", va="top", fontsize=7,
            family="monospace", weight="bold", color="#1b1b1f", bbox=box, zorder=6)
    ax.set_xticks(range(0, n, 2)); ax.set_yticks(range(0, n, 2))
    ax.tick_params(colors="white", labelsize=7, length=0)
    for lab in ax.get_xticklabels() + ax.get_yticklabels():
        lab.set_family("monospace")
    for sp in ax.spines.values():
        sp.set_edgecolor("#1b1b1f"); sp.set_linewidth(3)
    if title:
        ax.set_title(title, color="white", family="monospace", weight="bold", fontsize=11)
    fig.text(0.5, 0.012, STAMP, ha="center", fontsize=7, color="white", family="monospace")
    fig.tight_layout(rect=(0, 0.03, 1, 1))
    return fig
