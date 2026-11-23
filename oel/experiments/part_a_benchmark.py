"""Part A: vectorised vs pure-Python cost-map benchmark."""
import os, sys, timeit, json
import numpy as np
import matplotlib; matplotlib.use("Agg")
import matplotlib.pyplot as plt

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
from src.world import load_world, build_cost_vectorised, build_cost_loop, STAMP  # noqa: E402

OUT = os.path.join(ROOT, "results")


def bench(grid, tc, reps=20):
    g_list = grid.tolist()
    t_vec = min(timeit.repeat(lambda: build_cost_vectorised(grid, tc), number=reps, repeat=5)) / reps
    t_loop = min(timeit.repeat(lambda: build_cost_loop(g_list, tc), number=reps, repeat=5)) / reps
    assert np.array_equal(build_cost_vectorised(grid, tc), np.array(build_cost_loop(g_list, tc)))
    return t_vec, t_loop


def main():
    w = load_world()
    tc = w.inst["terrain_cost"]
    rows = []
    # own 23x23 grid, then the same grid tiled up to show how the gap scales
    for k in (1, 2, 4, 8, 16):
        g = np.tile(w.grid, (k, k))
        t_vec, t_loop = bench(g, tc, reps=max(1, 20 // k))
        rows.append({"size": g.shape[0], "vec_ms": t_vec * 1e3, "loop_ms": t_loop * 1e3,
                     "speedup": t_loop / t_vec})

    print(STAMP)
    print(f"{'grid':>8} {'vectorised ms':>14} {'loop ms':>10} {'speed-up':>9}")
    for r in rows:
        print(f"{r['size']:>4}x{r['size']:<3} {r['vec_ms']:>14.4f} {r['loop_ms']:>10.3f} {r['speedup']:>8.1f}x")

    with open(os.path.join(OUT, "part_a_benchmark.json"), "w") as f:
        json.dump({"stamp": STAMP, "rows": rows}, f, indent=2)

    fig, ax = plt.subplots(figsize=(7, 4.5))
    s = [r["size"] for r in rows]
    ax.plot(s, [r["loop_ms"] for r in rows], "o-", label="pure-Python loop")
    ax.plot(s, [r["vec_ms"] for r in rows], "s-", label="NumPy vectorised")
    ax.set_xscale("log"); ax.set_yscale("log")
    ax.set_xlabel("grid side (cells)"); ax.set_ylabel("time per build (ms)")
    ax.set_title(f"Cost-map build time, instance {w.inst['instance_id']}")
    ax.legend(); ax.grid(alpha=.3)
    fig.text(0.5, 0.01, STAMP, ha="center", fontsize=8)
    fig.tight_layout(rect=(0, 0.04, 1, 1))
    fig.savefig(os.path.join(OUT, "part_a_benchmark.png"), dpi=130)


if __name__ == "__main__":
    main()
