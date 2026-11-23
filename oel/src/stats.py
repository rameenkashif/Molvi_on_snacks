"""Confidence intervals used in every experiment table."""
from __future__ import annotations
import hashlib, math

from scipy import stats as _st


def mean_ci(xs, conf: float = 0.95) -> dict:
    """Mean with a t-distribution confidence interval (n-1 degrees of freedom)."""
    xs = [float(x) for x in xs]
    n = len(xs)
    if n == 0:
        return {"mean": float("nan"), "lo": float("nan"), "hi": float("nan"), "n": 0}
    m = sum(xs) / n
    if n == 1:
        return {"mean": m, "lo": m, "hi": m, "n": 1, "half": 0.0}
    sd = math.sqrt(sum((x - m) ** 2 for x in xs) / (n - 1))
    half = _st.t.ppf(0.5 + conf / 2, n - 1) * sd / math.sqrt(n)
    return {"mean": m, "lo": m - half, "hi": m + half, "n": n, "half": half}


def wilson(k: int, n: int, conf: float = 0.95) -> dict:
    """Wilson score interval for a proportion k/n (better than normal approx for small n)."""
    if n == 0:
        return {"p": float("nan"), "lo": float("nan"), "hi": float("nan"), "k": 0, "n": 0}
    z = _st.norm.ppf(0.5 + conf / 2)
    p = k / n
    den = 1 + z * z / n
    centre = (p + z * z / (2 * n)) / den
    half = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / den
    return {"p": p, "lo": max(0.0, centre - half), "hi": min(1.0, centre + half), "k": k, "n": n}


def fmt_ci(d: dict, digits: int = 1) -> str:
    return f"{d['mean']:.{digits}f} ± {d.get('half', 0):.{digits}f}"


def seed_for(tag: str, instance_id: str, i: int = 0) -> int:
    """Reproducible seed from the instance hash (which comes from our CMS IDs)."""
    return int(hashlib.sha256(f"{tag}|{instance_id}|{i}".encode()).hexdigest()[:16], 16)
