import importlib
import json
import os
from concurrent.futures import ThreadPoolExecutor
from typing import Any, Dict, List, TypedDict


types: Any = None
gemini_available: bool = False

try:
    genai = importlib.import_module("google.genai")
    types = getattr(genai, "types", None)
    gemini_available = True
except ImportError:  # pragma: no cover
    genai = None
    types = None
    gemini_available = False

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


class AgentResult(TypedDict):
    risk_score: int
    flagged_zone: str
    reasoning: str


def _normalize_oracle_result(result: Dict[str, Any]) -> AgentResult:
    return {
        "risk_score": int(result.get("risk_score", 0)),
        "flagged_zone": str(result.get("flagged_zone", "unknown")),
        "reasoning": str(result.get("reasoning", "No reasoning provided.")),
    }


def _call_oracle_agent(plant_state: Dict[str, Any], agent_name: str, system_instruction: str) -> AgentResult:
    """Call Gemini with a custom system instruction for one Oracle agent."""
    if not gemini_available or not GEMINI_API_KEY:
        return {
            "risk_score": 50,
            "flagged_zone": "unknown",
            "reasoning": f"{agent_name} agent is unavailable because Gemini is not configured.",
        }

    assert genai is not None
    assert types is not None

    try:
        client: Any = genai.Client(api_key=GEMINI_API_KEY)  # type: ignore[attr-defined]
        user_content = (
            "Analyze this industrial plant safety state and return valid JSON only with this shape: "
            '{"risk_score": number, "flagged_zone": string, "reasoning": string}. '
            f"Plant state: {json.dumps(plant_state)}"
        )

        response: Any = client.models.generate_content(
            model="gemini-2.5-flash",
            contents=[{"role": "user", "parts": [{"text": user_content}]}],
            config=types.GenerateContentConfig(  # type: ignore[attr-defined]
                system_instruction=system_instruction,
                response_mime_type="application/json",
            ),
        )

        response_text = str(getattr(response, "text", "")).strip()
        if response_text.startswith("```"):
            response_text = response_text.split("```")[1]
            if response_text.startswith("json"):
                response_text = response_text[4:]
        response_text = response_text.strip()

        parsed: Dict[str, Any] = json.loads(response_text)
        return _normalize_oracle_result(parsed)
    except Exception as exc:  # pragma: no cover
        return {
            "risk_score": 0,
            "flagged_zone": "unknown",
            "reasoning": f"{agent_name} agent failed: {exc}",
        }


def runOracleSwarm(plantState: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Run the Oracle Swarm in parallel and return all three agent results."""
    agents = [
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


def resolveConsensus(swarmResults: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Resolve a final verdict from the Oracle Swarm results."""
    high_count = sum(1 for result in swarmResults if result.get("risk_score", 0) > 70)
    final_verdict = "high" if high_count >= 2 else "low"
    consensus = high_count >= 2

    return {
        "final_verdict": final_verdict,
        "consensus": consensus,
        "agent_results": swarmResults,
    }


if __name__ == "__main__":
    import sys

    try:
        plant_state = json.load(sys.stdin)
    except json.JSONDecodeError as exc:
        sys.stderr.write(f"Invalid JSON input: {exc}\n")
        sys.exit(1)

    swarm_results = runOracleSwarm(plant_state)
    consensus_result = resolveConsensus(swarm_results)
    output: Dict[str, Any] = {
        "agent_results": swarm_results,
        **consensus_result,
    }
    print(json.dumps(output))
