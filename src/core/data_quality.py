"""
Data Quality Gates for BCScanTool
Validates and preprocesses scan data before it enters the ML pipeline.
"""

import pandas as pd
import numpy as np
import logging
from pathlib import Path
from typing import Optional, Tuple

from src import config

logger = logging.getLogger("BCScanTool.DataQuality")


class DataQualityReport:
    """Results of quality gate checks on a single scan file."""
    def __init__(self, filepath: str):
        self.filepath = filepath
        self.passed = True
        self.gates = {}
        self.rows_before = 0
        self.rows_after = 0
        self.columns_kept = 0
        self.columns_dropped = 0

    def fail(self, gate_name: str, reason: str):
        self.passed = False
        self.gates[gate_name] = {"passed": False, "reason": reason}

    def ok(self, gate_name: str, detail: str = ""):
        self.gates[gate_name] = {"passed": True, "detail": detail}

    def summary(self) -> str:
        status = "PASS" if self.passed else "FAIL"
        lines = [f"[{status}] {self.filepath}"]
        lines.append(f"  Rows: {self.rows_before} -> {self.rows_after}")
        lines.append(f"  Columns: kept {self.columns_kept}, dropped {self.columns_dropped}")
        for gate, result in self.gates.items():
            icon = "✓" if result["passed"] else "✗"
            detail = result.get("reason") or result.get("detail", "")
            lines.append(f"  {icon} {gate}: {detail}")
        return "\n".join(lines)


def preprocess_scan(df: pd.DataFrame, filepath: str = "",
                    scan_type: str = "baseline", only_tier_a: bool = True) -> Tuple[Optional[pd.DataFrame], DataQualityReport]:
    """
    Apply all data quality gates to a scan DataFrame.

    Args:
        df: Raw scan DataFrame from X431 CSV
        filepath: Source filename for reporting
        scan_type: 'baseline' or 'fault' (affects min row threshold)
        only_tier_a: Filter strictly to Tier A features if True, else Tier A + B

    Returns:
        (cleaned_df, report) — cleaned_df is None if scan fails gates
    """
    report = DataQualityReport(filepath)
    report.rows_before = len(df)

    # ── Gate 1: Minimum row count ──
    min_rows = config.MIN_ROWS_BASELINE if scan_type == "baseline" else config.MIN_ROWS_FAULT
    if len(df) < min_rows:
        report.fail("min_rows", f"{len(df)} rows < {min_rows} minimum for {scan_type}")
        return None, report
    report.ok("min_rows", f"{len(df)} rows >= {min_rows}")

    # ── Gate 2: Drop sensor initialization rows ──
    n_drop = config.INIT_ROWS_TO_DROP
    if len(df) > n_drop:
        df = df.iloc[n_drop:].reset_index(drop=True)
        report.ok("init_drop", f"Dropped first {n_drop} initialization rows")
    else:
        report.fail("init_drop", f"Only {len(df)} rows, cannot drop {n_drop}")
        return None, report

    # ── Gate 3: Engine running verification ──
    rpm_cols = [c for c in df.columns if "engine speed" in c.lower() or "engine_speed" in c.lower()]
    if rpm_cols:
        rpm_col = rpm_cols[0]
        rpm_data = pd.to_numeric(df[rpm_col], errors="coerce")
        engine_off_rows = (rpm_data < config.MIN_RPM_ENGINE_RUNNING).sum()
        engine_off_pct = engine_off_rows / len(df) * 100
        if engine_off_pct > 50:
            report.fail("engine_running", f"{engine_off_pct:.0f}% of rows have RPM < {config.MIN_RPM_ENGINE_RUNNING}")
            return None, report
        # Drop rows where engine stalled mid-scan
        stall_mask = rpm_data >= config.MIN_RPM_ENGINE_RUNNING
        df = df[stall_mask].reset_index(drop=True)
        report.ok("engine_running", f"{engine_off_pct:.0f}% engine-off rows filtered")
    else:
        report.ok("engine_running", "No RPM column found, skipping check")

    # ── Gate 4: Steady-State Window (discard transients) ──
    # For fault captures: discard the first 30 seconds of data.
    # For baseline captures: discard the first 60 seconds of warm-up ramp.
    time_col = None
    for col in df.columns:
        if "time since engine start" in col.lower() or "engine run time" in col.lower():
            time_col = col
            break

    if time_col is not None:
        try:
            # Sort by time just in case
            df = df.sort_values(by=time_col).reset_index(drop=True)
            time_data = pd.to_numeric(df[time_col], errors="coerce")
            if len(time_data) > 0 and not time_data.isna().all():
                start_time = time_data.iloc[0]
                if scan_type == "fault":
                    valid_mask = time_data >= (start_time + 30.0)
                    desc = "30s fault transient"
                else:
                    # If the engine was already running for > 300 seconds before capture started,
                    # the warm-up ramp has already happened, so do not discard anything!
                    if start_time > 300.0:
                        valid_mask = pd.Series(True, index=df.index)
                        desc = "skipped (engine already warm)"
                    else:
                        valid_mask = time_data >= (start_time + 60.0)
                        desc = "60s warm-up"
                rows_before_gate4 = len(df)
                df = df[valid_mask].reset_index(drop=True)
                dropped_rows = rows_before_gate4 - len(df)
                report.ok("steady_state", f"Steady-state window ({desc}): dropped first {dropped_rows} rows based on '{time_col}'")
            else:
                time_col = None
        except Exception as e:
            logger.warning(f"Error applying steady-state using time column: {e}")
            time_col = None

    if time_col is None:
        # Fallback to row counts at ~2 Hz (0.5s per row)
        # 30s = 60 rows; 60s = 120 rows
        n_drop_g4 = 60 if scan_type == "fault" else 120
        if len(df) > n_drop_g4:
            df = df.iloc[n_drop_g4:].reset_index(drop=True)
            report.ok("steady_state", f"Steady-state fallback: dropped first {n_drop_g4} rows (~{n_drop_g4/2}s)")
        else:
            if scan_type == "fault":
                report.fail("steady_state", f"Fault scan: only {len(df)} rows, cannot drop {n_drop_g4}")
                return None, report
            else:
                report.ok("steady_state", f"Baseline scan: only {len(df)} rows, skipped drop")

    # ── Gate 4.5: Filter to ML-relevant columns (Tier A or Tier A + B) ──
    tiers = config.load_parameter_tiers()
    ml_columns = tiers["tier_a"] if only_tier_a else (tiers["tier_a"] + tiers["tier_b"])
    if ml_columns:
        available_ml = [c for c in ml_columns if c in df.columns]
        dropped = [c for c in df.columns if c not in ml_columns and c not in ("Row",)]
        report.columns_kept = len(available_ml)
        report.columns_dropped = len(dropped)
        if available_ml:
            # Keep Row column for reference if present, plus ML columns
            keep = [c for c in ["Row"] if c in df.columns] + available_ml
            df = df[keep]
            report.ok("tier_filter", f"Kept {len(available_ml)} ML columns, dropped {len(dropped)}")
        else:
            report.ok("tier_filter", "No tier columns matched — keeping all numeric")
    else:
        report.ok("tier_filter", "No parameter_tiers.json loaded — keeping all columns")

    # ── Gate 5: Convert all sensor columns to numeric ──
    for col in df.columns:
        if col != "Row":
            df[col] = pd.to_numeric(df[col], errors="coerce")

    # ── Final check ──
    report.rows_after = len(df)
    if len(df) < 15:  # Lowered slightly as window slicing works on 60 rows but we might have smaller residual parts
        report.fail("final_count", f"Only {len(df)} rows remain after filtering")
        return None, report
    report.ok("final_count", f"{len(df)} clean rows ready for ML")

    logger.info(report.summary())
    return df, report


def load_scan_manifest() -> Optional[pd.DataFrame]:
    """Load the scan manifest CSV that maps files to labels."""
    if not config.SCAN_MANIFEST_PATH.exists():
        logger.warning(f"Scan manifest not found at {config.SCAN_MANIFEST_PATH}")
        return None
    manifest = pd.read_csv(config.SCAN_MANIFEST_PATH)
    logger.info(f"Loaded scan manifest: {len(manifest)} entries")
    return manifest


def load_labeled_dataset(data_dir: Path = None, only_tier_a: bool = True) -> Optional[pd.DataFrame]:
    """
    Load all scans using the manifest for labels instead of filename guessing.
    Applies quality gates to each file.

    Returns a single DataFrame with 'condition' and 'operating_mode' columns.
    """
    manifest = load_scan_manifest()
    if manifest is None:
        logger.warning("No manifest found — falling back to unlabeled loading")
        return None

    csv_dir = data_dir or config.VEHICLE_CSV_DIR
    all_dfs = []

    for _, row in manifest.iterrows():
        filepath = csv_dir
        # Search recursively for the filename
        matches = list(csv_dir.rglob(row["filename"]))
        if not matches:
            logger.debug(f"File not found: {row['filename']}")
            continue

        try:
            raw_df = pd.read_csv(matches[0], low_memory=False)
        except Exception as e:
            logger.warning(f"Failed to read {row['filename']}: {e}")
            continue

        scan_type = "fault" if "fault" in str(row.get("condition", "")) else "baseline"
        clean_df, report = preprocess_scan(raw_df, row["filename"], scan_type, only_tier_a=only_tier_a)

        if clean_df is None:
            continue

        # Attach labels from manifest
        clean_df["condition"] = row.get("condition", "unknown")
        clean_df["operating_mode"] = row.get("operating_mode", "unknown")
        clean_df["source_file"] = row["filename"]
        all_dfs.append(clean_df)

    if not all_dfs:
        logger.warning("No valid scans loaded from manifest")
        return None

    combined = pd.concat(all_dfs, ignore_index=True)
    logger.info(f"Loaded {len(all_dfs)} scans, {len(combined)} total rows")

    # Report class distribution
    if "condition" in combined.columns:
        dist = combined.groupby("condition").size()
        logger.info(f"Class distribution:\n{dist.to_string()}")

    return combined
