"""Part E: 30 seeded scenarios per configuration, ablation and failure analysis.

Scenario i is seeded from sha256("scenario|<instance_id>|<i>") (src/simulator.scenario):
it fixes the rival's start cell and the slip draws. Every configuration sees the same 30
scenarios, so differences come from the configuration, not the luck of the draw.

Outputs results/part_e_scenarios.json, part_e_configs.png, part_e_flood.png, part_e_ablation.png
"""
from __future__ import annotations
import json, os, sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
from src.world import load_world, STAMP  # noqa: E402
from src.problem import DeliveryProblem  # noqa: E402
from src.search import run, astar  # noqa: E402
from src.heuristics import make_heuristic  # noqa: E402
from src.simulator import Simulator, scenario  # noqa: E402
from src.game import DEFAULT_WEIGHTS  # noqa: E402
from src.stats import mean_ci, wilson  # noqa: E402
from experiments.common import save_json, save_fig, print_table, plt, OUT  # noqa: E402

N = 30


def tuned_weights() -> dict:
    path = os.path.join(OUT, "part_c_rival.json")
    if os.path.exists(path):
        return json.load(open(path)).get("tuned_weights", DEFAULT_WEIGHTS)
    return dict(DEFAULT_WEIGHTS)


def episodes(agent, weights=None, **world_overrides):
    res = []
    for i in range(N):
        w = load_world(**world_overrides)
        sc = scenario(w, i)
        w.rival_start = sc["rival_start"]
        flood_aware = agent == "planner_flood_aware"
        sim = Simulator(w, agent="planner" if flood_aware else agent, seed=sc["sim_seed"],
                        weights=weights, flood_aware=flood_aware)
        r = sim.run()
        r.update({"scenario": i, "rival_start": sc["rival_start"], "events": sim.log.events,
                  "flood_duration": w.flood_duration})
        res.append(r)
    return res


def summary(label, res):
    n = len(res)
    row = {"config": label}
    wins = wilson(sum(r["outcome"] == "win" for r in res), n)
    loss = wilson(sum(r["outcome"] == "loss" for r in res), n)
    row["win rate"] = f"{wins['p']:.2f} [{wins['lo']:.2f},{wins['hi']:.2f}]"
    row["loss rate"] = f"{loss['p']:.2f} [{loss['lo']:.2f},{loss['hi']:.2f}]"
    for k in ("delivered", "stolen", "cost", "steps", "replans"):
        ci = mean_ci([r[k] for r in res])
        row[k] = f"{ci['mean']:.2f} ± {ci['half']:.2f}"
    row["dam used"] = sum(r["dam_time"] is not None for r in res)
    return row


def ablation():
    """Our heuristic with and without its tunnel component, on 30 random stop sets."""
    rows, raw = [], {}
    for name in ("tunnel_mst", "mst_plain", "nearest", "zero"):
        exp, cost, ms, gap = [], [], [], []
        for i in range(N):
            w = load_world()
            sc = scenario(w, i, vary_stops=True)
            p = DeliveryProblem(w, w.start, sc["stops"])
            r = run(astar, p, make_heuristic(name, p), measure_memory=False)
            opt = run(astar, p, make_heuristic("zero", p), measure_memory=False).cost if name != "zero" else r.cost
            exp.append(r.expanded); cost.append(r.cost); ms.append(r.time * 1e3); gap.append(r.cost - opt)
        raw[name] = {"expanded": exp, "gap": gap}
        e, c, t = mean_ci(exp), mean_ci(cost), mean_ci(ms)
        rows.append({"heuristic": name, "A* expanded": f"{e['mean']:.0f} ± {e['half']:.0f}",
                     "cost": f"{c['mean']:.1f} ± {c['half']:.1f}",
                     "time ms": f"{t['mean']:.1f} ± {t['half']:.1f}",
                     "suboptimal runs": sum(g > 1e-9 for g in gap),
                     "mean gap": round(sum(gap) / N, 2)})
    return rows, raw


def failure_analysis(res):
    rows = []
    for r in res:
        if r["outcome"] != "loss":
            continue
        steals = [(t, e) for t, e in r["events"] if "stole" in e]
        dam = r["dam_time"]
        F = r.get("flood_duration", 15)
        flood_steal = dam is not None and any(dam <= t < dam + F + 1 for t, _ in steals)
        if flood_steal:
            cause = "a parcel was stolen while the flood cut the agent off"
        elif steals and steals[0][0] <= 10:
            cause = f"rival started next to a stop (first theft at t={steals[0][0]})"
        elif not r["finished"]:
            cause = "step cap reached (stand-off: the blocker guards a stop or corridor)"
        elif r["slips"] >= 10:
            cause = "many slips lost the race to the stops"
        else:
            cause = "rival won the race to the contested stops"
        steals = [f"t={t} {e}" for t, e in steals]
        rows.append({"scenario": r["scenario"], "rival start": r["rival_start"],
                     "delivered": r["delivered"], "stolen": r["stolen"], "slips": r["slips"],
                     "dam t": dam, "steals": "; ".join(steals), "cause": cause})
    return rows


def main():
    print(STAMP)
    wt = tuned_weights()
    configs = {
        "A* planner (naive)": episodes("planner"),
        "A* planner (flood-aware)": episodes("planner_flood_aware"),
        "Alpha-Beta agent (tuned)": episodes("alphabeta", wt),
        "Alpha-Beta, rival has no dam": episodes("alphabeta", wt, dam_enabled=False),
        "Alpha-Beta, no stealing": episodes("alphabeta", wt, steal_enabled=False),
    }
    e1 = [summary(k, v) for k, v in configs.items()]
    print_table(e1, list(e1[0]), f"Table E1: {N} scenarios per configuration (mean ± 95% CI, Wilson for rates)")

    flood = {}
    for F in (0, 10, 15, 25):
        flood[F] = episodes("alphabeta", wt, flood_duration=F)
    e2 = [summary(f"flood_duration={F}", v) for F, v in flood.items()]
    print_table(e2, list(e2[0]), "Table E2: flood duration sweep (Alpha-Beta agent)")

    e3, raw = ablation()
    print_table(e3, list(e3[0]), f"Table E3: heuristic ablation, A* on {N} random stop sets")

    e4 = failure_analysis(configs["Alpha-Beta agent (tuned)"])
    print_table(e4, list(e4[0]) if e4 else ["scenario"], "Table E4: failure analysis (losses of the tuned Alpha-Beta agent)")

    strip = lambda d: {k: [{kk: vv for kk, vv in r.items() if kk != "events"} for r in v] for k, v in d.items()}
    save_json("part_e_scenarios.json", {"configs": e1, "flood_sweep": e2, "ablation": e3,
                                        "failures": e4, "weights": wt, "raw": strip(configs),
                                        "raw_flood": strip({str(k): v for k, v in flood.items()})})

    fig, axes = plt.subplots(1, 2, figsize=(12, 4.2))
    labels = list(configs)
    for ax, key in zip(axes, ("delivered", "stolen")):
        cis = [mean_ci([r[key] for r in configs[k]]) for k in labels]
        ax.barh(labels, [c["mean"] for c in cis], xerr=[c["half"] for c in cis], color="#4a7ab8", capsize=3)
        ax.set_title(f"parcels {key} (mean, 95% CI)"); ax.set_xlim(0, 4)
    axes[1].set_yticklabels([])
    save_fig(fig, "part_e_configs.png")

    fig, ax = plt.subplots(figsize=(7, 4))
    Fs = list(flood)
    for key, mk in (("delivered", "o-"), ("stolen", "s--")):
        cis = [mean_ci([r[key] for r in flood[F]]) for F in Fs]
        ax.errorbar(Fs, [c["mean"] for c in cis], yerr=[c["half"] for c in cis], fmt=mk, capsize=3, label=key)
    ax.set_xlabel("flood duration F (steps)"); ax.set_ylabel("parcels"); ax.legend()
    ax.set_title("Effect of the rival-triggered flood")
    save_fig(fig, "part_e_flood.png")

    fig, ax = plt.subplots(figsize=(7, 4))
    ax.boxplot([raw[k]["expanded"] for k in raw], tick_labels=list(raw))
    ax.set_ylabel("A* nodes expanded"); ax.set_title(f"Heuristic ablation ({N} random stop sets)")
    save_fig(fig, "part_e_ablation.png")


if __name__ == "__main__":
    main()
