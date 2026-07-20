import importlib
import json
import os
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from typing import Any, Dict, List, TypedDict

import httpx
from fastapi import APIRouter

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

FALLBACK_FILE = Path(__file__).resolve().parents[2] / "data" / "fallback_responses.json"


def _load_fallback_oracle_swarm(unit_id: str):
    """Return a previously-captured real oracle-swarm response for this unit, if any."""
    if not FALLBACK_FILE.exists():
        return None
    try:
        with FALLBACK_FILE.open("r", encoding="utf-8") as fh:
            fallbacks = json.load(fh)
        return fallbacks.get(unit_id, {}).get("oracle_swarm")
    except Exception:
        return None


AGENT_INSTRUCTIONS: Dict[str, str] = {
    "Aggressive": (
        "You are the Aggressive Oracle agent. Assume the worst-case interpretation of any "
        "ambiguous signal and err on the side of danger when evaluating a plant state. "
        "Your risk_score MUST directly reflect the severity of your own reasoning: if your "
        "reasoning describes a catastrophic, lethal, or emergency scenario, risk_score must be "
        "80-100. If it describes a serious but non-immediate concern, risk_score must be 50-79. "
        "Only use a score below 50 if your reasoning genuinely supports a low-danger conclusion. "
        "Never describe a catastrophic scenario and then assign a low risk_score — the number and "
        "the reasoning must agree."
    ),
    "Conservative": (
        "You are the Conservative Oracle agent. Assume normal operations unless there is strong, "
        "explicit evidence of danger. Your risk_score MUST directly reflect the severity of your "
        "own reasoning: if you conclude operations are normal, risk_score must be 0-30. If you find "
        "explicit evidence of a real problem, raise the score to match its severity (50+). Never "
        "describe a dangerous finding and then assign a low risk_score — the number and the "
        "reasoning must agree."
    ),
    "Adversarial": (
        "You are the Adversarial Oracle agent. Specifically look for what the other agents might "
        "miss and argue for the more dangerous interpretation whenever there is any doubt. Your "
        "risk_score MUST directly reflect the severity of your own reasoning: if your reasoning "
        "describes a catastrophic, lethal, or emergency scenario, risk_score must be 80-100. If it "
        "describes a serious but non-immediate concern, risk_score must be 50-79. Never describe a "
        "catastrophic scenario and then assign a low risk_score — the number and the reasoning must "
        "agree."
    ),
}


class AgentResult(TypedDict, total=False):
    risk_score: int
    flagged_zone: str
    reasoning: str
    failed: bool  # True when Gemini could not be reached/parsed — result is NOT a real verdict


def _normalize_oracle_result(result: Dict[str, Any]) -> AgentResult:
    return {
        "risk_score": int(result.get("risk_score", 0)),
        "flagged_zone": str(result.get("flagged_zone", "unknown")),
        "reasoning": str(result.get("reasoning", "No reasoning provided.")),
        "failed": False,
    }


def _call_oracle_agent(plant_state: Dict[str, Any], agent_name: str, system_instruction: str) -> AgentResult:
    """Call Gemini with a custom system instruction for one Oracle agent.

    Includes one automatic retry specifically for malformed-JSON responses
    (a known LLM imperfection, distinct from quota/access failures), since
    those are often transient and worth one extra attempt before giving up.
    """
    if not gemini_available or not GEMINI_API_KEY:
        return {
            "risk_score": 0,
            "flagged_zone": "unknown",
            "reasoning": f"{agent_name} agent is unavailable because Gemini is not configured.",
            "failed": True,
        }

    assert genai is not None
    assert types is not None

    user_content = (
        "Analyze this industrial plant safety state and return valid JSON only with this shape: "
        '{"risk_score": number, "flagged_zone": string, "reasoning": string}. '
        "IMPORTANT: reasoning must be a single plain sentence or two, with no internal quotation "
        "marks and no line breaks, so the JSON stays valid. "
        f"Plant state: {json.dumps(plant_state)}"
    )

    last_json_error = ""
    for attempt in range(2):  # up to one retry, only for malformed-JSON responses
        try:
            client: Any = genai.Client(api_key=GEMINI_API_KEY)  # type: ignore[attr-defined]

            response: Any = client.models.generate_content(
                model="gemini-flash-latest",
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

        except json.JSONDecodeError as exc:
            last_json_error = str(exc)
            continue  # retry once for malformed JSON specifically

        except Exception as exc:  # pragma: no cover
            err_str = str(exc)
            if "RESOURCE_EXHAUSTED" in err_str or "429" in err_str:
                reasoning = f"{agent_name} agent unavailable — Gemini API quota exceeded (free-tier limit reached)."
            elif "NOT_FOUND" in err_str or "404" in err_str:
                reasoning = f"{agent_name} agent unavailable — configured Gemini model is no longer accessible."
            else:
                reasoning = f"{agent_name} agent failed: {err_str[:120]}"  # trimmed, avoids raw dumps
            return {
                "risk_score": 0,
                "flagged_zone": "unknown",
                "reasoning": reasoning,
                "failed": True,
            }

    # Both attempts produced malformed JSON — give up honestly
    return {
        "risk_score": 0,
        "flagged_zone": "unknown",
        "reasoning": f"{agent_name} agent failed after retry — malformed JSON response: {last_json_error[:120]}",
        "failed": True,
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
    """Resolve a final verdict from the Oracle Swarm results.

    Only agents that actually produced a real result (failed=False) count
    toward consensus — a failed agent contributes neither a "high" nor a
    "low" vote, since it never actually assessed anything.
    """
    valid_results = [r for r in swarmResults if not r.get("failed")]
    high_count = sum(1 for result in valid_results if result.get("risk_score", 0) > 70)
    any_failed = any(r.get("failed") for r in swarmResults)

    if not valid_results:
        return {
            "final_verdict": "unknown",
            "consensus": False,
            "agent_results": swarmResults,
        }

    final_verdict = "high" if high_count >= 2 else "low"
    consensus = high_count >= 2

    return {
        "final_verdict": final_verdict,
        "consensus": consensus,
        "partial_data": any_failed,  # true if fewer than 3 agents actually ran
        "agent_results": swarmResults,
    }


# ---------------------------------------------------------------------------
# FastAPI route — aggregates real plant_state (from guardrail-check) through
# the oracle swarm above, and reshapes it for the frontend. Falls back to a
# previously-captured real response if any agent failed (quota/access/model
# errors) and a fallback exists for this unit. If no fallback exists either,
# failed agents are shown as an honest "UNAVAILABLE" state — never a
# fabricated risk verdict.
# ---------------------------------------------------------------------------

router = APIRouter()
BASE_URL = "http://127.0.0.1:8000/api"


@router.get("/oracle-swarm/{unit_id}")
async def get_oracle_swarm(unit_id: str):
    async with httpx.AsyncClient() as client:
        try:
            res = await client.get(f"{BASE_URL}/guardrail-check/demo/{unit_id}", timeout=10.0)
            guardrail = res.json() if res.status_code == 200 else {}
        except Exception:
            guardrail = {}

    plant_state = guardrail.get("plant_state", {"zones": []})

    swarm_results = runOracleSwarm(plant_state)
    consensus = resolveConsensus(swarm_results)
    any_failed = any(r.get("failed") for r in swarm_results)

    agents = []
    for result in swarm_results:
        name = result.get("agent", "Unknown")
        failed = bool(result.get("failed"))
        risk_score = result.get("risk_score", 0)
        flagged_zone = result.get("flagged_zone", "unknown")
        reasoning = result.get("reasoning", "")

        lines = [
            f"> stance: {name.upper()} ORACLE",
            f"> plant zones analyzed: {len(plant_state.get('zones', []))}",
            f"> flagged zone: {flagged_zone}",
            f"> reasoning: {reasoning}",
        ]

        if failed:
            # Never fabricate a risk verdict for a failed call — be explicit
            # that no real assessment happened.
            verdict = "UNAVAILABLE"
            confidence = 0.0
            lines.append("> verdict: UNAVAILABLE — no risk assessment was produced")
        else:
            confidence = round(min(1.0, max(0.0, risk_score / 100)), 2)
            verdict = "HIGH RISK" if risk_score > 70 else "LOW RISK"
            lines.append(f"> verdict: {verdict} (risk {risk_score}/100)")

        agents.append(
            {
                "id": name,
                "name": f"{name} Oracle",
                "lines": lines,
                "confidence": confidence,
                "verdict": verdict,
                "failed": failed,
            }
        )

    # If any agent failed, prefer a real captured fallback response over
    # showing degraded/unavailable agents, IF a fallback actually exists.
    if any_failed:
        fallback = _load_fallback_oracle_swarm(unit_id)
        if fallback is not None:
            fallback = dict(fallback)
            fallback["fallback_used"] = True
            return fallback

    valid_scores = [r.get("risk_score", 0) for r in swarm_results if not r.get("failed")]
    avg_risk = sum(valid_scores) / len(valid_scores) if valid_scores else 0
    max_window_seconds = 6 * 3600  # tune if a different ceiling fits the demo better
    countdown_seconds = int(max_window_seconds * (1 - avg_risk / 100)) if valid_scores else None

    return {
        "unit_id": unit_id,
        "countdown_seconds": countdown_seconds,
        "consensus": consensus,  # {final_verdict, consensus: bool, partial_data, agent_results: [...]}
        "agents": agents,
        "fallback_used": False,
        "any_agent_failed": any_failed,
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