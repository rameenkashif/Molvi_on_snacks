"""Part C: the stochastic episode simulator.

Turn order (CLAUDE.md section 4):
  agent acts -> slip resolved -> deliveries checked -> rival acts -> steals checked -> t += 1
Slip: with p = slip_probability a move N/S/E/W goes to a random perpendicular neighbour
instead; if that cell is closed the agent stays put (and still pays 1). TUNNEL and WAIT never slip.

Agent policies
  "planner"   follow an A* plan (tunnel_mst heuristic). Replan after every slip, when the dam
              opens, when the flood ends, when a stop is stolen, and when the rival blocks the
              next cell (the rival's cell is then treated as a wall).
  "alphabeta" hybrid: while the rival is outside the reduced game's window (Chebyshev
              distance > game_radius + 1) the agent follows the A* plan exactly like
              "planner"; when the rival is inside, each move comes from Alpha-Beta on the
              reduced game (depth agent_depth). (Pure game search everywhere was worse: with
              the rival far away the evaluation's horizon is too short to make progress.)
              Horizon fix: if it has chosen WAIT `stall_limit` turns in a row (a standoff in
              which every detour looks worse than waiting inside the search horizon), the
              next move comes from the A* planner with the rival's cell treated as a wall.
"""
from __future__ import annotations
from dataclasses import dataclass, field

import numpy as np

from src.world import World
from src.problem import DeliveryProblem
from src.search import astar
from src.heuristics import make_heuristic
from src.game import (GState, Evaluator, initial_state, agent_actions, agent_target, apply_agent,
                      apply_rival, all_done, outcome, open_for, best_action, MOVES)
from src.rival import BlockerRival

PERP = {"N": ("W", "E"), "S": ("W", "E"), "E": ("N", "S"), "W": ("N", "S")}


@dataclass
class EpisodeLog:
    states: list = field(default_factory=list)
    events: list = field(default_factory=list)
    replans: dict = field(default_factory=lambda: {"slip": 0, "dam": 0, "flood_end": 0,
                                                   "stolen": 0, "blocked": 0})
    slips: int = 0
    planned_cost: float = 0.0     # cost of the very first deterministic plan
    plans: list = field(default_factory=list)   # (t, list of cells) for the UI


class Simulator:
    def __init__(self, w: World, agent: str = "planner", seed: int = 0, rival: bool = True,
                 weights: dict | None = None, agent_depth: int = 3, rival_depth: int | None = None,
                 step_cap: int = 200, algorithm: str = "astar", heuristic: str = "tunnel_mst",
                 flood_aware: bool = False, stall_limit: int = 3,
                 rival_weights: dict | None = None, constraints: dict | None = None,
                 game_radius: int = 3, pure_game: bool = False):
        self.w = w
        self.agent_kind = agent
        self.rng = np.random.default_rng(seed)
        self.ev = Evaluator(w, weights)
        # the rival is a fixed opponent: it always uses its own (default) weights, so changing
        # the agent's weights does not also change the rival
        self.rival_ev = Evaluator(w, rival_weights) if weights != rival_weights else self.ev
        self.rival = BlockerRival(w, self.rival_ev, rival_depth) if rival else None
        # planner constraints from the dispatcher: {"avoid_terrain": [...], "order": (i, ...)}
        self.constraints = constraints or {}
        self.agent_depth = agent_depth
        self.step_cap = step_cap
        self.heuristic = heuristic
        self.flood_aware = flood_aware     # planner avoids fords while the dam is unused
        self.s: GState = initial_state(w)
        self.log = EpisodeLog(states=[self.s])
        self.plan: list = []               # remaining planned actions
        self.agent_nodes = 0
        self.stall_limit = stall_limit
        self.waits = 0                     # consecutive WAITs chosen by the alphabeta agent
        self.stall_breaks = 0
        self.game_radius = game_radius
        self.pure_game = pure_game         # True = Alpha-Beta on every move (ablation)
        self.game_moves = 0                # moves chosen by game search
        self.used_game_last = False

    # ------------------------------------------------------------ planning
    def make_plan(self, reason: str | None = None) -> None:
        s, w = self.s, self.w
        if reason:
            self.log.replans[reason] += 1
        must_avoid = frozenset(self.constraints.get("avoid_terrain", ()))
        avoid = frozenset({"ford"}) if (self.flood_aware and not s.dam_used and w.flood_enabled
                                       and w.dam_enabled) else frozenset()
        blocked = frozenset({s.rival}) if self.rival else frozenset()
        done = s.delivered | s.stolen
        # a stop the rival is standing on cannot be entered; if needed, plan the others first
        guarded = sum(1 << i for i, st in enumerate(w.stops) if st == s.rival and self.rival)
        attempts = [(avoid | must_avoid, done), (must_avoid, done)]
        if guarded:
            attempts.append((must_avoid, done | guarded))
        for av, mask in attempts:                # drop the extra restrictions if infeasible
            p = DeliveryProblem(w, s.agent, w.stops, done_mask=mask,
                                flood_left=s.flood_left, avoid_terrain=av, blocked_cells=blocked,
                                order=tuple(self.constraints.get("order", ())))
            r = astar(p, make_heuristic(self.heuristic, p))
            if r.success and r.actions:
                break
        self.plan = list(r.actions) if r.success else []
        if r.success:
            self.log.plans.append((s.t, [st[0] for st in r.path]))
            if not self.log.planned_cost:
                self.log.planned_cost = r.cost

    def choose(self) -> str:
        s, w = self.s, self.w
        near = self.rival is not None and max(abs(s.agent[0] - s.rival[0]),
                                              abs(s.agent[1] - s.rival[1])) <= self.game_radius + 1
        if self.agent_kind == "alphabeta" and (near or self.pure_game):
            self.used_game_last = True
            self.game_moves += 1
            if self.waits >= self.stall_limit:
                self.waits = 0
                self.stall_breaks += 1
                self.make_plan()
                if self.plan and self.plan[0] in agent_actions(w, s):
                    return self.plan[0]
            a, _, n = best_action(w, s, self.agent_depth, maximizing=True, ev=self.ev)
            self.agent_nodes += n
            self.waits = self.waits + 1 if a == "WAIT" else 0
            return a
        if self.used_game_last:                              # back from game search: plan afresh
            self.used_game_last = False
            self.waits = 0
            self.plan = []
        if not self.plan:
            self.make_plan()
        if not self.plan:
            return "WAIT"                                    # no route right now (e.g. flooded)
        a = self.plan[0]
        if a not in agent_actions(w, s):                     # rival (or water) in the way
            self.make_plan("blocked")
            if not self.plan:
                return "WAIT"
            a = self.plan[0]
            if a not in agent_actions(w, s):
                return "WAIT"
        return a

    # ------------------------------------------------------------ one turn
    def step(self) -> bool:
        """Play one full turn. Returns False when the episode is over."""
        w = self.w
        if self.done():
            return False
        s0 = self.s
        a = self.choose()
        dest = agent_target(w, s0, a)
        slipped = False
        if a in MOVES and self.rng.random() < w.slip_probability:
            side = PERP[a][int(self.rng.integers(2))]
            dr, dc = MOVES[side]
            cand = (s0.agent[0] + dr, s0.agent[1] + dc)
            dest = cand if open_for(w, cand, s0.rival, s0.flood_left > 0) else s0.agent
            slipped = True
            self.log.slips += 1
            self.log.events.append((s0.t, f"slip: {a} -> {side}, now at {dest}"))
        s1 = apply_agent(w, s0, a, dest)
        if s1.delivered != s0.delivered:
            self.log.events.append((s0.t, f"delivered at {dest}"))
        if self.plan:
            self.plan.pop(0)
        if self.rival and not all_done(w, s1):
            ra = self.rival.act(s1)
            s2 = apply_rival(w, s1, ra)
            if ra == "OPEN_DAM":
                self.log.events.append((s0.t, "rival opened the dam"))
            if s2.stolen != s1.stolen:
                self.log.events.append((s0.t, f"rival stole parcel at {s2.rival}"))
        else:
            s2 = s1._replace(t=s1.t + 1)
        self.s = s2
        self.log.states.append(s2)
        if self.agent_kind == "planner" or not self.used_game_last:   # replanning triggers
            if slipped:
                self.make_plan("slip")
            elif s2.dam_used and not s1.dam_used:
                self.make_plan("dam")
            elif s2.stolen != s1.stolen:
                self.make_plan("stolen")
            elif s1.flood_left > 0 and s2.flood_left == 0:
                self.make_plan("flood_end")
        return not self.done()

    def done(self) -> bool:
        return all_done(self.w, self.s) or self.s.t >= self.step_cap

    def run(self) -> dict:
        self.make_plan()
        while self.step():
            pass
        return self.result()

    def result(self) -> dict:
        s = self.s
        d, st = bin(s.delivered).count("1"), bin(s.stolen).count("1")
        dam_t = next((t for t, e in self.log.events if e == "rival opened the dam"), None)
        return {"outcome": outcome(s), "delivered": d, "stolen": st,
                "undelivered": len(self.w.stops) - d - st, "cost": s.cost, "steps": s.t,
                "slips": self.log.slips, "replans": sum(self.log.replans.values()),
                "replans_by_reason": dict(self.log.replans), "planned_cost": self.log.planned_cost,
                "dam_time": dam_t, "rival_nodes": self.rival.nodes if self.rival else 0,
                "agent_nodes": self.agent_nodes, "stall_breaks": self.stall_breaks,
                "game_moves": self.game_moves,
                "finished": all_done(self.w, s)}


# ---------------------------------------------------------------- scenarios (Parts C and E)
def scenario(w: World, i: int, vary_stops: bool = False) -> dict:
    """Scenario i, seeded sha256("scenario|<instance_id>|<i>"): a rival start cell (free, not a
    stop / depot / tunnel mouth, >= n//3 from the depot), a seed for the slip draws and, if
    vary_stops, a fresh set of stop cells among the free cells."""
    from src.stats import seed_for
    rng = np.random.default_rng(seed_for("scenario", w.inst["instance_id"], i))
    free = [tuple(map(int, c)) for c in np.argwhere(w.grid >= 0)]
    stops = list(w.stops)
    if vary_stops:
        pool = [c for c in free if c != w.start and c not in w.tunnels]
        stops = [pool[j] for j in rng.choice(len(pool), len(w.stops), replace=False)]
    reserved = {w.start, *stops, *w.tunnels}
    cands = [c for c in free if c not in reserved
             and abs(c[0] - w.start[0]) + abs(c[1] - w.start[1]) >= w.n // 3]
    return {"i": i, "rival_start": cands[int(rng.integers(len(cands)))],
            "sim_seed": int(rng.integers(2**31)), "stops": stops}
