import json
import os
from datetime import datetime, timedelta, timezone
from typing import Dict, List, Optional
from pathlib import Path
from dotenv import load_dotenv

FALLBACK_FILE = Path(__file__).resolve().parents[2] / "data" / "fallback_responses.json"


def _load_fallback_compliance(unit_id: str) -> Optional[Dict]:
    """Return a previously-captured real compliance_audit for this unit, if any."""
    if not FALLBACK_FILE.exists():
        return None
    try:
        with FALLBACK_FILE.open("r", encoding="utf-8") as fh:
            fallbacks = json.load(fh)
        return fallbacks.get(unit_id, {}).get("compliance_audit")
    except Exception:
        return None

try:
    from google import genai
    GEMINI_AVAILABLE = True
except ImportError:
    GEMINI_AVAILABLE = False

from app.services.rag_service import retrieve_relevant
from app.models.guardrail_models import EngineOutput, PlantState, ZoneState, Permit
from app.services.guardrail_service import check_guardrail

load_dotenv()

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")


def _gather_current_state(unit_id: str) -> Dict:
    """Gather current operational state for a unit."""
    state = {
        "unit_id": unit_id,
        "permits": [],
        "staffing_level": "unknown",
        "guardrail_violations": [],
        "recent_alarms": 0,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }

    try:
        import pandas as pd
        data_dir = Path(__file__).resolve().parents[3] / "data"
        csv_path = data_dir / "combined_dataset.csv"

        if csv_path.exists():
            df = pd.read_csv(csv_path)
            unit_data = df[df["unit_id"] == unit_id]

            if not unit_data.empty:
                state["staffing_level"] = str(unit_data.iloc[0].get("shift_staffing", "unknown"))

                permit_ids = unit_data["permit_id"].dropna().unique()
                for permit_id in permit_ids:
                    permit_data = unit_data[unit_data["permit_id"] == permit_id].iloc[0]
                    state["permits"].append({
                        "permit_id": str(permit_id),
                        "zone_id": str(permit_data.get("zone_id", "")),
                        "status": str(permit_data.get("permit_status", "")),
                        "type": "hot-work" if "hot" in str(permit_data.get("permit_status", "")).lower() else "general",
                    })
    except Exception as e:
        pass

    try:
        from app.services.guardrail_service import check_guardrail
        from app.models.guardrail_models import PlantState, ZoneState, Permit, EngineOutput

        plant_state = PlantState(
            zones=[
                ZoneState(
                    zone_id=f"{unit_id}-zone-1",
                    gas_ppm=250.0,
                    active_permits=[Permit(permit_type="hot-work")],
                    supervisors_present=1,
                )
            ]
        )
        engine_output = EngineOutput(
            risk_score=25,
            flagged_zone=f"{unit_id}-zone-1",
            reasoning="Baseline",
            contributing_factors=["baseline"],
        )
        result = check_guardrail(plant_state, engine_output)
        if result.overridden:
            state["guardrail_violations"].append(result.reasoning)
    except Exception:
        pass

    try:
        from app.services.alarm_fatigue_service import generate_demo_alerts, detect_alarm_fatigue

        alerts = generate_demo_alerts(unit_id)
        fatigue_result = detect_alarm_fatigue(alerts)
        state["recent_alarms"] = fatigue_result.alert_count_last_hour
    except Exception:
        pass

    return state


def audit_unit_compliance(unit_id: str) -> Dict:
    """Audit a unit's compliance against regulatory standards."""

    if not GEMINI_AVAILABLE or not GEMINI_API_KEY:
        fallback = _load_fallback_compliance(unit_id)
        if fallback is not None:
            result = dict(fallback)
            result["error"] = None
            result["fallback_used"] = True
            return result
        return {
            "unit_id": unit_id,
            "compliance_status": "unknown",
            "anomalies": [],
            "error": "Gemini API not available",
            "fallback_used": False,
        }

    try:
        current_state = _gather_current_state(unit_id)

        query = "compliance audit permit staffing safety procedures supervision"
        guidance_chunks = retrieve_relevant(query, top_k=5)

        if not guidance_chunks:
            regulatory_context = "No relevant regulatory guidance found in knowledge base."
        else:
            regulatory_context = "\n\n".join(
                [f"From {chunk['source']}:\n{chunk['text']}" for chunk in guidance_chunks]
            )

        state_summary = f"""
Unit ID: {unit_id}
Active Permits: {len(current_state['permits'])} permits
  - Types: {', '.join(set(p.get('type', 'unknown') for p in current_state['permits']))}
  - Statuses: {', '.join(set(p.get('status', 'unknown') for p in current_state['permits']))}
Shift Staffing: {current_state['staffing_level']}
Guardrail Violations: {len(current_state['guardrail_violations'])} found
  - {'; '.join(current_state['guardrail_violations']) if current_state['guardrail_violations'] else 'None'}
Recent Alarms (Last Hour): {current_state['recent_alarms']}
"""

        client = genai.Client(api_key=GEMINI_API_KEY)

        # NOTE: Schema changed from three parallel arrays (deviations_found /
        # corrective_actions / regulatory_references) to a single array of
        # objects. The old shape had no structural guarantee that index i in
        # each array referred to the same anomaly, and mismatched lengths
        # caused the frontend to backfill placeholder strings like
        # "No citation provided" as if they were real audit content.
        system_prompt = (
            "You are a compliance audit agent. Given current operational state and relevant regulatory guidance, "
            "identify compliance deviations and output ONLY valid JSON with this exact shape: "
            "{compliance_status: 'compliant'|'minor_deviation'|'major_deviation', "
            "anomalies: [{deviation: string, corrective_action: string, regulatory_reference: string}]}. "
            "Each anomaly object MUST include all three fields fully populated. "
            "If you cannot find a specific regulatory citation for a deviation, do not include that "
            "deviation in the anomalies array at all rather than leaving a field blank or vague. "
            "Respond with ONLY the JSON object, no markdown, no preamble."
        )

        user_content = f"""
Current Operational State for {unit_id}:
{state_summary}

Relevant Regulatory Guidance:
{regulatory_context}

Please audit this unit's compliance against the provided regulatory standards.
"""

        response = client.models.generate_content(
            model="gemini-flash-latest",
            contents=[{"role": "user", "parts": [{"text": user_content}]}],
            config={
                "system_instruction": system_prompt,
                "response_mime_type": "application/json",
            },
        )

        response_text = response.text.strip()

        if response_text.startswith("```"):
            response_text = response_text.split("```")[1]
            if response_text.startswith("json"):
                response_text = response_text[4:]
        response_text = response_text.strip()

        result = json.loads(response_text)

        # Defense-in-depth: even with the new schema, drop any anomaly
        # object that Gemini returned with a missing/empty field instead of
        # ever surfacing a placeholder string to the frontend.
        raw_anomalies = result.get("anomalies", [])
        clean_anomalies = [
            a for a in raw_anomalies
            if isinstance(a, dict)
            and str(a.get("deviation", "")).strip()
            and str(a.get("corrective_action", "")).strip()
            and str(a.get("regulatory_reference", "")).strip()
        ]

        return {
            "unit_id": unit_id,
            "compliance_status": result.get("compliance_status", "unknown"),
            "anomalies": clean_anomalies,
            "current_state_summary": state_summary,
            "fallback_used": False,
        }

    except json.JSONDecodeError as e:
        fallback = _load_fallback_compliance(unit_id)
        if fallback is not None:
            result = dict(fallback)
            result["error"] = None
            result["fallback_used"] = True
            return result
        return {
            "unit_id": unit_id,
            "compliance_status": "unknown",
            "anomalies": [],
            "error": f"Failed to parse Gemini response: {str(e)}",
            "fallback_used": False,
        }
    except Exception as e:
        fallback = _load_fallback_compliance(unit_id)
        if fallback is not None:
            result = dict(fallback)
            result["error"] = None
            result["fallback_used"] = True
            return result
        return {
            "unit_id": unit_id,
            "compliance_status": "unknown",
            "anomalies": [],
            "error": str(e),
            "fallback_used": False,
        }