# Part D — LLM dispatcher

Rameen Kashif (456834) | Manal Aslam (465734) | Zainab Ali Bangash (486688)

Code: `src/llm_agent.py`; experiment: `experiments/part_d_llm.py`; requests:
`experiments/llm_requests.json`; traces: `results/llm_traces/`; cache: `results/llm_cache.json`.

## Design
* **Model / SDK.** Anthropic Python SDK, `client.messages.create` with native tool use and a
  manual ReAct loop (≤ 10 model turns). Key from `ANTHROPIC_API_KEY`, model from `OEL_MODEL`
  (default `claude-haiku-5-5`, chosen for cost).
* **Tools.**
  * `plan_route(algorithm, heuristic, stops?, stop_order?, avoid_terrain?)` → our Part B search.
  * `simulate(steps)` → our Part C simulator (slip, blocker, stealing, dam, automatic replanning).
  * `flood_status()` (**custom tool for our 3rd twist**) → dam used?, flood steps left, which stops
    need a ford, at which steps the current plan crosses fords.
  * `tunnel_info()` → tunnel pairs.
* **Validation layer** (`Session.validate`), run before every tool call: algorithm and heuristic
  names; stop ids exist; `stop_order` has no duplicates and ⊆ `stops`; terrain names; obviously
  infeasible constraints (a requested stop is itself of an avoided terrain — e.g. "avoid fords"
  with S3, which is a ford); `simulate` needs 1 ≤ steps ≤ 200 and an existing plan; unknown
  arguments. A failed check returns `{"ok": false, "validation_errors": [...]}` so the model retries.
  Without validation, tools run on whatever arrives (unknown stop ids and terrain names are
  silently dropped, unknown algorithms raise and the exception text is returned).
* **Reproducibility.** Every API response is cached, keyed by
  `sha256(model, system, tools, messages so far, mode)`. Our tools are deterministic (seeded), so
  a cached conversation replays exactly and `python run_all.py` reproduces Part D with no key.

## Requests (20, difficulty 1→5)
Simple single plans → ordering constraints → terrain constraints and cost caps → tool
selection (flood/tunnel questions, simulation) → infeasible requests (avoid fords with S3,
avoid mud — the depot is enclosed by mud, cost < 100 when the optimum is 111, a non-existent
stop S5) → combined constraints. Each request carries a machine-checkable `check` (stops,
order prefix, avoided terrain, cost cap, required tools/algorithms, or "must report infeasible").

## Metrics (Table D1/D2 in `results/part_d_llm.json`)
* Success rate (Wilson 95 % CI) for: direct planner call, LLM with validation, LLM without.
* Tool calls per request, plan cost.
* Error log: **wrong tool** (unknown tool, simulate before plan), **invented arguments**
  (validation errors on names/ids/arguments), **ignored constraints** (final plan violates the
  request, or an infeasible request is reported as done).

## Sense–Reason–Act mapping
`experiments/part_d_llm.py` writes each run as Markdown with every step labelled:

| ReAct step | Lab 3 cycle | In our system |
|---|---|---|
| Observation | **Sense** | tool result: plan cost / route terrain / delivered & stolen / dam state |
| Thought | **Reason** | the model's text: which constraint matters, which tool to call next |
| Action | **Act** | a tool call (`plan_route`, `simulate`, `flood_status`, `tunnel_info`) |

The first user message is the initial percept (the request plus the system prompt's map
summary). Use two traces from `results/llm_traces/` in the report (e.g. request 14 "avoid fords"
— validation tells the model *why* it is infeasible — and request 18 "S3 first then simulate").

## Status
Without an API key the experiment still runs: the direct-planner baseline is computed and the
LLM columns read "not run". To fill them once (cost: a few cents with Haiku):

```bash
export ANTHROPIC_API_KEY=...        # your key
python run_all.py d                 # runs the 40 conversations and writes results/llm_cache.json
git add results/llm_cache.json results/llm_traces results/part_d_llm.json
```
After that, every `python run_all.py` replays the cache for free.
