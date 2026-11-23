"""Part C: the reduced two-player game, Minimax, Alpha-Beta and our evaluation function.

Players: MAX = delivery agent, MIN = blocker rival. One round = agent move, then rival move.
The game is "reduced" in two ways so that depth-5 search is cheap:
  * the agent's moves are restricted to a 7x7 window (radius 3) around its position at the
    root of the search (tunnel jumps out of the window are still allowed);
  * the leaves are scored by an evaluation function that summarises the rest of the
    episode (remaining tour, race to the stops, ford dependence, mobility) instead of
    searching to the end of the episode.
The same rule functions (agent_actions/apply_agent/rival_actions/apply_rival) are used by the
simulator, so the game and the real episode cannot drift apart. Search assumes moves never slip.
"""
from __future__ import annotations
import heapq, itertools
from collections import deque
from typing import NamedTuple

from src.world import World, FORD

MOVES = {"N": (-1, 0), "S": (1, 0), "W": (0, -1), "E": (0, 1)}
INF = float("inf")


class GState(NamedTuple):
    agent: tuple
    rival: tuple
    delivered: int      # bitmask over world.stops
    stolen: int         # bitmask over world.stops
    dam_used: bool
    flood_left: int     # steps of flood left at the start of the agent's next move
    t: int
    cost: float         # path cost paid by the agent so far


def initial_state(w: World) -> GState:
    return GState(w.start, w.rival_start, 0, 0, False, 0, 0, 0.0)


# ---------------------------------------------------------------- rules
def open_for(w: World, cell, other, flooded: bool) -> bool:
    """Can a player enter `cell`? Walls, the other player's cell and (while flooded) fords are closed."""
    r, c = cell
    if not (0 <= r < w.n and 0 <= c < w.n) or w.grid[r, c] < 0 or cell == other:
        return False
    return not (flooded and w.flood_enabled and w.grid[r, c] == FORD)


def agent_actions(w: World, s: GState, window=None) -> list:
    """Legal agent actions. `window` = (centre, radius) limits moves to the reduced board."""
    flooded = s.flood_left > 0
    acts = []
    for a, (dr, dc) in MOVES.items():
        nxt = (s.agent[0] + dr, s.agent[1] + dc)
        if window and max(abs(nxt[0] - window[0][0]), abs(nxt[1] - window[0][1])) > window[1]:
            continue
        if open_for(w, nxt, s.rival, flooded):
            acts.append(a)
    if s.agent in w.tunnels and open_for(w, w.tunnels[s.agent], s.rival, flooded):
        acts.append("TUNNEL")
    # WAIT is always allowed except on a flooded ford (the agent gets one move to leave);
    # if it has no other move at all it must wait anyway.
    if not (flooded and w.grid[s.agent] == FORD) or not acts:
        acts.append("WAIT")
    return acts


def agent_target(w: World, s: GState, a: str):
    """Cell the agent would reach with action a (deterministic)."""
    if a == "WAIT":
        return s.agent
    if a == "TUNNEL":
        return w.tunnels[s.agent]
    dr, dc = MOVES[a]
    return (s.agent[0] + dr, s.agent[1] + dc)


def apply_agent(w: World, s: GState, a: str, dest=None) -> GState:
    """Move the agent (to `dest` if a slip changed it) and deliver if it enters a stop."""
    dest = agent_target(w, s, a) if dest is None else dest
    if dest == s.agent:
        step = 1.0                                      # waiting (or bumping after a slip) costs 1
    elif a == "TUNNEL" and dest == w.tunnels.get(s.agent):
        step = w.tunnel_cost
    else:
        step = float(w.cost[dest])
    delivered = s.delivered
    for i, st in enumerate(w.stops):
        if st == dest and not ((s.delivered | s.stolen) >> i & 1):
            delivered |= 1 << i
    return s._replace(agent=dest, delivered=delivered, cost=s.cost + step,
                      flood_left=max(s.flood_left - 1, 0))


def rival_actions(w: World, s: GState) -> list:
    flooded = s.flood_left > 0
    acts = [a for a, (dr, dc) in MOVES.items()
            if open_for(w, (s.rival[0] + dr, s.rival[1] + dc), s.agent, flooded)]
    acts.append("WAIT")
    if w.flood_enabled and w.dam_enabled and not s.dam_used:
        acts.append("OPEN_DAM")
    return acts


def apply_rival(w: World, s: GState, a: str) -> GState:
    """Rival moves (stealing an undelivered stop it enters) or opens the dam; then t += 1."""
    rival, stolen, dam, fl = s.rival, s.stolen, s.dam_used, s.flood_left
    if a == "OPEN_DAM":
        dam, fl = True, w.flood_duration      # fords closed for the agent's next flood_duration moves
    elif a != "WAIT":
        dr, dc = MOVES[a]
        rival = (rival[0] + dr, rival[1] + dc)
        if w.steal_enabled:
            for i, st in enumerate(w.stops):
                if st == rival and not ((s.delivered | s.stolen) >> i & 1):
                    stolen |= 1 << i
    return s._replace(rival=rival, stolen=stolen, dam_used=dam, flood_left=fl, t=s.t + 1)


def all_done(w: World, s: GState) -> bool:
    return (s.delivered | s.stolen) == (1 << len(w.stops)) - 1


def outcome(s: GState) -> str:
    d, st = bin(s.delivered).count("1"), bin(s.stolen).count("1")
    return "win" if d > st else "draw" if d == st else "loss"


# ---------------------------------------------------------------- distance maps (our own Dijkstra/BFS)
def cost_to_target(w: World, target, fords: bool = True) -> dict:
    """Dijkstra *backwards* from target: d[cell] = cheapest cost to walk from cell to target
    (entering a cell costs its terrain; a tunnel jump costs tunnel_cost)."""
    reverse_tunnel = {b: a for a, b in w.tunnels.items()}
    d = {target: 0.0}
    pq = [(0.0, target)]
    while pq:
        du, u = heapq.heappop(pq)
        if du > d[u]:
            continue
        if not fords and w.grid[u] == FORD:
            continue                                  # cannot step through a ford
        preds = [(u[0] + dr, u[1] + dc) for dr, dc in MOVES.values()]
        steps = [(v, float(w.cost[u])) for v in preds]
        if u in reverse_tunnel:
            steps.append((reverse_tunnel[u], w.tunnel_cost))
        for v, c in steps:
            if not (0 <= v[0] < w.n and 0 <= v[1] < w.n) or w.grid[v] < 0:
                continue
            if not fords and w.grid[v] == FORD:
                continue
            if du + c < d.get(v, INF):
                d[v] = du + c
                heapq.heappush(pq, (du + c, v))
    if not fords and w.grid[target] == FORD:
        return {}                                     # the target itself is a ford (S3)
    return d


def steps_to_target(w: World, target, tunnels: bool = True) -> dict:
    """BFS backwards: number of moves (time steps) from each cell to target."""
    reverse_tunnel = {b: a for a, b in w.tunnels.items()} if tunnels else {}
    d = {target: 0}
    q = deque([target])
    while q:
        u = q.popleft()
        preds = [(u[0] + dr, u[1] + dc) for dr, dc in MOVES.values()]
        if u in reverse_tunnel:
            preds.append(reverse_tunnel[u])
        for v in preds:
            if 0 <= v[0] < w.n and 0 <= v[1] < w.n and w.grid[v] >= 0 and v not in d:
                d[v] = d[u] + 1
                q.append(v)
    return d


# ---------------------------------------------------------------- evaluation
DEFAULT_WEIGHTS = {"tour": 1.0, "score": 40.0, "race": 2.0, "ford": 6.0, "mobility": 0.25}


class Evaluator:
    """Our evaluation function, from the agent's (MAX) point of view.

      f1 tour     -(cost paid so far + cost of the best remaining tour), where the remaining
                  tour = min over delivery orders of the remaining stops, using exact
                  shortest-path costs from our Dijkstra maps (no flood, no rival).
                  We first used the admissible MST lower bound here, but then g+h grows by
                  more than 1 along the optimal route and WAIT (+1) always looked better:
                  the agent stalled. With the exact static tour, g+f1 is flat on the optimal
                  route and every detour or wait is penalised by exactly its extra cost.
      f2 score    delivered - stolen
      f3 race     mean over remaining stops of clip(rival steps - agent steps, -10, 10):
                  positive = the agent would get there first. Agent steps use tunnels;
                  the blocker cannot use tunnels. (Using only the "next" stop made the
                  feature jump when the nearest stop changed, which again caused stalls;
                  the mean changes by at most 1 per move.)
      f4 ford     -(number of remaining ford-dependent stops) x threat, where a stop is
                  ford-dependent if, from the depot or any other stop, it cannot be reached
                  as cheaply without crossing a ford (S3 is itself a ford), and
                  threat = 1 if the dam is unused + fraction of the flood still to run.
                  It depends only on WHICH stops remain, not on the agent's cell: a per-cell
                  version flipped between neighbouring cells and made the agent stall.
      f5 mobility number of agent moves that are not blocked (walls / rival / flood)
    """

    def __init__(self, w: World, weights: dict | None = None):
        self.w = w
        self.wt = dict(DEFAULT_WEIGHTS, **(weights or {}))
        self.k = len(w.stops)
        self.cost = [cost_to_target(w, st) for st in w.stops]
        self.cost_nf = [cost_to_target(w, st, fords=False) for st in w.stops]
        self.steps_agent = [steps_to_target(w, st, tunnels=True) for st in w.stops]
        self.steps_rival = [steps_to_target(w, st, tunnels=False) for st in w.stops]
        self.pair = [[self.cost[j].get(w.stops[i], INF) for j in range(self.k)] for i in range(self.k)]
        self._mst = {}
        self._tour = {}
        points = [w.start] + list(w.stops)
        self.ford_dep = [all(self.cost_nf[i].get(p, INF) > self.cost[i].get(p, INF) + 1e-9
                             for p in points if p != w.stops[i]) for i in range(self.k)]

    # ---- helpers
    def remaining(self, s: GState) -> list:
        done = s.delivered | s.stolen
        return [i for i in range(self.k) if not done >> i & 1]

    def mst(self, rem: tuple) -> float:
        if rem not in self._mst:
            if len(rem) <= 1:
                self._mst[rem] = 0.0
            else:                                         # Prim on <= 4 stops
                tree, best, tot = {rem[0]}, {j: self.pair[rem[0]][j] for j in rem[1:]}, 0.0
                while best:
                    j = min(best, key=best.get); tot += best.pop(j); tree.add(j)
                    for k in best:
                        best[k] = min(best[k], self.pair[j][k], self.pair[k][j])
                self._mst[rem] = tot
        return self._mst[rem]

    def tour_bound(self, cell, rem) -> float:
        """Exact static cost of the best remaining tour from `cell` (<= 4! = 24 orders)."""
        if not rem:
            return 0.0
        key = (cell, tuple(rem))
        if key not in self._tour:
            best = INF
            for order in itertools.permutations(rem):
                c = self.cost[order[0]].get(cell, 999.0)
                for a, b in zip(order, order[1:]):
                    c += self.pair[a][b]
                best = min(best, c)
            self._tour[key] = best
        return self._tour[key]

    def next_stop(self, s: GState):
        rem = self.remaining(s)
        return min(rem, key=lambda i: self.cost[i].get(s.agent, INF)) if rem else None

    def ford_dependence(self, cell, rem) -> int:
        return sum(1 for i in rem if self.cost_nf[i].get(cell, INF) > self.cost[i].get(cell, INF) + 1e-9)

    # ---- the features
    def features(self, s: GState) -> dict:
        w, rem = self.w, self.remaining(s)
        f = {"tour": -(s.cost + self.tour_bound(s.agent, rem)),
             "score": bin(s.delivered).count("1") - bin(s.stolen).count("1")}
        if rem and w.steal_enabled:
            f["race"] = sum(max(-10, min(10, self.steps_rival[i].get(s.rival, 99)
                                         - self.steps_agent[i].get(s.agent, 99)))
                            for i in rem) / len(rem)
        else:
            f["race"] = 10.0
        threat = (0.0 if s.dam_used or not (w.flood_enabled and w.dam_enabled) else 1.0) \
            + (s.flood_left / w.flood_duration if w.flood_duration else 0.0)
        f["ford"] = -sum(self.ford_dep[i] for i in rem) * threat
        flooded = s.flood_left > 0
        f["mobility"] = sum(open_for(w, (s.agent[0] + dr, s.agent[1] + dc), s.rival, flooded)
                            for dr, dc in MOVES.values())
        return f

    def __call__(self, s: GState) -> float:
        f = self.features(s)
        return sum(self.wt[k] * v for k, v in f.items())


# ---------------------------------------------------------------- search
class Counter:
    def __init__(self):
        self.nodes = 0


def _children(w, s, maximizing, window):
    if maximizing:
        return [(a, apply_agent(w, s, a)) for a in agent_actions(w, s, window)]
    return [(a, apply_rival(w, s, a)) for a in rival_actions(w, s)]


def minimax(w: World, s: GState, depth: int, maximizing: bool, ev: Evaluator,
            window=None, cnt: Counter | None = None) -> float:
    """Plain Minimax over plies (one ply = one player's move)."""
    if cnt:
        cnt.nodes += 1
    if depth == 0 or all_done(w, s):
        return ev(s)
    vals = [minimax(w, c, depth - 1, not maximizing, ev, window, cnt)
            for _, c in _children(w, s, maximizing, window)]
    return max(vals) if maximizing else min(vals)


def order_moves(w: World, s: GState, kids: list, maximizing: bool, ev: Evaluator) -> list:
    """OUR move ordering.
    Agent: children that bring it closest to the remaining tour (smallest tour bound) first.
    Rival: OPEN_DAM first when the agent's next stop needs a ford, then moves that bring the
    rival closest (in steps) to the agent's next stop, i.e. moves that block or steal."""
    if maximizing:
        return sorted(kids, key=lambda ac: ev.tour_bound(ac[1].agent, ev.remaining(ac[1])) + ac[1].cost)
    nxt = ev.next_stop(s)
    needs_ford = nxt is not None and ev.ford_dependence(s.agent, [nxt]) > 0

    def key(ac):
        a, c = ac
        if a == "OPEN_DAM":
            return -1 if needs_ford else 1000
        return ev.steps_rival[nxt].get(c.rival, 999) if nxt is not None else 0
    return sorted(kids, key=key)


def alphabeta(w: World, s: GState, depth: int, alpha: float, beta: float, maximizing: bool,
              ev: Evaluator, window=None, cnt: Counter | None = None, ordering: bool = True) -> float:
    """Alpha-Beta pruning. Same value as Minimax, fewer nodes."""
    if cnt:
        cnt.nodes += 1
    if depth == 0 or all_done(w, s):
        return ev(s)
    kids = _children(w, s, maximizing, window)
    if ordering:
        kids = order_moves(w, s, kids, maximizing, ev)
    if maximizing:
        v = -INF
        for _, c in kids:
            v = max(v, alphabeta(w, c, depth - 1, alpha, beta, False, ev, window, cnt, ordering))
            alpha = max(alpha, v)
            if alpha >= beta:
                break                                  # MIN will never allow this branch
        return v
    v = INF
    for _, c in kids:
        v = min(v, alphabeta(w, c, depth - 1, alpha, beta, True, ev, window, cnt, ordering))
        beta = min(beta, v)
        if alpha >= beta:
            break                                      # MAX already has something better
    return v


def best_action(w: World, s: GState, depth: int, maximizing: bool, ev: Evaluator,
                method: str = "alphabeta", ordering: bool = True, radius: int = 3):
    """Pick the root action for the player to move. Returns (action, value, nodes)."""
    window = (s.agent, radius)
    cnt = Counter()
    kids = _children(w, s, maximizing, window)
    if ordering:
        kids = order_moves(w, s, kids, maximizing, ev)
    best_a, best_v = None, -INF if maximizing else INF
    alpha, beta = -INF, INF
    for a, c in kids:
        if method == "minimax":
            v = minimax(w, c, depth - 1, not maximizing, ev, window, cnt)
        else:
            v = alphabeta(w, c, depth - 1, alpha, beta, not maximizing, ev, window, cnt, ordering)
        if (maximizing and v > best_v) or (not maximizing and v < best_v):
            best_a, best_v = a, v
        if maximizing:
            alpha = max(alpha, v)
        else:
            beta = min(beta, v)
    return best_a, best_v, cnt.nodes + 1
