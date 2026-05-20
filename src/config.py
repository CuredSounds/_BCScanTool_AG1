import os
import json
import logging
from pathlib import Path

# ──────────────────────────────────────────────
# Project root calculation
# ──────────────────────────────────────────────
PROJECT_ROOT = Path(__file__).resolve().parent.parent

# ──────────────────────────────────────────────
# Logging (used project-wide instead of print())
# ──────────────────────────────────────────────
LOG_FORMAT = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
LOG_LEVEL = os.getenv("BCSCAN_LOG_LEVEL", "INFO")

logging.basicConfig(level=getattr(logging, LOG_LEVEL), format=LOG_FORMAT)
logger = logging.getLogger("BCScanTool")

# ──────────────────────────────────────────────
# Data directories
# ──────────────────────────────────────────────
DATA_DIR = PROJECT_ROOT / "data"
DATABASE_PATH = DATA_DIR / "diagnostics.db"
RAW_X431_DIR = DATA_DIR / "raw_x431"
CSV_DIR = DATA_DIR / "csv"
VEHICLE_CSV_DIR = CSV_DIR / "Vehicle_make_model"
PDF_DIR = DATA_DIR / "raw"
PROCESSED_DIR = DATA_DIR / "processed"
MODELS_DIR = PROJECT_ROOT / "models"
LOGS_DIR = PROJECT_ROOT / "logs"

# Metadata & labeled dataset directories
METADATA_DIR = DATA_DIR / "metadata"
LABELED_DIR = DATA_DIR / "labeled"
LABELED_BASELINES_DIR = LABELED_DIR / "baselines"
LABELED_FAULTS_DIR = LABELED_DIR / "faults"
LABELED_ORGANIC_DIR = LABELED_DIR / "organic"

# Metadata files
SCAN_MANIFEST_PATH = METADATA_DIR / "scan_manifest.csv"
TEST_EXECUTIONS_PATH = METADATA_DIR / "test_executions.csv"
PARAMETER_TIERS_PATH = METADATA_DIR / "parameter_tiers.json"

# ──────────────────────────────────────────────
# External paths (overridable via environment)
# ──────────────────────────────────────────────
DEFAULT_SOURCE_X431_DIR = "/Users/sonic.design/Library/CloudStorage/MacDroid-googleAISystemENP10-01/storage/emulated/0/CNLAUNCH/X431/images"
SOURCE_X431_DIR = os.getenv("BCSCAN_SOURCE_X431_DIR", DEFAULT_SOURCE_X431_DIR)
CONVERTER_SCRIPT = PROJECT_ROOT / "scripts" / "convert_x431.py"

# ──────────────────────────────────────────────
# API Security
# ──────────────────────────────────────────────
API_KEY = os.getenv("BCSCAN_API_KEY", "bcscan_secret_key_2026")
API_KEY_NAME = "X-API-Key"

# ──────────────────────────────────────────────
# Analysis settings
# ──────────────────────────────────────────────
DEFAULT_ESTIMATORS = 200
DEFAULT_CONTAMINATION = 0.1

# ──────────────────────────────────────────────
# Data quality gate constants
# ──────────────────────────────────────────────
MIN_ROWS_BASELINE = 200     # ~1.6 min at 2 Hz
MIN_ROWS_FAULT = 120        # ~1 min at 2 Hz
INIT_ROWS_TO_DROP = 30      # X431 progressive fill - first 30 rows are sensor init
MIN_RPM_ENGINE_RUNNING = 50 # Below this = engine off

# ──────────────────────────────────────────────
# Temperature unit handling
# ──────────────────────────────────────────────
# X431 exports Tacoma data in Celsius. All internal thresholds use Celsius.
TEMP_UNIT = "celsius"
TEMP_OVERHEAT_C = 104       # ~220°F
TEMP_COLD_C = 71            # ~160°F
TEMP_NORMAL_LOW_C = 82      # ~180°F
TEMP_NORMAL_HIGH_C = 99     # ~210°F
TEMP_RAPID_CHANGE_C = 11    # ~20°F jump

# ──────────────────────────────────────────────
# Model versioning
# ──────────────────────────────────────────────
MODEL_METADATA_FILE = "model_metadata.json"


def setup_directories():
    """Create necessary directories if they don't exist."""
    directories = [
        RAW_X431_DIR, CSV_DIR, VEHICLE_CSV_DIR, PDF_DIR,
        PROCESSED_DIR, MODELS_DIR, LOGS_DIR,
        METADATA_DIR, LABELED_DIR, LABELED_BASELINES_DIR,
        LABELED_FAULTS_DIR, LABELED_ORGANIC_DIR,
    ]
    for directory in directories:
        directory.mkdir(parents=True, exist_ok=True)


def load_parameter_tiers():
    """Load parameter tier definitions from JSON config."""
    if not PARAMETER_TIERS_PATH.exists():
        logger.warning(f"Parameter tiers not found at {PARAMETER_TIERS_PATH}")
        return {"tier_a": [], "tier_b": [], "tier_c": []}
    with open(PARAMETER_TIERS_PATH) as f:
        tiers = json.load(f)
    return {
        "tier_a": tiers.get("tier_a_ml_features", {}).get("columns", []),
        "tier_b": tiers.get("tier_b_secondary_features", {}).get("columns", []),
        "tier_c": (tiers.get("tier_c_metadata_only", {}).get("columns", [])
                   + tiers.get("tier_c_binary_signals", {}).get("columns", [])),
    }


def save_model_metadata(model_name: str, metadata: dict):
    """Save model training metadata alongside the model file."""
    from datetime import datetime
    meta_path = MODELS_DIR / f"{model_name}_metadata.json"
    metadata["saved_at"] = datetime.utcnow().isoformat()
    metadata["model_name"] = model_name
    with open(meta_path, "w") as f:
        json.dump(metadata, f, indent=2, default=str)
    logger.info(f"Model metadata saved to {meta_path}")
