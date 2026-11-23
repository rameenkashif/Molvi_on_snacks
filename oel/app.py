"""Part E: Streamlit UI.  Run:  streamlit run app.py

Shows the grid (terrain, fords, tunnels, stops, depot), the planned route, the agent, the
rival and the flood state. The sidebar changes every viva parameter live.
"""
from __future__ import annotations

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
import streamlit as st  # noqa: E402
from matplotlib.colors import ListedColormap  # noqa: E402

from src.world import load_world, STAMP, TERRAINS  # noqa: E402
from src.problem import DeliveryProblem  # noqa: E402
from src.search import solve, ALGORITHMS  # noqa: E402
from src.heuristics import make_heuristic, HEURISTICS  # noqa: E402
from src.simulator import Simulator, scenario  # noqa: E402

st.set_page_config(page_title="CS-370 OEL delivery agent", layout="wide")
st.markdown(f"#### {STAMP}")
st.title("Autonomous Delivery Agent — instance 6a18af32")

base = load_world()

# ---------------------------------------------------------------- sidebar
sb = st.sidebar
sb.header("Planner")
algorithm = sb.selectbox("Algorithm", ALGORITHMS, index=ALGORITHMS.index("astar"))
heuristic = sb.selectbox("Heuristic", list(HEURISTICS), index=0)
agent = sb.selectbox("Agent policy", ["planner", "alphabeta"], index=1)
agent_depth = sb.slider("Agent search depth (alphabeta)", 1, 5, 3)
flood_aware = sb.checkbox("Flood-aware planner (avoid fords while dam unused)", False)

sb.header("World / twists")
slip = sb.slider("Slip probability", 0.0, 0.6, float(base.slip_probability), 0.01)
flood_duration = sb.slider("Flood duration F", 0, 40, base.flood_duration)
flood_enabled = sb.checkbox("Flooding twist", True)
dam_enabled = sb.checkbox("Rival may open the dam", True)
steal_enabled = sb.checkbox("Rival steals parcels", True)
rival_on = sb.checkbox("Rival active", True)
rival_depth = sb.slider("Rival search depth", 1, 6, base.rival_depth)
scen = sb.number_input("Scenario (rival start + slip seed); -1 = default", -1, 999, -1)

sb.header("Edit a stop")
stops = list(base.stops)
which = sb.selectbox("Stop", [f"S{i + 1}" for i in range(len(stops))])
k = int(which[1:]) - 1
r_ = sb.number_input("row", 0, base.n - 1, stops[k][0], key=f"r{k}")
c_ = sb.number_input("col", 0, base.n - 1, stops[k][1], key=f"c{k}")
stops[k] = (int(r_), int(c_))

params = dict(slip_probability=slip, flood_duration=flood_duration, flood_enabled=flood_enabled,
              dam_enabled=dam_enabled, steal_enabled=steal_enabled, rival_depth=rival_depth,
              delivery_stops=stops)
key = (tuple(sorted((k2, str(v)) for k2, v in params.items())), algorithm, heuristic, agent,
       agent_depth, flood_aware, rival_on, scen)


def build():
    try:
        w = load_world(**params)
    except ValueError as e:
        st.error(f"Invalid stop: {e}")
        st.stop()
    seed = 7
    if scen >= 0:
        sc = scenario(w, int(scen))
        w.rival_start, seed = sc["rival_start"], sc["sim_seed"]
    sim = Simulator(w, agent=agent, seed=seed, rival=rival_on, agent_depth=agent_depth,
                    heuristic=heuristic, flood_aware=flood_aware)
    return w, sim


if st.session_state.get("key") != key:
    st.session_state.key = key
    st.session_state.w, st.session_state.sim = build()
    st.session_state.route = None
    st.session_state.search = None
w, sim = st.session_state.w, st.session_state.sim

# ---------------------------------------------------------------- buttons
b1, b2, b3, b4 = st.columns(4)
if b1.button("Plan route"):
    s = sim.s
    p = DeliveryProblem(w, s.agent, w.stops, done_mask=s.delivered | s.stolen, flood_left=s.flood_left)
    res = solve(p, algorithm, make_heuristic(heuristic, p), measure_memory=True)
    st.session_state.search = res
    st.session_state.route = [x[0] for x in res.path] if res.success else None
if b2.button("Step"):
    if agent == "planner" and not sim.plan:
        sim.make_plan()
    sim.step()
if b3.button("Run episode"):
    if agent == "planner" and not sim.plan:
        sim.make_plan()
    while sim.step():
        pass
if b4.button("Reset"):
    st.session_state.w, st.session_state.sim = build()
    st.session_state.route = None
    w, sim = st.session_state.w, st.session_state.sim

# ---------------------------------------------------------------- drawing
s = sim.s


def draw():
    colours = ["#f2f2f2", "#b7dd9a", "#b48a5a", "#7fb2e5"]        # road grass mud ford
    img = np.where(w.grid < 0, 4, w.grid)
    cmap = ListedColormap(colours + ["#333333"])
    fig, ax = plt.subplots(figsize=(7.2, 7.2))
    show = img.copy()
    if s.flood_left > 0:
        cmap = ListedColormap(colours + ["#333333", "#1f4e9c"])
        show = np.where(w.grid == 3, 5, img)
    ax.imshow(show, cmap=cmap, vmin=0, vmax=cmap.N - 1)
    for a, b in {tuple(sorted(x)) for x in w.tunnels.items()}:
        ax.plot([a[1], b[1]], [a[0], b[0]], ":", c="purple", lw=1)
        for m in (a, b):
            ax.scatter(m[1], m[0], marker="o", s=90, facecolors="none", edgecolors="purple", lw=2)
    route = st.session_state.route
    if route:
        ax.plot([c for _, c in route], [r for r, _ in route], "-", c="#e07b00", lw=2, alpha=.8, label="planned route")
    if sim.log.plans:
        cells = sim.log.plans[-1][1]
        ax.plot([c for _, c in cells], [r for r, _ in cells], "--", c="#ff3d7f", lw=1.3, label="agent's current plan")
    trail = [x.agent for x in sim.log.states]
    ax.plot([c for _, c in trail], [r for r, _ in trail], "-", c="k", lw=1, alpha=.5, label="agent trail")
    for i, stp in enumerate(w.stops):
        col = "green" if s.delivered >> i & 1 else "red" if s.stolen >> i & 1 else "gold"
        ax.scatter(stp[1], stp[0], marker="*", s=320, c=col, edgecolors="k", zorder=5)
        ax.text(stp[1] + .4, stp[0] - .4, f"S{i + 1}", fontsize=9, weight="bold")
    ax.scatter(w.start[1], w.start[0], marker="s", s=130, c="white", edgecolors="k", zorder=5)
    ax.text(w.start[1] + .4, w.start[0] - .4, "depot", fontsize=8)
    ax.scatter(s.agent[1], s.agent[0], s=160, c="#1565c0", edgecolors="white", zorder=6, label="agent")
    if sim.rival:
        ax.scatter(s.rival[1], s.rival[0], s=160, marker="X", c="#c62828", edgecolors="white", zorder=6, label="rival")
    ax.set_xticks(range(0, w.n, 2)); ax.set_yticks(range(0, w.n, 2))
    ax.legend(loc="upper center", bbox_to_anchor=(0.5, -0.04), ncol=3, fontsize=8)
    fig.text(0.5, 0.005, STAMP, ha="center", fontsize=7)
    fig.tight_layout(rect=(0, 0.02, 1, 1))
    return fig


left, right = st.columns([3, 2])
left.pyplot(draw())
with right:
    st.subheader("State")
    names = lambda m: ", ".join(f"S{i + 1}" for i in range(len(w.stops)) if m >> i & 1) or "—"
    st.write(f"**t** = {s.t}   **cost** = {s.cost:g}")
    st.write(f"**delivered:** {names(s.delivered)}   **stolen:** {names(s.stolen)}")
    st.write(f"**dam used:** {s.dam_used}   **flood steps left:** {s.flood_left}")
    st.write(f"agent {s.agent}  rival {s.rival}")
    if sim.done():
        r = sim.result()
        st.success(f"Episode over: {r['outcome'].upper()} — delivered {r['delivered']}, stolen {r['stolen']}, "
                   f"cost {r['cost']:g}, slips {r['slips']}, replans {r['replans']}")
    res = st.session_state.search
    if res is not None:
        st.subheader("Last search")
        st.json(res.summary())
    st.subheader("Events")
    st.text("\n".join(f"t={t}: {e}" for t, e in sim.log.events[-20:]) or "—")
    st.caption("Terrain: road (light), grass (green), mud (brown), ford (blue, dark blue when flooded), "
               "blocked (black). Purple circles = tunnel mouths.")
st.caption(STAMP)
