"""Part B: heuristics for the DeliveryProblem state (pos, done_mask, flood_left).

  tunnel_mst   OUR heuristic. h = min_x d*(pos, x) + MST(remaining stops), with edge
               weights d*, a relaxed distance that knows about the teleport tunnels.
               (An MST over {pos} + remaining is admissible but NOT consistent - we measured
               674 violating edges - so pos is attached to the tree by its cheapest edge.)
  mst_plain    ablation: same MST but d* without tunnel edges (plain Manhattan x c_min).
  nearest      baseline 1: Manhattan x c_min to the nearest remaining stop.
  farthest     baseline 2: Manhattan x c_min to the farthest remaining stop.
  sum_dstar    inadmissible variant: sum of d* from pos to every remaining stop.
  zero         h = 0 (A* becomes UCS).

Proof of admissibility for tunnel_mst: docs/part_b_heuristic.md.
Note: the two Manhattan baselines are NOT guaranteed admissible on our map, because a
tunnel jump (cost 1) can be much cheaper than the Manhattan distance it covers.
"""
from __future__ import annotations
import itertools

from src.problem import DeliveryProblem


def manhattan(a, b) -> int:
    return abs(a[0] - b[0]) + abs(a[1] - b[1])


class RelaxedDistance:
    """d*(a, b): shortest path in a tiny complete graph.

    Nodes  = the problem's stops + tunnel mouths.
    Edges  = Manhattan(a, b) * c_min between every pair (ignores walls, terrain above
             c_min and flooding), plus tunnel_cost between the two mouths of each tunnel.
    All-pairs distances are precomputed with Floyd-Warshall (at most 4 + 6 = 10 nodes).
    For an arbitrary cell p:  d*(p, x) = min( M(p, x),  min over mouths m of M(p, m) + D(m, x) ).
    """

    def __init__(self, problem: DeliveryProblem, use_tunnels: bool = True):
        w = problem.world
        self.cmin = w.c_min
        self.mouths = list(w.tunnels) if use_tunnels else []
        self.nodes = list(problem.stops) + [m for m in self.mouths if m not in problem.stops]
        idx = {p: i for i, p in enumerate(self.nodes)}
        k = len(self.nodes)
        D = [[manhattan(a, b) * self.cmin for b in self.nodes] for a in self.nodes]
        if use_tunnels:
            for a, b in w.tunnels.items():
                D[idx[a]][idx[b]] = min(D[idx[a]][idx[b]], w.tunnel_cost)
        for m in range(k):                               # Floyd-Warshall
            for i in range(k):
                for j in range(k):
                    if D[i][m] + D[m][j] < D[i][j]:
                        D[i][j] = D[i][m] + D[m][j]
        self.D, self.idx = D, idx
        self._cache = {}

    def between_nodes(self, a, b) -> float:
        return self.D[self.idx[a]][self.idx[b]]

    def from_cell(self, p, x) -> float:
        """d*(p, x) for any cell p and a node x (a stop)."""
        key = (p, x)
        if key not in self._cache:
            best = manhattan(p, x) * self.cmin
            j = self.idx[x]
            for m in self.mouths:
                best = min(best, manhattan(p, m) * self.cmin + self.D[self.idx[m]][j])
            self._cache[key] = best
        return self._cache[key]


def mst_weight(points: list, dist) -> float:
    """Prim's algorithm on a complete graph (at most 5 points here)."""
    if len(points) <= 1:
        return 0.0
    in_tree = {0}
    best = {i: dist(points[0], points[i]) for i in range(1, len(points))}
    total = 0.0
    while best:
        i = min(best, key=best.get)
        total += best.pop(i)
        in_tree.add(i)
        for j in best:
            best[j] = min(best[j], dist(points[i], points[j]))
    return total


class TunnelMST:
    """h(s) = d*(pos, nearest remaining stop) + MST(remaining stops) under d*.
    Admissible and consistent (proof in docs/part_b_heuristic.md)."""

    def __init__(self, problem: DeliveryProblem, use_tunnels: bool = True):
        self.p = problem
        self.d = RelaxedDistance(problem, use_tunnels)
        self._cache = {}

    def _dist(self, a, b):
        if a in self.d.idx and b in self.d.idx:
            return self.d.between_nodes(a, b)
        if b in self.d.idx:
            return self.d.from_cell(a, b)
        return self.d.from_cell(b, a)

    def __call__(self, s) -> float:
        pos, mask, _ = s
        key = (pos, mask)
        if key not in self._cache:
            rem = self.p.remaining(mask)
            if not rem:
                self._cache[key] = 0.0
            else:
                reach = min(self._dist(pos, x) for x in rem)       # get to the first stop
                self._cache[key] = reach + self._mst(mask, rem)    # then connect all of them
        return self._cache[key]

    def _mst(self, mask, rem):
        """MST of the remaining stops only; depends on mask alone, so cache it."""
        key = ("mst", mask)
        if key not in self._cache:
            self._cache[key] = mst_weight(rem, self._dist)
        return self._cache[key]


class SumDStar(TunnelMST):
    """Inadmissible: counts the trip to every remaining stop as if each started from pos."""

    def __call__(self, s) -> float:
        pos, mask, _ = s
        return sum(self._dist(pos, x) for x in self.p.remaining(mask))


def nearest(problem: DeliveryProblem):
    c = problem.world.c_min
    def h(s):
        rem = problem.remaining(s[1])
        return min(manhattan(s[0], x) for x in rem) * c if rem else 0.0
    return h


def farthest(problem: DeliveryProblem):
    c = problem.world.c_min
    def h(s):
        rem = problem.remaining(s[1])
        return max(manhattan(s[0], x) for x in rem) * c if rem else 0.0
    return h


HEURISTICS = {
    "tunnel_mst": lambda p: TunnelMST(p, use_tunnels=True),
    "mst_plain": lambda p: TunnelMST(p, use_tunnels=False),
    "nearest": nearest,
    "farthest": farthest,
    "sum_dstar": lambda p: SumDStar(p, use_tunnels=True),
    "zero": lambda p: (lambda s: 0.0),
}


def make_heuristic(name: str, problem: DeliveryProblem):
    if name not in HEURISTICS:
        raise ValueError(f"unknown heuristic {name!r}; choose from {list(HEURISTICS)}")
    return HEURISTICS[name](problem)
