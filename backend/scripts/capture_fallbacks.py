"""
One-time capture script: hits real Gemini-backed endpoints for a chosen set
of units and saves the successful responses to backend/data/fallback_responses.json.

Run this only when Gemini quota is available. Each unit costs:
  - 1 call for risk-assessment (guardrail-check reuses this via cache if run
    within the same 30-min window, so no extra cost there)
  - 1 call for compliance-audit
  - 3 calls for oracle-swarm (Aggressive/Conservative/Adversarial agents)
  Total: 5 Gemini requests per unit.

Usage:
    python capture_fallbacks.py unit-1 unit-2
"""

import json
import sys
from pathlib import Path

import httpx

BASE_URL = "http://127.0.0.1:8000/api"
OUTPUT_FILE = Path(__file__).resolve().parent / "data" / "fallback_responses.json"


def capture_unit(client: httpx.Client, unit_id: str) -> dict:
    print(f"\n--- Capturing fallbacks for {unit_id} ---")
    result = {}

    print("  -> risk-assessment (1 Gemini call)...")
    res = client.get(f"{BASE_URL}/risk-assessment/{unit_id}", timeout=30.0)
    data = res.json()
    if not data.get("error"):
        result["risk_assessment"] = data
        print(f"     OK: risk_score={data.get('risk_score')}, risk_level={data.get('risk_level')}")
    else:
        print(f"     SKIPPED (error): {data.get('error')[:100]}")

    print("  -> guardrail-check (0 calls if cache hit)...")
    res = client.get(f"{BASE_URL}/guardrail-check/demo/{unit_id}", timeout=30.0)
    data = res.json()
    guardrail_result = data.get("guardrail_result", {})
    if not (guardrail_result.get("reasoning", "").startswith("Gemini API call failed")):
        result["guardrail_check"] = data
        print(f"     OK: risk_score={guardrail_result.get('risk_score')}")
    else:
        print("     SKIPPED (error)")

    print("  -> compliance-audit (1 Gemini call)...")
    res = client.get(f"{BASE_URL}/compliance-audit/{unit_id}", timeout=30.0)
    data = res.json()
    if not data.get("error"):
        result["compliance_audit"] = data
        print(f"     OK: compliance_status={data.get('compliance_status')}")
    else:
        print(f"     SKIPPED (error): {data.get('error')[:100]}")

    print("  -> oracle-swarm (3 Gemini calls)...")
    res = client.get(f"{BASE_URL}/oracle-swarm/{unit_id}", timeout=60.0)
    data = res.json()
    agents = data.get("agents", [])
    failed_agents = [a for a in agents if "unavailable" in str(a.get("lines", [])).lower() or "failed" in str(a.get("lines", [])).lower()]
    if agents and len(failed_agents) == 0:
        result["oracle_swarm"] = data
        print(f"     OK: {len(agents)} agents captured")
    else:
        print(f"     PARTIAL/SKIPPED: {len(failed_agents)}/{len(agents)} agents failed")

    return result


def main():
    unit_ids = sys.argv[1:] if len(sys.argv) > 1 else ["unit-1"]
    print(f"Capturing fallbacks for: {unit_ids}")
    print(f"Estimated Gemini calls: {len(unit_ids) * 5}")

    confirm = input("Proceed? (y/n): ").strip().lower()
    if confirm != "y":
        print("Aborted.")
        return

    OUTPUT_FILE.parent.mkdir(parents=True, exist_ok=True)

    existing = {}
    if OUTPUT_FILE.exists():
        with OUTPUT_FILE.open("r", encoding="utf-8") as fh:
            existing = json.load(fh)

    with httpx.Client() as client:
        for unit_id in unit_ids:
            captured = capture_unit(client, unit_id)
            if captured:
                existing[unit_id] = captured

    with OUTPUT_FILE.open("w", encoding="utf-8") as fh:
        json.dump(existing, fh, indent=2)

    print(f"\nSaved to {OUTPUT_FILE}")
    print(f"Units with captured data: {list(existing.keys())}")


if __name__ == "__main__":
    main()
