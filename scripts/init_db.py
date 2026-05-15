#!/usr/bin/env python3
import sys
from pathlib import Path

# Add project root to path
sys.path.append(str(Path(__file__).resolve().parent.parent))

from src.core.database import init_db

if __name__ == "__main__":
    print("Initializing Database...")
    init_db()
    print("Done!")
