"""Reproduces every table and figure in the report.

Usage:  python run_all.py            # everything (~8-10 min on a laptop)
        python run_all.py b c        # only some parts (a, b, c, d, e, report)
"""
import importlib, os, sys, time
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from src.world import STAMP

STEPS = [
    "experiments.part_a_benchmark",
    "experiments.part_b_search",
    "experiments.part_c_rival",       # must run before part E (writes the tuned weights)
    "experiments.part_d_llm",         # replays results/llm_cache.json; live calls need ANTHROPIC_API_KEY
    "experiments.part_e_scenarios",
    "experiments.make_report_tables",
]

if __name__ == "__main__":
    os.chdir(os.path.dirname(os.path.abspath(__file__)))
    os.makedirs("results", exist_ok=True)
    print(STAMP)
    want = [a.lower() for a in sys.argv[1:]]
    for mod in STEPS:
        tag = mod.split(".")[1].split("_")[1] if "part_" in mod else "report"
        if want and tag not in want:
            continue
        print(f"\n=== {mod} ===", flush=True)
        t0 = time.time()
        importlib.import_module(mod).main()
        print(f"--- {mod} done in {time.time() - t0:.0f}s", flush=True)
