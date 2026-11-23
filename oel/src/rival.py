"""Part C: the blocker rival.

The blocker searches the reduced game with Alpha-Beta at the instance's depth (5 plies) as
MIN, using the same evaluation function as the agent (zero-sum). Its actions: 4 moves,
WAIT, and OPEN_DAM once per episode. Because the evaluation rewards the agent for winning the
race to stops and for not depending on fords, MIN naturally learns to (a) stand in the
agent's way, (b) walk onto stops the agent cannot reach first (steal), and (c) open the dam
when the agent's next leg needs a ford.
"""
from __future__ import annotations

from src.game import GState, Evaluator, best_action, rival_actions
from src.world import World


class BlockerRival:
    def __init__(self, w: World, ev: Evaluator, depth: int | None = None, ordering: bool = True):
        self.w, self.ev = w, ev
        self.depth = depth if depth is not None else w.rival_depth
        self.ordering = ordering
        self.nodes = 0                       # total nodes searched in this episode

    def act(self, s: GState) -> str:
        if self.depth <= 0:
            return "WAIT"
        a, _, n = best_action(self.w, s, self.depth, maximizing=False, ev=self.ev,
                              ordering=self.ordering)
        self.nodes += n
        return a or rival_actions(self.w, s)[0]
