import httpx
from fastapi import APIRouter, Query

router = APIRouter()
BASE_URL = "http://127.0.0.1:8000/api"

GAS_DANGER_THRESHOLD = 200  # ppm — consistent with the elevated levels already seen in guardrail data

# Deterministic quadrant centers per zone-id suffix, so positions are stable
# across reloads without needing real spatial data from any endpoint.
_ZONE_QUADRANTS = {
    "zone-1": (0.2, 0.25),
    "zone-2": (0.75, 0.3),
    "zone-3": (0.45, 0.75),
}

PRIMARY_EXIT = {"id": "EXIT", "x": 0.92, "y": 0.88, "label": "EXIT GATE"}
ALT_EXIT = {"id": "ALT-EXIT", "x": 0.92, "y": 0.18, "label": "ALT GATE"}


def _seeded_offset(seed_str: str) -> tuple[float, float]:
    seed = sum(ord(c) for c in seed_str)
    dx = ((seed % 17) - 8) / 100  # small deterministic spread within a quadrant
    dy = ((seed * 3 % 19) - 9) / 100
    return dx, dy


@router.get("/evac-routing")
async def get_evac_routing(unit_id: str = Query(default="unit-1"), compromised: bool = Query(default=False)):
    async with httpx.AsyncClient() as client:
        try:
            permit_res = await client.get(f"{BASE_URL}/permit-gaming-check/demo/{unit_id}", timeout=10.0)
            permits_data = permit_res.json() if permit_res.status_code == 200 else {}
        except Exception:
            permits_data = {}
        try:
            guardrail_res = await client.get(f"{BASE_URL}/guardrail-check/demo/{unit_id}", timeout=10.0)
            guardrail_data = guardrail_res.json() if guardrail_res.status_code == 200 else {}
        except Exception:
            guardrail_data = {}

    zones = guardrail_data.get("plant_state", {}).get("zones", [])
    raw_permits = permits_data.get("permits", [])

    # Dedupe permits by permit_id (source endpoint currently repeats entries)
    seen = {}
    for p in raw_permits:
        seen[p.get("permit_id")] = p
    permits = list(seen.values())

    # Build worker nodes from real permits, positioned by their real zone_id
    workers = []
    for p in permits:
        zone_id = p.get("zone_id", "unit-1-zone-1")
        quadrant_key = next((k for k in _ZONE_QUADRANTS if k in zone_id), "zone-1")
        base_x, base_y = _ZONE_QUADRANTS[quadrant_key]
        dx, dy = _seeded_offset(p.get("permit_id", zone_id))
        workers.append(
            {
                "id": p.get("permit_id", zone_id),
                "label": p.get("permit_id", zone_id),
                "x": round(min(0.95, max(0.05, base_x + dx)), 3),
                "y": round(min(0.95, max(0.05, base_y + dy)), 3),
            }
        )

    # Danger zones from real gas_ppm readings
    danger_zones = []
    worst_zone_key = None
    worst_ppm = -1
    for z in zones:
        zone_id = z.get("zone_id", "")
        quadrant_key = next((k for k in _ZONE_QUADRANTS if k in zone_id), "zone-1")
        ppm = z.get("gas_ppm", 0)
        if ppm > worst_ppm:
            worst_ppm = ppm
            worst_zone_key = quadrant_key
        if ppm > GAS_DANGER_THRESHOLD or compromised:
            base_x, base_y = _ZONE_QUADRANTS[quadrant_key]
            radius = 60 + min(80, ppm / 5) + (30 if compromised else 0)
            danger_zones.append({"x": base_x, "y": base_y, "r": round(radius, 1), "zone_id": zone_id, "gas_ppm": ppm})

    # Pick exit farthest from the worst zone when compromised
    exit_gate = ALT_EXIT if (compromised and worst_zone_key in ("zone-1", "zone-3")) else PRIMARY_EXIT

    avg_ppm = sum(z.get("gas_ppm", 0) for z in zones) / max(1, len(zones))
    base_eta_minutes = 2 + (avg_ppm / 100)
    eta_minutes = base_eta_minutes + (0.7 if compromised else 0)  # rerouting overhead
    eta_str = f"{int(eta_minutes):02d}:{int((eta_minutes % 1) * 60):02d}"

    return {
        "unit_id": unit_id,
        "compromised": compromised,
        "workers": workers,
        "danger_zones": danger_zones,
        "exit": exit_gate,
        "active_paths": [{"worker_id": w["id"], "status": "REROUTED" if compromised else "OPTIMAL"} for w in workers],
        "evac_eta": eta_str,
        "eta_note": f"+{0.7:.1f}min rerouting overhead" if compromised else "avg · all paths nominal",
    }