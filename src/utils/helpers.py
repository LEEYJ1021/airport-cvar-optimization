# src/utils/helpers.py
from __future__ import annotations

import hashlib
import math
import random
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

import numpy as np
import typer

from src.settings import (
    BUS_TO_CHECKIN,
    PARKING_TO_CHECKIN,
    RAILROAD_TO_CHECKIN,
    TAXI_TO_CHECKIN,
    GATE_OPERATING_HOURS,
)

def parse_time_hhmm(s: str) -> Optional[datetime]:
    if not s or not s.strip(): return None
    try:
        t = datetime.strptime(s.strip(), "%H:%M")
        return datetime.now().replace(hour=t.hour, minute=t.minute, second=0, microsecond=0)
    except ValueError:
        return None

def clamp(x: float, lo: float, hi: float) -> float:
    return max(lo, min(hi, x))

def minutes_between(t1: datetime, t2: datetime) -> float:
    return (t2 - t1).total_seconds() / 60.0

def is_gate_open(gate_id: str, at_time: datetime) -> bool:
    hours = GATE_OPERATING_HOURS.get(gate_id, "24시간")
    if hours in ("24시간", "00:00-24:00"): return True
    try:
        start_str, end_str = hours.split("-")
        start = at_time.replace(hour=int(start_str[:2]), minute=int(start_str[3:]), second=0, microsecond=0)
        end = at_time.replace(hour=int(end_str[:2]), minute=int(end_str[3:]), second=0, microsecond=0)
        return start <= at_time < end if start < end else at_time >= start or at_time < end
    except Exception:
        return True

def winsorize(values: List[float], p: float = 0.05) -> List[float]:
    if not values: return []
    arr = np.array(values, dtype=float)
    lo, hi = np.quantile(arr, [p, 1 - p])
    return np.clip(arr, lo, hi).tolist()

def sigmoid(x: float) -> float:
    return 1.0 / (1.0 + math.exp(-x))

def hour_of_week(t: datetime) -> int:
    return t.weekday() * 24 + t.hour

def hour_to_slot(h: int) -> str:
    return f"{h:02d}_{(h + 1) % 24:02d}"

def compute_cvar(values: list, alpha: float = 0.9) -> float:
    if not values: return float("nan")
    arr = np.array(values)
    q = np.quantile(arr, alpha)
    tail = arr[arr >= q]
    return float(np.mean(tail)) if len(tail) > 0 else float(q)

def stable_seed(*parts: Any) -> int:
    s = "|".join(str(p) for p in parts)
    h = hashlib.md5(s.encode("utf-8")).hexdigest()
    return int(h[:8], 16)

def get_travel_time(origin_type: str, origin_location: str, counter: str) -> float:
    db = {
        "railroad": RAILROAD_TO_CHECKIN,
        "bus": BUS_TO_CHECKIN,
        "taxi": TAXI_TO_CHECKIN,
        "parking": PARKING_TO_CHECKIN,
        "checkin": {counter: {}}, # For Q1, travel_to_checkin is 0
    }.get(origin_type, {})
    return db.get(origin_location, {}).get(counter, 10.0) # Default 10 min if not found

def print_recommendations(title: str, result: Dict[str, Any]):
    typer.secho(f"\n--- {title} ---", fg=typer.colors.BLUE)
    typer.echo(f"Data Source: {result['data_source']} | Quality: {result['quality_score']:.2f} | Timestamp: {result['collected_at']}")
    
    for i, route in enumerate(result["top3_routes"], 1):
        comps = route["components"]
        typer.secho(f"\n{i}. Route: {route['origin']} -> {route['checkin_counter']} -> {route['gate_id']}", bold=True)
        typer.echo(
            f"   - Score: {route['score']:.2f} (Risk Metric: {comps['risk_metric']:.1f} min)"
            f" | Wait Time (μ/σ): {route['gate_wait_dist']['mu']:.1f}/{route['gate_wait_dist']['sigma']:.1f} min"
        )
        typer.echo(
            f"   - Penalties (Hysteresis/Miss/Risk): {comps['hysteresis']:.1f}/{comps['miss_penalty']:.1f}/{comps['risk_penalty']:.1f}"
        )
    typer.secho("\nExplanation:", fg=typer.colors.YELLOW)
    typer.echo(result["explanation"])