"""Part B: compare BFS / UCS / DLS / IDS / Greedy / A* and the heuristics.

Outputs
  results/part_b_search.json   all tables below
  results/part_b_algorithms.png, part_b_heuristics.png, part_b_memory.png
Tables
  1. algorithms on 1-stop variants (all six algorithms, IDS is exponential beyond ~12 steps)
  2. algorithms on the full 4-stop tour (DLS/IDS excluded: did not finish, see note)
  3. heuristics with A* and Greedy, full tour, with and without an active flood
  4. admissibility: h(s) <= h*(s) on sampled states (h* from UCS)
  5. inadmissible variants: cost gap
  6. memory limit: A* with a capped frontier+closed vs IDS
"""
from __future__ import annotations
import os, sys

import numpy as np

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
from src.world import load_world, STAMP  # noqa: E402
from src.problem import DeliveryProblem, full_problem  # noqa: E402
from src.search import run, bfs, ucs, dls, ids, greedy, astar  # noqa: E402
from src.heuristics import make_heuristic, HEURISTICS  # noqa: E402
from src.stats import seed_for  # noqa: E402
from experiments.common import save_json, save_fig, print_table, plt  # noqa: E402

COLS = ["problem", "algorithm", "success", "cost", "steps", "expanded", "max_stored",
        "peak_mem_kb", "time_ms", "note"]


def all_algorithms(p, label, ids_cap=3_000_000):
    h = make_heuristic("tunnel_mst", p)
    depth = len(run(bfs, p, measure_memory=False).actions)   # DLS limit = shallowest depth
    rows = []
    for name, fn, args, kw in [
        ("BFS", bfs, (), {}), ("UCS", ucs, (), {}),
        (f"DLS(l={depth})", dls, (depth,), {}),
        ("IDS", ids, (), {"max_expansions": ids_cap}),
        ("Greedy", greedy, (h,), {}), ("A*", astar, (h,), {})]:
        r = run(fn, p, *args, **kw)
        d = r.summary(); d["algorithm"] = name; d["problem"] = label
        rows.append(d)
    return rows


def admissibility(w, n_samples=150):
    """Sample random states (pos, mask) and compare h with the true optimal cost h* (UCS)."""
    rng = np.random.default_rng(seed_for("admissible", w.inst["instance_id"]))
    free = [tuple(map(int, c)) for c in np.argwhere(w.grid >= 0)]
    names = ["tunnel_mst", "mst_plain", "nearest", "farthest", "sum_dstar"]
    stats = {n: {"over": 0, "max_ratio": 0.0, "sum_ratio": 0.0} for n in names}
    done = 0
    while done < n_samples:
        pos = free[int(rng.integers(len(free)))]
        mask = int(rng.integers(0, 15))
        p = DeliveryProblem(w, pos, w.stops, done_mask=mask)
        hstar = run(ucs, p, measure_memory=False).cost
        if not np.isfinite(hstar) or hstar == 0:
            continue
        s = p.initial()
        for n in names:
            hv = make_heuristic(n, p)(s)
            st = stats[n]
            st["over"] += hv > hstar + 1e-9
            st["max_ratio"] = max(st["max_ratio"], hv / hstar)
            st["sum_ratio"] += hv / hstar
        done += 1
    rows = [{"heuristic": n, "samples": n_samples, "h>h*": st["over"],
             "max h/h*": round(st["max_ratio"], 3), "mean h/h*": round(st["sum_ratio"] / n_samples, 3)}
            for n, st in stats.items()]
    return rows


def memory_limit(w):
    """A* stores frontier+closed; IDS stores only the current path and its successor lists."""
    rows = []
    for label, stops in [("depot->S2", [w.stops[1]]), ("depot->S4", [w.stops[3]])]:
        p = DeliveryProblem(w, w.start, stops)
        h = make_heuristic("tunnel_mst", p)
        for cap in [25, 50, 100, 200, 400, 800]:
            ra = run(astar, p, h, max_nodes=cap, measure_memory=False)
            ri = run(ids, p, max_nodes=cap, max_expansions=3_000_000)
            rows.append({"problem": label, "node cap": cap,
                         "A* ok": ra.success, "A* cost": ra.cost, "A* stored": ra.max_stored,
                         "IDS ok": ri.success, "IDS cost": ri.cost, "IDS stored": ri.max_stored,
                         "IDS expanded": ri.expanded, "IDS ms": round(ri.time * 1e3, 1)})
    # full tour: A* needs a few thousand nodes
    p = full_problem(w)
    h = make_heuristic("tunnel_mst", p)
    for cap in [1000, 2000, 4000, 10000]:
        ra = run(astar, p, h, max_nodes=cap, measure_memory=False)
        rows.append({"problem": "full tour", "node cap": cap, "A* ok": ra.success,
                     "A* cost": ra.cost, "A* stored": ra.max_stored, "IDS ok": "n/a",
                     "IDS cost": "", "IDS stored": "", "IDS expanded": "", "IDS ms": ""})
    return rows


def main():
    print(STAMP)
    w = load_world()
    out = {"instance": w.inst["instance_id"]}

    # 1. all algorithms on 1-stop variants -------------------------------------------
    t1 = []
    for i in (1, 3, 0):                     # S2, S4, S1 (increasing depth)
        p = DeliveryProblem(w, w.start, [w.stops[i]])
        t1 += all_algorithms(p, f"depot->S{i + 1}")
    print_table(t1, COLS, "Table B1: all algorithms, 1-stop variants")
    out["algorithms_one_stop"] = t1

    # 2. full tour ------------------------------------------------------------------
    p = full_problem(w)
    h = make_heuristic("tunnel_mst", p)
    t2 = []
    for name, fn, args in [("BFS", bfs, ()), ("UCS", ucs, ()),
                           ("Greedy", greedy, (h,)), ("A*", astar, (h,))]:
        d = run(fn, p, *args).summary(); d["algorithm"] = name; d["problem"] = "full tour"
        t2.append(d)
    r = run(ids, p, max_expansions=500_000)
    d = r.summary(); d["problem"] = "full tour"; t2.append(d)
    print_table(t2, COLS, "Table B2: full 4-stop tour (IDS capped at 500k expansions)")
    out["algorithms_full"] = t2

    # 3. heuristics -----------------------------------------------------------------
    t3 = []
    for flood in (0, w.flood_duration):
        p = full_problem(w, flood_left=flood)
        for hn in HEURISTICS:
            h = make_heuristic(hn, p)
            ra = run(astar, p, h, check_consistency=True)
            rg = run(greedy, p, make_heuristic(hn, p))
            t3.append({"flood_left": flood, "heuristic": hn, "h(start)": h(p.initial()),
                       "A* cost": ra.cost, "A* expanded": ra.expanded,
                       "A* ms": round(ra.time * 1e3, 1), "A* peak kb": round(ra.peak_mem / 1024, 1),
                       "consistency viol.": ra.consistency_violations,
                       "edges checked": ra.consistency_checks,
                       "Greedy cost": rg.cost, "Greedy expanded": rg.expanded})
    print_table(t3, list(t3[0]), "Table B3: heuristics (A* and Greedy), full tour")
    out["heuristics"] = t3

    # 4. admissibility --------------------------------------------------------------
    t4 = admissibility(w)
    print_table(t4, list(t4[0]), "Table B4: admissibility on sampled states (h* by UCS)")
    out["admissibility"] = t4

    # 5. inadmissible but faster -------------------------------------------------------
    p = full_problem(w)
    opt = run(astar, p, make_heuristic("tunnel_mst", p))
    t5 = [{"variant": "A* + tunnel_mst (optimal)", "cost": opt.cost, "expanded": opt.expanded,
           "time_ms": round(opt.time * 1e3, 1), "gap": 0.0, "gap %": 0.0}]
    for label, r in [("A* + sum_dstar", run(astar, p, make_heuristic("sum_dstar", p))),
                     ("WA* w=2 + tunnel_mst", run(astar, p, make_heuristic("tunnel_mst", p), 2.0)),
                     ("WA* w=3 + tunnel_mst", run(astar, p, make_heuristic("tunnel_mst", p), 3.0)),
                     ("Greedy + tunnel_mst", run(greedy, p, make_heuristic("tunnel_mst", p)))]:
        t5.append({"variant": label, "cost": r.cost, "expanded": r.expanded,
                   "time_ms": round(r.time * 1e3, 1), "gap": r.cost - opt.cost,
                   "gap %": round(100 * (r.cost - opt.cost) / opt.cost, 1)})
    print_table(t5, list(t5[0]), "Table B5: inadmissible / faster variants")
    out["inadmissible"] = t5

    # 6. memory limit ---------------------------------------------------------------
    t6 = memory_limit(w)
    print_table(t6, list(t6[0]), "Table B6: memory limit (stored-node cap)")
    out["memory_limit"] = t6

    out["notes"] = [
        "DLS limit = BFS depth of that variant. IDS/DLS revisit check: candidate vs states on the current path.",
        "IDS on the full tour (61 actions deep) is exponential in depth and is stopped at 500k expansions.",
        "Manhattan baselines and mst_plain ignore tunnels and can overestimate (see Table B4).",
    ]
    save_json("part_b_search.json", out)

    # figures -------------------------------------------------------------------------
    fig, axes = plt.subplots(1, 3, figsize=(13, 4))
    sub = [r for r in t1 if r["problem"] == "depot->S4"]
    names = [r["algorithm"] for r in sub]
    for ax, key, lab in zip(axes, ["expanded", "time_ms", "peak_mem_kb"],
                            ["nodes expanded (log)", "runtime ms (log)", "peak memory KB (log)"]):
        ax.bar(names, [max(r[key], 1e-3) for r in sub], color="#4a7ab8")
        ax.set_yscale("log"); ax.set_title(lab); ax.tick_params(axis="x", rotation=35)
    fig.suptitle(f"Part B: algorithms on depot->S4 (instance {w.inst['instance_id']})")
    save_fig(fig, "part_b_algorithms.png")

    fig, axes = plt.subplots(1, 2, figsize=(11, 4))
    sub = [r for r in t3 if r["flood_left"] == 0]
    hn = [r["heuristic"] for r in sub]
    axes[0].bar(hn, [r["A* expanded"] for r in sub], color="#5a9e6f")
    axes[0].set_title("A* nodes expanded, full tour"); axes[0].tick_params(axis="x", rotation=30)
    axes[1].bar(hn, [r["A* cost"] for r in sub], color="#c77d3a")
    axes[1].axhline(opt.cost, ls="--", c="k", lw=1, label=f"optimal {opt.cost:g}")
    axes[1].set_ylim(opt.cost * 0.9, max(r["A* cost"] for r in sub) * 1.03)
    axes[1].set_title("A* solution cost"); axes[1].legend(); axes[1].tick_params(axis="x", rotation=30)
    save_fig(fig, "part_b_heuristics.png")

    fig, ax = plt.subplots(figsize=(7, 4))
    sub = [r for r in t6 if r["problem"] == "depot->S4"]
    caps = [r["node cap"] for r in sub]
    ax.plot(caps, [int(r["A* ok"]) for r in sub], "o-", label="A* succeeds")
    ax.plot(caps, [int(r["IDS ok"]) + 0.03 for r in sub], "s--", label="IDS succeeds")
    ax.set_xscale("log"); ax.set_yticks([0, 1], ["fail", "ok"])
    ax.set_xlabel("stored-node cap"); ax.set_title("Memory limit, depot->S4"); ax.legend()
    save_fig(fig, "part_b_memory.png")


if __name__ == "__main__":
    main()
