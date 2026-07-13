import json
import os
from concurrent.futures import ThreadPoolExecutor
from typing import Any, Dict, List, Tuple

from dotenv import load_dotenv

load_dotenv()

try:
    from google import genai
    from google.genai import types

    GEMINI_AVAILABLE = True
except ImportError:  # pragma: no cover - depends on environment
    genai = None
    types = None
    GEMINI_AVAILABLE = False

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

AGENT_INSTRUCTIONS: Dict[str, str] = {
    "Aggressive": (
        "You are the Aggressive Oracle agent. Assume the worst-case interpretation of any "
        "ambiguous signal and err on the side of danger when evaluating a plant state."
    ),
    "Conservative": (
        "You are the Conservative Oracle agent. Assume normal operations unless there is strong, "
        "explicit evidence of danger."
    ),
    "Adversarial": (
        "You are the Adversarial Oracle agent. Specifically look for what the other agents might "
        "miss and argue for the more dangerous interpretation whenever there is any doubt."
    ),
}


def _normalize_oracle_result(result: Any) -> Dict[str, Any]:
    if isinstance(result, dict):
        return {
            "risk_score": int(result.get("risk_score", 0)),
            "flagged_zone": str(result.get("flagged_zone", "unknown")),
            "reasoning": str(result.get("reasoning", "No reasoning provided.")),
        }

    return {
        "risk_score": 0,
        "flagged_zone": "unknown",
        "reasoning": "No reasoning provided.",
    }


def _call_oracle_agent(plant_state: Dict[str, Any], agent_name: str, system_instruction: str) -> Dict[str, Any]:
    """Call the Gemini API for a single Oracle agent with a custom system instruction."""
    if not GEMINI_AVAILABLE or not GEMINI_API_KEY:
        return {
            "risk_score": 50,
            "flagged_zone": "unknown",
            "reasoning": f"{agent_name} agent is unavailable because Gemini is not configured.",
        }

    try:
        client = genai.Client(api_key=GEMINI_API_KEY)
        user_content = (
            "Analyze this industrial plant safety state and return valid JSON only with this shape: "
            '{"risk_score": number, "flagged_zone": string, "reasoning": string}. '
            f"Plant state: {json.dumps(plant_state)}"
        )

        response = client.models.generate_content(
            model="gemini-2.5-flash",
            contents=[{"role": "user", "parts": [{"text": user_content}]}],
            config=types.GenerateContentConfig(
                system_instruction=system_instruction,
                response_mime_type="application/json",
            ),
        )

        response_text = response.text.strip()
        if response_text.startswith("```"):
            response_text = response_text.split("```")[1]
            if response_text.startswith("json"):
                response_text = response_text[4:]
        response_text = response_text.strip()

        parsed = json.loads(response_text)
        return _normalize_oracle_result(parsed)
    except Exception as exc:  # pragma: no cover - network or API issues
        return {
            "risk_score": 0,
            "flagged_zone": "unknown",
            "reasoning": f"{agent_name} agent failed: {exc}",
        }


def runOracleSwarm(plantState: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Run the Oracle Swarm in parallel and return one result per agent."""
    agents: List[Tuple[str, str]] = [
        ("Aggressive", AGENT_INSTRUCTIONS["Aggressive"]),
        ("Conservative", AGENT_INSTRUCTIONS["Conservative"]),
        ("Adversarial", AGENT_INSTRUCTIONS["Adversarial"]),
    ]

    with ThreadPoolExecutor(max_workers=3) as executor:
        futures = [
            executor.submit(_call_oracle_agent, plantState, agent_name, instruction)
            for agent_name, instruction in agents
        ]
        results = [future.result() for future in futures]

    return [
        {"agent": agent_name, **result}
        for (agent_name, _), result in zip(agents, results)
    ]
