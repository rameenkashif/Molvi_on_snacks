# Part C — Reduced game, move ordering and evaluation function

Rameen Kashif (456834) | Manal Aslam (465734) | Zainab Ali Bangash (486688)

Code: `src/game.py` (rules, Minimax, Alpha-Beta, ordering, evaluation), `src/rival.py`
(blocker), `src/simulator.py` (slip, turn order, replanning). Numbers: `results/part_c_rival.json`.

## 1. Reduced game
* **Players.** MAX = delivery agent, MIN = blocker rival; one round = agent ply then rival ply.
* **Window.** The agent's moves inside the search are restricted to the 7×7 window (radius 3)
  around its cell at the root (a tunnel jump may leave it). The rival moves on the full grid.
* **Rival actions.** N/S/E/W, WAIT, and **OPEN_DAM** (once per episode: fords closed for F moves).
  Entering an undelivered stop **steals** it. Neither player can enter the other's cell (blocking).
* **Leaves** are scored with the evaluation function below; search assumes moves never slip.
* **Depth.** The rival searches 5 plies (instance depth). The agent uses 3 plies.
* **When is the game played?** The agent is a hybrid: it follows its A\* plan while the rival is
  outside the window (Chebyshev distance > 4) and switches to Alpha-Beta when the rival is
  inside. Playing the game on every move was no better and much slower: with the rival far
  away, a 3-ply horizon cannot see any interaction, only noise.

## 2. Move ordering (ours)
* **Agent (MAX):** children sorted by `cost so far + remaining tour cost` (ascending) — the move
  that keeps the best tour cheapest is searched first, which tightens α early.
* **Rival (MIN):** `OPEN_DAM` first if the agent's next stop (nearest remaining by true cost)
  needs a ford; then moves sorted by the rival's step distance to the agent's next stop
  (blocking/stealing moves first); `OPEN_DAM` last otherwise.
* Result (Table C1): at depth 5 the ordering raises pruning from ≈82 % to ≈91 % of Minimax nodes.
  Values are identical to Minimax at every depth (`tests/test_core.py::test_alphabeta_equals_minimax`).
  Why ordering saves *less* than the ideal `b^{d/2}`: many children have **equal** values
  (WAIT vs. a move that changes nothing in the evaluation, symmetric rival moves), so the
  "best first" child is often tied with later ones and does not produce a cut-off.

## 3. Evaluation function (agent's point of view, zero-sum)
`eval = w1·f1 + w2·f2 + w3·f3 + w4·f4 + w5·f5`

| Feature | Definition | Why it is there |
|---|---|---|
| f1 tour | −(cost paid so far + **exact static cost of the best remaining tour**: min over the ≤24 orders of the remaining stops, using our Dijkstra maps) | The primary objective: total path cost. It must be *exact* on the static map: with the admissible MST lower bound, g+h rises by more than 1 along the optimal route, WAIT (+1) always looked best and the agent stalled. |
| f2 score | delivered − stolen | The outcome measure (win = delivered > stolen). Large weight so that a theft or a delivery dominates any path-cost difference. |
| f3 race | mean over remaining stops of clip(rival steps − agent steps, −10, 10) | Stealing is a race: positive = the agent gets there first. Agent steps include tunnels, the blocker cannot use them. Using only the "next" stop made the feature jump when the nearest stop changed (another stall); the mean changes by ≤ 1 per move. |
| f4 ford | −(#remaining ford-dependent stops) × (1 if dam unused + fraction of flood remaining) | Our third twist. A stop is ford-dependent if it cannot be reached as cheaply without fords from the depot and every other stop (S2 and S3 on our map; S3 is itself a ford). Rewards finishing those stops before the dam is used. It depends only on which stops remain — a per-cell version flipped between neighbouring cells and caused stalls. |
| f5 mobility | number of unblocked moves from the agent's cell | A blocker wins by trapping the agent in corridors; low mobility is an early warning. |

Default weights: `tour 1, score 40, race 2, ford 6, mobility 0.25`.

## 4. Weight tuning
`experiments/part_c_rival.py::tune` grid-searches race ∈ {0, 2, 5}, ford ∈ {0, 6, 15},
mobility ∈ {0, 0.25} (18 combinations) on 12 scenarios with reduced depths (agent 2, rival 3),
scoring `mean(delivered − stolen) − 0.002·mean(cost)`. The rival always keeps the default
weights, so only the agent changes. The best weights are stored in
`results/part_c_rival.json["tuned_weights"]` and reused in Part E.

## 5. Slip and replanning
The simulator slips a move with p = 0.12 to a random perpendicular neighbour (stay if closed).
The planner agent replans after every slip, when the dam opens, when the flood ends, when a
stop is stolen and when the rival blocks its next cell. Table C4 reports replans and extra cost
versus the deterministic plan (111) for p ∈ {0, 0.12, 0.3, 0.5}.

**What the deterministic assumption gets wrong.**
1. Plan cost is a lower bound: each slip costs the step it wasted plus the detour back, so the
   realised cost grows roughly linearly with p (Table C4), and every slip invalidates the plan.
2. Timing: Minimax/Alpha-Beta assume the agent arrives at a ford or stop exactly when planned;
   a slip delays it by ≥ 2 steps, which is enough for the blocker to win a race the search
   believed was won, or for the dam to open while the agent is still on the wrong side.
3. Fords are the worst place to slip: they cost 8, and S3 sits on one. A plan that is optimal
   under determinism can be a poor bet under slip + flooding (flood-aware planner, Part E).
4. At p = 0.5 half the moves go sideways, episodes need about 2× the steps, some hit the
   200-step cap, and the blocker has far more time to steal.
