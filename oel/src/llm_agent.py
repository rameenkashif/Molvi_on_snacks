"""Part D: Claude as a dispatcher that drives our planners through tools (manual ReAct loop).

Tools
  plan_route(algorithm, heuristic, stops?, stop_order?, avoid_terrain?)   -> Part B planner
  simulate(steps)                                                          -> Part C simulator
  flood_status()                    (custom, our 3rd twist: dam state + which stops need fords)
  tunnel_info()                     (optional, our tunnel twist)

Validation layer (validate=True): every tool call's arguments are checked against the
instance BEFORE execution (names, stop ids, terrain names, step range, feasibility such as
"avoid fords" while S3 is itself a ford). A failed check returns an error observation so the
model can retry. With validate=False the tools run on whatever arguments arrive: unknown
stop ids / terrain names are silently dropped and unknown algorithm names raise.

Every API response is cached in results/llm_cache.json keyed by sha256(model + system +
tools + messages so far + mode), so run_all.py replays Part D with no API key and no cost.
Key from env ANTHROPIC_API_KEY, model from env OEL_MODEL (default claude-haiku-5-5).
"""
from __future__ import annotations
import hashlib, json, os

from src.world import World, STAMP, ROOT, TERRAINS, load_world
from src.problem import DeliveryProblem
from src.search import solve, ALGORITHMS
from src.heuristics import make_heuristic, HEURISTICS
from src.simulator import Simulator
from src.game import Evaluator

CACHE_PATH = os.path.join(ROOT, "results", "llm_cache.json")
DEFAULT_MODEL = "claude-haiku-5-5"
MAX_TURNS = 10

TOOLS = [
    {"name": "plan_route",
     "description": ("Plan a delivery route from the agent's current position with one of our "
                     "search algorithms. Returns cost, number of steps, the order the stops are "
                     "delivered in, terrain used and whether the route crosses fords. The plan "
                     "becomes the current plan that simulate() executes."),
     "input_schema": {"type": "object", "properties": {
         "algorithm": {"type": "string", "description": "bfs, ucs, dls, ids, greedy, astar or wastar"},
         "heuristic": {"type": "string",
                       "description": "tunnel_mst (ours, admissible), mst_plain, nearest, farthest, sum_dstar, zero"},
         "stops": {"type": "array", "items": {"type": "string"},
                   "description": "stop ids to deliver, e.g. [\"S1\",\"S3\"]; default all undelivered stops"},
         "stop_order": {"type": "array", "items": {"type": "string"},
                        "description": "stops that must be delivered first, in this order"},
         "avoid_terrain": {"type": "array", "items": {"type": "string"},
                           "description": "terrain types to treat as walls: road, grass, mud, ford"}},
         "required": ["algorithm", "heuristic"]}},
    {"name": "simulate",
     "description": ("Execute the current plan in the real (stochastic) world for N steps: the agent "
                     "may slip, the blocker rival moves, may steal parcels and may open the dam. "
                     "The agent replans automatically after slips. Returns events and the state."),
     "input_schema": {"type": "object", "properties": {
         "steps": {"type": "integer", "description": "number of time steps, 1..200"}},
         "required": ["steps"]}},
    {"name": "flood_status",
     "description": ("Our flooding twist: whether the rival has used its single dam charge, how many "
                     "flooded steps remain, which stops need a ford crossing, and whether the "
                     "current plan crosses fords (and at which step)."),
     "input_schema": {"type": "object", "properties": {}}},
    {"name": "tunnel_info",
     "description": "List the teleport tunnel pairs (cost 1 per jump).",
     "input_schema": {"type": "object", "properties": {}}},
]


def system_prompt(w: World) -> str:
    stops = ", ".join(f"S{i + 1} {s}" for i, s in enumerate(w.stops))
    return (
        "You are the dispatcher of an autonomous delivery robot on a 23x23 grid city. "
        f"Depot {w.start}. Stops: {stops}. Terrain cost: road 1, grass 2, mud 3, ford 8. "
        "Coordinates are (row, col). Twists: teleport tunnels; a blocker rival that steals any "
        "parcel whose stop it reaches first; the rival can open a dam once, flooding every ford "
        f"for {w.flood_duration} steps (S3 is itself a ford). Use the tools to satisfy the request. "
        "Always call plan_route before simulate. If a request cannot be satisfied, say clearly "
        "that it is infeasible and why. End with a short final answer that states the plan cost.")


# ---------------------------------------------------------------- tool execution
class Session:
    """World + current plan + simulator for one dispatcher request."""

    def __init__(self, w: World | None = None):
        self.w = w or load_world()
        self.plan = None          # dict describing the last successful plan
        self.constraints = {}
        self.sim = None
        self.calls = []           # log of every tool call

    def stop_idx(self, sid: str) -> int:
        return int(str(sid).upper().lstrip("S")) - 1

    # ---- validation layer
    def validate(self, name: str, args: dict) -> list:
        errs = []
        k = len(self.w.stops)
        valid_ids = {f"S{i + 1}" for i in range(k)}
        if name == "plan_route":
            alg = str(args.get("algorithm", "")).lower().replace("*", "star").replace("-", "")
            if alg not in ALGORITHMS:
                errs.append(f"unknown algorithm {args.get('algorithm')!r}; use one of {ALGORITHMS}")
            if args.get("heuristic") not in HEURISTICS:
                errs.append(f"unknown heuristic {args.get('heuristic')!r}; use one of {list(HEURISTICS)}")
            for key in ("stops", "stop_order"):
                for sid in args.get(key) or []:
                    if str(sid).upper() not in valid_ids:
                        errs.append(f"{key}: stop {sid!r} does not exist (valid: {sorted(valid_ids)})")
            order = [str(s).upper() for s in args.get("stop_order") or []]
            if len(order) != len(set(order)):
                errs.append("stop_order lists a stop twice")
            if args.get("stops") and any(s not in [str(x).upper() for x in args["stops"]] for s in order):
                errs.append("stop_order contains a stop that is not in stops")
            for t in args.get("avoid_terrain") or []:
                if t not in TERRAINS:
                    errs.append(f"unknown terrain {t!r}; use {TERRAINS}")
            avoid = set(args.get("avoid_terrain") or [])
            if avoid >= {"road"}:
                errs.append("avoiding road makes the depot area unreachable; road is the cheapest terrain")
            for i, st in enumerate(self.w.stops):
                wanted = not args.get("stops") or f"S{i + 1}" in [str(x).upper() for x in args["stops"]]
                if wanted and TERRAINS[self.w.grid[st]] in avoid:
                    errs.append(f"infeasible: S{i + 1} {st} is itself a {TERRAINS[self.w.grid[st]]} "
                                f"cell, so it cannot be delivered while avoiding {TERRAINS[self.w.grid[st]]}")
            unknown = set(args) - {"algorithm", "heuristic", "stops", "stop_order", "avoid_terrain"}
            if unknown:
                errs.append(f"unknown argument(s) {sorted(unknown)}")
        elif name == "simulate":
            st = args.get("steps")
            if not isinstance(st, int) or not 1 <= st <= 200:
                errs.append("steps must be an integer between 1 and 200")
            if self.plan is None:
                errs.append("no current plan: call plan_route first")
        elif name not in ("flood_status", "tunnel_info"):
            errs.append(f"unknown tool {name!r}")
        return errs

    # ---- tools
    def plan_route(self, algorithm, heuristic, stops=None, stop_order=None, avoid_terrain=None, **_):
        w = self.w
        k = len(w.stops)
        ids = [s for s in (stops or [f"S{i + 1}" for i in range(k)]) if str(s).upper().lstrip("S").isdigit()
               and 0 <= self.stop_idx(s) < k]
        keep = sorted({self.stop_idx(s) for s in ids})
        state = self.sim.s if self.sim else None
        done = (state.delivered | state.stolen) if state else 0
        sub = [w.stops[i] for i in keep]
        sub_done = sum(1 << j for j, i in enumerate(keep) if done >> i & 1)
        order = [keep.index(self.stop_idx(s)) for s in (stop_order or [])
                 if str(s).upper().lstrip("S").isdigit() and self.stop_idx(s) in keep]
        avoid = frozenset(t for t in (avoid_terrain or []) if t in TERRAINS)
        p = DeliveryProblem(w, state.agent if state else w.start, sub, done_mask=sub_done,
                            flood_left=state.flood_left if state else 0, avoid_terrain=avoid,
                            order=tuple(order), names=[f"S{i + 1}" for i in keep])
        h = make_heuristic(heuristic if heuristic in HEURISTICS else "zero", p)
        r = solve(p, algorithm, h)
        if not r.success:
            return {"ok": False, "error": f"no route found ({r.note or 'search failed'})",
                    "expanded": r.expanded}
        visit, terrain, fords = [], {}, []
        for t, (a, b) in enumerate(zip(r.path, r.path[1:])):
            terrain[TERRAINS[w.grid[b[0]]]] = terrain.get(TERRAINS[w.grid[b[0]]], 0) + 1
            if w.grid[b[0]] == 3:
                fords.append(t + 1)
            for j in range(len(sub)):
                if b[1] >> j & 1 and not a[1] >> j & 1:
                    visit.append({"stop": f"S{keep[j] + 1}", "step": t + 1})
        self.plan = {"algorithm": algorithm, "heuristic": heuristic, "cost": r.cost,
                     "steps": len(r.actions), "delivery_order": visit, "terrain_steps": terrain,
                     "ford_steps": fords, "stops": [f"S{i + 1}" for i in keep],
                     "avoid_terrain": sorted(avoid), "cells": [s[0] for s in r.path]}
        self.constraints = {"avoid_terrain": sorted(avoid),
                            "order": tuple(self.stop_idx(s) for s in (stop_order or [])
                                           if self.stop_idx(s) in keep)}
        return {"ok": True, **{k: v for k, v in self.plan.items() if k != "cells"},
                "nodes_expanded": r.expanded, "uses_tunnel": "TUNNEL" in r.actions}

    def simulate(self, steps, **_):
        w = self.w
        if self.sim is None:
            self.sim = Simulator(w, agent="planner", seed=7, constraints=self.constraints)
            self.sim.make_plan()
        else:
            self.sim.constraints = self.constraints
            self.sim.make_plan()
        n0 = len(self.sim.log.events)
        for _ in range(int(steps)):
            if not self.sim.step():
                break
        s = self.sim.s
        return {"t": s.t, "position": s.agent, "rival": s.rival, "cost_so_far": s.cost,
                "delivered": [f"S{i + 1}" for i in range(len(w.stops)) if s.delivered >> i & 1],
                "stolen": [f"S{i + 1}" for i in range(len(w.stops)) if s.stolen >> i & 1],
                "dam_used": s.dam_used, "flood_steps_left": s.flood_left,
                "finished": self.sim.done(),
                "events": [f"t={t}: {e}" for t, e in self.sim.log.events[n0:]][-15:]}

    def flood_status(self, **_):
        w = self.w
        s = self.sim.s if self.sim else None
        ev = Evaluator(w)
        need = [f"S{i + 1}" for i in range(len(w.stops)) if ev.ford_dep[i]]
        return {"dam_used": bool(s and s.dam_used), "flood_steps_left": s.flood_left if s else 0,
                "flood_duration": w.flood_duration, "stops_that_need_a_ford": need,
                "stop_cells_that_are_fords": [f"S{i + 1}" for i, st in enumerate(w.stops) if w.grid[st] == 3],
                "current_plan_ford_steps": self.plan["ford_steps"] if self.plan else None}

    def tunnel_info(self, **_):
        pairs = sorted({tuple(sorted((a, b))) for a, b in self.w.tunnels.items()})
        return {"pairs": [list(p) for p in pairs], "cost_per_jump": self.w.tunnel_cost}

    def execute(self, name: str, args: dict, validate: bool) -> tuple:
        """Returns (observation dict, list of validation errors)."""
        errs = self.validate(name, args)
        rec = {"tool": name, "args": args, "validation_errors": errs}
        if validate and errs:
            rec["blocked"] = True
            self.calls.append(rec)
            return {"ok": False, "validation_errors": errs}, errs
        try:
            obs = getattr(self, name)(**args) if name in ("plan_route", "simulate", "flood_status",
                                                         "tunnel_info") else {"ok": False, "error": f"no tool {name}"}
        except Exception as e:                       # noqa: BLE001 - surfaced to the model
            obs = {"ok": False, "error": f"{type(e).__name__}: {e}"}
        rec["ok"] = obs.get("ok", True)
        self.calls.append(rec)
        return obs, errs


# ---------------------------------------------------------------- cache + loop
class NoCachedResponse(RuntimeError):
    pass


def _load_cache() -> dict:
    if os.path.exists(CACHE_PATH):
        with open(CACHE_PATH) as f:
            return json.load(f)
    return {}


def _save_cache(c: dict) -> None:
    os.makedirs(os.path.dirname(CACHE_PATH), exist_ok=True)
    with open(CACHE_PATH, "w") as f:
        json.dump(c, f, indent=1, sort_keys=True)


def _call(client, cache, model, system, messages, mode) -> dict:
    key = hashlib.sha256(json.dumps([model, system, TOOLS, messages, mode], sort_keys=True,
                                    default=str).encode()).hexdigest()
    if key in cache:
        return cache[key]
    if client is None:
        raise NoCachedResponse("no cached response and no ANTHROPIC_API_KEY set")
    import anthropic
    try:
        resp = client.messages.create(model=model, max_tokens=4096, system=system,
                                      tools=TOOLS, messages=messages)
    except anthropic.APIStatusError as e:
        raise RuntimeError(f"Claude API error {e.status_code}: {e.message}") from e
    data = resp.model_dump(mode="json", exclude_none=True)
    data = {"content": data["content"], "stop_reason": data["stop_reason"],
            "usage": data.get("usage", {}), "model": data.get("model", model)}
    cache[key] = data
    _save_cache(cache)
    return data


def make_client():
    if not os.environ.get("ANTHROPIC_API_KEY") and not os.environ.get("ANTHROPIC_AUTH_TOKEN"):
        return None
    import anthropic
    return anthropic.Anthropic()


def run_request(text: str, validate: bool = True, w: World | None = None, client=None,
                model: str | None = None) -> dict:
    """Run one dispatcher request through the ReAct loop. Returns the trace and the session."""
    model = model or os.environ.get("OEL_MODEL", DEFAULT_MODEL)
    sess = Session(w)
    system = system_prompt(sess.w)
    cache = _load_cache()
    messages = [{"role": "user", "content": text}]
    trace, final_text, usage = [], "", {"input_tokens": 0, "output_tokens": 0}
    for _ in range(MAX_TURNS):
        resp = _call(client, cache, model, system, messages, "validated" if validate else "raw")
        for k in usage:
            usage[k] += resp.get("usage", {}).get(k, 0)
        content = resp["content"]
        messages.append({"role": "assistant", "content": content})
        thoughts = [b["text"] for b in content if b["type"] == "text"]
        uses = [b for b in content if b["type"] == "tool_use"]
        if thoughts:
            trace.append({"type": "Thought", "text": "\n".join(thoughts)})
        if resp["stop_reason"] != "tool_use" or not uses:
            final_text = "\n".join(thoughts)
            break
        results = []
        for b in uses:
            obs, errs = sess.execute(b["name"], b.get("input") or {}, validate)
            trace.append({"type": "Action", "tool": b["name"], "args": b.get("input")})
            trace.append({"type": "Observation", "tool": b["name"], "result": obs,
                          "validation_errors": errs})
            results.append({"type": "tool_result", "tool_use_id": b["id"],
                            "content": json.dumps(obs, default=str),
                            **({"is_error": True} if not obs.get("ok", True) else {})})
        messages.append({"role": "user", "content": results})
    return {"stamp": STAMP, "request": text, "validate": validate, "model": model,
            "trace": trace, "final": final_text, "calls": sess.calls, "plan": sess.plan,
            "sim": sess.sim.result() if sess.sim else None, "usage": usage}
