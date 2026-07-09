from typing import List, Dict
from datetime import datetime
import pandas as pd


def detect_flatlines(readings: List[Dict], window: int = 10, epsilon: float = 0.01) -> List[Dict]:
    """Detect flatline sequences in sensor readings.

    readings: list of dicts with keys: sensor_reading_id, timestamp, sensor_type, sensor_value, unit_id
    Returns list of flags: {unit_id, sensor_type, flatline_start, flatline_end, duration_minutes, severity}
    """
    if not readings:
        return []

    df = pd.DataFrame(readings)
    # ensure timestamp is datetime
    df["timestamp"] = pd.to_datetime(df["timestamp"])
    # ensure numeric
    df["sensor_value"] = pd.to_numeric(df["sensor_value"], errors="coerce")

    flags = []

    # Group by unit and sensor_type
    grouped = df.groupby(["unit_id", "sensor_type"])
    for (unit_id, sensor_type), group in grouped:
        g = group.sort_values("timestamp").reset_index(drop=True)
        if g.shape[0] < window:
            continue

        # iterate and find consecutive runs where change < epsilon
        run_start_idx = 0
        for i in range(1, len(g)):
            prev = g.at[i - 1, "sensor_value"]
            cur = g.at[i, "sensor_value"]
            if pd.isna(prev) or pd.isna(cur) or abs(cur - prev) > epsilon:
                # end of run
                run_len = i - run_start_idx
                if run_len >= window:
                    start_ts = g.at[run_start_idx, "timestamp"]
                    end_ts = g.at[i - 1, "timestamp"]
                    duration = (end_ts - start_ts).total_seconds() / 60.0
                    if duration > 60:
                        severity = "critical"
                    elif duration > 15:
                        severity = "warning"
                    else:
                        severity = "info"
                    flags.append({
                        "unit_id": unit_id,
                        "sensor_type": sensor_type,
                        "flatline_start": start_ts.isoformat(),
                        "flatline_end": end_ts.isoformat(),
                        "duration_minutes": round(duration, 2),
                        "severity": severity,
                    })
                run_start_idx = i

        # check final run
        run_len = len(g) - run_start_idx
        if run_len >= window:
            start_ts = g.at[run_start_idx, "timestamp"]
            end_ts = g.at[len(g) - 1, "timestamp"]
            duration = (end_ts - start_ts).total_seconds() / 60.0
            if duration > 60:
                severity = "critical"
            elif duration > 15:
                severity = "warning"
            else:
                severity = "info"
            flags.append({
                "unit_id": unit_id,
                "sensor_type": sensor_type,
                "flatline_start": start_ts.isoformat(),
                "flatline_end": end_ts.isoformat(),
                "duration_minutes": round(duration, 2),
                "severity": severity,
            })

    return flags
