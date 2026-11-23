"""Part B: uninformed and informed search, written from scratch.

Every algorithm works on any object with  initial(), is_goal(s), successors(s) -> [(action, s2, cost)]
and returns a SearchResult. Nothing here imports a search library.
"""
from __future__ import annotations
import heapq, itertools, time, tracemalloc
from collections import deque
from dataclasses import dataclass, field


@dataclass
class SearchResult:
    algorithm: str
    success: bool
    path: list = field(default_factory=list)       # list of states, start .. goal
    actions: list = field(default_factory=list)
    cost: float = float("inf")
    expanded: int = 0           # nodes whose successors were generated
    generated: int = 0          # successor nodes created
    max_stored: int = 0         # peak number of nodes held (frontier + closed, or path for DLS/IDS)
    peak_mem: int = 0           # bytes, from tracemalloc (0 if not measured)
    time: float = 0.0           # seconds, time.perf_counter
    note: str = ""
    consistency_checks: int = 0
    consistency_violations: int = 0

    def summary(self) -> dict:
        return {"algorithm": self.algorithm, "success": self.success, "cost": self.cost,
                "steps": len(self.actions), "expanded": self.expanded, "generated": self.generated,
                "max_stored": self.max_stored, "peak_mem_kb": round(self.peak_mem / 1024, 1),
                "time_ms": round(self.time * 1e3, 2), "note": self.note}


def _rebuild(parent: dict, goal):
    """Follow parent pointers back from goal. parent[s] = (prev_state, action, step_cost)."""
    states, actions, cost = [goal], [], 0.0
    s = goal
    while parent[s] is not None:
        prev, a, c = parent[s]
        states.append(prev); actions.append(a); cost += c
        s = prev
    return states[::-1], actions[::-1], cost


def run(fn, problem, *args, measure_memory: bool = True, **kw) -> SearchResult:
    """Run one search with timing and (optionally) tracemalloc peak memory."""
    if measure_memory:
        tracemalloc.start()
    t0 = time.perf_counter()
    res = fn(problem, *args, **kw)
    res.time = time.perf_counter() - t0
    if measure_memory:
        res.peak_mem = tracemalloc.get_traced_memory()[1]
        tracemalloc.stop()
    return res


# ---------------------------------------------------------------- uninformed
def bfs(problem) -> SearchResult:
    """Breadth-first graph search. Optimal in number of actions, not in cost."""
    res = SearchResult("BFS", False)
    start = problem.initial()
    parent = {start: None}
    if problem.is_goal(start):
        res.success, res.path, res.cost = True, [start], 0.0
        return res
    frontier = deque([start])
    while frontier:
        s = frontier.popleft()
        res.expanded += 1
        for a, s2, c in problem.successors(s):
            res.generated += 1
            if s2 in parent:
                continue
            parent[s2] = (s, a, c)
            if problem.is_goal(s2):                      # goal test on generation
                res.success = True
                res.path, res.actions, res.cost = _rebuild(parent, s2)
                res.max_stored = len(parent)
                return res
            frontier.append(s2)
        res.max_stored = max(res.max_stored, len(parent))
    return res


def ucs(problem) -> SearchResult:
    """Uniform-cost search (Dijkstra). Goal test when a node is popped -> cost-optimal."""
    return best_first(problem, lambda s: 0.0, name="UCS", use_g=True)


def dls(problem, limit: int, max_nodes: int | None = None, _res: SearchResult | None = None) -> SearchResult:
    """Depth-limited DFS, iterative (explicit stack) so that recursion depth is not an issue.

    Revisits are avoided only along the *current path*: before pushing a child we check
    it against `on_path`, a set holding exactly the states on the path from the root.
    Memory is O(b*d): the stack holds one successor list per depth level.
    Returns success, or note='cutoff' if the limit was hit somewhere (deeper search may help),
    or note='failure' if the whole tree was exhausted.
    """
    res = _res or SearchResult(f"DLS(l={limit})", False)
    start = problem.initial()
    if problem.is_goal(start):
        res.success, res.path, res.cost = True, [start], 0.0
        return res
    path, acts, costs = [start], [], []
    on_path = {start}
    first = problem.successors(start)
    stack = [[first, 0]]                                 # one (successor list, next index) per level
    held = len(first)                                    # successor entries currently on the stack
    res.expanded += 1
    cutoff = False
    while stack:
        res.max_stored = max(res.max_stored, len(path) + held)
        if max_nodes is not None and len(path) + held > max_nodes:
            res.note = "memory limit"
            return res
        level = stack[-1]
        if level[1] >= len(level[0]):                    # this level is exhausted -> backtrack
            held -= len(level[0])
            stack.pop()
            on_path.discard(path.pop())
            if acts:
                acts.pop(); costs.pop()
            continue
        a, s2, c = level[0][level[1]]
        level[1] += 1
        res.generated += 1
        if s2 in on_path:                                # cycle on the current path
            continue
        if problem.is_goal(s2):
            res.success = True
            res.path, res.actions = path + [s2], acts + [a]
            res.cost = sum(costs) + c
            return res
        if len(path) >= limit:                           # depth limit reached
            cutoff = True
            continue
        path.append(s2); acts.append(a); costs.append(c); on_path.add(s2)
        succ = problem.successors(s2)
        stack.append([succ, 0]); held += len(succ)
        res.expanded += 1
    res.note = "cutoff" if cutoff else "failure"
    return res


def ids(problem, max_depth: int = 200, max_nodes: int | None = None,
        max_expansions: int | None = None) -> SearchResult:
    """Iterative deepening: DLS with limit 0, 1, 2, ... Finds the shallowest goal
    (fewest actions). Node counts are accumulated over all iterations."""
    res = SearchResult("IDS", False)
    for limit in range(max_depth + 1):
        res.note = ""
        dls(problem, limit, max_nodes=max_nodes, _res=res)
        if res.success:
            res.note = f"depth {limit}"
            return res
        if res.note in ("failure", "memory limit"):
            return res
        if max_expansions is not None and res.expanded > max_expansions:
            res.note = f"gave up at depth {limit} (>{max_expansions} expansions)"
            return res
    res.note = "max depth"
    return res


# ---------------------------------------------------------------- informed
def best_first(problem, h, name: str, use_g: bool = True, weight: float = 1.0,
               max_nodes: int | None = None, check_consistency: bool = False) -> SearchResult:
    """Generic best-first search with priority  g*use_g + weight*h.

      UCS    : h = 0, use_g = True
      Greedy : use_g = False         (priority = h only)
      A*     : use_g = True, weight 1
      WA*    : weight > 1            (inadmissible, faster, may return a worse plan)

    Uses lazy deletion: a state may sit in the heap several times; stale entries are skipped.
    max_nodes caps frontier + closed (memory limit); exceeding it is a failure.
    """
    res = SearchResult(name, False)
    start = problem.initial()
    g = {start: 0.0}
    parent = {start: None}
    closed = set()
    tie = itertools.count()                              # FIFO tie-break, keeps runs deterministic
    frontier = [(weight * h(start), next(tie), start)]
    while frontier:
        _, _, s = heapq.heappop(frontier)
        if s in closed:
            continue                                     # stale heap entry
        if problem.is_goal(s):
            res.success = True
            res.path, res.actions, res.cost = _rebuild(parent, s)
            return res
        closed.add(s)
        res.expanded += 1
        hs = h(s) if check_consistency else 0.0
        for a, s2, c in problem.successors(s):
            res.generated += 1
            if check_consistency:
                res.consistency_checks += 1
                if hs > c + h(s2) + 1e-9:                # h(s) <= c(s,s') + h(s')
                    res.consistency_violations += 1
            if s2 in closed:
                continue
            g2 = g[s] + c
            if s2 not in g or g2 < g[s2]:
                g[s2] = g2
                parent[s2] = (s, a, c)
                prio = (g2 if use_g else 0.0) + weight * h(s2)
                heapq.heappush(frontier, (prio, next(tie), s2))
        res.max_stored = max(res.max_stored, len(frontier) + len(closed))
        if max_nodes is not None and res.max_stored > max_nodes:
            res.note = "memory limit"
            return res
    return res


def greedy(problem, h, **kw) -> SearchResult:
    return best_first(problem, h, name="Greedy", use_g=False, **kw)


def astar(problem, h, weight: float = 1.0, **kw) -> SearchResult:
    return best_first(problem, h, name="A*" if weight == 1 else f"WA*(w={weight:g})",
                      use_g=True, weight=weight, **kw)


ALGORITHMS = ["bfs", "ucs", "dls", "ids", "greedy", "astar", "wastar"]


def solve(problem, algorithm: str = "astar", h=None, measure_memory: bool = False, **kw) -> SearchResult:
    """One entry point used by the simulator, UI and LLM tools."""
    algorithm = algorithm.lower().replace("*", "star").replace("-", "")
    zero = lambda s: 0.0
    if algorithm == "bfs":
        return run(bfs, problem, measure_memory=measure_memory)
    if algorithm == "ucs":
        return run(ucs, problem, measure_memory=measure_memory)
    if algorithm == "dls":
        return run(dls, problem, kw.get("limit", 60), measure_memory=measure_memory)
    if algorithm == "ids":
        return run(ids, problem, measure_memory=measure_memory,
                   max_expansions=kw.get("max_expansions", 2_000_000))
    if algorithm == "greedy":
        return run(greedy, problem, h or zero, measure_memory=measure_memory)
    if algorithm == "astar":
        return run(astar, problem, h or zero, measure_memory=measure_memory)
    if algorithm == "wastar":
        return run(astar, problem, h or zero, kw.get("weight", 2.0), measure_memory=measure_memory)
    raise ValueError(f"unknown algorithm {algorithm!r}; choose from {ALGORITHMS}")
