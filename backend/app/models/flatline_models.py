from pydantic import BaseModel
from typing import Optional


class FlatlineReading(BaseModel):
    sensor_reading_id: str
    timestamp: str
    sensor_type: str
    sensor_value: float
    unit_id: str


class FlatlineFlag(BaseModel):
    unit_id: str
    sensor_type: str
    flatline_start: str
    flatline_end: str
    duration_minutes: float
    severity: str
