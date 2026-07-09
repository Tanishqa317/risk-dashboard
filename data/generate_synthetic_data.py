"""Generate synthetic datasets and merge with AI4I 2020 data.

Outputs:
- plant_layout.json
- combined_dataset.csv
- permits.csv (optional, for inspection)
- shifts.csv (optional, for inspection)

Usage:
    python generate_synthetic_data.py

Requires: pandas, numpy, faker
"""
from pathlib import Path
import json
import random
from datetime import datetime, timedelta

import numpy as np
import pandas as pd
from faker import Faker

# Reproducibility
SEED = 42
random.seed(SEED)
np.random.seed(SEED)
Faker.seed(SEED)
fake = Faker()

DATA_DIR = Path(__file__).parent
AI4I_CSV = DATA_DIR / "ai4i2020.csv"
PLANT_LAYOUT_JSON = DATA_DIR / "plant_layout.json"
COMBINED_CSV = DATA_DIR / "combined_dataset.csv"
PERMITS_CSV = DATA_DIR / "permits.csv"
SHIFTS_CSV = DATA_DIR / "shifts.csv"

# Shift definitions
SHIFTS = [
    {
        "shift_id": "shift_day",
        "shift_name": "Day",
        "start_hour": 6,
        "end_hour": 14,
    },
    {
        "shift_id": "shift_evening",
        "shift_name": "Evening",
        "start_hour": 14,
        "end_hour": 22,
    },
    {
        "shift_id": "shift_night",
        "shift_name": "Night",
        "start_hour": 22,
        "end_hour": 6,
    },
]

PERMIT_TYPES = ["hot_work", "confined_space", "electrical", "general"]
PERMIT_STATUS = ["active", "expired", "revoked"]

ZONE_NAME_POOL = [
    "Compressor Bay",
    "Storage Tank",
    "Control Room",
    "Maintenance Bay",
    "Loading Dock",
    "Pump House",
    "Generator Room",
    "Inspection Alley",
    "Chemical Storage",
]

SENSOR_COLUMNS = [
    "Air temperature [K]",
    "Process temperature [K]",
    "Rotational speed [rpm]",
    "Torque [Nm]",
    "Tool wear [min]",
]

SENSOR_TYPE_MAP = {
    "Air temperature [K]": "air_temperature",
    "Process temperature [K]": "process_temperature",
    "Rotational speed [rpm]": "rotational_speed",
    "Torque [Nm]": "torque",
    "Tool wear [min]": "tool_wear",
}

def load_ai4i():
    if not AI4I_CSV.exists():
        raise FileNotFoundError(f"Expected {AI4I_CSV} to exist. Place ai4i2020.csv in the data folder.")
    df = pd.read_csv(AI4I_CSV)
    return df


def generate_plant_layout():
    layout = []
    for i in range(1, 6):
        unit_id = f"unit-{i}"
        unit_name = f"Unit-{i}"
        num_zones = random.choice([3, 4])
        zone_names = random.sample(ZONE_NAME_POOL, num_zones)
        zones = []
        for j, zn in enumerate(zone_names, start=1):
            zones.append({"zone_id": f"{unit_id}-zone-{j}", "zone_name": zn})
        layout.append({"unit_id": unit_id, "unit_name": unit_name, "zones": zones})
    with open(PLANT_LAYOUT_JSON, "w", encoding="utf-8") as fh:
        json.dump(layout, fh, indent=2)
    return layout


def generate_shifts():
    rows = []
    for s in SHIFTS:
        for day_offset in range(0, 31):
            # Create a repeating shift instance per day for optional export
            start_date = (datetime.utcnow() - timedelta(days=day_offset)).date()
            start_dt = datetime.combine(start_date, datetime.min.time()) + timedelta(hours=s["start_hour"])
            # handle night wrap
            end_hour = s["end_hour"]
            end_dt = start_dt + (((end_hour - s["start_hour"]) % 24) * timedelta(hours=1))
            staffing = random.choices(["understaffed", "normal", "overstaffed"], weights=[0.15, 0.75, 0.10])[0]
            rows.append({
                "shift_id": s["shift_id"],
                "shift_name": s["shift_name"],
                "start_time": start_dt.isoformat(),
                "end_time": end_dt.isoformat(),
                "staffing_level": staffing,
                "supervisor_name": fake.name(),
            })
    shifts_df = pd.DataFrame(rows)
    shifts_df.to_csv(SHIFTS_CSV, index=False)
    return shifts_df


def assign_shift_for_timestamp(ts: datetime):
    hour = ts.hour
    # Day 6-13:59, Evening 14-21:59, Night 22-5:59
    if 6 <= hour < 14:
        return "shift_day"
    if 14 <= hour < 22:
        return "shift_evening"
    return "shift_night"


def generate_permits(df, plant_layout):
    permits = []
    zone_map = {z["zone_id"]: u["unit_id"] for u in plant_layout for z in u["zones"]}
    zone_ids = list(zone_map.keys())
    for idx, sensor_id in enumerate(df["UDI"].tolist()):
        permit_id = f"PERMIT-{idx+1:06d}"
        permit_type = random.choice(PERMIT_TYPES)
        if random.random() < 0.15:
            status = "expired"
        else:
            status = "revoked" if random.random() < 0.02 else "active"
        zone_id = random.choice(zone_ids)
        unit_id = zone_map[zone_id]
        permits.append({
            "permit_id": permit_id,
            "sensor_reading_id": sensor_id,
            "permit_type": permit_type,
            "status": status,
            "zone_id": zone_id,
            "unit_id": unit_id,
        })
    permits_df = pd.DataFrame(permits)
    permits_df.to_csv(PERMITS_CSV, index=False)
    return permits_df


def finalize_permits(permits_df, timestamps):
    rows = []
    for idx, row in permits_df.iterrows():
        ts = timestamps[idx]
        issued_at = ts - timedelta(hours=random.uniform(0, 4))
        expires_at = issued_at + timedelta(hours=random.uniform(2, 8))
        if row["status"] == "expired":
            expires_at = ts - timedelta(minutes=random.uniform(1, 120))
        elif expires_at < ts and row["status"] == "active":
            row["status"] = "expired"
        rows.append({
            **row.to_dict(),
            "issued_at": issued_at.isoformat(),
            "expires_at": expires_at.isoformat(),
            "status": row["status"],
        })
    finalized = pd.DataFrame(rows)
    finalized.to_csv(PERMITS_CSV, index=False)
    return finalized


def synthesize_timestamps(df, permits_df):
    timestamps = [None] * len(df)
    now = datetime.utcnow()
    start_window = now - timedelta(days=30)

    unit_groups = {}
    for idx, unit_id in enumerate(permits_df["unit_id"]):
        unit_groups.setdefault(unit_id, []).append(idx)

    for unit_id, indices in unit_groups.items():
        count = len(indices)
        end_time = start_window + timedelta(seconds=random.uniform(0, (now - start_window).total_seconds()))
        seq_start = end_time - timedelta(minutes=10 * (count - 1))
        if seq_start < start_window:
            seq_start = start_window
        for i, idx in enumerate(sorted(indices)):
            timestamps[idx] = seq_start + timedelta(minutes=10 * i)
    return timestamps


def build_combined(df, plant_layout, permits_df, shifts_df, timestamps):
    sensor_cols = SENSOR_COLUMNS
    zone_map = {z["zone_id"]: u["unit_id"] for u in plant_layout for z in u["zones"]}
    shift_mode = shifts_df.groupby("shift_id")["staffing_level"].agg(lambda x: x.mode().iloc[0] if len(x.mode()) else "normal").to_dict()

    df = df.copy()
    df["timestamp"] = pd.to_datetime(timestamps)

    stacked = df[sensor_cols + ["UDI", "Machine failure", "TWF", "HDF", "PWF", "OSF", "RNF", "timestamp"]].melt(
        id_vars=["UDI", "Machine failure", "TWF", "HDF", "PWF", "OSF", "RNF", "timestamp"],
        value_vars=sensor_cols,
        var_name="sensor_type_raw",
        value_name="sensor_value",
    )
    stacked["sensor_type"] = stacked["sensor_type_raw"].map(SENSOR_TYPE_MAP)

    merged = stacked.merge(
        permits_df[["sensor_reading_id", "permit_id", "status", "zone_id", "unit_id"]],
        left_on="UDI",
        right_on="sensor_reading_id",
        how="left",
    )
    merged["shift_id"] = merged["timestamp"].apply(assign_shift_for_timestamp)
    merged["shift_staffing"] = merged["shift_id"].map(shift_mode).fillna("normal")
    merged["machine_failure"] = merged["Machine failure"].astype(int)
    merged["failure_type"] = ""
    for ft in ["TWF", "HDF", "PWF", "OSF", "RNF"]:
        mask = (merged[ft] == 1) & (merged["failure_type"] == "")
        merged.loc[mask, "failure_type"] = ft

    combined_df = merged[
        [
            "UDI",
            "timestamp",
            "sensor_type",
            "sensor_value",
            "unit_id",
            "zone_id",
            "permit_id",
            "status",
            "shift_id",
            "shift_staffing",
            "machine_failure",
            "failure_type",
        ]
    ].rename(columns={
        "UDI": "sensor_reading_id",
        "status": "permit_status",
    })

    combined_df = combined_df.sort_values(["unit_id", "timestamp"]).reset_index(drop=True)
    combined_df.to_csv(COMBINED_CSV, index=False)
    return combined_df


def print_summary(combined_df, permits_df, shifts_df):
    total_rows = len(combined_df)
    pct_expired = (permits_df[permits_df["status"] == "expired"].shape[0] / permits_df.shape[0]) * 100
    pct_understaffed = (shifts_df[shifts_df["staffing_level"] == "understaffed"].shape[0] / shifts_df.shape[0]) * 100
    pct_failures = (combined_df[combined_df["machine_failure"] == 1].shape[0] / total_rows) * 100

    print("=== Synthetic Data Summary ===")
    print(f"Total sensor rows: {total_rows}")
    print(f"Expired permits: {pct_expired:.2f}%")
    print(f"Understaffed shifts: {pct_understaffed:.2f}%")
    print(f"Failure events: {pct_failures:.2f}%")


if __name__ == "__main__":
    print("Loading real dataset...")
    df = load_ai4i()
    print(f"Loaded {len(df)} rows from {AI4I_CSV.name}")

    print("Generating plant layout...")
    plant_layout = generate_plant_layout()

    print("Generating permit assignments...")
    permits_df = generate_permits(df, plant_layout)

    print("Synthesizing timestamps (10-minute intervals per unit)...")
    timestamps = synthesize_timestamps(df, permits_df)

    print("Finalizing permits with issued/expires timestamps...")
    permits_df = finalize_permits(permits_df, timestamps)

    print("Generating shifts (and exporting shifts.csv)...")
    shifts_df = generate_shifts()

    print("Building combined dataset and exporting combined_dataset.csv...")
    combined_df = build_combined(df, plant_layout, permits_df, shifts_df, timestamps)

    print_summary(combined_df, permits_df, shifts_df)

    print(f"Saved plant layout to: {PLANT_LAYOUT_JSON}")
    print(f"Saved combined dataset to: {COMBINED_CSV}")
    print(f"Saved permits to: {PERMITS_CSV}")
    print(f"Saved shifts to: {SHIFTS_CSV}")
