import re
from pathlib import Path

def f_to_c(f: float) -> float:
    """Convert Fahrenheit to Celsius"""
    if f is None: return None
    return (f - 32) * 5 / 9

def c_to_f(c: float) -> float:
    """Convert Celsius to Fahrenheit"""
    if c is None: return None
    return (c * 9 / 5) + 32

def extract_vehicle_metadata(filepath: Path):
    """
    Extract make, model, and label from filename and directory.
    Works for both .x431 and .csv files.
    """
    filename = filepath.name
    parent_dir = filepath.parent.name
    
    make = "Unknown"
    model = "Unknown"
    label = "normal"
    
    # Extract make from prefix (e.g., TOYOTA_...)
    parts = filename.split('_')
    if len(parts) > 0:
        # Try to match known makes if possible, or just take first part
        potential_make = parts[0].upper()
        if potential_make in ['TOYOTA', 'GMC', 'VOLVO', 'GM', 'FORD', 'CHEVY', 'HONDA']:
            make = potential_make
        else:
            # Fallback to first part if it looks like a word
            if potential_make.isalpha():
                make = potential_make
    
    # Extract model from parent directory if it's not a generic data dir
    # Generic dirs from config
    generic_dirs = ['csv', 'raw', 'raw_x431', 'data', 'Vehicle_make_model']
    
    if parent_dir not in generic_dirs and not parent_dir.startswith('raw'):
        model = parent_dir
    else:
        # Try to guess model from filename
        if "Tacoma" in filename:
            model = "Tacoma"
        elif "Yukon" in filename:
            model = "Yukon"
        elif "S60" in filename:
            model = "S60"

    # Cross-reference make and model for consistency
    if model == "Tacoma":
        if make == "Unknown": make = "Toyota"
    elif model == "Yukon":
        if make in ["Unknown", "GM"]: make = "GMC"
    elif model == "S60":
        if make in ["Unknown", "VOLVO"]: make = "Volvo"

    # Extract label (classifier) from filename
    if "baseline" in filename.lower():
        label = "baseline"
    elif "fault" in filename.lower() or "disconnected" in filename.lower():
        for fault_type in ['maf', 'o2', 'misfire', 'vacuum', 'tps']:
            if fault_type in filename.lower():
                label = f"{fault_type}_fault"
                break
        else:
            label = "general_fault"
    elif "cleared" in filename.lower() or "restored" in filename.lower():
        label = "restored"
        
    def format_meta(s: str):
        if s.upper() in ['GMC', 'GM', 'BMW', 'VW']:
            return s.upper()
        return s.capitalize()

    return format_meta(make), format_meta(model), label
