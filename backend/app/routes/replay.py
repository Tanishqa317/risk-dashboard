import math
import random
from fastapi import APIRouter, Query

router = APIRouter()

# Deterministic crisis-window narrative, keyed by relative time (0.0-1.0 across a 24h window).
# Mirrors the story already used in the frontend mock so the visual and the data agree.
_TIMELINE_TEMPLATE = [
    {"t": 0.04, "label": "Permit issued", "tone": "mint", "zone": "zone-1"},
    {"t": 0.12, "label": "Gas concentration +18ppm", "tone": "amber", "zone": "zone-1"},
    {"t": 0.23, "label": "Permit gaming detected", "tone": "crimson", "zone": "zone-2"},
    {"t": 0.34, "label": "Guardrail override blocked", "tone": "mint", "zone": "zone-2"},
    {"t": 0.46, "label": "Vibration anomaly detected", "tone": "amber", "zone": "zone-3"},
    {"t": 0.58, "label": "Counterfactual divergence peak", "tone": "crimson", "zone": "zone-3"},
    {"t": 0.71, "label": "Sensor flatline", "tone": "crimson", "zone": "zone-1"},
    {"t": 0.83, "label": "Evacuation route recalculated", "tone": "mint", "zone": "zone-2"},
    {"t": 0.92, "label": "Incident contained", "tone": "mint", "zone": "zone-3"},
]


def _generate_series(unit_id: str, mode: str, points: int = 200) -> list[float]:
    """
    Deterministic pseudo-telemetry series, seeded by unit_id so the same unit
    always produces the same curve (no true randomness — random.Random(seed)
    is fully reproducible, so demos stay repeatable).

    mode: 'history'         -> stable, lightly-noisy recovery pattern
          'counterfactual'  -> growing instability (no guardrail intervention),
                               amplitude/frequency ramp up but stay bounded so
                               the line never clips the chart edges
    """
    seed = sum(ord(c) for c in unit_id)
    rng = random.Random(seed)
    base = 50 + 6 * math.sin(seed)

    series = []
    for i in range(points):
        x = i / points
        noise = rng.uniform(-1.5, 1.5)
        smooth = 10 * math.sin(2 * math.pi * x * 3 + seed * 0.7)

        if mode == "history":
            # oscillation gently damps toward baseline -> reads as "recovered/stable"
            damp = max(0.3, 1 - x * 0.6)
            value = base + smooth * damp + noise
        else:
            # growth ramps 0 -> 1 across the window and then holds, so amplitude
            # and frequency both increase but never runs away unbounded
            growth = min(1.0, max(0.0, (x - 0.2) / 0.8))
            freq = 5 + 15 * growth
            amplitude = 22 * growth
            instability = amplitude * math.sin(2 * math.pi * x * freq + seed)
            value = base + smooth * 0.4 + instability + noise * (1 + growth)
            # hard safety clamp so the render never touches chart bounds
            value = max(base - 45, min(base + 45, value))

        series.append(round(value, 2))
    return series


@router.get("/replay")
def get_replay(unit_id: str = Query(default="unit-1", description="Unit to replay")):
    return {
        "unit_id": unit_id,
        "window_hours": 24,
        "timeline": _TIMELINE_TEMPLATE,
        "historical_series": _generate_series(unit_id, "history"),
        "counterfactual_series": _generate_series(unit_id, "counterfactual"),
    }