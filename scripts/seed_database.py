import sys
from pathlib import Path
import pandas as pd
import json

sys.path.append(str(Path(__file__).resolve().parent.parent))

from src.core.database import SessionLocal, Vehicle, DiagnosticScan, init_db
from src import config

def seed_database():
    # Make sure tables exist
    init_db()
    
    db = SessionLocal()
    processed_file = config.DATA_DIR / 'processed' / 'diagnostic_reports.csv'
    
    if not processed_file.exists():
        print("No processed diagnostic reports found to seed.")
        return
        
    df = pd.read_csv(processed_file, low_memory=False)
    print(f"Loaded {len(df)} rows from CSV. Seeding database...")
    
    # Track created vehicles
    vehicle_cache = {}
    
    for _, row in df.iterrows():
        vin = str(row.get('vin', 'UNKNOWN_VIN'))
        if vin == 'nan' or not vin:
            continue
            
        # Create Vehicle if it doesn't exist
        if vin not in vehicle_cache:
            v = db.query(Vehicle).filter(Vehicle.vin == vin).first()
            if not v:
                v = Vehicle(vin=vin, make="Unknown", model="Unknown", year=0)
                db.add(v)
                db.commit()
                db.refresh(v)
            vehicle_cache[vin] = v.id
            
        # Add Scan
        scan = DiagnosticScan(
            vehicle_id=vehicle_cache[vin],
            sensor_data=row.to_dict() # Dump everything as JSON for now
        )
        db.add(scan)
        
    db.commit()
    db.close()
    
    print("Database seeding complete!")

if __name__ == "__main__":
    seed_database()
