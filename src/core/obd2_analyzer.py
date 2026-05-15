import os
import shutil
import sys
from pathlib import Path
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
import subprocess
from glob import glob
import re
try:
    import PyPDF2
except ImportError:
    print("Warning: PyPDF2 not installed. PDF parsing will be skipped.")
    print("Install with: pip install PyPDF2")
    PyPDF2 = None

# Import diagnostic engine
try:
    from .diagnostic_engine import run_diagnostics
except (ImportError, ValueError):
    try:
        from diagnostic_engine import run_diagnostics
    except ImportError:
        print("Warning: diagnostic_engine.py not found")
        run_diagnostics = None

# Import predictive analytics
try:
    from .predictive_analytics import run_predictive_analytics
except (ImportError, ValueError):
    try:
        from predictive_analytics import run_predictive_analytics
    except ImportError:
        print("Warning: predictive_analytics.py not found")
        run_predictive_analytics = None

# Import Phase 1 modules
try:
    from .pid_analyzer import analyze_pids
except (ImportError, ValueError):
    try:
        from pid_analyzer import analyze_pids
    except ImportError:
        print("Warning: pid_analyzer.py not found")
        analyze_pids = None

try:
    from src.ml_models.lstm_predictor import run_lstm_analysis
except (ImportError, ValueError):
    try:
        from lstm_predictor import run_lstm_analysis
    except ImportError:
        print("Warning: lstm_predictor.py not found")
        run_lstm_analysis = None

try:
    from src.ml_models.vehicle_baselines import create_vehicle_baselines
except (ImportError, ValueError):
    try:
        from vehicle_baselines import create_vehicle_baselines
    except ImportError:
        print("Warning: vehicle_baselines.py not found")
        create_vehicle_baselines = None

# Import Phase 2 modules
try:
    from src.ml_models.autoencoder_anomaly import run_autoencoder_analysis
except (ImportError, ValueError):
    try:
        from autoencoder_anomaly import run_autoencoder_analysis
    except ImportError:
        print("Warning: autoencoder_anomaly.py not found")
        run_autoencoder_analysis = None

try:
    from src.utils.repair_cost_estimator import estimate_repair_costs
except (ImportError, ValueError):
    try:
        from repair_cost_estimator import estimate_repair_costs
    except ImportError:
        print("Warning: repair_cost_estimator.py not found")
        estimate_repair_costs = None

# Configuration
from src import config

SOURCE_X431_DIR = config.SOURCE_X431_DIR
PROJECT_ROOT = config.PROJECT_ROOT
DATA_DIR = config.DATA_DIR
RAW_DIR = config.RAW_X431_DIR
CSV_DIR = config.CSV_DIR
PDF_DIR = config.PDF_DIR
CONVERTER_SCRIPT = config.CONVERTER_SCRIPT

def setup_directories():
    """Create necessary directories."""
    config.setup_directories()
    print(f"Directories setup:\nRaw: {RAW_DIR}\nCSV: {CSV_DIR}")

def copy_files():
    """Copy all .x431 files from source to raw directory."""
    print(f"Searching for .x431 files in {SOURCE_X431_DIR}...")
    
    files_found = []
    try:
        if not os.path.exists(SOURCE_X431_DIR):
            print(f"Error: Source directory does not exist: {SOURCE_X431_DIR}")
            return False

        for root, dirs, files in os.walk(SOURCE_X431_DIR):
            for file in files:
                if file.endswith(".x431"):
                     files_found.append(os.path.join(root, file))
    except Exception as e:
        print(f"Error during file search: {e}")
        return False
    
    if not files_found:
        print(f"No files found in {SOURCE_X431_DIR}")
        return False
        
    print(f"Found {len(files_found)} files. Copying...")
    count = 0
    for f in files_found:
        filename = os.path.basename(f)
        dest = os.path.join(RAW_DIR, filename)
        if not os.path.exists(dest):
            try:
                shutil.copy2(f, RAW_DIR)
                count += 1
            except Exception as e:
                print(f"Failed to copy {f}: {e}")
    print(f"Files copied: {count} (skipped existing)")
    return True

def convert_files():
    """Convert .x431 files to CSV using the external script."""
    print("Converting files to CSV...")
    
    # Check if converter exists
    if not os.path.exists(CONVERTER_SCRIPT):
        print(f"Error: Converter script not found at {CONVERTER_SCRIPT}")
        return False
    
    # Strategy: Find all .x431 files in RAW_DIR and PDF_DIR recursively
    files_to_convert = []
    for root in [RAW_DIR, PDF_DIR]:
        for path in Path(root).rglob("*.x431"):
             files_to_convert.append(str(path))
             
    if not files_to_convert:
        print("No raw files to convert.")
        return False

    print(f"Staging {len(files_to_convert)} files for conversion...")
    for f in files_to_convert:
        # Copy to CSV_DIR to maintain flat structure for the converter if needed, 
        # or just run converter on them. 
        # The external converter supports a directory argument.
        shutil.copy2(f, CSV_DIR)
        
    cmd = [sys.executable, CONVERTER_SCRIPT, CSV_DIR]
    print(f"Running: {' '.join(cmd)}")
    result = subprocess.run(cmd, capture_output=True, text=True)
    
    print("Conversion Output:")
    print(result.stdout)
    if result.stderr:
        print("Conversion Errors:")
        print(result.stderr)
        
    # Remove .x431 files from CSV_DIR to keep it clean
    for f in glob(os.path.join(CSV_DIR, "*.x431")):
        os.remove(f)
        
    return True

def load_data():
    """Load converted CSV files into a single DataFrame."""
    print("Loading CSV data...")
    
    # Find all CSV files recursively in data/raw and data/csv
    csv_files = []
    for root in [RAW_DIR, CSV_DIR, PDF_DIR]:
        for path in Path(root).rglob("*_clean.csv"):
            csv_files.append(str(path))
    
    # Deduplicate by filename
    seen = {}
    unique_csvs = []
    for f in csv_files:
        name = os.path.basename(f)
        if name not in seen:
            seen[name] = f
            unique_csvs.append(f)
    
    if not unique_csvs:
        print("No converted CSV files found.")
        return None
        
    dfs = []
    for f in unique_csvs:
        try:
            # Read as string first to avoid mixed type errors
            df = pd.read_csv(f, dtype=str)
            filename = os.path.basename(f)
            df['Source_File'] = filename
            
            # Extract Make and Model from filename or path
            make = "Unknown"
            model = "Unknown"
            
            # Try to get make from filename prefix
            parts = filename.split('_')
            if len(parts) > 0:
                make = parts[0].upper()
            
            # Try to get model from directory name if it's in a subfolder
            parent_name = os.path.basename(os.path.dirname(f))
            if parent_name not in ['csv', 'raw', 'raw_x431']:
                model = parent_name
            
            df['Make'] = make
            df['Model'] = model
            
            dfs.append(df)
        except Exception as e:
            print(f"Error reading {f}: {e}")
            
    if not dfs:
        return None
        
    combined_df = pd.concat(dfs, ignore_index=True)
    print(f"Loaded {len(dfs)} files. Total rows: {len(combined_df)}")
    
    # Convert numeric columns
    for col in combined_df.columns:
        if col not in ['Row', 'Source_File', 'Time', 'Make', 'Model']:
             combined_df[col] = pd.to_numeric(combined_df[col], errors='coerce')
            
    return combined_df

def clean_data(df):
    """Clean the DataFrame."""
    print("Cleaning data...")
    
    # Drop empty columns (>90% missing)
    missing = df.isnull().sum() / len(df)
    drop_cols = missing[missing > 0.9].index
    df_clean = df.drop(columns=drop_cols)
    print(f"Dropped {len(drop_cols)} columns with >90% missing data.")
    
    return df_clean

def analyze_and_plot(df):
    """Perform analysis and generate plots."""
    print("Analyzing data...")
    
    # Identify numeric columns for plotting
    numeric_cols = df.select_dtypes(include=[np.number]).columns.tolist()
    
    if not numeric_cols:
        print("No numeric columns found for analysis.")
        return

    # Filter out columns that are likely just indices or unrelated
    target_cols = [c for c in numeric_cols if 'Row' not in c and 'Unnamed' not in c]
    
    if not target_cols:
        print("No relevant numeric columns found.")
        return

    # Select top 5 variance columns or just first few?
    # Let's pick first 5 for now to avoid explosion
    selected_cols = target_cols[:5]
    print(f"Plotting distributions for: {selected_cols}")
    
    plt.figure(figsize=(15, 3 * len(selected_cols)))
    for i, col in enumerate(selected_cols):
        plt.subplot(len(selected_cols), 1, i+1)
        sns.histplot(df[col].dropna(), kde=True)
        plt.title(f'Distribution of {col}')
    
    plot_path = os.path.join(DATA_DIR, "analysis_plots.png")
    plt.tight_layout()
    plt.savefig(plot_path)
    print(f"Plots saved to {plot_path}")
    
    # Save Summary Stats
    stats_path = os.path.join(DATA_DIR, "summary_stats.csv")
    df[target_cols].describe().to_csv(stats_path)
    print(f"Summary stats saved to {stats_path}")

    print(f"Summary stats saved to {stats_path}")

def parse_pdf_reports():
    """Parse PDF diagnostic reports and extract misfire data."""
    if PyPDF2 is None:
        print("Skipping PDF parsing (PyPDF2 not installed)")
        return None

    print("Parsing PDF diagnostic reports...")
    pdf_files = []

    # Search for PDFs recursively in data/raw
    for root, dirs, files in os.walk(PDF_DIR):
        # Skip virtual environments
        if 'venv' in root or 'site-packages' in root:
            continue
        for file in files:
            if file.endswith('.pdf') and ('DataStream' in file or 'DTC' in file):
                pdf_files.append(os.path.join(root, file))

    if not pdf_files:
        print("No diagnostic PDF files found")
        return None

    print(f"Found {len(pdf_files)} PDF files to parse")

    records = []
    for pdf_path in pdf_files:
        try:
            with open(pdf_path, 'rb') as f:
                reader = PyPDF2.PdfReader(f)
                text = ""
                for page in reader.pages:
                    text += page.extract_text()

                # Extract key information
                record = extract_diagnostic_data(text, pdf_path)
                if record:
                    records.append(record)
        except Exception as e:
            print(f"Error parsing {os.path.basename(pdf_path)}: {e}")

    if not records:
        return None

    df = pd.DataFrame(records)
    print(f"Extracted data from {len(records)} PDFs")
    return df

def extract_diagnostic_data(text, pdf_path):
    """Extract diagnostic data from PDF text."""
    record = {'source_file': os.path.basename(pdf_path)}

    # Extract VIN
    vin_match = re.search(r'VIN:(\w+)', text)
    if vin_match:
        record['vin'] = vin_match.group(1)

    # Extract vehicle info
    year_match = re.search(r'Year:(\d{4})', text)
    make_match = re.search(r'Make:(\w+)', text)
    model_match = re.search(r'Model:([\w\s]+?)(?:VIN|$)', text)

    if year_match:
        record['year'] = year_match.group(1)
    if make_match:
        record['make'] = make_match.group(1)
    if model_match:
        record['model'] = model_match.group(1).strip()

    # Extract test time
    time_match = re.search(r'Test Time:([^\n]+)', text)
    if time_match:
        record['test_time'] = time_match.group(1).strip()

    # Extract misfire data - Current
    for i in range(1, 9):  # Cylinders 1-8
        pattern = rf'Misfire Current Cylinder {i}\s+(\d+)'
        match = re.search(pattern, text)
        if match:
            record[f'misfire_current_cyl{i}'] = int(match.group(1))

    # Extract misfire data - History
    for i in range(1, 9):
        pattern = rf'Misfire History Cylinder {i}\s+(\d+)'
        match = re.search(pattern, text)
        if match:
            record[f'misfire_history_cyl{i}'] = int(match.group(1))

    # Extract total misfire
    total_match = re.search(r'Total Misfire\s+(\d+)', text)
    if total_match:
        record['total_misfire'] = int(total_match.group(1))

    # Extract cycles of misfire data
    cycles_match = re.search(r'Cycles Of Misfire Data\s+(\d+)', text)
    if cycles_match:
        record['misfire_cycles'] = int(cycles_match.group(1))

    # Extract engine data
    rpm_match = re.search(r'Engine Speed\s+(\d+)\s+rpm', text)
    if rpm_match:
        record['engine_speed_rpm'] = int(rpm_match.group(1))

    temp_match = re.search(r'Engine Coolant Temperature.*?(\d+)\s+degree F', text)
    if temp_match:
        record['coolant_temp_f'] = int(temp_match.group(1))

    return record if len(record) > 1 else None

def analyze_misfires(pdf_df):
    """Analyze misfire data and identify problem cylinders."""
    if pdf_df is None or pdf_df.empty:
        print("No PDF data to analyze")
        return

    print("\n" + "="*60)
    print("MISFIRE ANALYSIS")
    print("="*60)

    # Convert test_time to datetime for proper sorting
    if 'test_time' in pdf_df.columns:
        pdf_df['test_time_dt'] = pd.to_datetime(pdf_df['test_time'], errors='coerce')

    # Group by VIN to analyze each vehicle
    if 'vin' in pdf_df.columns:
        for vin in pdf_df['vin'].unique():
            vehicle_data = pdf_df[pdf_df['vin'] == vin].copy()

            # Sort by time to get latest scan
            if 'test_time_dt' in vehicle_data.columns:
                vehicle_data = vehicle_data.sort_values('test_time_dt')

            print(f"\nVehicle: {vin}")
            if 'make' in vehicle_data.columns and 'model' in vehicle_data.columns:
                make = vehicle_data['make'].iloc[0]
                model = vehicle_data['model'].iloc[0]
                year = vehicle_data.get('year', {}).iloc[0] if 'year' in vehicle_data.columns else 'Unknown'
                print(f"{year} {make} {model}")

            # Find cylinders with misfires
            misfire_cols = [c for c in vehicle_data.columns if 'misfire_history' in c]
            if misfire_cols:
                latest = vehicle_data.iloc[-1]  # Most recent scan after sorting
                print(f"\nLatest scan: {latest.get('test_time', 'Unknown time')}")
                print(f"Source: {latest.get('source_file', 'Unknown')}")

                # Check for any misfires
                has_misfires = False
                for col in sorted(misfire_cols):
                    count = latest.get(col, 0)
                    if pd.notna(count) and count > 0:
                        has_misfires = True
                        break

                if has_misfires:
                    print("\nCylinder Misfire History:")
                    for col in sorted(misfire_cols):
                        cyl_num = col.split('cyl')[1]
                        count = latest.get(col, 0)
                        if pd.notna(count) and count > 0:
                            status = "⚠️  CRITICAL" if count > 100 else "⚠️  WARNING" if count > 10 else "ℹ️  MINOR"
                            print(f"  Cylinder {cyl_num}: {int(count)} misfires {status}")
                else:
                    print("\n✓ No misfire history detected")

                # Current misfires
                current_cols = [c for c in vehicle_data.columns if 'misfire_current' in c]
                current_misfires = {col: latest.get(col, 0) for col in current_cols if pd.notna(latest.get(col, 0)) and latest.get(col, 0) > 0}
                if current_misfires:
                    print("\nActive Misfires (Current):")
                    for col, count in sorted(current_misfires.items()):
                        cyl_num = col.split('cyl')[1]
                        print(f"  Cylinder {cyl_num}: {int(count)} active misfires")

            if 'total_misfire' in vehicle_data.columns:
                total = latest.get('total_misfire', 0)
                if pd.notna(total) and total > 0:
                    print(f"\nTotal Misfires: {int(total)}")

    print("\n" + "="*60)

def export_data(df, pdf_df=None):
    """Export data to robust formats for external usage (DataSpell, MATLAB, GCP)."""
    print("Exporting data...")

    # 1. Parquet (High performance, compressed, good for Cloud/Python/MATLAB)
    parquet_path = os.path.join(DATA_DIR, "obd2_dataset.parquet")
    print(f"Saving to Parquet: {parquet_path}")
    try:
        df.to_parquet(parquet_path, index=False, engine='fastparquet')
        print("✓ Parquet export successful (Use this for GCP, BigQuery, Modern MATLAB)")
    except Exception as e:
        print(f"✗ Parquet export failed: {e} (Try: pip install pyarrow fastparquet)")

    # 2. SQLite (Great for DataSpell, SQL based exploration)
    db_path = os.path.join(DATA_DIR, "obd2_data.db")
    import sqlite3
    conn = sqlite3.connect(db_path)
    print(f"Saving to SQLite: {db_path}")
    try:
        # 'replace' to overwrite, or 'append' if we had incremental logic properly set up
        # For now, since we load FULL dataset every time, 'replace' is correct.
        df.to_sql("sensor_data", conn, if_exists="replace", index=False)
        print("✓ SQLite export successful (Use this for DataSpell, DBeaver)")

        # Export PDF data to separate table
        if pdf_df is not None and not pdf_df.empty:
            pdf_df.to_sql("diagnostic_reports", conn, if_exists="replace", index=False)
            print("✓ PDF diagnostic data exported to 'diagnostic_reports' table")
    except Exception as e:
        print(f"✗ SQLite export failed: {e}")
    finally:
        conn.close()

    # Export PDF data to CSV for easy viewing
    if pdf_df is not None and not pdf_df.empty:
        pdf_csv_path = os.path.join(DATA_DIR, "processed", "diagnostic_reports.csv")
        os.makedirs(os.path.dirname(pdf_csv_path), exist_ok=True)
        pdf_df.to_csv(pdf_csv_path, index=False)
        print(f"✓ PDF data exported to CSV: {pdf_csv_path}")

def main():
    setup_directories()

    # Parse PDF reports first
    pdf_df = parse_pdf_reports()
    if pdf_df is not None:
        analyze_misfires(pdf_df)

    # Check if CSVs already exist to save time
    # existing_csvs = glob(os.path.join(CSV_DIR, "*_clean.csv"))
    # if existing_csvs:
    #     print(f"Found {len(existing_csvs)} existing CSV files. Skipping copy/conversion.")
    # else:
    
    if copy_files():
        if not convert_files():
             print("Conversion failed.")
             # return # Continue anyway with what we have
    else:
         print("File copy/search complete.")

    df = load_data()
    if df is not None:
        df_clean = clean_data(df)
        export_data(df_clean, pdf_df)
        analyze_and_plot(df_clean)

        # PHASE 1: Enhanced Data Collection & ML
        print("\n" + "="*70)
        print("PHASE 1: ENHANCED DATA ANALYSIS")
        print("="*70)

        # 1.1: PID Analysis
        if analyze_pids is not None:
            pid_analyzer, pid_results, pid_quality = analyze_pids(df_clean)

        # 1.2: LSTM Time-Series Prediction
        if run_lstm_analysis is not None:
            lstm_analyzer = run_lstm_analysis(df_clean)

        # 1.3: Vehicle Baseline Profiles
        if create_vehicle_baselines is not None and pdf_df is not None:
            baseline_manager = create_vehicle_baselines(pdf_df)

        # PHASE 2: Advanced Analytics
        print("\n" + "="*70)
        print("PHASE 2: ADVANCED ANALYTICS")
        print("="*70)

        # 2.1: Autoencoder Anomaly Detection
        if run_autoencoder_analysis is not None:
            autoencoder_results = run_autoencoder_analysis(df_clean)

        # Run intelligent diagnostics
        if run_diagnostics is not None:
            print("\n" + "="*70)
            print("DIAGNOSTIC ENGINE")
            print("="*70)
            diagnostic_issues = run_diagnostics(df_clean, pdf_df)

        # Run predictive analytics
        if run_predictive_analytics is not None and pdf_df is not None:
            run_predictive_analytics(pdf_df, df_clean)

        # 2.4: Repair Cost Estimation
        if estimate_repair_costs is not None and 'diagnostic_issues' in locals():
            # Load diagnostic issues from file
            import csv
            diagnostic_file = os.path.join(DATA_DIR, 'diagnostic_report.csv')
            if os.path.exists(diagnostic_file):
                with open(diagnostic_file, 'r') as f:
                    reader = csv.DictReader(f)
                    issues = list(reader)
                    if issues:
                        estimate_repair_costs(issues, labor_rate=125)

        print("\n✓ Analysis complete.")
    else:
        print("Failed to load data.")

if __name__ == "__main__":
    main()