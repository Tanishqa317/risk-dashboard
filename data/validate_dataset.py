"""Validate `data/combined_dataset.csv` for CI/demo readiness.

Checks performed:
1. No nulls in critical columns
2. `timestamp` parses to datetime and is sorted per sensor (or globally if sensor grouping absent)
3. `permit_status` values are valid
4. `shift_staffing` values are valid
5. `sensor_value` numeric; flag outliers beyond 3 stddev
6. Referential integrity: `unit_id` and `zone_id` exist in `plant_layout.json`
7. `machine_failure` is binary (0/1)

Exits with non-zero code if any check fails.
"""
from pathlib import Path
import json
import sys
import traceback

import numpy as np
import pandas as pd

DATA_DIR = Path(__file__).parent
COMBINED_CSV = DATA_DIR / "combined_dataset.csv"
PLANT_LAYOUT_JSON = DATA_DIR / "plant_layout.json"

CRITICAL_COLS = ["sensor_reading_id", "timestamp", "sensor_value", "permit_status", "shift_id"]
VALID_PERMIT_STATUS = {"active", "expired", "revoked"}
VALID_SHIFT_STAFFING = {"understaffed", "normal", "overstaffed"}

failures = []


def fail(msg: str):
    print("[FAIL]", msg)
    failures.append(msg)


def ok(msg: str):
    print("[PASS]", msg)


def load_inputs():
    if not COMBINED_CSV.exists():
        fail(f"Missing file: {COMBINED_CSV}")
        raise SystemExit(2)
    if not PLANT_LAYOUT_JSON.exists():
        fail(f"Missing file: {PLANT_LAYOUT_JSON}")
        raise SystemExit(2)

    df = pd.read_csv(COMBINED_CSV)
    with open(PLANT_LAYOUT_JSON, "r", encoding="utf-8") as fh:
        layout = json.load(fh)
    return df, layout


def check_nulls(df: pd.DataFrame):
    missing = [c for c in CRITICAL_COLS if c not in df.columns]
    if missing:
        fail(f"Missing critical columns: {missing}")
        return
    null_report = df[CRITICAL_COLS].isnull().sum()
    nulls = {c: int(v) for c, v in null_report.items() if v > 0}
    if nulls:
        fail(f"Null values found in critical columns: {nulls}")
    else:
        ok("No nulls in critical columns")


def check_timestamps(df: pd.DataFrame):
    if "timestamp" not in df.columns:
        fail("No `timestamp` column present")
        return
    ts = pd.to_datetime(df["timestamp"], errors="coerce")
    n_bad = ts.isna().sum()
    if n_bad > 0:
        fail(f"timestamp parse errors: {n_bad} rows could not be parsed")
        return
    ok("All timestamps parse as datetimes")

    # check sorting per sensor if a sensor grouping exists
    grouping_col = None
    for c in ("sensor_id", "Product ID", "unit_id"):  # try common grouping columns
        if c in df.columns:
            grouping_col = c
            break

    if grouping_col:
        not_sorted = 0
        for _, g in df.groupby(grouping_col):
            if not g["timestamp"].is_monotonic_increasing:
                not_sorted += 1
        if not_sorted == 0:
            ok(f"Timestamps are sorted within each `{grouping_col}` group")
        else:
            fail(f"Timestamps are not sorted for {not_sorted} groups based on `{grouping_col}`")
    else:
        # fallback: check global sort
        if df["timestamp"].is_monotonic_increasing:
            ok("Timestamps are globally sorted")
        else:
            fail("Timestamps are not globally sorted and no sensor grouping column found to check per-sensor order")


def check_permit_status(df: pd.DataFrame):
    if "permit_status" not in df.columns:
        fail("No `permit_status` column present")
        return
    vals = set(df["permit_status"].dropna().unique())
    invalid = vals - VALID_PERMIT_STATUS
    if invalid:
        fail(f"Invalid permit_status values found: {sorted(invalid)}")
    else:
        ok("All permit_status values are valid")


def check_shift_staffing(df: pd.DataFrame):
    if "shift_staffing" not in df.columns:
        fail("No `shift_staffing` column present")
        return
    vals = set(df["shift_staffing"].dropna().unique())
    invalid = vals - VALID_SHIFT_STAFFING
    if invalid:
        fail(f"Invalid shift_staffing values: {sorted(invalid)}")
    else:
        ok("All shift_staffing values are valid")


def check_sensor_values(df: pd.DataFrame):
    if "sensor_value" not in df.columns:
        fail("No `sensor_value` column present")
        return
    sv = pd.to_numeric(df["sensor_value"], errors="coerce")
    n_non_numeric = int(sv.isna().sum())
    if n_non_numeric > 0:
        fail(f"sensor_value has {n_non_numeric} non-numeric rows")
        return
    mean = sv.mean()
    std = sv.std()
    if pd.isna(mean) or pd.isna(std):
        fail("sensor_value mean/std could not be computed")
        return
    # outliers beyond 3 stddev
    z = (sv - mean).abs() / std
    outliers = df[z > 3]
    pct_outliers = (len(outliers) / len(df)) * 100 if len(df) > 0 else 0.0
    ok(f"sensor_value numeric. mean={mean:.3f}, std={std:.3f}, outliers={len(outliers)} ({pct_outliers:.2f}%)")
    if len(outliers) > 0:
        # print up to 5 example outliers
        print("Example outliers:")
        print(outliers[["sensor_reading_id", "timestamp", "sensor_type", "sensor_value"]].head(5).to_string(index=False))


def check_referential_integrity(df: pd.DataFrame, layout):
    # Build set of valid unit_ids and zone_ids from layout
    valid_unit_ids = {u["unit_id"] for u in layout}
    valid_zone_ids = {z["zone_id"] for u in layout for z in u.get("zones", [])}

    errs = []
    if "unit_id" in df.columns:
        bad_units = set(df["unit_id"].dropna().unique()) - valid_unit_ids
        if bad_units:
            errs.append(f"Unknown unit_id values: {sorted(bad_units)}")
    else:
        errs.append("No `unit_id` column present")

    if "zone_id" in df.columns:
        bad_zones = set(df["zone_id"].dropna().unique()) - valid_zone_ids
        if bad_zones:
            errs.append(f"Unknown zone_id values: {sorted(bad_zones)}")
    else:
        errs.append("No `zone_id` column present")

    if errs:
        for e in errs:
            fail(e)
    else:
        ok("unit_id and zone_id values exist in plant_layout.json")


def check_machine_failure(df: pd.DataFrame):
    if "machine_failure" not in df.columns:
        fail("No `machine_failure` column present")
        return
    vals = set(df["machine_failure"].dropna().unique())
    # allow booleans and 0/1
    normalized = set()
    for v in vals:
        if v in (0, 1):
            normalized.add(int(v))
        elif str(v).lower() in {"0", "1"}:
            normalized.add(int(str(v)))
        elif isinstance(v, (bool, np.bool_)):
            normalized.add(int(bool(v)))
        else:
            normalized.add(str(v))
    if not normalized.issubset({0, 1}):
        fail(f"machine_failure contains non-binary values: {sorted(normalized)}")
    else:
        ok("machine_failure is binary (0/1)")


def main():
    try:
        df, layout = load_inputs()

        # keep a copy of original timestamp column for sorting checks
        if "timestamp" in df.columns:
            # ensure timestamp column exists as string for monotonic checks
            # but do not overwrite original values permanently
            df = df.copy()
            df["timestamp"] = pd.to_datetime(df["timestamp"], errors="coerce")

        check_nulls(df)
        check_timestamps(df)
        check_permit_status(df)
        check_shift_staffing(df)
        check_sensor_values(df)
        check_referential_integrity(df, layout)
        check_machine_failure(df)

    except SystemExit as e:
        # already reported
        sys.exit(e.code if isinstance(e.code, int) else 1)
    except Exception:
        print("Unexpected error during validation:")
        traceback.print_exc()
        sys.exit(2)

    if failures:
        print("\nValidation completed: FAIL\n")
        sys.exit(1)
    else:
        print("\nValidation completed: PASS\n")
        sys.exit(0)


if __name__ == "__main__":
    main()
