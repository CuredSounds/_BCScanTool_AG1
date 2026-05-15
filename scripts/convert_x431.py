#!/usr/bin/env python3
"""
X431 to CSV Batch Converter Tool

Unified utility for converting LAUNCH X431 diagnostic log files to CSV.
Supports single files, directories, and multiple output formats.

Usage:
    python scripts/convert_x431.py [path] [--raw] [--output dir]

Author: Neural Harmonics Lab
"""

import sys
import argparse
from pathlib import Path

# Add project root to path to allow importing src
project_root = Path(__file__).resolve().parent.parent
sys.path.append(str(project_root))

from src.core.x431_parser import X431Parser, convert_file
from src.core.database_manager import DatabaseManager
from src.core.utils import extract_vehicle_metadata
from src.core import database_manager
from src import config


def process_path(target_path: Path, clean: bool, output_dir: Path = None, import_db: bool = False) -> None:
    """Process a file or directory of .x431 files."""
    if target_path.is_file():
        files = [target_path]
    elif target_path.is_dir():
        files = sorted(target_path.glob('**/*.x431'))
    else:
        print(f"Error: Path not found: {target_path}")
        return

    if not files:
        print(f"No .x431 files found at: {target_path}")
        return

    print(f"Found {len(files)} file(s) to process.")
    print(f"Format: {'Clean (Excel-friendly)' if clean else 'Raw (Detailed)'}")
    if import_db:
        print("Database: Enabled (data will be imported to diagnostics.db)")
    print("-" * 60)

    db = DatabaseManager() if import_db else None
    success_count = 0
    error_count = 0

    for file_path in files:
        try:
            # Determine output path
            if output_dir:
                suffix = "_clean.csv" if clean else ".csv"
                
                # Determine vehicle-specific subdirectory
                make, model, _ = extract_vehicle_metadata(file_path)
                
                if make != "Unknown" and model != "Unknown":
                    # Use the new structure: data/csv/Vehicle_make_model/Make/Model/
                    target_dir = config.VEHICLE_CSV_DIR / make / model
                else:
                    target_dir = output_dir
                
                if not target_dir.exists():
                    target_dir.mkdir(parents=True, exist_ok=True)
                    
                out_path = target_dir / (file_path.stem + suffix)
            else:
                out_path = None

            final_path = convert_file(file_path, out_path, clean=clean)
            
            # Import to database if requested
            db_status = ""
            if db:
                from scripts.import_to_db import import_csv_to_db
                import_csv_to_db(final_path, db)
                db_status = " [+DB]"

            # Print relative path from project root if possible, else absolute
            try:
                rel_path = final_path.relative_to(project_root)
                print(f"✓ {file_path.name} → {rel_path}{db_status}")
            except ValueError:
                print(f"✓ {file_path.name} → {final_path}{db_status}")
            success_count += 1
        except Exception as e:
            print(f"✗ {file_path.name}: {e}")
            error_count += 1

    print("-" * 60)
    print(f"Complete: {success_count} success, {error_count} failed.")


def main():
    parser = argparse.ArgumentParser(description="X431 to CSV Converter")
    parser.add_argument("path", nargs="?", default=".", help="File or directory to convert")
    parser.add_argument("--raw", action="store_true", help="Use raw headers instead of clean ones")
    parser.add_argument("--output", "-o", help="Output directory")
    parser.add_argument("--db", action="store_true", help="Import data to database after conversion")

    args = parser.parse_args()

    target_path = Path(args.path)
    clean = not args.raw
    import_db = args.db
    
    # If no path provided or default '.' has no files, try config paths
    if args.path == "." and not list(target_path.glob('**/*.x431')):
        print(f"No files found in current directory. Checking configured data directory: {config.DATA_DIR}")
        target_path = config.DATA_DIR
    
    # Default output directory from config if not specified
    output_dir = Path(args.output) if args.output else config.CSV_DIR

    if output_dir and not output_dir.exists():
        output_dir.mkdir(parents=True)

    process_path(target_path, clean, output_dir, import_db)


if __name__ == "__main__":
    main()
