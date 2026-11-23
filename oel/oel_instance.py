"""CS-370 OEL instance generator. Usage: python oel_instance.py CMS_ID_1 CMS_ID_2 CMS_ID_3

Every plot, table, log and UI screen must print stamp(MEMBERS): the full name and CMS ID of each member."""
import hashlib, json, sys
import numpy as np
from collections import deque

ADVERSARIES = ["chaser", "blocker", "interceptor"]
TWISTS = ["fuel_limit_with_charging_stations", "one_way_streets", "rush_hour_time_varying_costs",
          "fog_partial_observability", "toll_gates_budget", "teleport_tunnels",
          "wind_drift", "rival_steals_parcels"]
TERRAINS = ["road", "grass", "mud", "ford"]

def reachable(grid, start, targets):
    n = len(grid); seen = {start}; q = deque([start])
    while q:
        r, c = q.popleft()
        for dr, dc in ((1,0),(-1,0),(0,1),(0,-1)):
            nr, nc = r+dr, c+dc
            if 0 <= nr < n and 0 <= nc < n and grid[nr][nc] >= 0 and (nr, nc) not in seen:
                seen.add((nr, nc)); q.append((nr, nc))
    return all(t in seen for t in targets)

def stamp(members):
    """members = [('Full Name', 'CMS ID'), ...] -> one line to print on every output."""
    return " | ".join(f"{name} ({cms})" for name, cms in members)

def make_instance(cms_ids):
    key = "|".join(sorted(r.strip().upper() for r in cms_ids))
    h = hashlib.sha256(key.encode()).hexdigest()
    rng = np.random.default_rng(int(h[:16], 16))
    n = int(rng.integers(20, 41))
    costs = sorted(int(x) for x in rng.choice(np.arange(1, 10), 4, replace=False))
    density = float(rng.uniform(0.15, 0.30))
    while True:
        grid = rng.choice(4, size=(n, n), p=[0.4, 0.3, 0.2, 0.1])
        grid[rng.random((n, n)) < density] = -1          # -1 = blocked
        free = np.argwhere(grid >= 0)
        pick = free[rng.choice(len(free), 1 + int(rng.integers(3, 7)), replace=False)]
        start, stops = tuple(map(int, pick[0])), [tuple(map(int, p)) for p in pick[1:]]
        if reachable(grid.tolist(), start, stops):
            break
    return {"instance_id": h[:8], "grid_size": n, "terrain_cost": dict(zip(TERRAINS, costs)),
            "obstacle_density": round(density, 3), "start": start, "delivery_stops": stops,
            "adversary": str(rng.choice(ADVERSARIES)), "slip_probability": round(float(rng.uniform(0.10, 0.30)), 2),
            "adversary_search_depth": int(rng.integers(3, 7)),
            "twists": [str(t) for t in rng.choice(TWISTS, 2, replace=False)]}, grid

if __name__ == "__main__":
    inst, grid = make_instance(sys.argv[1:])
    np.save(f"grid_{inst['instance_id']}.npy", grid)
    print(json.dumps(inst, indent=2))
