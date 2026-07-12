import hashlib
import math
import random
from typing import List, Dict, Optional


def _seed_for_unit(unit_id: str) -> int:
    digest = hashlib.sha256(unit_id.encode("utf-8")).hexdigest()
    return int(digest[:8], 16)


def generate_baseline_signature(unit_id: str, length: int = 200) -> List[float]:
    if length <= 0:
        return []

    seed = _seed_for_unit(unit_id)
    rng = random.Random(seed)
    signature: List[float] = []

    for index in range(length):
        base_value = math.sin(2 * math.pi * 5 * index / length)
        noise = rng.uniform(-0.05, 0.05)
        signature.append(round(base_value + noise, 6))

    return signature


def generate_current_signature(unit_id: str, wear_level: Optional[float] = None) -> List[float]:
    if wear_level is None:
        seed = _seed_for_unit(unit_id)
        wear_level = (seed % 1000) / 1000.0

    wear_level = max(0.0, min(1.0, float(wear_level)))

    baseline = generate_baseline_signature(unit_id, length=200)
    signature: List[float] = []

    seed = _seed_for_unit(unit_id)
    rng = random.Random(seed + 17)

    for index, baseline_value in enumerate(baseline):
        frequency_drift = 1.0 + (wear_level * 0.08) * (index % 7 - 3) / 6.0
        disturbed_value = math.sin(2 * math.pi * 5 * frequency_drift * index / len(baseline))
        noise_amp = 0.05 + wear_level * 0.25
        noise = rng.uniform(-noise_amp, noise_amp)
        amplitude_spike = 0.0
        if wear_level > 0.6 and rng.random() < 0.08:
            amplitude_spike = rng.uniform(0.15, 0.35)
        adjusted = baseline_value + (wear_level * 0.35) * (disturbed_value - baseline_value) + noise + amplitude_spike
        signature.append(round(adjusted, 6))

    return signature


def calculate_deviation(baseline: List[float], current: List[float]) -> Dict[str, object]:
    if not baseline or not current:
        return {
            "deviation_score": 0.0,
            "status": "healthy",
            "time_to_failure_weeks": None,
            "explanation": "No vibration data was available for comparison.",
        }

    if len(baseline) != len(current):
        length = min(len(baseline), len(current))
        baseline = baseline[:length]
        current = current[:length]

    squared_error = sum((a - b) ** 2 for a, b in zip(baseline, current))
    mean_squared_error = squared_error / len(baseline)
    rmse = math.sqrt(mean_squared_error)
    baseline_norm = math.sqrt(sum(a * a for a in baseline) / len(baseline)) or 1.0
    normalized_rmse = rmse / baseline_norm
    deviation_score = min(100.0, max(0.0, normalized_rmse * 100.0))

    if deviation_score < 15:
        status = "healthy"
        time_to_failure_weeks = None
        explanation = "The vibration signature remains close to the healthy baseline with no immediate signs of wear."
    elif deviation_score < 35:
        status = "early_warning"
        time_to_failure_weeks = max(1, int(12 - deviation_score / 5))
        explanation = "The vibration pattern is beginning to deviate from baseline and may indicate emerging mechanical wear."
    elif deviation_score < 60:
        status = "degrading"
        time_to_failure_weeks = max(1, int(12 - deviation_score / 5))
        explanation = "The equipment shows clear vibration drift and should be inspected soon to prevent escalation."
    else:
        status = "critical"
        time_to_failure_weeks = max(1, int(12 - deviation_score / 5))
        explanation = "The vibration signature has diverged sharply from the healthy baseline and failure risk is elevated."

    return {
        "deviation_score": round(deviation_score, 2),
        "status": status,
        "time_to_failure_weeks": time_to_failure_weeks,
        "explanation": explanation,
    }


def get_vibration_analysis(unit_id: str) -> Dict[str, object]:
    baseline_signature = generate_baseline_signature(unit_id)
    current_signature = generate_current_signature(unit_id)
    deviation_result = calculate_deviation(baseline_signature, current_signature)

    deviation_score = float(deviation_result["deviation_score"])
    status = str(deviation_result["status"])
    time_to_failure_weeks = deviation_result["time_to_failure_weeks"]
    explanation = str(deviation_result["explanation"])

    if deviation_score <= 0:
        trend = [0.0 for _ in range(30)]
    else:
        trend = [round((deviation_score / 29.0) * index, 2) for index in range(30)]
        trend[-1] = round(deviation_score, 2)

    return {
        "unit_id": unit_id,
        "baseline_signature": baseline_signature,
        "current_signature": current_signature,
        "deviation_score": deviation_score,
        "status": status,
        "time_to_failure_weeks": time_to_failure_weeks,
        "explanation": explanation,
        "trend_last_30_days": trend,
    }
