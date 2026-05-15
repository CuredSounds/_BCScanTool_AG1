import argparse
import os
import sys
import pandas as pd
from pathlib import Path
import re

# Add project root to path
project_root = Path(__file__).resolve().parent.parent
sys.path.append(str(project_root))

from src.core.database_manager import DatabaseManager
from src.core.utils import extract_vehicle_metadata
from src import config

def import_csv_to_db(csv_path: Path, db: DatabaseManager):
    print(f"Processing {csv_path.name}...")
    
    make, model, label = extract_vehicle_metadata(csv_path)
    print(f"  Detected: Make={make}, Model={model}, Label={label}")
    
    # 1. Get or create vehicle
    vehicle_id = db.get_or_create_vehicle(make, model)
    
    # 2. Add session
    # Try to extract date from filename
    date_match = re.search(r'(\d{8})|(\d{4}\d{2}\d{2})', csv_path.name)
    timestamp = date_match.group(0) if date_match else None
    
    # Check if session already exists to avoid duplicates
    with db._get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT id FROM sessions WHERE source_file = ?", (str(csv_path),))
        if cursor.fetchone():
            print(f"  Session already exists. Skipping.")
            return

    session_id = db.add_session(vehicle_id, str(csv_path), label, timestamp)
    
    # 3. Read CSV and import readings
    try:
        df = pd.read_csv(csv_path, low_memory=False)
    except Exception as e:
        print(f"  Error reading CSV: {e}")
        return

    # Check for 'Row' column and drop it (it's index)
    if 'Row' in df.columns:
        df = df.drop(columns=['Row'])
    elif 'Num' in df.columns:
        df = df.drop(columns=['Num'])

    readings = []
    param_map = {} # cache param_id
    
    # Iterate through columns (parameters)
    for col in df.columns:
        # Extract name and unit ONLY from "Name [Unit]"
        # We don't use () because many names contain parentheses as part of the label
        name = col
        unit = None
        if '[' in col:
            name, unit = col.split('[', 1)
            unit = unit.rstrip(']')
        
        name = name.strip()
        if unit: unit = unit.strip()
        
        param_id = db.get_or_create_parameter(name, unit)
        param_map[col] = param_id

    # Bulk insert readings
    print(f"  Importing {len(df) * len(df.columns)} data points...")
    
    for row_idx, row in df.iterrows():
        for col_name, val in row.items():
            param_id = param_map[col_name]
            # Handle non-numeric values
            try:
                numeric_val = float(val)
                readings.append((session_id, param_id, int(row_idx), numeric_val))
            except (ValueError, TypeError):
                continue
                
        # Bulk insert every 5000 readings to keep memory low
        if len(readings) > 10000:
            db.bulk_add_readings(readings)
            readings = []

    if readings:
        db.bulk_add_readings(readings)
    
    print(f"  Successfully imported session {session_id}")

def main():
    parser = argparse.ArgumentParser(description="Import CSV diagnostic data to SQLite database")
    parser.add_argument("--clear", action="store_true", help="Clear the database before importing")
    args = parser.parse_args()

    db = DatabaseManager()
    
    if args.clear:
        print("Clearing database...")
        db.clear_database()
        print("Database cleared.")
    
    # Find CSV files to import
    # Prioritize 'clean' files in data/csv/ recursively
    csv_files = list(config.CSV_DIR.glob("**/*_clean.csv"))
    
    if not csv_files:
        print(f"No clean CSV files found in {config.CSV_DIR}")
        # Try any CSV files in data/ recursively if no clean ones
        csv_files = list(config.DATA_DIR.glob("**/*.csv"))
        # Filter out ones that are probably not ours
        csv_files = [f for f in csv_files if "clean" in f.name or "baseline" in f.name.lower()]

    print(f"Found {len(csv_files)} files to import.")
    
    for csv_file in csv_files:
        import_csv_to_db(csv_file, db)
        
    print("\nImport complete!")
    print(f"Database located at: {db.db_path}")

if __name__ == "__main__":
    main()
