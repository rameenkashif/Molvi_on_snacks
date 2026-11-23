# Part A — Agent Formalisation (instance 6a18af32)

Rameen Kashif (456834) | Manal Aslam (465734) | Zainab Ali Bangash (486688)

## Instance summary
23×23 grid, 24% blocked. Terrain costs: road 1, grass 2, mud 3, ford 8. Depot (8,7).
Stops S1 (21,5), S2 (0,1), S3 (22,17), S4 (15,18). Rival: **blocker**, search depth 5.
Slip probability 0.12. Twists: **teleport tunnels**, **rival steals parcels**; proposed 3rd twist: **rival-triggered flooding** (blocker opens a dam once; fords impassable for 15 steps).

Tunnels (seeded from the instance hash, cost 1 per jump): (0,5)↔(9,2), (12,0)↔(13,10), (12,4)↔(12,17).

## PEAS
| | |
|---|---|
| **Performance** | Parcels delivered (stolen parcels count as failures), total path cost, steps taken, number of replans; penalty for ending with undelivered parcels. |
| **Environment** | 23×23 grid with 4 terrain types and blocked cells; 3 teleport-tunnel pairs; 4 delivery stops; a blocker rival that moves to obstruct cells and steals any parcel whose stop it reaches first; a dam the rival can open once to flood all fords for 15 steps. |
| **Actuators** | Move N/S/E/W (slips with p = 0.12 to a random perpendicular neighbour); enter a tunnel; deliver at a stop; wait. |
| **Sensors** | Own position, full map and terrain, tunnel locations, rival position, set of delivered and stolen parcels, current time step, dam status (used or not, flood steps remaining). |

## Environment classification
| Property | Answer | Justification |
|---|---|---|
| Observable | **Fully** | The whole map, tunnel pairs and rival position are visible (no fog twist). The rival's *intention* is not observable, but its state is. |
| Deterministic | **Stochastic** | Moves slip with p = 0.12, and the rival's choices are outside the agent's control. |
| Episodic | **Sequential** | Which stops are already delivered or stolen, and whether the dam has been used, depend on every earlier move. |
| Static | **Dynamic** | The rival moves and steals while the agent plans; the rival can flood the fords, so legal moves and costs change over time. |
| Discrete | **Discrete** | Finite cells, four moves plus tunnel jumps, integer time steps. |
| Agents | **Multi-agent, competitive** | The blocker rival actively works against the agent (blocking cells, stealing parcels). |

## Agent type
A **utility-based** agent fits. A goal-based agent only asks "are all parcels delivered?", but here the agent must trade off path cost against the risk of a parcel being stolen and the risk of the rival flooding the fords, so it needs a numeric utility over outcomes, not a yes/no goal.

A **simple reflex agent fails** because:
1. It has no memory, so it cannot track which parcels are delivered or stolen, which is part of the state.
2. Tunnels make good moves non-local: the best first step can be *away* from a stop, toward a tunnel mouth, which a percept→action rule cannot see.
3. The rival and flooding make the environment change over time, so the agent has to look ahead and replan, not just react to the current cell.
