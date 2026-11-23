"""World model for CS-370 OEL instance 6a18af32 (Part A).

Loads the generated instance, builds the terrain cost map, and adds the
group-specific mechanics the generator does not place itself:
  * teleport tunnels  (assigned twist 1) - seeded from the CMS IDs
  * rival steals parcels (assigned twist 2) - parameters live here, logic in the simulator
  * rival-triggered flooding (proposed 3rd twist) - the blocker can open a dam once
    per episode; every ford is impassable for flood_duration steps, then recedes
"""
from __future__ import annotations
import hashlib, os, sys
from dataclasses import dataclass, field
import numpy as np

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
from oel_instance import make_instance, stamp, TERRAINS  # noqa: E402

MEMBERS = [("Rameen Kashif", "456834"),
           ("Manal Aslam", "465734"),
           ("Zainab Ali Bangash", "486688")]
CMS_IDS = [cms for _, cms in MEMBERS]
STAMP = stamp(MEMBERS)

BLOCKED = -1
FORD = TERRAINS.index("ford")          # terrain code 3


@dataclass
class World:
    inst: dict
    grid: np.ndarray                    # int, -1 = blocked, 0..3 = terrain code
    cost: np.ndarray                    # float, np.inf where blocked
    tunnels: dict = field(default_factory=dict)   # cell -> paired cell (both directions)
    tunnel_cost: float = 1.0
    # rival_steals_parcels: rival takes a parcel if it reaches an undelivered stop first
    steal_enabled: bool = True
    # 3rd twist: rival-triggered flooding. The rival may open the dam once per episode
    # (costs its move). Fords are impassable for t in [flood_start, flood_start + flood_duration).
    flood_enabled: bool = True
    flood_duration: int = 15
    flood_start: int | None = None      # set by the simulator when the rival opens the dam
    # simulator / rival parameters (copied from the instance so they can be overridden live)
    slip_probability: float = 0.0
    rival_depth: int = 5
    rival_start: tuple | None = None    # seeded free cell, see pick_rival_start
    dam_enabled: bool = True            # False = rival has no dam action (ablation)

    def flooded(self, t: int) -> bool:
        return (self.flood_enabled and self.flood_start is not None
                and self.flood_start <= t < self.flood_start + self.flood_duration)

    def open_dam(self, t: int) -> bool:
        """Rival action. Returns False if the single dam charge is already used."""
        if not self.flood_enabled or self.flood_start is not None:
            return False
        self.flood_start = t
        return True

    @property
    def n(self): return self.grid.shape[0]
    @property
    def start(self): return tuple(self.inst["start"])
    @property
    def stops(self): return [tuple(map(int, s)) for s in self.inst["delivery_stops"]]
    @property
    def c_min(self) -> float:
        """Cheapest terrain cost; used to scale Manhattan distance in heuristics."""
        return float(min(self.inst["terrain_cost"].values()))

    def flood_left(self, t: int) -> int:
        """Remaining flooded steps at time t (0 if no flood is active)."""
        if not self.flooded(t):
            return 0
        return self.flood_start + self.flood_duration - t

    def is_ford(self, cell) -> bool:
        return self.grid[cell] == FORD

    def passable(self, cell, t: int = 0) -> bool:
        r, c = cell
        if not (0 <= r < self.n and 0 <= c < self.n) or self.grid[r, c] == BLOCKED:
            return False
        if self.grid[r, c] == FORD and self.flooded(t):
            return False
        return True

    def neighbours(self, cell, t: int = 0):
        """Yield (next_cell, step_cost). Moving onto a cell costs that cell's terrain;
        standing on a tunnel mouth allows a jump to its pair for tunnel_cost."""
        r, c = cell
        for dr, dc in ((1, 0), (-1, 0), (0, 1), (0, -1)):
            nxt = (r + dr, c + dc)
            if self.passable(nxt, t):
                yield nxt, float(self.cost[nxt])
        if cell in self.tunnels and self.passable(self.tunnels[cell], t):
            # (0,5) is a ford, so that tunnel exit is closed while the fords are flooded
            yield self.tunnels[cell], self.tunnel_cost


# ---------------------------------------------------------------- cost map
def build_cost_vectorised(grid: np.ndarray, terrain_cost: dict) -> np.ndarray:
    """Lookup-table indexing: one NumPy op over the whole grid, no Python loop."""
    lut = np.array([terrain_cost[t] for t in TERRAINS], dtype=float)
    return np.where(grid >= 0, lut[np.clip(grid, 0, None)], np.inf)


def build_cost_loop(grid, terrain_cost: dict) -> list:
    """Pure-Python reference version, used only for the Part A benchmark."""
    n, m = len(grid), len(grid[0])
    out = [[0.0] * m for _ in range(n)]
    for r in range(n):
        for c in range(m):
            v = grid[r][c]
            out[r][c] = float("inf") if v < 0 else float(terrain_cost[TERRAINS[v]])
    return out


# ---------------------------------------------------------------- tunnels
def make_tunnels(grid: np.ndarray, inst: dict, n_pairs: int = 3, min_sep: int | None = None):
    """Place tunnel pairs on free, non-stop, non-depot cells, far apart.
    Seeded from the instance hash so the instructor can regenerate them."""
    n = grid.shape[0]
    min_sep = min_sep or n // 2
    seed = int(hashlib.sha256(("tunnels|" + inst["instance_id"]).encode()).hexdigest()[:16], 16)
    rng = np.random.default_rng(seed)
    reserved = {tuple(inst["start"]), *map(tuple, inst["delivery_stops"])}
    free = [tuple(map(int, p)) for p in np.argwhere(grid >= 0) if tuple(map(int, p)) not in reserved]
    used, tunnels = set(), {}
    while len(tunnels) < 2 * n_pairs:
        a, b = (free[i] for i in rng.choice(len(free), 2, replace=False))
        if a in used or b in used or abs(a[0]-b[0]) + abs(a[1]-b[1]) < min_sep:
            continue
        tunnels[a], tunnels[b] = b, a
        used |= {a, b}
    return tunnels


def pick_rival_start(grid: np.ndarray, inst: dict, tunnels: dict, salt: str = "rival") -> tuple:
    """Seeded rival start: a free cell that is not the depot, a stop or a tunnel mouth,
    and at least n//3 Manhattan away from the depot (so the race is not decided at t=0)."""
    n = grid.shape[0]
    seed = int(hashlib.sha256((salt + "|" + inst["instance_id"]).encode()).hexdigest()[:16], 16)
    rng = np.random.default_rng(seed)
    depot = tuple(inst["start"])
    reserved = {depot, *map(tuple, inst["delivery_stops"]), *tunnels}
    cands = [tuple(map(int, p)) for p in np.argwhere(grid >= 0)
             if tuple(map(int, p)) not in reserved
             and abs(int(p[0]) - depot[0]) + abs(int(p[1]) - depot[1]) >= n // 3]
    return cands[int(rng.integers(len(cands)))]


# keys that live inside the instance dict rather than on the World object
INST_KEYS = {"terrain_cost", "start", "delivery_stops", "adversary"}


def load_world(cms_ids=CMS_IDS, **overrides) -> World:
    """Build the World for our instance. Any field can be overridden for the live viva,
    e.g. load_world(slip_probability=0.5, flood_duration=25, steal_enabled=False,
    delivery_stops=[(21,5),(0,1),(22,17),(10,10)]). Overriding the terrain cost or the
    stops rebuilds the cost map; tunnels stay at their seeded positions."""
    inst, grid = make_instance(cms_ids)
    inst["start"] = tuple(map(int, inst["start"]))
    inst["delivery_stops"] = [tuple(map(int, s)) for s in inst["delivery_stops"]]
    for k in INST_KEYS & overrides.keys():
        v = overrides.pop(k)
        if k == "delivery_stops":
            v = [tuple(map(int, s)) for s in v]
        if k == "start":
            v = tuple(map(int, v))
        inst[k] = v
    for cell in [inst["start"], *inst["delivery_stops"]]:
        if grid[cell] == BLOCKED:
            raise ValueError(f"cell {cell} is blocked")
    cost = build_cost_vectorised(grid, inst["terrain_cost"])
    tunnels = make_tunnels(grid, inst)
    w = World(inst=inst, grid=grid, cost=cost, tunnels=tunnels,
              slip_probability=float(inst["slip_probability"]),
              rival_depth=int(inst["adversary_search_depth"]),
              rival_start=pick_rival_start(grid, inst, tunnels))
    for k, v in overrides.items():          # live viva changes, e.g. flood_duration=25
        if not hasattr(w, k):
            raise AttributeError(f"unknown World parameter {k!r}")
        setattr(w, k, tuple(v) if k == "rival_start" and v is not None else v)
    return w


if __name__ == "__main__":
    w = load_world()
    print(STAMP)
    print(f"instance {w.inst['instance_id']}  n={w.n}  start={w.start}  stops={w.stops}")
    pairs = {tuple(sorted((a, b))) for a, b in w.tunnels.items()}
    print("tunnels:", sorted(pairs))
    print(f"rival start={w.rival_start}  depth={w.rival_depth}  slip={w.slip_probability}"
          f"  flood_duration={w.flood_duration}")
