"""Part C: game search vs the blocker rival.

Outputs results/part_c_rival.json and part_c_nodes.png, part_c_games.png, part_c_slip.png
  C1 node counts, Minimax vs Alpha-Beta (with / without our move ordering), depths 2..5
  C2 weight tuning: grid search over game outcomes (reduced depth for speed)
  C3 30 games vs the blocker (rival depth 5): Alpha-Beta agent vs planner agent, Wilson CIs
  C4 slip and replanning: planner agent, no rival, slip p in {0, 0.12, 0.3, 0.5}
"""
from __future__ import annotations
import itertools, os, sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
from src.world import load_world, STAMP  # noqa: E402
from src.game import Evaluator, best_action, DEFAULT_WEIGHTS  # noqa: E402
from src.simulator import Simulator, scenario  # noqa: E402
from src.stats import mean_ci, wilson  # noqa: E402
from experiments.common import save_json, save_fig, print_table, plt  # noqa: E402

N_GAMES = 30


def sample_positions(w, n=8):
    """Positions taken from a planner episode, so they are realistic mid-game states."""
    sim = Simulator(w, agent="planner", seed=1)
    sim.run()
    states = sim.log.states
    step = max(1, len(states) // n)
    return states[::step][:n]


def node_counts(w, ev):
    rows = []
    positions = sample_positions(w)
    for depth in range(2, w.rival_depth + 1):
        for root, maxi in (("agent (MAX)", True), ("rival (MIN)", False)):
            tot = {"minimax": 0, "ab_plain": 0, "ab_ordered": 0}
            same = True
            for s in positions:
                _, vm, nm = best_action(w, s, depth, maxi, ev, method="minimax")
                _, va, na = best_action(w, s, depth, maxi, ev, ordering=False)
                _, vo, no = best_action(w, s, depth, maxi, ev, ordering=True)
                same &= abs(vm - va) < 1e-9 and abs(vm - vo) < 1e-9
                tot["minimax"] += nm; tot["ab_plain"] += na; tot["ab_ordered"] += no
            k = len(positions)
            rows.append({"depth": depth, "root": root, "minimax": round(tot["minimax"] / k),
                         "AB (no order)": round(tot["ab_plain"] / k),
                         "AB (our order)": round(tot["ab_ordered"] / k),
                         "saved % (no order)": round(100 * (1 - tot["ab_plain"] / tot["minimax"]), 1),
                         "saved % (our order)": round(100 * (1 - tot["ab_ordered"] / tot["minimax"]), 1),
                         "same value": same})
    return rows


def play(w, i, agent, weights=None, agent_depth=3, rival_depth=None, **kw):
    sc = scenario(w, i)
    w.rival_start = sc["rival_start"]
    sim = Simulator(w, agent=agent, seed=sc["sim_seed"], weights=weights,
                    agent_depth=agent_depth, rival_depth=rival_depth, **kw)
    r = sim.run()
    r["scenario"] = i
    r["rival_start"] = sc["rival_start"]
    return r


def summarise(results, label):
    n = len(results)
    k = {o: sum(r["outcome"] == o for r in results) for o in ("win", "draw", "loss")}
    row = {"config": label, "games": n}
    for o in ("win", "draw", "loss"):
        ci = wilson(k[o], n)
        row[o] = f"{ci['p']:.2f} [{ci['lo']:.2f}, {ci['hi']:.2f}]"
    for key in ("delivered", "stolen", "cost", "steps"):
        ci = mean_ci([r[key] for r in results])
        row[key] = f"{ci['mean']:.1f} ± {ci['half']:.1f}"
    return row


def tune(w):
    """Grid search over the race and ford weights (others fixed), on 12 scenarios with
    reduced depths (agent 2, rival 3) so the whole grid runs in about a minute.
    Score = mean(delivered - stolen) - 0.002 * mean(cost) (tie-break on cost)."""
    rows = []
    for race, ford, mob in itertools.product([0.0, 2.0, 5.0], [0.0, 6.0, 15.0], [0.0, 0.25]):
        wt = dict(DEFAULT_WEIGHTS, race=race, ford=ford, mobility=mob)
        res = [play(w, 1000 + i, "alphabeta", wt, agent_depth=2, rival_depth=3) for i in range(12)]
        margin = sum(r["delivered"] - r["stolen"] for r in res) / len(res)
        cost = sum(r["cost"] for r in res) / len(res)
        rows.append({"race": race, "ford": ford, "mobility": mob, "margin": round(margin, 3),
                     "wins": sum(r["outcome"] == "win" for r in res), "mean cost": round(cost, 1),
                     "score": round(margin - 0.002 * cost, 4)})
    rows.sort(key=lambda r: -r["score"])
    return rows


def slip_study(w):
    rows, raw = [], []
    base = Simulator(w, agent="planner", rival=False, seed=0)
    base.make_plan()
    det = base.log.planned_cost
    for p in (0.0, 0.12, 0.3, 0.5):
        w.slip_probability = p
        res = []
        for i in range(N_GAMES):
            sim = Simulator(w, agent="planner", rival=False, seed=scenario(w, i)["sim_seed"])
            res.append(sim.run())
        extra = mean_ci([r["cost"] - det for r in res])
        rep = mean_ci([r["replans"] for r in res])
        rows.append({"slip p": p, "replans": f"{rep['mean']:.1f} ± {rep['half']:.1f}",
                     "slips": round(sum(r["slips"] for r in res) / N_GAMES, 1),
                     "extra cost": f"{extra['mean']:.1f} ± {extra['half']:.1f}",
                     "extra %": round(100 * extra["mean"] / det, 1),
                     "steps": round(sum(r["steps"] for r in res) / N_GAMES, 1),
                     "finished": sum(r["finished"] for r in res)})
        raw.append({"p": p, "extra": [r["cost"] - det for r in res], "replans": [r["replans"] for r in res]})
    w.slip_probability = float(w.inst["slip_probability"])
    return rows, raw, det


def main():
    print(STAMP)
    w = load_world()
    ev = Evaluator(w)
    out = {"instance": w.inst["instance_id"]}

    c1 = node_counts(w, ev)
    print_table(c1, list(c1[0]), "Table C1: nodes per decision (mean over 8 positions)")
    out["node_counts"] = c1

    c2 = tune(w)
    print_table(c2[:8], list(c2[0]), "Table C2: weight grid search (top 8 of 18)")
    out["tuning"] = c2
    best = dict(DEFAULT_WEIGHTS, race=c2[0]["race"], ford=c2[0]["ford"], mobility=c2[0]["mobility"])
    out["tuned_weights"] = best
    print("tuned weights:", best)

    games = {
        "Alpha-Beta agent (d=3), tuned": [play(w, i, "alphabeta", best) for i in range(N_GAMES)],
        "Alpha-Beta agent (d=3), default": [play(w, i, "alphabeta", None) for i in range(N_GAMES)],
        "A* planner agent": [play(w, i, "planner", best) for i in range(N_GAMES)],
    }
    w.rival_start = load_world().rival_start
    c3 = [summarise(r, k) for k, r in games.items()]
    print_table(c3, list(c3[0]), f"Table C3: {N_GAMES} games vs blocker (rival depth {w.rival_depth}), Wilson 95% CI")
    out["games_summary"] = c3
    out["games"] = {k: v for k, v in games.items()}

    c4, raw, det = slip_study(w)
    print_table(c4, list(c4[0]), f"Table C4: slip and replanning, planner agent, no rival (deterministic plan {det:g})")
    out["slip"] = c4
    out["deterministic_plan_cost"] = det
    save_json("part_c_rival.json", out)

    # figures
    fig, ax = plt.subplots(figsize=(7, 4.2))
    for key, mk in (("minimax", "o-"), ("AB (no order)", "s--"), ("AB (our order)", "^-")):
        sub = [r for r in c1 if r["root"] == "rival (MIN)"]
        ax.plot([r["depth"] for r in sub], [r[key] for r in sub], mk, label=key)
    ax.set_yscale("log"); ax.set_xlabel("search depth (plies)"); ax.set_ylabel("nodes per decision")
    ax.set_title("Rival decision: Minimax vs Alpha-Beta"); ax.legend()
    save_fig(fig, "part_c_nodes.png")

    fig, ax = plt.subplots(figsize=(8, 4))
    labels = list(games)
    bottoms = [0] * len(labels)
    for o, col in (("win", "#4c9a5b"), ("draw", "#c9b458"), ("loss", "#c0504d")):
        vals = [sum(r["outcome"] == o for r in games[k]) / N_GAMES for k in labels]
        ax.barh(labels, vals, left=bottoms, color=col, label=o)
        bottoms = [b + v for b, v in zip(bottoms, vals)]
    ax.set_xlim(0, 1); ax.set_xlabel("fraction of games"); ax.legend(loc="lower right")
    ax.set_title(f"{N_GAMES} games vs blocker rival (depth {w.rival_depth})")
    save_fig(fig, "part_c_games.png")

    fig, ax = plt.subplots(figsize=(7, 4))
    ax.boxplot([r["extra"] for r in raw], tick_labels=[str(r["p"]) for r in raw])
    ax.set_xlabel("slip probability"); ax.set_ylabel("extra cost vs deterministic plan")
    ax.set_title("Cost of slipping (planner agent, replans after each slip)")
    save_fig(fig, "part_c_slip.png")


if __name__ == "__main__":
    main()
