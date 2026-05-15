#!/usr/bin/env python3
"""
BCScanTool v2.0 - MATLAB Data Export
Export diagnostic data to MATLAB .mat format for advanced signal processing
"""
import pandas as pd
import numpy as np
from pathlib import Path
from scipy.io import savemat
import json
from datetime import datetime
import re
import sys
import gc

def sanitize_matlab_name(name):
    """Sanitize string to be a valid MATLAB variable name"""
    # Replace common symbols first
    clean = name.replace('%', 'pct').replace('@', 'at').replace('&', 'and')
    # Replace all non-alphanumeric with underscores
    clean = re.sub(r'[^a-zA-Z0-9_]', '_', clean)
    # Ensure it starts with a letter
    if not clean or not clean[0].isalpha():
        clean = 'v_' + clean
    # Truncate to 63 chars (MATLAB limit)
    return clean[:63]

def export_session_to_mat(csv_path, output_path=None, metadata=None):
    """
    Export a single diagnostic session to MATLAB .mat format

    Parameters:
    -----------
    csv_path : str or Path
        Path to CSV file containing diagnostic data
    output_path : str or Path, optional
        Output .mat file path (auto-generated if None)
    metadata : dict, optional
        Additional metadata to include

    Returns:
    --------
    output_path : Path
        Path to created .mat file
    """
    csv_path = Path(csv_path)

    if output_path is None:
        output_path = csv_path.parent / (csv_path.stem + '.mat')
    else:
        output_path = Path(output_path)

    # Read CSV data
    df = pd.read_csv(csv_path, low_memory=False)

    # Convert to numeric where possible
    print(f"  Cleaning data...")
    for col in df.columns:
        df[col] = pd.to_numeric(df[col], errors='coerce')

    # Prepare MATLAB structure
    print(f"  Preparing structure...")
    matlab_data = {
        'data': df.values,  # Numeric array
        'column_names': df.columns.tolist(),
        'num_samples': len(df),
        'num_parameters': len(df.columns),
        'timestamp': datetime.now().isoformat(),
        'source_file': str(csv_path)
    }

    # Add metadata if provided
    if metadata:
        matlab_data['metadata'] = metadata

    # Extract time series for ALL parameters with sanitized names
    print(f"  Extracting parameters...")
    seen_names = {}
    for param in df.columns:
        base_name = sanitize_matlab_name(param)
        param_clean = base_name
        
        # Handle duplicate sanitized names
        if param_clean in seen_names:
            seen_names[base_name] += 1
            param_clean = f"{base_name}_{seen_names[base_name]}"
        else:
            seen_names[base_name] = 0
            
        # Store as separate variable for easy MATLAB access
        matlab_data[param_clean] = df[param].values

    # Save to .mat file
    print(f"  Saving .mat file (compressed)...")
    try:
        savemat(output_path, matlab_data, do_compression=True)
    except Exception as e:
        print(f"  Compression failed, trying without compression: {e}")
        savemat(output_path, matlab_data, do_compression=False)

    print(f"✓ Exported to: {output_path.name}")
    print(f"  {len(df):,} samples × {len(df.columns)} parameters")

    return output_path


def export_all_sessions(input_dir, output_dir=None, pattern="*.csv"):
    """
    Export all CSV files in a directory to MATLAB format

    Parameters:
    -----------
    input_dir : str or Path
        Directory containing CSV files
    output_dir : str or Path, optional
        Output directory (default: input_dir/matlab)
    pattern : str
        File pattern to match (default: *.csv)
    """
    input_dir = Path(input_dir)

    if output_dir is None:
        output_dir = input_dir / "matlab"
    else:
        output_dir = Path(output_dir)

    output_dir.mkdir(parents=True, exist_ok=True)

    # Find all CSV files
    csv_files = list(input_dir.rglob(pattern))

    print(f"Found {len(csv_files)} CSV files")
    print(f"Exporting to: {output_dir}")

    exported = []
    total_files = len(csv_files)
    for i, csv_file in enumerate(csv_files, 1):
        try:
            print(f"[{i}/{total_files}] Processing: {csv_file.name}")
            # Create output path preserving directory structure
            rel_path = csv_file.relative_to(input_dir)
            mat_path = output_dir / rel_path.parent / (csv_file.stem + '.mat')
            mat_path.parent.mkdir(parents=True, exist_ok=True)

            # Export
            export_session_to_mat(csv_file, mat_path)
            exported.append(str(mat_path))
            
            # Help garbage collector
            if i % 10 == 0:
                gc.collect()
        except Exception as e:
            print(f"✗ Error exporting {csv_file.name}: {str(e)}")

    print(f"\n✓ Exported {len(exported)} files to MATLAB format")

    # Create index file
    index_path = output_dir / "export_index.json"
    with open(index_path, 'w') as f:
        json.dump({
            'export_date': datetime.now().isoformat(),
            'source_dir': str(input_dir),
            'files_exported': exported,
            'count': len(exported)
        }, f, indent=2)

    print(f"✓ Index saved: {index_path}")
    return exported


def export_test_triplet(baseline_path, fault_path, cleared_path, output_dir=None):
    """
    Export a test triplet (baseline, fault, cleared) to MATLAB

    Creates a single .mat file with all three conditions for comparison
    """
    baseline_path = Path(baseline_path)
    fault_path = Path(fault_path)
    cleared_path = Path(cleared_path)

    if output_dir is None:
        output_dir = baseline_path.parent / "matlab"
    else:
        output_dir = Path(output_dir)

    output_dir.mkdir(parents=True, exist_ok=True)

    # Read all three files
    print("Reading triplet...")
    df_baseline = pd.read_csv(baseline_path, low_memory=False)
    df_fault = pd.read_csv(fault_path, low_memory=False)
    df_cleared = pd.read_csv(cleared_path, low_memory=False)

    # Convert to numeric
    for df in [df_baseline, df_fault, df_cleared]:
        for col in df.columns:
            df[col] = pd.to_numeric(df[col], errors='coerce')

    # Create combined structure
    matlab_data = {
        'baseline': {
            'data': df_baseline.values,
            'num_samples': len(df_baseline)
        },
        'fault': {
            'data': df_fault.values,
            'num_samples': len(df_fault)
        },
        'cleared': {
            'data': df_cleared.values,
            'num_samples': len(df_cleared)
        },
        'column_names': df_baseline.columns.tolist(),
        'num_parameters': len(df_baseline.columns),
        'export_timestamp': datetime.now().isoformat(),
        'source_files': {
            'baseline': str(baseline_path),
            'fault': str(fault_path),
            'cleared': str(cleared_path)
        }
    }

    # Save combined file
    output_path = output_dir / f"{baseline_path.stem}_triplet.mat"
    savemat(output_path, matlab_data, do_compression=True)

    print(f"✓ Triplet exported: {output_path.name}")
    print(f"  Baseline: {len(df_baseline)} samples")
    print(f"  Fault: {len(df_fault)} samples")
    print(f"  Cleared: {len(df_cleared)} samples")

    return output_path


def export_ml_model_data(model_path, output_path):
    """
    Export ML model parameters to MATLAB format

    Allows MATLAB to use trained model for predictions
    """
    import joblib

    model_path = Path(model_path)
    output_path = Path(output_path)

    # Load model
    model_data = joblib.load(model_path)

    # Extract key components
    matlab_export = {
        'model_type': 'IsolationForest',
        'feature_columns': model_data.get('feature_columns', []),
        'num_features': len(model_data.get('feature_columns', [])),
        'scaler_mean': model_data['scaler'].mean_ if hasattr(model_data.get('scaler'), 'mean_') else None,
        'scaler_scale': model_data['scaler'].scale_ if hasattr(model_data.get('scaler'), 'scale_') else None,
        'export_timestamp': datetime.now().isoformat()
    }

    # Note: sklearn models can't be directly used in MATLAB
    # This exports the preprocessing parameters only
    # For predictions, use Python or retrain in MATLAB

    savemat(output_path, matlab_export)

    print(f"✓ Model metadata exported: {output_path.name}")
    print(f"  Features: {matlab_export['num_features']}")
    print(f"  Note: For predictions, use Python or retrain model in MATLAB")

    return output_path


def main():
    """Main export function"""
    print("="*70)
    print("  BCScanTool → MATLAB Data Export")
    print("="*70)

    project_root = Path(__file__).resolve().parents[1]
    raw_data = project_root / "data" / "raw"
    matlab_dir = project_root / "matlab" / "data"

    # Export all CSV files
    print("\nExporting all diagnostic data to MATLAB format...")
    exported_files = export_all_sessions(raw_data, matlab_dir)

    # Export ML model metadata
    model_path = project_root / "data" / "processed" / "toyota_anomaly_model.joblib"
    if model_path.exists():
        print("\nExporting ML model metadata...")
        export_ml_model_data(
            model_path,
            matlab_dir / "toyota_model_metadata.mat"
        )

    # Find a good example file for the instructions
    example_file = "TOYOTA_SESSION.mat"
    if exported_files:
        # Try to find a Toyota file first
        toyota_files = [f for f in exported_files if "TOYOTA" in f]
        if toyota_files:
            example_file = Path(toyota_files[0]).relative_to(matlab_dir)
        else:
            example_file = Path(exported_files[0]).relative_to(matlab_dir)

    print("\n" + "="*70)
    print("  Export Complete!")
    print("="*70)
    print(f"\nMATLAB data directory: {matlab_dir}")
    print(f"\nIn MATLAB, run:")
    print(f"  cd '{matlab_dir}'")
    print(f"  load('{example_file}')  % Load a session")
    print(f"  whos  % View loaded variables")


if __name__ == "__main__":
    main()
