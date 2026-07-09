import os
import json
from pathlib import Path
from typing import Dict, Optional
import pandas as pd
from dotenv import load_dotenv
from google.genai import types

# Load environment
load_dotenv()

try:
    from google import genai
    GEMINI_AVAILABLE = True
except ImportError:
    GEMINI_AVAILABLE = False

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

DATA_DIR = Path(__file__).resolve().parents[2] / "data"
COMBINED_CSV = DATA_DIR / "combined_dataset.csv"


def build_context(unit_id: str) -> Dict:
    """Build a compact context summary for a unit from recent readings.
    
    Returns dict with: unit_id, recent_readings (grouped by sensor_type), 
    active_permits_count, expired_permits_count, shift_staffing
    """
    if not Path(COMBINED_CSV).exists():
        return {
            "unit_id": unit_id,
            "error": f"Data file not found: {COMBINED_CSV}",
            "recent_readings": {},
            "active_permits": 0,
            "expired_permits": 0,
            "shift_staffing": "unknown",
        }

    df = pd.read_csv(COMBINED_CSV)
    df["timestamp"] = pd.to_datetime(df["timestamp"])

    unit_data = df[df["unit_id"] == unit_id].sort_values("timestamp", ascending=False)

    if unit_data.empty:
        return {
            "unit_id": unit_id,
            "error": f"No data found for unit_id: {unit_id}",
            "recent_readings": {},
            "active_permits": 0,
            "expired_permits": 0,
            "shift_staffing": "unknown",
        }

    recent_readings = {}
    for sensor_type in unit_data["sensor_type"].unique():
        sensor_data = unit_data[unit_data["sensor_type"] == sensor_type].head(5)
        recent_readings[sensor_type] = [
            {
                "value": float(row["sensor_value"]),
                "timestamp": row["timestamp"].isoformat(),
            }
            for _, row in sensor_data.iterrows()
        ]

    active_permits = (unit_data["permit_status"] == "active").sum()
    expired_permits = (unit_data["permit_status"] == "expired").sum()
    shift_staffing = unit_data["shift_staffing"].iloc[0] if not unit_data.empty else "unknown"

    return {
        "unit_id": unit_id,
        "recent_readings": recent_readings,
        "active_permits": int(active_permits),
        "expired_permits": int(expired_permits),
        "shift_staffing": str(shift_staffing),
    }


def call_gemini_for_risk_score(context: Dict) -> Dict:
    """Call Gemini API with JSON mode to get risk assessment.
    
    Returns dict with: risk_score, risk_level, primary_concern, reasoning
    On error, returns error dict.
    """
    if not GEMINI_AVAILABLE or not GEMINI_API_KEY:
        return {
            "error": "Gemini API not available or GEMINI_API_KEY not set",
            "risk_score": 50,
            "risk_level": "unknown",
            "primary_concern": "API unavailable",
            "reasoning": "Gemini API is not configured.",
        }

    try:
        client = genai.Client(api_key=GEMINI_API_KEY)

        system_prompt = (
            "You are an industrial safety risk analyst. Given sensor readings, permit status, "
            "and shift staffing for a plant unit, output a JSON object with: "
            "risk_score (0-100), risk_level (low/medium/high/critical), "
            "primary_concern (short string), reasoning (2-3 sentence explanation). "
            "Respond with ONLY valid JSON, no markdown, no preamble."
        )

        user_content = f"Analyze this plant unit data for risk: {json.dumps(context)}"

        # Fixed syntax to map system instruction and generation configurations correctly
        response = client.models.generate_content(
            model="gemini-2.5-flash",
            contents=[
                {
                    "role": "user",
                    "parts": [{"text": user_content}],
                }
            ],
            config=types.GenerateContentConfig(
                system_instruction=system_prompt,
                response_mime_type="application/json",
            ),
        )

        response_text = response.text.strip()
        
        # Try to extract JSON if there's markdown wrapping
        if response_text.startswith("```"):
            response_text = response_text.split("```")[1]
            if response_text.startswith("json"):
                response_text = response_text[4:]
        response_text = response_text.strip()

        result = json.loads(response_text)
        return {
            "risk_score": int(result.get("risk_score", 50)),
            "risk_level": str(result.get("risk_level", "unknown")),
            "primary_concern": str(result.get("primary_concern", "")),
            "reasoning": str(result.get("reasoning", "")),
        }

    except json.JSONDecodeError as e:
        return {
            "error": f"Failed to parse Gemini response as JSON: {str(e)}",
            "risk_score": 50,
            "risk_level": "error",
            "primary_concern": "Response parsing failed",
            "reasoning": f"Could not parse Gemini response: {str(e)}",
        }
    except Exception as e:
        return {
            "error": f"Gemini API error: {str(e)}",
            "risk_score": 50,
            "risk_level": "error",
            "primary_concern": "API error",
            "reasoning": f"Gemini API call failed: {str(e)}",
        }


def get_risk_assessment(unit_id: str) -> Dict:
    """Get full risk assessment for a unit.
    
    Combines build_context and call_gemini_for_risk_score.
    Returns dict with unit_id, risk_score, risk_level, primary_concern, reasoning.
    """
    context = build_context(unit_id)
    risk_data = call_gemini_for_risk_score(context)
    
    return {
        "unit_id": unit_id,
        "risk_score": risk_data.get("risk_score", 50),
        "risk_level": risk_data.get("risk_level", "error"),
        "primary_concern": risk_data.get("primary_concern", ""),
        "reasoning": risk_data.get("reasoning", ""),
        "error": risk_data.get("error"),
    }