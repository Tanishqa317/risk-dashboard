"""
Run this ONCE per unit whenever Gemini quota is working, to capture a real
Oracle Swarm response and save it as a permanent fallback. This protects
the live demo from quota exhaustion — if all 3 agents fail during a demo,
the route will automatically serve this captured real response instead of
showing "UNAVAILABLE".

Usage: python capture_oracle_fallbacks.py unit-1
       python capture_oracle_fallbacks.py unit-2
       ... etc for each unit you want covered.
"""
import asyncio
import json
import sys
from pathlib import Path

from app.routes.Oracle_Swarm import get_oracle_swarm

FALLBACK_PATH = Path("data/fallback_responses.json")


async def capture(unit_id: str):
    print(f"Fetching real Oracle Swarm response for {unit_id}...")
    result = await get_oracle_swarm(unit_id)

    any_failed = result.get("any_agent_failed", False)
    if any_failed:
        print(f"  WARNING: at least one agent failed for {unit_id} — not saving this as a fallback.")
        print(f"  (Quota may still be exhausted, or a transient error occurred. Try again later.)")
        return False

    data = json.loads(FALLBACK_PATH.read_text()) if FALLBACK_PATH.exists() else {}
    data.setdefault(unit_id, {})["oracle_swarm"] = result
    FALLBACK_PATH.write_text(json.dumps(data, indent=2))

    print(f"  SUCCESS: saved real oracle_swarm response for {unit_id}")
    print(f"  Consensus: {result.get('consensus', {}).get('final_verdict')}")
    return True


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python capture_oracle_fallbacks.py <unit_id>")
        print("Example: python capture_oracle_fallbacks.py unit-1")
        sys.exit(1)

    unit_id = sys.argv[1]
    asyncio.run(capture(unit_id))