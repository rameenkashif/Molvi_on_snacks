"""Part D: Claude dispatcher vs calling the planner directly, with and without validation.

Needs either ANTHROPIC_API_KEY (first run, fills results/llm_cache.json) or the committed
cache (every later run, no key, no cost). Requests that are neither cached nor runnable are
reported as "not run" rather than invented.

Outputs results/part_d_llm.json, results/part_d_llm.png, results/llm_traces/*.json|.md
"""
from __future__ import annotations
import json, os, re, sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
from src.world import STAMP  # noqa: E402
from src.llm_agent import Session, run_request, make_client, NoCachedResponse, DEFAULT_MODEL  # noqa: E402
from src.stats import wilson, mean_ci  # noqa: E402
from experiments.common import save_json, save_fig, print_table, plt, OUT  # noqa: E402

REQ_PATH = os.path.join(ROOT, "experiments", "llm_requests.json")
INFEASIBLE_WORDS = re.compile(r"infeasib|not possible|impossible|cannot|can't|unable|no (valid )?route|"
                              r"does not exist|doesn't exist|not feasible", re.I)


def check(spec: dict, plan: dict | None, calls: list, final: str) -> tuple:
    """Return (success, list of ignored constraints)."""
    c = spec
    if c.get("feasible") is False:
        ok = bool(INFEASIBLE_WORDS.search(final or ""))
        return ok, ([] if ok else ["claimed an infeasible request was satisfied / did not say infeasible"])
    used_tools = {x["tool"] for x in calls if x.get("ok", True) and not x.get("blocked")}
    missing = [t for t in c.get("tools", []) if t not in used_tools]
    ignored = [f"did not call {t}" for t in missing]
    if c.get("no_plan_needed"):
        return not missing, ignored
    if plan is None:
        return False, ignored + ["no successful plan"]
    want_stops = set(c.get("stops", ["S1", "S2", "S3", "S4"]))
    if set(plan["stops"]) != want_stops:
        ignored.append(f"stops {plan['stops']} != {sorted(want_stops)}")
    order = [v["stop"] for v in plan["delivery_order"]]
    if order[:len(c.get("order", []))] != c.get("order", []):
        ignored.append(f"order {order} does not start with {c['order']}")
    for t in c.get("avoid", []):
        if plan["terrain_steps"].get(t):
            ignored.append(f"route crosses {t}")
    if "max_cost" in c and plan["cost"] >= c["max_cost"]:
        ignored.append(f"cost {plan['cost']} >= {c['max_cost']}")
    if "algorithm" in c and plan["algorithm"].lower() != c["algorithm"]:
        ignored.append(f"algorithm {plan['algorithm']} != {c['algorithm']}")
    if "heuristic" in c and plan["heuristic"] != c["heuristic"]:
        ignored.append(f"heuristic {plan['heuristic']} != {c['heuristic']}")
    for alg in c.get("algorithms_called", []):
        if not any(x["tool"] == "plan_route" and str(x["args"].get("algorithm", "")).lower() == alg
                   for x in calls):
            ignored.append(f"never planned with {alg}")
    if c.get("simulate") and "simulate" not in used_tools:
        ignored.append("did not simulate")
    return not ignored, ignored


def direct_baseline(req: dict) -> dict:
    """What a programmer calling our planner directly gets (no LLM)."""
    c, sess, n = req["check"], Session(), 0
    if req["direct"] is None:
        # infeasible or no plan needed: the direct call reports it with one tool call
        if c.get("no_plan_needed"):
            sess.execute("flood_status", {}, True)
            return {"success": True, "tool_calls": 1, "cost": None}
        return {"success": True, "tool_calls": 1, "cost": None, "note": "planner/validator reports infeasible"}
    obs, _ = sess.execute("plan_route", dict(req["direct"]), True); n += 1
    for alg in c.get("algorithms_called", []):
        if alg != req["direct"]["algorithm"]:
            sess.execute("plan_route", {**req["direct"], "algorithm": alg}, True); n += 1
            sess.execute("plan_route", dict(req["direct"]), True); n += 1
    for t in c.get("tools", []):
        sess.execute(t, {}, True); n += 1
    if c.get("simulate"):
        sess.execute("simulate", {"steps": 200}, True); n += 1
    ok, ign = check(c, sess.plan, sess.calls, "")
    return {"success": ok, "tool_calls": n, "cost": sess.plan["cost"] if sess.plan else None,
            "ignored": ign}


def errors_of(run: dict, spec: dict) -> dict:
    wrong_tool = [x["tool"] for x in run["calls"]
                  if x["tool"] not in ("plan_route", "simulate", "flood_status", "tunnel_info")
                  or any("no current plan" in e for e in x["validation_errors"])]
    invented = [e for x in run["calls"] for e in x["validation_errors"]
                if "infeasible" not in e and "no current plan" not in e]
    return {"wrong_tool": wrong_tool, "invented_args": invented}


def write_trace(req, run, mode):
    os.makedirs(os.path.join(OUT, "llm_traces"), exist_ok=True)
    base = os.path.join(OUT, "llm_traces", f"req{req['id']:02d}_{mode}")
    with open(base + ".json", "w") as f:
        json.dump(run, f, indent=1, default=str)
    lines = [f"# Request {req['id']} ({mode})", "", STAMP, "", f"> {req['text']}", ""]
    for step in run["trace"]:
        if step["type"] == "Thought":
            lines += [f"**Thought (Reason):** {step['text']}", ""]
        elif step["type"] == "Action":
            lines += [f"**Action (Act):** `{step['tool']}({json.dumps(step['args'])})`", ""]
        else:
            lines += [f"**Observation (Sense):** `{json.dumps(step['result'], default=str)[:600]}`", ""]
    lines += ["**Final answer:**", "", run["final"] or "(none)"]
    with open(base + ".md", "w") as f:
        f.write("\n".join(lines))


def main():
    print(STAMP)
    reqs = json.load(open(REQ_PATH))["requests"]
    client = make_client()
    model = os.environ.get("OEL_MODEL", DEFAULT_MODEL)
    print(f"model={model}  api key {'set' if client else 'NOT set (cache only)'}")
    rows, log, per_mode = [], [], {"validated": [], "raw": []}
    for req in reqs:
        d = direct_baseline(req)
        row = {"id": req["id"], "diff": req["difficulty"], "direct ok": d["success"],
               "direct calls": d["tool_calls"], "direct cost": d["cost"]}
        for mode, val in (("validated", True), ("raw", False)):
            try:
                run = run_request(req["text"], validate=val, client=client, model=model)
            except NoCachedResponse:
                row[f"{mode} ok"] = "not run"
                continue
            except RuntimeError as e:
                row[f"{mode} ok"] = f"error: {e}"
                continue
            ok, ignored = check(req["check"], run["plan"], run["calls"], run["final"])
            err = errors_of(run, req["check"])
            write_trace(req, run, mode)
            row[f"{mode} ok"] = ok
            row[f"{mode} calls"] = len(run["calls"])
            row[f"{mode} cost"] = run["plan"]["cost"] if run["plan"] else None
            per_mode[mode].append({"id": req["id"], "ok": ok, "calls": len(run["calls"]),
                                   "cost": run["plan"]["cost"] if run["plan"] else None,
                                   "tokens": run["usage"]})
            if ignored or err["wrong_tool"] or err["invented_args"]:
                log.append({"id": req["id"], "mode": mode, "request": req["text"],
                            "ignored_constraints": ignored, **err})
        rows.append(row)
    cols = ["id", "diff", "direct ok", "direct calls", "direct cost", "validated ok", "validated calls",
            "validated cost", "raw ok", "raw calls", "raw cost"]
    print_table(rows, cols, "Table D1: 20 dispatcher requests")

    summary = []
    k = sum(r["direct ok"] for r in rows)
    ci = wilson(k, len(rows))
    summary.append({"method": "direct planner call", "runs": len(rows),
                    "success": f"{ci['p']:.2f} [{ci['lo']:.2f}, {ci['hi']:.2f}]",
                    "mean tool calls": round(sum(r["direct calls"] for r in rows) / len(rows), 2)})
    for mode, runs in per_mode.items():
        if not runs:
            summary.append({"method": f"LLM ({mode})", "runs": 0, "success": "not run (no key, no cache)",
                            "mean tool calls": ""})
            continue
        ci = wilson(sum(r["ok"] for r in runs), len(runs))
        summary.append({"method": f"LLM ({mode})", "runs": len(runs),
                        "success": f"{ci['p']:.2f} [{ci['lo']:.2f}, {ci['hi']:.2f}]",
                        "mean tool calls": round(mean_ci([r["calls"] for r in runs])["mean"], 2)})
    print_table(summary, list(summary[0]), "Table D2: success rate (Wilson 95% CI) and tool calls")
    if log:
        print("\nLogged LLM errors (wrong tool / invented args / ignored constraints):")
        for e in log:
            print(f"  req {e['id']:>2} [{e['mode']}]: ignored={e['ignored_constraints']} "
                  f"wrong_tool={e['wrong_tool']} invented={e['invented_args']}")
    save_json("part_d_llm.json", {"model": model, "rows": rows, "summary": summary,
                                  "error_log": log, "per_mode": per_mode})

    fig, ax = plt.subplots(figsize=(7, 4))
    labels, vals = [], []
    for s in summary:
        labels.append(s["method"])
        vals.append(float(s["success"].split()[0]) if s["runs"] else 0.0)
    ax.bar(labels, vals, color=["#777", "#4a7ab8", "#c77d3a"][:len(labels)])
    ax.set_ylim(0, 1.05); ax.set_ylabel("success rate (20 requests)")
    ax.set_title(f"Dispatcher success, model {model}")
    for i, s in enumerate(summary):
        if not s["runs"]:
            ax.text(i, 0.05, "not run\n(no API key)", ha="center", fontsize=8)
    save_fig(fig, "part_d_llm.png")


if __name__ == "__main__":
    main()
