"""
OBD2 Triplet Ingestion Engine
Parses controlled triplet test executions (baseline, fault, cleared) from test_executions.csv,
applies strict Gates 2 & 4, and performs physical feature filtering to isolate clean signals.
"""

import os
import sys
from pathlib import Path
import logging
import pandas as pd
import numpy as np
from typing import Optional

# Setup path relative to project root
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.append(str(PROJECT_ROOT))

from src import config

# Set up logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")
logger = logging.getLogger("BCScanTool.TripletIngestor")

# Strictly defined 24 physical core features (expanded to 28 columns for Cylinder Count1-6)
CORE_PHYSICAL_FEATURES = [
    "Engine Speed [rpm]",
    "Calculate Load [%]",
    "Coolant Temp [degree C]",
    "Intake Air [degree C]",
    "MAF [gm/s]",
    "Atmosphere Pressure [kPa]",
    "AF Lambda (Bank1 Sensor1)",
    "AF Lambda (Bank2 Sensor1)",
    "AFS Current (Bank1 Sensor1) [mA]",
    "AFS Current (Bank2 Sensor1) [mA]",
    "O2S B1S2 [V]",
    "O2S B2S2 [V]",
    "Short FT (Bank1 Sensor1) [%]",
    "Short FT (Bank2 Sensor1) [%]",
    "Long FT (Bank1 Sensor1) [%]",
    "Long FT (Bank2 Sensor1) [%]",
    "IGN Advance [deg]",
    "All Cylinders Misfire Count",
    "Cylinder Count1 Misfire Count",
    "Cylinder Count2 Misfire Count",
    "Cylinder Count3 Misfire Count",
    "Cylinder Count4 Misfire Count",
    "Cylinder Count5 Misfire Count",
    "Cylinder Count6 Misfire Count",
    "Vehicle Speed [km/h]",
    "Throttle Sensor Position [%]",
    "Accelerator Position [%]",
    "Battery Voltage [V]"
]


def create_default_test_executions_template(output_path: Path):
    """Creates a default, beautiful template for test_executions.csv if it does not exist."""
    output_path.parent.mkdir(parents=True, exist_ok=True)
    headers = [
        "test_id", "date", "time", "ambient_temp_f", "engine_temp_f", "mileage",
        "duration_fault_s", "dtcs_triggered", "symptoms_observed",
        "baseline_file", "fault_file", "cleared_file", "operator_notes"
    ]
    # Write empty headers
    with open(output_path, "w") as f:
        f.write(",".join(headers) + "\n")
    logger.info(f"Created default template test_executions.csv at {output_path}")


def load_all_triplets(
    metadata_path: Optional[Path] = None,
    csv_root_dir: Optional[Path] = None
) -> pd.DataFrame:
    """
    Parses test_executions.csv to locate and load all baseline-fault-cleared triplets.
    Applies strict physical feature filtering, Gate 2, Gate 4, labeling, and leakage grouping.
    
    Returns a unified concatenated Pandas DataFrame.
    """
    meta_path = metadata_path or config.TEST_EXECUTIONS_PATH
    root_dir = csv_root_dir or config.VEHICLE_CSV_DIR

    # Create default template if it does not exist
    if not meta_path.exists():
        logger.warning(f"Test executions CSV not found at {meta_path}. Creating default template.")
        create_default_test_executions_template(meta_path)
        return pd.DataFrame()

    try:
        executions = pd.read_csv(meta_path, low_memory=False)
    except Exception as e:
        logger.error(f"Failed to read test_executions.csv: {e}")
        return pd.DataFrame()

    # Drop fully empty/blank rows
    executions = executions.dropna(subset=["test_id", "fault_file"])
    if executions.empty:
        logger.warning("test_executions.csv is currently empty. Add controlled triplet rows to process.")
        return pd.DataFrame()

    all_dataframes = []
    logger.info(f"Processing {len(executions)} registered triplet test execution(s)...")

    for idx, row in executions.iterrows():
        test_id = str(row["test_id"]).strip()
        baseline_filename = str(row.get("baseline_file", "")).strip()
        fault_filename = str(row.get("fault_file", "")).strip()
        cleared_filename = str(row.get("cleared_file", "")).strip()

        # Build triplet configuration
        triplet_files = {
            "baseline": (baseline_filename, "healthy"),
            "fault": (fault_filename, None),  # target label derived below
            "cleared": (cleared_filename, "healthy")
        }

        # Determine custom class label for the fault file
        # E.g., if fault_file is "TACOMA_T01_maf_fault.csv" -> label "fault_maf"
        # Otherwise fallback to "fault_{test_id}"
        fault_label = f"fault_{test_id.lower()}"
        if fault_filename:
            # Look for clean descriptive token in the filename
            clean_name = Path(fault_filename).stem.lower()
            for token in ["maf", "lambda", "temp", "misfire", "throttle", "injector", "voltage"]:
                if token in clean_name:
                    fault_label = f"fault_{token}"
                    break
        triplet_files["fault"] = (fault_filename, fault_label)

        logger.info(f"\n[Test {test_id}] Loading baseline/fault/cleared files:")

        for role, (filename, label) in triplet_files.items():
            if not filename or pd.isna(filename) or filename.lower() in ("nan", "none", ""):
                logger.warning(f"  Missing {role} filename for Test {test_id}. Skipping.")
                continue

            # Search recursively for the filename in the CSV root tree
            matches = list(root_dir.rglob(filename))
            if not matches:
                logger.error(f"  ✗ {role.capitalize()} file not found: {filename}")
                continue

            filepath = matches[0]
            try:
                df = pd.read_csv(filepath, low_memory=False)
            except Exception as e:
                logger.error(f"  ✗ Failed to read {filename}: {e}")
                continue

            # ── 1. Feature Filtering: Keep only the 28 columns representing the 24 physical parameters ──
            available_features = [col for col in CORE_PHYSICAL_FEATURES if col in df.columns]
            missing_features = [col for col in CORE_PHYSICAL_FEATURES if col not in df.columns]
            
            if missing_features:
                logger.warning(f"  ⚠️ {filename} is missing physical features: {missing_features}")
                
            # Select features
            filtered_df = df[available_features].copy()

            # Ensure all core features exist in DataFrame (fill missing with NaN)
            for col in missing_features:
                filtered_df[col] = np.nan

            # Reorder to match CORE_PHYSICAL_FEATURES exactly
            filtered_df = filtered_df[CORE_PHYSICAL_FEATURES]

            # ── 2. Gate 2: Drop first 30 progressive CAN bus fill rows ──
            if len(filtered_df) <= config.INIT_ROWS_TO_DROP:
                logger.error(f"  ✗ File {filename} has {len(filtered_df)} rows. Too small after initialization drop. Skipping.")
                continue
            filtered_df = filtered_df.iloc[config.INIT_ROWS_TO_DROP:].reset_index(drop=True)

            # Calculate derived physics features strictly after Gate 2 drop
            filtered_df["Delta_MAF"] = filtered_df["MAF [gm/s]"].diff().fillna(0.0)
            filtered_df["Delta_RPM"] = filtered_df["Engine Speed [rpm]"].diff().fillna(0.0)
            filtered_df["Delta_Calculate_Load"] = filtered_df["Calculate Load [%]"].diff().fillna(0.0)

            # ── 3. Gate 4: Drop additional 60 rows for fault transients (first 30s) ──
            if role == "fault":
                n_drop_fault = 60
                if len(filtered_df) <= n_drop_fault:
                    logger.error(f"  ✗ Fault file {filename} has only {len(filtered_df)} rows. Cannot apply 30s transient drop. Skipping.")
                    continue
                # If engine is already warm, we still preserve the settled fault signature after 30s transient.
                filtered_df = filtered_df.iloc[n_drop_fault:].reset_index(drop=True)
                logger.info(f"  ✓ {role.capitalize()} file: dropped 30 rows (init) + {n_drop_fault} rows (transient) and calculated derived features")
            else:
                logger.info(f"  ✓ {role.capitalize()} file: dropped 30 rows (init) and calculated derived features")

            # ── 4. Labeling & Anti-Leakage session assignment ──
            filtered_df["target_class"] = label
            filtered_df["test_id"] = test_id
            filtered_df["source_file"] = filename

            all_dataframes.append(filtered_df)
            logger.info(f"    Loaded {len(filtered_df)} clean rows with target class '{label}'.")

    if not all_dataframes:
        logger.warning("No triplet files were successfully processed.")
        return pd.DataFrame()

    unified_df = pd.concat(all_dataframes, ignore_index=True)
    logger.info(f"\n✓ Unified Ingestion Complete: Loaded {len(unified_df)} total rows across triplets.")
    logger.info(f"Class distribution:\n{unified_df['target_class'].value_counts().to_string()}")
    
    return unified_df


if __name__ == "__main__":
    # Test script self-execution
    print("Testing Triplet Ingestor Module...")
    df = load_all_triplets()
    if not df.empty:
        print("Success! Consolidated columns:")
        print(df.columns.tolist())
    else:
        print("No test_executions data loaded yet. Template successfully verified.")
