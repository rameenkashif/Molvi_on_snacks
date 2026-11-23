"""Core correctness tests (CLAUDE.md section 8)."""
import numpy as np
import pytest

from src.world import load_world, STAMP
from src.problem import DeliveryProblem, full_problem
from src.search import run, bfs, ucs, dls, ids, greedy, astar
from src.heuristics import make_heuristic
from src.game import (Evaluator, initial_state, minimax, alphabeta, apply_agent, apply_rival,
                      agent_actions, INF)
from src.simulator import Simulator, scenario
from src.stats import wilson, mean_ci


@pytest.fixture(scope="module")
def w():
    return load_world()


def test_stamp():
    assert STAMP == "Rameen Kashif (456834) | Manal Aslam (465734) | Zainab Ali Bangash (486688)"


def test_instance(w):
    assert w.n == 23 and w.start == (8, 7)
    assert w.stops == [(21, 5), (0, 1), (22, 17), (15, 18)]
    assert w.grid[(22, 17)] == 3            # S3 is a ford


def test_tunnels_symmetric(w):
    assert len(w.tunnels) == 6
    for a, b in w.tunnels.items():
        assert w.tunnels[b] == a and a != b


def test_flood_window(w):
    w = load_world(flood_duration=15)
    assert w.open_dam(10) and not w.open_dam(11)          # one charge only
    assert not w.flooded(9) and w.flooded(10) and w.flooded(24) and not w.flooded(25)
    assert not w.passable((22, 17), 12) and w.passable((22, 17), 25)


def test_overrides():
    w2 = load_world(slip_probability=0.5, delivery_stops=[(21, 5), (0, 1), (22, 17), (10, 10)])
    assert w2.slip_probability == 0.5 and w2.stops[3] == (10, 10)
    with pytest.raises(AttributeError):
        load_world(not_a_param=1)


def test_ucs_known_costs(w):
    for stop, c in zip(w.stops, (26, 22, 42, 26)):
        assert run(ucs, DeliveryProblem(w, w.start, [stop]), measure_memory=False).cost == c


def test_astar_equals_ucs(w):
    for flood in (0, 15):
        p = full_problem(w, flood_left=flood)
        a = run(astar, p, make_heuristic("tunnel_mst", p), measure_memory=False)
        u = run(ucs, p, measure_memory=False)
        assert a.cost == u.cost and a.expanded < u.expanded
        assert p.path_cost(a.path) == a.cost


def test_uninformed_agree_on_depth(w):
    p = DeliveryProblem(w, w.start, [w.stops[1]])
    b = run(bfs, p, measure_memory=False)
    i = run(ids, p, measure_memory=False)
    d = run(dls, p, len(b.actions), measure_memory=False)
    assert len(i.actions) == len(b.actions) == len(d.actions)
    assert not run(dls, p, len(b.actions) - 1, measure_memory=False).success


def test_heuristic_admissible_sampled(w):
    rng = np.random.default_rng(1)
    free = [tuple(map(int, c)) for c in np.argwhere(w.grid >= 0)]
    for _ in range(25):
        pos = free[int(rng.integers(len(free)))]
        mask = int(rng.integers(0, 15))
        p = DeliveryProblem(w, pos, w.stops, done_mask=mask)
        hstar = run(ucs, p, measure_memory=False).cost
        assert make_heuristic("tunnel_mst", p)(p.initial()) <= hstar + 1e-9


def test_heuristic_consistent_everywhere(w):
    p = full_problem(w)
    h = make_heuristic("tunnel_mst", p)
    for r in range(w.n):
        for c in range(w.n):
            if w.grid[r, c] < 0:
                continue
            for m in range(16):
                s = ((r, c), m, 0)
                for _, s2, cost in p.successors(s):
                    assert h(s) <= cost + h(s2) + 1e-9


def test_alphabeta_equals_minimax(w):
    ev = Evaluator(w)
    s = initial_state(w)
    states = [s]
    for a in ("W", "W", "N"):
        s = apply_rival(w, apply_agent(w, s, a), "N")
        states.append(s)
    for s in states:
        for depth in (2, 3, 4):
            for maxi in (True, False):
                win = (s.agent, 3)
                m = minimax(w, s, depth, maxi, ev, win)
                for order in (False, True):
                    ab = alphabeta(w, s, depth, -INF, INF, maxi, ev, win, ordering=order)
                    assert abs(m - ab) < 1e-9


def test_agent_cannot_enter_rival_cell(w):
    s = initial_state(w)._replace(rival=(8, 8))
    assert "E" not in agent_actions(w, s)


def test_simulator_reproducible(w):
    a = Simulator(load_world(), agent="planner", seed=3).run()
    b = Simulator(load_world(), agent="planner", seed=3).run()
    assert a == b


def test_scenario_seeded(w):
    assert scenario(w, 4) == scenario(w, 4) and scenario(w, 4) != scenario(w, 5)


def test_stats():
    ci = wilson(15, 30)
    assert ci["lo"] < 0.5 < ci["hi"]
    m = mean_ci([1, 2, 3])
    assert m["mean"] == 2 and m["lo"] < 2 < m["hi"]
