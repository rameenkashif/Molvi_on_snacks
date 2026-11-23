"""Exercise the Part D ReAct loop with a scripted fake client (no network, no key)."""
import os
import src.llm_agent as la


class _Resp:
    def __init__(self, d):
        self.d = d

    def model_dump(self, **_):
        return self.d


class FakeClient:
    """Returns: a bad tool call, then a good one, then a final answer."""
    def __init__(self):
        self.n = 0
        self.messages = self

    def create(self, **kw):
        self.n += 1
        if self.n == 1:
            c = [{"type": "text", "text": "I will plan."},
                 {"type": "tool_use", "id": "t1", "name": "plan_route",
                  "input": {"algorithm": "astar", "heuristic": "magic", "stops": ["S9"]}}]
            return _Resp({"content": c, "stop_reason": "tool_use", "usage": {}})
        if self.n == 2:
            c = [{"type": "tool_use", "id": "t2", "name": "plan_route",
                  "input": {"algorithm": "astar", "heuristic": "tunnel_mst"}}]
            return _Resp({"content": c, "stop_reason": "tool_use", "usage": {}})
        return _Resp({"content": [{"type": "text", "text": "Plan cost 111."}],
                      "stop_reason": "end_turn", "usage": {}})


def test_validation_blocks_invented_args(tmp_path, monkeypatch):
    monkeypatch.setattr(la, "CACHE_PATH", str(tmp_path / "cache.json"))
    run = la.run_request("Deliver everything", validate=True, client=FakeClient())
    first = run["calls"][0]
    assert first["blocked"] and any("S9" in e for e in first["validation_errors"])
    assert run["plan"]["cost"] == 111.0
    assert run["final"] == "Plan cost 111."
    # the cache now replays the same conversation without any client
    again = la.run_request("Deliver everything", validate=True, client=None)
    assert again["plan"]["cost"] == 111.0
    assert os.path.exists(tmp_path / "cache.json")
