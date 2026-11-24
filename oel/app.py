"""Part E: Streamlit UI.  Run:  streamlit run app.py

Tab 1 "Game map": pixel-art view of the city (terrain, tunnels, stops, depot), the planned
route, the agent, the rival and the flood; Plan / Step / Run episode / Reset.
Tab 2 "AI dispatcher": type a request in plain English; Claude plans it by calling our
tools (Part D). Needs ANTHROPIC_API_KEY, or replays cached answers from results/llm_cache.json.
The sidebar changes every viva parameter live and applies to both tabs.
"""
from __future__ import annotations
import json, os

import matplotlib
matplotlib.use("Agg")
import streamlit as st  # noqa: E402

from src.world import load_world, STAMP, ROOT  # noqa: E402
from src.problem import DeliveryProblem  # noqa: E402
from src.search import solve, ALGORITHMS  # noqa: E402
from src.heuristics import make_heuristic, HEURISTICS  # noqa: E402
from src.simulator import Simulator, scenario  # noqa: E402
from src.game import initial_state  # noqa: E402
from src.pixel_map import draw_map, sprite_image  # noqa: E402
from src.llm_agent import run_request, make_client, NoCachedResponse, DEFAULT_MODEL  # noqa: E402

st.set_page_config(page_title="CS-370 OEL delivery agent", layout="wide", page_icon="🚚")

# ---------------------------------------------------------------- game styling
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Press+Start+2P&display=swap');
.pixel-title {font-family:'Press Start 2P', monospace; font-size:34px; line-height:1.4;
  text-shadow: 4px 4px 0 #1b1b1f; letter-spacing:2px; margin:0.2rem 0 0.4rem 0;}
.pixel-sub {font-family:'Press Start 2P', monospace; font-size:11px; color:#2f7d32;}
.stamp {font-family:'Press Start 2P', monospace; font-size:10px; background:#1b1b1f;
  color:#f7e26b; padding:8px 10px; border:3px solid #6abe30; display:inline-block;}
.panel {font-family:'Press Start 2P', monospace; font-size:10px; line-height:2;
  background:#e9e5dc; border:4px solid #8d8d8d; box-shadow:4px 4px 0 #1b1b1f;
  padding:12px 14px; margin-bottom:12px; color:#1b1b1f;}
.panel b {color:#c62828;}
div.stButton > button {font-family:'Press Start 2P', monospace; font-size:10px;
  background:#6abe30; color:white; border:3px solid #1b1b1f; border-radius:0;
  box-shadow:3px 3px 0 #1b1b1f;}
div.stButton > button:hover {background:#4e9a22; color:#f7e26b; border-color:#1b1b1f;}
</style>""", unsafe_allow_html=True)

COLS = ["#e23b3b", "#c8b88a", "#f2c94c", "#5fa8a0"]
title = "DELIVERY QUEST"
letters = "".join(f'<span style="color:{COLS[i % 4]}">{ch}</span>' for i, ch in enumerate(title))
st.markdown(f'<div class="stamp">{STAMP}</div>', unsafe_allow_html=True)
st.markdown(f'<div class="pixel-title">{letters}</div>'
            '<div class="pixel-sub">CS-370 OEL · instance 6a18af32 · courier vs. blocker</div>',
            unsafe_allow_html=True)

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
    st.session_state.llm = None
w, sim = st.session_state.w, st.session_state.sim


def legend():
    items = [("Courier (agent)", sprite_image("agent")), ("Raccoon (rival)", sprite_image("rival")),
             ("Stop to deliver", sprite_image("pin")),
             ("Delivered", sprite_image("pin", {"r": "E", "R": "g"})),
             ("Stolen", sprite_image("pin", {"r": "Q", "R": "l"})), ("Depot", sprite_image("house")),
             ("Wall (tree / rock)", sprite_image("tree"))]
    cols = st.columns(len(items))
    for col, (label, img) in zip(cols, items):
        col.image(img, width=36)
        col.caption(label)
    st.caption("Tiles: dark asphalt = road (cost 1) · green = grass (2) · brown = mud (3) · "
               "light blue = ford (8), dark blue with foam = flooded · purple portals = tunnels (1 per jump). "
               "Yellow dashed line = route from 'Plan route'; red line = the agent's current plan.")


tab_game, tab_llm = st.tabs(["🗺️  Game map", "🤖  AI dispatcher (Claude)"])

# ================================================================= tab 1: game
with tab_game:
    b1, b2, b3, b4 = st.columns(4)
    if b1.button("PLAN ROUTE"):
        s = sim.s
        p = DeliveryProblem(w, s.agent, w.stops, done_mask=s.delivered | s.stolen, flood_left=s.flood_left)
        res = solve(p, algorithm, make_heuristic(heuristic, p), measure_memory=True)
        st.session_state.search = res
        st.session_state.route = [x[0] for x in res.path] if res.success else None
    if b2.button("STEP"):
        if not sim.plan:
            sim.make_plan()
        sim.step()
    if b3.button("RUN EPISODE"):
        if not sim.plan:
            sim.make_plan()
        while sim.step():
            pass
    if b4.button("RESET"):
        st.session_state.w, st.session_state.sim = build()
        st.session_state.route = None
        w, sim = st.session_state.w, st.session_state.sim

    s = sim.s
    left, right = st.columns([3, 2])
    plan_cells = sim.log.plans[-1][1] if sim.log.plans else None
    left.pyplot(draw_map(w, s, route=st.session_state.route, plan=plan_cells,
                         trail=[x.agent for x in sim.log.states], rival=bool(sim.rival)))
    with right:
        names = lambda m: ", ".join(f"S{i + 1}" for i in range(len(w.stops)) if m >> i & 1) or "—"
        flood_txt = f"<b>FLOODED</b> {s.flood_left} steps left" if s.flood_left else (
            "dam used, water gone" if s.dam_used else "dam ready (unused)")
        st.markdown(f"""<div class="panel">
            TIME&nbsp;&nbsp;&nbsp; {s.t}<br>COST&nbsp;&nbsp;&nbsp; {s.cost:g}<br>
            DELIVERED {names(s.delivered)}<br>STOLEN&nbsp;&nbsp;&nbsp; {names(s.stolen)}<br>
            DAM&nbsp;&nbsp;&nbsp;&nbsp; {flood_txt}<br>
            COURIER {s.agent}<br>RACCOON {s.rival}</div>""", unsafe_allow_html=True)
        if sim.done():
            r = sim.result()
            msg = {"win": "🏆 YOU WIN", "draw": "🤝 DRAW", "loss": "💀 RIVAL WINS"}[r["outcome"]]
            st.success(f"{msg} — delivered {r['delivered']}, stolen {r['stolen']}, cost {r['cost']:g}, "
                       f"slips {r['slips']}, replans {r['replans']}")
        res = st.session_state.search
        if res is not None:
            st.markdown("**Last search**")
            st.json(res.summary())
        st.markdown("**Event log**")
        st.text("\n".join(f"t={t}: {e}" for t, e in sim.log.events[-20:]) or "—")
    legend()

# ================================================================= tab 2: LLM dispatcher
with tab_llm:
    st.markdown("""<div class="panel">Type a delivery request in plain English. Claude reads it,
        calls our tools (<b>plan_route</b>, <b>simulate</b>, <b>flood_status</b>, <b>tunnel_info</b>)
        and answers. The <b>validation layer</b> checks every tool call against the map before it runs.</div>""",
                unsafe_allow_html=True)
    client = make_client()
    model = os.environ.get("OEL_MODEL", DEFAULT_MODEL)
    if client is None:
        st.warning("No ANTHROPIC_API_KEY in this terminal, so only answers already saved in "
                   "results/llm_cache.json can be shown. To ask new questions: stop the app, run "
                   "`export ANTHROPIC_API_KEY=...` and start `streamlit run app.py` again.")
    else:
        st.caption(f"Model: {model}")
    reqs = json.load(open(os.path.join(ROOT, "experiments", "llm_requests.json")))["requests"]
    choice = st.selectbox("Example requests (the 20 used in Part D)",
                          ["— write my own —"] + [f"{r['id']}. {r['text']}" for r in reqs])
    default = "" if choice.startswith("—") else choice.split(". ", 1)[1]
    text = st.text_area("Request", value=default, height=80,
                        placeholder="e.g. Deliver S3 first, avoid mud, and tell me the cost")
    validate = st.checkbox("Use the validation layer", True)
    if st.button("ASK CLAUDE") and text.strip():
        with st.spinner("Claude is planning..."):
            try:
                st.session_state.llm = run_request(text.strip(), validate=validate, w=load_world(**params),
                                                   client=client, model=model)
            except NoCachedResponse:
                st.session_state.llm = None
                st.error("This request has no saved answer and no API key is set (see the warning above).")
            except RuntimeError as e:
                st.session_state.llm = None
                st.error(str(e))

    run = st.session_state.llm
    if run:
        left, right = st.columns([3, 2])
        with right:
            st.markdown("**Claude's answer**")
            st.info(run["final"] or "(no final answer)")
            if run["plan"]:
                p = run["plan"]
                st.markdown(f"""<div class="panel">PLAN COST {p['cost']:g}<br>STEPS {p['steps']}<br>
                    ORDER {' → '.join(v['stop'] for v in p['delivery_order'])}<br>
                    ALGORITHM {p['algorithm']} / {p['heuristic']}<br>
                    AVOIDS {', '.join(p['avoid_terrain']) or '—'}<br>
                    TOOL CALLS {len(run['calls'])}</div>""", unsafe_allow_html=True)
            if run["sim"]:
                r = run["sim"]
                st.markdown(f"Simulation: **{r['outcome']}**, delivered {r['delivered']}, "
                            f"stolen {r['stolen']}, cost {r['cost']:g}")
            blocked = [c for c in run["calls"] if c.get("validation_errors")]
            if blocked:
                st.markdown("**Caught by validation**" if validate else "**Invalid arguments (not blocked)**")
                for c in blocked:
                    st.code(f"{c['tool']}({json.dumps(c['args'])})\n→ " + "\n→ ".join(c["validation_errors"]))
        with left:
            w2 = load_world(**params)
            s2 = initial_state(w2)
            st.pyplot(draw_map(w2, s2, plan=run["plan"]["cells"] if run["plan"] else None, rival=False,
                               title="Claude's plan"))
        st.markdown("### ReAct trace (Thought → Action → Observation)")
        for step in run["trace"]:
            if step["type"] == "Thought":
                with st.chat_message("assistant"):
                    st.markdown(f"**Thought (Reason):** {step['text']}")
            elif step["type"] == "Action":
                with st.chat_message("user", avatar="🛠️"):
                    st.markdown(f"**Action (Act):** `{step['tool']}({json.dumps(step['args'])})`")
            else:
                with st.chat_message("user", avatar="👁️"):
                    st.markdown("**Observation (Sense):**")
                    st.json(step["result"], expanded=False)

st.markdown(f'<div class="stamp">{STAMP}</div>', unsafe_allow_html=True)
