import sqlite3
from pathlib import Path
import sys

# Add project root to path
project_root = Path(__file__).resolve().parent.parent
sys.path.append(str(project_root))

from src.config import DATABASE_PATH

def verify():
    if not DATABASE_PATH.exists():
        print(f"Database not found at {DATABASE_PATH}")
        return

    conn = sqlite3.connect(DATABASE_PATH)
    cursor = conn.cursor()

    print("=== Database Statistics ===")
    
    cursor.execute("SELECT count(*) FROM vehicles")
    print(f"Vehicles: {cursor.fetchone()[0]}")

    cursor.execute("SELECT count(*) FROM sessions")
    print(f"Sessions: {cursor.fetchone()[0]}")

    cursor.execute("SELECT count(*) FROM parameters")
    print(f"Parameters (Categories): {cursor.fetchone()[0]}")

    cursor.execute("SELECT count(*) FROM readings")
    print(f"Readings (Data Points): {cursor.fetchone()[0]:,}")

    print("\n=== Top Sessions by Category Count ===")
    cursor.execute("""
        SELECT s.id, s.source_file, count(DISTINCT r.parameter_id) as param_count 
        FROM sessions s
        JOIN readings r ON s.id = r.session_id 
        GROUP BY s.id 
        ORDER BY param_count DESC 
        LIMIT 10
    """)
    rows = cursor.fetchall()
    print(f"{'ID':<5} {'Param Count':<12} {'Source File'}")
    for row in rows:
        filename = Path(row[1]).name
        print(f"{row[0]:<5} {row[2]:<12} {filename}")

    conn.close()

if __name__ == "__main__":
    verify()
