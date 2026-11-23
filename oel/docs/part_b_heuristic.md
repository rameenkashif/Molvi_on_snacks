# Part B — Search formulation and our heuristic `h_tunnel_mst`

Rameen Kashif (456834) | Manal Aslam (465734) | Zainab Ali Bangash (486688)

## 1. Search problem (`src/problem.py`)
| Element | Definition |
|---|---|
| State | `(pos, done_mask, flood_left)`. `done_mask` has bit *i* set when stop *i* is delivered **or stolen**. `flood_left` is the number of flooded steps still to come (0 = fords open). Time only matters while the fords are flooded, so a countdown replaces the raw time step: at most 529 × 16 × (F+1) states. |
| Initial state | `(depot, 0, 0)` for the full tour; any `(pos, mask, flood_left)` when replanning. |
| Actions | N, S, E, W (cost = terrain cost of the cell entered: road 1, grass 2, mud 3, ford 8); `TUNNEL` on a mouth (cost 1, to the paired mouth); `WAIT` (cost 1, only generated while flooded, and not on a flooded ford). |
| Transition | Entering an undelivered stop delivers it. While `flood_left > 0` fords cannot be entered (S3 is a ford, so it cannot be delivered either); the tunnel mouth (0,5) is a ford, so that tunnel is closed during a flood. Each action decrements `flood_left`. |
| Goal | `done_mask == 1111₂`. |
| Constraints (Part D) | `avoid_terrain` (treated as walls), `blocked_cells` (rival cell), `order` (required delivery prefix). |

Planners assume deterministic moves and a passive rival; the simulator adds slip and the rival and the agent replans.

## 2. The heuristic

Let `c_min = 1` (road) and `M(a,b) = |Δr| + |Δc|`.

**Relaxed distance d\*.** Build a tiny complete graph on the stops and the six tunnel mouths.
Every pair gets an edge of weight `M(a,b)·c_min`; each tunnel pair additionally gets an edge of
weight 1. Floyd–Warshall gives all-pairs distances `D`. For any cell *p*,
`d*(p, x) = min( M(p,x)·c_min , min over mouths m of M(p,m)·c_min + D(m,x) )`.

**Heuristic.** With *R* the set of remaining stops,

    h(pos, mask) = min_{x ∈ R} d*(pos, x)  +  MST_{d*}(R)        (0 if R is empty)

i.e. the cheapest relaxed way to reach the first remaining stop plus a minimum spanning tree
that connects all remaining stops. It is cached per `(pos, mask)`.

### Why not the MST over {pos} ∪ R?
That was our first design. It is admissible, but we tested consistency on **every edge of the
state space** and found **674 violations**: removing a point of degree 2 from an MST can make the
tree *shorter* by more than the step cost (e.g. three points on a line). Attaching `pos` by its
single cheapest edge fixes this and is never weaker, because `MST({pos} ∪ R) ≤ min d*(pos,R) + MST(R)`.

## 3. Proof of admissibility

1. **d\* never overestimates the true cost between two cells.** Any real path of *k* moves
   costs at least `k·c_min` (every terrain costs ≥ c_min), and a path without tunnel jumps
   between *a* and *b* needs at least `M(a,b)` moves. A real path that uses tunnels splits into
   walking segments (each ≥ M·c_min) and jumps (each costs exactly 1). The relaxed graph contains
   an edge for every such segment and every jump, so the relaxed shortest path is ≤ the real
   cost. Walls, terrain above c_min, flooding, the rival and the delivery order only add cost or
   remove options, so ignoring them is a relaxation.
2. **The remaining route contains a spanning structure.** Any real route from *pos* that
   delivers every stop in *R* first reaches some stop `x₁ ∈ R` (cost ≥ `d*(pos, x₁)` ≥ `min_x d*(pos,x)`)
   and then visits the remaining stops in some order `x₁, x₂, …, x_k`; the legs `x_i → x_{i+1}`
   form a spanning path of *R*, whose cost under d\* is ≥ `MST_{d*}(R)` and, by (1), ≤ the
   real cost of those legs.
3. Adding the two parts: `h(s) ≤ h*(s)`. ∎

### Consistency (proof sketch, plus exhaustive check)
For a step `s → s'` with cost *c*:
* **No delivery** (R unchanged). Each `d*(·, x)` is 1-Lipschitz w.r.t. the step cost: a move
  changes Manhattan distance by 1 ≤ c, and a tunnel jump from mouth *m* has
  `d*(m,x) ≤ 1 + d*(m', x)` through the tunnel edge. A minimum of such functions is also
  Lipschitz, and `MST(R)` does not change, so `h(s) ≤ c + h(s')`.
* **Delivery of y ∈ R** (`pos' = y`, `R' = R \ {y}`). The tree `MST(R') + edge(y, nearest in R')`
  spans *R*, so `h(s') ≥ MST(R)`; and `h(s) ≤ d*(pos, y) + MST(R) ≤ c + MST(R) ≤ c + h(s')`.

**Empirical check:** `tests/test_core.py::test_heuristic_consistent_everywhere` evaluates
`h(s) ≤ c(s,s') + h(s')` on **all** 418 free cells × 16 masks × every successor: 0 violations.
A\* also counts violations on every expanded edge (Table B3: 0 for `tunnel_mst`).

## 4. Baselines and variants (Table B3/B4, `results/part_b_search.json`)
| Heuristic | Definition | Admissible on our map? |
|---|---|---|
| `nearest` | `min_x M(pos,x)·c_min` | **No** — a tunnel jump (cost 1) can beat Manhattan; A\* returned 116 instead of 111 |
| `farthest` | `max_x M(pos,x)·c_min` | **No**, same reason |
| `mst_plain` (ablation) | our heuristic **without tunnel edges** | **No**: 116 instead of 111 — the tunnel component is what makes the heuristic correct, not only faster |
| `sum_dstar` (inadmissible variant) | `Σ_x d*(pos,x)` | No (counts shared legs repeatedly); 113 vs 111 |
| `tunnel_mst` (ours) | above | **Yes, and consistent** |

The handout's suggested Manhattan baselines silently become inadmissible once tunnels exist;
this is the main reason our heuristic has to model the tunnels.
