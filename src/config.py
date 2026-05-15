import os
from pathlib import Path

# Project root calculation
PROJECT_ROOT = Path(__file__).resolve().parent.parent

# Data directories
DATA_DIR = PROJECT_ROOT / "data"
DATABASE_PATH = DATA_DIR / "diagnostics.db"
RAW_X431_DIR = DATA_DIR / "raw_x431"
CSV_DIR = DATA_DIR / "csv"
VEHICLE_CSV_DIR = CSV_DIR / "Vehicle_make_model"
PDF_DIR = DATA_DIR / "raw"  # PDFs are in data/raw
PROCESSED_DIR = DATA_DIR / "processed"
MODELS_DIR = PROJECT_ROOT / "models"
LOGS_DIR = PROJECT_ROOT / "logs"

# External paths (can be overridden by environment variables)
# Default path from original obd2.py
DEFAULT_SOURCE_X431_DIR = "/Users/sonic.design/Library/CloudStorage/MacDroid-googleAISystemENP10-01/storage/emulated/0/CNLAUNCH/X431/images"
SOURCE_X431_DIR = os.getenv("BCSCAN_SOURCE_X431_DIR", DEFAULT_SOURCE_X431_DIR)

# Scripts
CONVERTER_SCRIPT = PROJECT_ROOT / "scripts" / "convert_x431.py"

# Analysis settings
DEFAULT_ESTIMATORS = 200
DEFAULT_CONTAMINATION = 0.1

def setup_directories():
    """Create necessary directories if they don't exist."""
    directories = [
        RAW_X431_DIR,
        CSV_DIR,
        VEHICLE_CSV_DIR,
        PDF_DIR,
        PROCESSED_DIR,
        MODELS_DIR,
        LOGS_DIR
    ]
    for directory in directories:
        directory.mkdir(parents=True, exist_ok=True)
