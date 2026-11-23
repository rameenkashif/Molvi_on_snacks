"""Part B: the delivery task as one search problem.

State = (pos, done_mask, flood_left)
  pos         (row, col) of the agent
  done_mask   bit i is set when stop i is delivered *or stolen* (nothing left to do there)
  flood_left  remaining flooded steps (0 = fords are passable). Time only matters while the
              fords are flooded, so we keep a countdown instead of the raw time step t.
              This keeps the state space small: 529 cells x 16 masks x (flood_duration+1).

Actions: N, S, E, W (cost = terrain cost of the cell entered), TUNNEL (cost 1, only on a
mouth), WAIT (cost 1, only generated while flooded - otherwise it can never help).
Delivery is automatic when the agent enters an undelivered stop.
Planners assume deterministic moves and that the rival does not act (the simulator handles
slip and the rival, and the agent replans).
"""
from __future__ import annotations
from dataclasses import dataclass, field

from src.world import World, TERRAINS

MOVES = {"N": (-1, 0), "S": (1, 0), "W": (0, -1), "E": (0, 1)}
State = tuple  # (pos, done_mask, flood_left)


@dataclass
class DeliveryProblem:
    world: World
    start: tuple                              # agent position
    stops: list                               # stop cells this plan must cover (order = bit index)
    done_mask: int = 0                        # stops already delivered or stolen
    flood_left: int = 0                       # remaining flooded steps at plan time
    avoid_terrain: frozenset = frozenset()    # terrain names treated as walls, e.g. {"mud"}
    blocked_cells: frozenset = frozenset()    # extra walls, e.g. the rival's current cell
    order: tuple = ()                         # required delivery order prefix (stop indices)
    names: list = field(default_factory=list) # stop labels for printing

    def __post_init__(self):
        self.start = tuple(self.start)
        self.stops = [tuple(s) for s in self.stops]
        self.stop_index = {s: i for i, s in enumerate(self.stops)}
        self.goal_mask = (1 << len(self.stops)) - 1
        self.avoid_codes = {TERRAINS.index(t) for t in self.avoid_terrain}
        if not self.names:
            self.names = [f"S{i + 1}" for i in range(len(self.stops))]

    # ------------------------------------------------------------ interface
    def initial(self) -> State:
        mask = self.done_mask | self._deliver_bit(self.start, self.done_mask)
        return (self.start, mask, self.flood_left)

    def is_goal(self, s: State) -> bool:
        return s[1] == self.goal_mask

    def open_cell(self, cell, flooded: bool) -> bool:
        """Can the agent enter `cell` in a step taken while `flooded`?"""
        w = self.world
        r, c = cell
        if not (0 <= r < w.n and 0 <= c < w.n):
            return False
        code = w.grid[r, c]
        if code < 0 or cell in self.blocked_cells or code in self.avoid_codes:
            return False
        if flooded and w.flood_enabled and code == 3:     # 3 = ford
            return False
        return True

    def successors(self, s: State):
        """Return a list of (action, next_state, step_cost)."""
        pos, mask, fl = s
        flooded = fl > 0
        nfl = max(fl - 1, 0)          # one time step passes for every action
        out = []
        for a, (dr, dc) in MOVES.items():
            nxt = (pos[0] + dr, pos[1] + dc)
            if self.open_cell(nxt, flooded):
                out.append((a, (nxt, mask | self._deliver_bit(nxt, mask), nfl),
                            float(self.world.cost[nxt])))
        if pos in self.world.tunnels:
            nxt = self.world.tunnels[pos]
            if self.open_cell(nxt, flooded):
                out.append(("TUNNEL", (nxt, mask | self._deliver_bit(nxt, mask), nfl),
                            self.world.tunnel_cost))
        # WAIT only makes sense while the water is up, and not on a flooded ford
        if flooded and not (self.world.grid[pos] == 3):
            out.append(("WAIT", (pos, mask, nfl), 1.0))
        return out

    # ------------------------------------------------------------ helpers
    def _deliver_bit(self, cell, mask: int) -> int:
        """Bit to add when the agent enters `cell` (0 if nothing is delivered)."""
        i = self.stop_index.get(cell)
        if i is None or mask >> i & 1:
            return 0
        if self.order:                       # enforce the required delivery order
            for j in self.order:
                if j == i:
                    break
                if not mask >> j & 1:
                    return 0                 # an earlier stop in the order is not done yet
            else:
                if not all(mask >> j & 1 for j in self.order):
                    return 0                 # stop not in `order`: only after all of it
        return 1 << i

    def remaining(self, mask: int) -> list:
        return [s for i, s in enumerate(self.stops) if not mask >> i & 1]

    def path_cost(self, states: list) -> float:
        """Recompute the cost of a state path (used by tests)."""
        total = 0.0
        for a, b in zip(states, states[1:]):
            total += min(c for _, s2, c in self.successors(a) if s2 == b)
        return total


def full_problem(world: World, **kw) -> DeliveryProblem:
    """The whole tour: depot -> all stops, no flood at t=0."""
    return DeliveryProblem(world, world.start, world.stops, **kw)
