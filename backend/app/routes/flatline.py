from typing import List
from fastapi import APIRouter
from fastapi import Body
import pandas as pd

from app.models.flatline_models import FlatlineReading, FlatlineFlag
from app.services.flatline_service import detect_flatlines

router = APIRouter()


@router.post("/flatline-check", response_model=List[FlatlineFlag])
def post_flatline_check(readings: List[FlatlineReading] = Body(...)):
    data = [r.dict() for r in readings]
    flags = detect_flatlines(data)
    return flags


@router.get("/flatline-check/demo", response_model=List[FlatlineFlag])
def demo_flatline_check():
    # load combined dataset and run check
    df = pd.read_csv("../data/combined_dataset.csv")
    # select relevant columns and convert to dicts
    subset = df[["sensor_reading_id", "timestamp", "sensor_type", "sensor_value", "unit_id"]]
    readings = subset.rename(columns={
        "sensor_reading_id": "sensor_reading_id",
    }).to_dict(orient="records")
    flags = detect_flatlines(readings)
    return flags
