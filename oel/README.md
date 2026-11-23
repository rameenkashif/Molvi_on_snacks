# CS-370 OEL — Autonomous Delivery Agent (instance 6a18af32)

Rameen Kashif (456834) | Manal Aslam (465734) | Zainab Ali Bangash (486688)

23×23 grid city, depot (8,7), stops S1 (21,5), S2 (0,1), S3 (22,17), S4 (15,18); blocker rival
(depth 5), slip 0.12. Twists: **teleport tunnels**, **rival steals parcels**, and our approved
third twist **rival-triggered flooding** (the blocker can open a dam once; fords are closed for
F = 15 steps; S3 is itself a ford). Full spec: `CLAUDE.md`, handout: `docs/OEL_handout.pdf`.

## Setup
Python 3.11+.
```bash
python -m venv .venv
source .venv/bin/activate            # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

## Run
```bash
python -m src.world                  # sanity check: stamp, stops, tunnels, rival start
pytest -q                            # 16 tests: tunnels, flood window, A* == UCS, admissible, consistent, AB == Minimax
python run_all.py                    # every table and figure -> results/ (about 8-10 minutes)
python run_all.py b                  # just one part: a, b, c, d, e or report
streamlit run app.py                 # UI
```
Part D (LLM dispatcher) replays `results/llm_cache.json`. To make the live calls once:
```bash
export ANTHROPIC_API_KEY=...         # optional: export OEL_MODEL=claude-haiku-5-5 (default)
python run_all.py d
```

## Live parameter changes (viva)
Everything is overridable without editing code:
```python
from src.world import load_world
w = load_world(slip_probability=0.5, flood_duration=25, steal_enabled=False,
               dam_enabled=False, rival_depth=3, rival_start=(3, 20),
               delivery_stops=[(21, 5), (0, 1), (22, 17), (10, 10)])
```
The Streamlit sidebar exposes the same parameters (slip, F, twist flags, rival depth,
scenario, edit a stop) plus the algorithm, heuristic and agent policy.

## Layout
```
oel_instance.py          instructor generator (unchanged)
src/world.py             instance loader, cost map, tunnels, flooding, overrides, STAMP
src/problem.py           Part B search problem: state (pos, done_mask, flood_left)
src/search.py            BFS, UCS, DLS, IDS, Greedy, A*, weighted A* (from scratch)
src/heuristics.py        tunnel_mst (ours), mst_plain (ablation), nearest, farthest, sum_dstar
src/game.py              reduced game, Minimax, Alpha-Beta, move ordering, evaluation function
src/rival.py             blocker rival (Alpha-Beta, depth 5, OPEN_DAM)
src/simulator.py         slip, turn order, steals, dam, replanning, seeded scenarios
src/llm_agent.py         Claude dispatcher: tools, validation layer, ReAct loop, response cache
src/stats.py             mean ± 95% t-CI, Wilson CI, seeds from the instance hash
experiments/part_*.py    one script per part, each main() writes stamped results/*.json + *.png
experiments/llm_requests.json   20 dispatcher requests with machine-checkable success criteria
app.py                   Streamlit UI
docs/                    PEAS (A), heuristic proof (B), evaluation function (C), LLM (D), ethics, report/
tests/                   pytest
```

## Status
- [x] Part A: world model, vectorised cost map + benchmark, PEAS, environment classification
- [x] Part B: BFS / UCS / DLS / IDS / Greedy / A*, admissible + consistent `tunnel_mst`, baselines, inadmissible variants, memory limit
- [x] Part C: Minimax / Alpha-Beta with move ordering vs blocker, evaluation function + grid-search tuning, 30 games, slip/replanning study
- [x] Part D: Claude dispatcher with 4 tools + validation layer, 20 requests, direct-planner baseline (LLM runs need one keyed run to fill the cache)
- [x] Part E: Streamlit UI, 30 scenarios × configurations, flood sweep, heuristic ablation, failure analysis, ethics
- [ ] IEEE report: draft in `docs/report/report.tex` (tables auto-generated into `docs/report/tables.tex`) — finish the prose and compile
