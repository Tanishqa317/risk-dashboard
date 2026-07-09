import sys
from pathlib import Path
import datetime

# ensure backend is importable
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.services.flatline_service import detect_flatlines


def make_readings(unit_id, sensor_type, start_ts, values):
    readings = []
    for i, v in enumerate(values):
        readings.append({
            "sensor_reading_id": f"r{i}",
            "timestamp": (start_ts + datetime.timedelta(minutes=i)).isoformat(),
            "sensor_type": sensor_type,
            "sensor_value": v,
            "unit_id": unit_id,
        })
    return readings


def test_detects_flatline():
    start = datetime.datetime.utcnow()
    # 10 identical readings -> should trigger flatline with default window=10
    vals = [100.0] * 10
    readings = make_readings("unit-1", "torque", start, vals)
    flags = detect_flatlines(readings, window=10, epsilon=0.001)
    assert len(flags) >= 1
    f = flags[0]
    assert f["unit_id"] == "unit-1"
    assert f["sensor_type"] == "torque"


def test_no_flatline_for_noisy_sensor():
    start = datetime.datetime.utcnow()
    # small random-like noise > epsilon
    vals = [100.0, 100.2, 99.8, 100.5, 99.0, 101.0, 98.5, 100.7, 99.4, 100.6]
    readings = make_readings("unit-2", "torque", start, vals)
    flags = detect_flatlines(readings, window=10, epsilon=0.001)
    assert len(flags) == 0
