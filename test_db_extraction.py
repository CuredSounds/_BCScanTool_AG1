import os
from pathlib import Path

def test_extraction(filename, parent_dir):
    make = "Unknown"
    model = "Unknown"
    
    # Try to get make from filename prefix
    parts = filename.split('_')
    if len(parts) > 0:
        make = parts[0].upper()
    
    # Try to get model from directory name if it's in a subfolder
    if parent_dir not in ['csv', 'raw', 'raw_x431']:
        model = parent_dir
    
    return make, model

# Test cases
test_files = [
    ("TOYOTA_989347712041_20251018170040_clean.csv", "Tacoma Data"),
    ("GM_989347712041_20260314080930_clean.csv", "GMC_Yukon"),
    ("VOLVO_989347712041_20251219145944_clean.csv", "Volvo_S60"),
    ("TOYOTA_test.csv", "csv")
]

for f, p in test_files:
    m, md = test_extraction(f, p)
    print(f"File: {f} in {p} -> Make: {m}, Model: {md}")
