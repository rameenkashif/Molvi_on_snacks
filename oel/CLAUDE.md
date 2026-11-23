# CLAUDE.md — CS-370 OEL: Autonomous Delivery Agent (instance 6a18af32)

Handoff for Claude Code. Read this whole file before writing code. The full handout is
`docs/OEL_handout.pdf`; the approved 3rd-twist proposal is `docs/third_twist_proposal_APPROVED.pdf`.

## 1. Group and the stamp rule (non-negotiable)
| Member | CMS ID |
|---|---|
| Rameen Kashif | 456834 |
| Manal Aslam | 465734 |
| Zainab Ali Bangash | 486688 |

**Every plot, table, console log, UI screen and report figure must show the stamp**
`Rameen Kashif (456834) | Manal Aslam (465734) | Zainab Ali Bangash (486688)`.
Use `from src.world import STAMP`. Unstamped output is not marked. Print it first in every
console script, put it in every figure footer (`fig.text(0.5, 0.01, STAMP, ...)`), store it in
every results JSON, and show it at the top of the Streamlit app.

## 2. Hard rules from the handout
- BFS, UCS, DLS, IDS, Greedy, A*, Minimax, Alpha-Beta are written **from scratch**. Never use
  networkx shortest paths, simpleai, AIMA, gym solvers or minimax packages. (networkx drawing only is OK.)
- Instance generation stays in the instructor's `oel_instance.py` — **do not modify it**.
- All numbers must be reproducible from the CMS IDs: seed every RNG from them (see `src/world.py`).
- `python run_all.py` must regenerate every table and figure in the report.
- At the viva the instructor changes one parameter live (slip, a stop, a twist flag, flood duration)
  and we must rerun within ~5 min → every parameter must be overridable via `load_world(**overrides)`
  and the Streamlit sidebar. Never hard-code instance values outside `src/world.py`.
- Each member must be able to explain every line → keep code simple, commented, no clever tricks.

## 3. Our instance (generated, do not hand-edit)
`python oel_instance.py 456834 465734 486688` →
- Grid 23×23, obstacle density 0.24 (111 blocked). Terrain codes 0..3 = road 1, grass 2, mud 3, ford 8; -1 = blocked.
- Depot (8,7). Stops: S1 (21,5), S2 (0,1), S3 (22,17), S4 (15,18). Coordinates are (row, col).
- Rival: **blocker**, search depth **5**. Slip probability **0.12**.
- Assigned twists: **teleport_tunnels**, **rival_steals_parcels**.
- Approved 3rd twist: **rival-triggered flooding**.

Facts already verified (UCS from depot, no flood): S1 26, S2 22, S3 42, S4 26.
**S3 (22,17) is itself a ford cell**, so it is undeliverable while the fords are flooded.

## 4. Twist specifications (implement exactly this)
**Teleport tunnels** (generator does not place them; we do, seeded from instance hash in `make_tunnels`):
pairs (0,5)↔(9,2), (12,0)↔(13,10), (12,4)↔(12,17). Standing on a mouth, action `TUNNEL` jumps to the
pair for cost 1. Bidirectional. Already in `World.neighbours`.

**Rival steals parcels:** if the rival steps onto an undelivered stop before the agent, that parcel is
stolen (permanently lost). Stolen stops are removed from the agent's goal. `World.steal_enabled` flag.

**Rival-triggered flooding (approved):** the blocker has **one dam charge per episode**. On its turn it may
play `OPEN_DAM` instead of moving. Fords are impassable for t ∈ [flood_start, flood_start + flood_duration),
default `flood_duration = 15`, then return to cost 8. An agent standing on a ford when the dam opens gets
one move to leave. Dam state (used?, steps remaining) is visible to the agent. Implemented in
`World.open_dam / flooded / passable`. `World.flood_enabled` flag.

**Slip:** in the simulator only. With p = slip_probability, the agent's move goes to a random perpendicular
neighbour instead (if that is blocked, the agent stays put). Tunnel jumps and waits do not slip.
Planners (Part B) and game search (Part C) assume deterministic moves.

**Turn order (simulator):** agent acts → slip resolved → deliveries checked → rival acts → steals checked →
t += 1. Rival occupies a cell; the agent cannot enter the rival's cell (that is how blocking works).

## 5. Current state of the repo
**Update:** Parts B–E are implemented (see README "Status"). Deviations from §7, all documented
in docs/: `h_tunnel_mst` = min d*(pos, R) + MST(R) (MST over {pos}∪R was inconsistent); the
evaluation's f1 uses the exact static remaining tour, f3 is the mean race margin over remaining
stops, f4 counts remaining ford-dependent stops (per-cell versions caused stalls); the game
agent is a hybrid (A* plan while the rival is outside the window, Alpha-Beta inside); the rival
keeps default weights while the agent is tuned. Part D needs one keyed run to fill the cache.

Done (Part A):
- `src/world.py` — `World` dataclass, `load_world(**overrides)`, vectorised `build_cost_vectorised`,
  pure-Python `build_cost_loop`, `make_tunnels`, flood logic, `STAMP`, `MEMBERS`.
- `experiments/part_a_benchmark.py` — vectorised vs loop speed-up (7.3× at 23×23, ~45× at 184×184).
- `docs/part_a_analysis.md` — PEAS, environment classification, agent type. Already uses the approved twist.
- `run_all.py` — imports each `experiments.*` module and calls `main()`. Uncomment entries as parts land.
- `results/` — instance_map.png, part_a_benchmark.{json,png}.

## 6. Target layout
```
src/world.py          (exists) world model + twists
src/search.py         BFS, UCS, DLS, IDS, Greedy, A*  + SearchResult(path, cost, expanded, peak_mem, time)
src/problem.py        DeliveryProblem: state, successors, goal test, step cost
src/heuristics.py     our heuristic + baselines + inadmissible variant
src/simulator.py      step the world: slip, rival turn, steals, dam, replanning hooks
src/game.py           reduced game, Minimax, Alpha-Beta (+ move ordering), evaluation function
src/rival.py          blocker policy (uses game.py at depth 5)
src/llm_agent.py      Claude dispatcher, tools, validation layer, trace logging
src/stats.py          mean ± 95% CI (t-dist), Wilson CI for win rates
experiments/part_{a,b,c,d,e}_*.py   each exposes main(), writes stamped results/*.json and *.png
app.py                Streamlit UI
docs/report/          IEEE report notes / figures index
```

## 7. Work plan with acceptance criteria

### Part B — Route planning (`src/problem.py`, `src/search.py`, `src/heuristics.py`)
- **State:** `(pos, done_mask, flood_left)` where `done_mask` is a 4-bit int of stops delivered *or stolen*,
  `flood_left` = remaining flooded steps (0 if no flood). Time only matters while flooded, so cap it this way
  instead of carrying raw t (keeps the state space small). Hashable tuple.
- **Actions:** N/S/E/W, TUNNEL (if on a mouth), WAIT (cost 1; only useful while flooded).
  Delivery is automatic on entering an undelivered stop.
- **Goal:** done_mask == all stops.
- Implement BFS, UCS, DLS(limit), IDS, Greedy, A* — all against the same `Problem` interface.
  Return expanded nodes, solution cost, runtime (`time.perf_counter`), peak memory (`tracemalloc`).
- **Our heuristic (`h_tunnel_mst`):** precompute relaxed distances d*(a,b) between depot, stops and tunnel
  mouths as Dijkstra on a tiny graph whose edges are Manhattan×c_min between any two points plus cost-1 tunnel
  edges. h = MST weight over {current pos} ∪ {remaining stops} using d*. Admissible because (1) d* ≤ true
  cost (relaxation: ignores walls, terrain above c_min, flooding), (2) any route visiting all remaining stops
  contains a spanning tree, so MST ≤ remaining cost. Write this proof in `docs/part_b_heuristic.md`.
  Test consistency empirically: for every expanded edge check h(s) ≤ c(s,s') + h(s'); report violations (expect 0).
- **Baselines:** (1) Manhattan to nearest remaining stop × c_min, (2) Manhattan to farthest remaining stop × c_min.
- **Inadmissible variant:** sum of d* to every remaining stop (or weighted A*, w=2). Show it is faster and
  returns a worse plan; report the cost gap.
- **IDS under memory limit:** IDS keeps only the current path (O(bd)); avoid revisits by checking the
  candidate state against the set of states on the current path. Compare peak memory and success vs A* with a
  capped frontier/closed set (e.g. limit 10k nodes → A* fails, IDS still finishes but slower).
- `experiments/part_b_search.py` → table: algorithm × {nodes expanded, runtime, peak mem, cost}; figure bars.
- Note: full-tour BFS/IDS may be slow; it is fine to run them on reduced variants (2–3 stops) and say so.

### Part C — Rival (`src/game.py`, `src/rival.py`, `src/simulator.py`)
- **Reduced game:** local window of radius 3 (7×7) around the agent, containing both agents if within range,
  plus the dam action. Alternate MAX (agent) / MIN (rival). Rival moves: 4 moves, WAIT, OPEN_DAM (once).
- Minimax, then Alpha-Beta with **our move ordering** (try moves that reduce d* to the nearest stop first; for
  rival, try OPEN_DAM first when the agent's next stop needs a ford, then moves toward the agent's next stop).
- Node counts for depths 2..5; % saved by pruning = 1 − AB/Minimax.
- **Evaluation function (≥4 weighted features, justify each in `docs/part_c_eval.md`):**
  f1 −(remaining tour lower bound h_tunnel_mst), f2 (delivered − stolen), f3 race margin = rival's distance to
  agent's next stop − agent's distance, f4 −(ford dependence of the remaining route × dam unused),
  f5 agent mobility (unblocked moves). Tune weights by a small grid search over game outcomes.
- Simulator applies slip; agent replans after every slip and when the dam opens. Report replan count,
  extra cost vs the deterministic plan, and what the deterministic assumption gets wrong.
- **30+ games** vs blocker: win = delivered > stolen, draw = equal, loss otherwise; step cap 200.
  Report rates with Wilson 95% CI.

### Part D — LLM dispatcher (`src/llm_agent.py`)
- Anthropic Python SDK (`anthropic`), key from env `ANTHROPIC_API_KEY`, model from env `OEL_MODEL`
  (default `claude-haiku-5-5` for cost). Native tool use, manual ReAct loop.
- Tools: `plan_route(algorithm, heuristic, stop_order?, avoid_terrain?)` → calls Part B;
  `simulate(steps)` → steps the world; `flood_status()` → dam used?, steps remaining, which stops/route
  segments need fords (custom tool tied to our twist). Optional `tunnel_info()`.
- 20 dispatcher requests of increasing difficulty in `experiments/llm_requests.json`
  (e.g. "deliver S3 first", "avoid mud", "finish before the rival can flood the fords", "cost under 120").
- Compare LLM vs calling the planner directly: success rate, cost, number of tool calls. Log every wrong
  tool, invented argument, ignored constraint.
- **Validation layer:** before executing a tool call, check algorithm/heuristic names, stop ids exist,
  coordinates in bounds and passable, constraints feasible; on failure return an error observation so the
  model retries. Report results with and without validation.
- Save Thought/Action/Observation traces to `results/llm_traces/`; map ≥2 to Sense–Reason–Act.
- **Cache every API response** (`results/llm_cache.json`, keyed by request + config) so `run_all.py`
  reproduces Part D without an API key or cost.

### Part E — UI, experiments, report
- `streamlit run app.py`: grid with terrain colours, tunnels, stops, depot, planned route, rival position,
  flood state; sidebar: algorithm, heuristic, slip, flood_duration, twist flags, edit a stop; buttons
  plan / step / run episode. STAMP at the top of the page.
- 30 scenarios per configuration, seeded `sha256("scenario|<instance_id>|<i>")`; vary rival start and
  slip draws (and optionally stop positions among free cells). Mean ± 95% CI.
- Ablation: `h_tunnel_mst` without the tunnel edges (plain MST on Manhattan×c_min).
- Failure analysis: list scenarios where the agent loses, with the cause.
- Half-page ethics & reflection.
- Report: 8–10 pages, IEEE format (LaTeX IEEEtran or Word template).

## 8. Conventions
- Python 3.11+, type hints, docstrings on every public function. No global state except constants in world.py.
- Coordinates are always `(row, col)` tuples of Python ints.
- Each experiment script: `main()` prints STAMP first, saves `results/<part>_<name>.json` (with `"stamp"` key)
  and stamped PNGs; runs headless (`matplotlib.use("Agg")`).
- Seeds: derive from `inst["instance_id"]` / CMS IDs via sha256 — never `random.seed(0)`.
- Tests in `tests/` with pytest: tunnels symmetric, flood window, A* cost == UCS cost, heuristic admissible
  (h ≤ UCS cost from sampled states), consistency, Alpha-Beta value == Minimax value.
- After finishing each part: add it to `run_all.py`, tick it in README, run `python run_all.py`.

## 9. Commands
```bash
pip install -r requirements.txt
python oel_instance.py 456834 465734 486688   # regenerate instance (prints JSON, saves grid .npy)
python -m src.world                           # sanity check: stamp, stops, tunnels
python run_all.py                             # all tables and figures → results/
streamlit run app.py
pytest -q
```

## 10. Start here
Begin with Part B: write `src/problem.py` and `src/search.py` (UCS first, verify depot→stop costs match §3),
then `src/heuristics.py`, then `experiments/part_b_search.py`. Work iteratively and show results after each step.
