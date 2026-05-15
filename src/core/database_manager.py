import sqlite3
from pathlib import Path
from typing import List, Dict, Any, Optional
import pandas as pd
from src.config import DATABASE_PATH

class DatabaseManager:
    """Manages the structured SQLite database for diagnostic data."""

    def __init__(self, db_path: Path = DATABASE_PATH):
        self.db_path = db_path
        self._initialize_db()

    def _get_connection(self):
        return sqlite3.connect(self.db_path)

    def _initialize_db(self):
        """Create tables if they don't exist."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            
            # 1. Vehicles table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS vehicles (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    make TEXT NOT NULL,
                    model TEXT,
                    year INTEGER,
                    vin TEXT UNIQUE,
                    UNIQUE(make, model, year)
                )
            """)
            
            # 2. Parameters table (unique across all scans)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS parameters (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT NOT NULL,
                    unit TEXT,
                    UNIQUE(name, unit)
                )
            """)
            
            # 3. Sessions table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS sessions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    vehicle_id INTEGER,
                    timestamp TIMESTAMP,
                    source_file TEXT,
                    label TEXT,  -- This is the 'classifier' ground truth (e.g., 'normal', 'maf_fault')
                    FOREIGN KEY (vehicle_id) REFERENCES vehicles(id)
                )
            """)
            
            # 4. Readings table (normalized)
            # Note: For performance with 200+ categories, we might use a wider format 
            # if we mostly query all parameters at once. But normalized is more flexible.
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS readings (
                    session_id INTEGER,
                    parameter_id INTEGER,
                    row_index INTEGER,
                    value REAL,
                    FOREIGN KEY (session_id) REFERENCES sessions(id),
                    FOREIGN KEY (parameter_id) REFERENCES parameters(id)
                )
            """)
            
            # Indices for performance
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_readings_session ON readings(session_id)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_readings_param ON readings(parameter_id)")
            
            conn.commit()

    def get_or_create_vehicle(self, make: str, model: str = None, year: int = None) -> int:
        with self._get_connection() as conn:
            cursor = conn.cursor()
            if model:
                cursor.execute(
                    "SELECT id FROM vehicles WHERE make = ? AND model = ?", 
                    (make.upper(), model)
                )
            else:
                cursor.execute(
                    "SELECT id FROM vehicles WHERE make = ? AND model IS NULL", 
                    (make.upper(),)
                )
            
            row = cursor.fetchone()
            if row:
                return row[0]
            
            cursor.execute(
                "INSERT INTO vehicles (make, model, year) VALUES (?, ?, ?)",
                (make.upper(), model, year)
            )
            return cursor.lastrowid

    def get_or_create_parameter(self, name: str, unit: str = None) -> int:
        with self._get_connection() as conn:
            cursor = conn.cursor()
            if unit:
                cursor.execute("SELECT id FROM parameters WHERE name = ? AND unit = ?", (name, unit))
            else:
                cursor.execute("SELECT id FROM parameters WHERE name = ? AND unit IS NULL", (name,))
            
            row = cursor.fetchone()
            if row:
                return row[0]
            
            cursor.execute("INSERT INTO parameters (name, unit) VALUES (?, ?)", (name, unit))
            return cursor.lastrowid

    def add_session(self, vehicle_id: int, source_file: str, label: str = None, timestamp: str = None) -> int:
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "INSERT INTO sessions (vehicle_id, source_file, label, timestamp) VALUES (?, ?, ?, ?)",
                (vehicle_id, source_file, label, timestamp)
            )
            return cursor.lastrowid

    def bulk_add_readings(self, readings: List[tuple]):
        """readings: list of (session_id, parameter_id, row_index, value)"""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.executemany(
                "INSERT INTO readings (session_id, parameter_id, row_index, value) VALUES (?, ?, ?, ?)",
                readings
            )
            conn.commit()

    def clear_database(self):
        """Drops all tables to allow a clean re-import."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("DROP TABLE IF EXISTS readings")
            cursor.execute("DROP TABLE IF EXISTS sessions")
            cursor.execute("DROP TABLE IF EXISTS parameters")
            cursor.execute("DROP TABLE IF EXISTS vehicles")
            conn.commit()
        self._initialize_db()

    def get_session_data(self, session_id: int) -> pd.DataFrame:
        """Retrieves session data in wide format (rows x parameters)."""
        query = """
            SELECT r.row_index, p.name, r.value
            FROM readings r
            JOIN parameters p ON r.parameter_id = p.id
            WHERE r.session_id = ?
            ORDER BY r.row_index, p.name
        """
        df = pd.read_sql_query(query, self._get_connection(), params=(session_id,))
        return df.pivot(index='row_index', columns='name', values='value')
