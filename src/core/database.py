import sys
from pathlib import Path

# Add project root to path so 'src' can be imported when running directly
sys.path.append(str(Path(__file__).resolve().parent.parent.parent))

from sqlalchemy import create_engine, Column, Integer, String, Float, DateTime, ForeignKey, JSON
from sqlalchemy.orm import declarative_base, relationship, sessionmaker
from datetime import datetime
from src import config

# Create declarative base for ORM models
Base = declarative_base()

# --- DATABASE MODELS ---

class Vehicle(Base):
    __tablename__ = 'vehicles'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    vin = Column(String, unique=True, index=True, nullable=False)
    make = Column(String)
    model = Column(String)
    year = Column(Integer)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    scans = relationship("DiagnosticScan", back_populates="vehicle", cascade="all, delete-orphan")
    predictions = relationship("MLPrediction", back_populates="vehicle", cascade="all, delete-orphan")

class DiagnosticScan(Base):
    __tablename__ = 'diagnostic_scans'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    vehicle_id = Column(Integer, ForeignKey('vehicles.id'), nullable=False)
    timestamp = Column(DateTime, default=datetime.utcnow, index=True)
    
    # Store raw sensor data as JSON for flexibility
    sensor_data = Column(JSON)
    
    # Known DTCs (Diagnostic Trouble Codes) active during this scan
    active_dtcs = Column(JSON) 
    
    # Relationships
    vehicle = relationship("Vehicle", back_populates="scans")

class MLPrediction(Base):
    __tablename__ = 'ml_predictions'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    vehicle_id = Column(Integer, ForeignKey('vehicles.id'), nullable=False)
    timestamp = Column(DateTime, default=datetime.utcnow)
    
    severity = Column(String)     # INFO, WARNING, CRITICAL
    issue = Column(String)        # Short title
    details = Column(String)      # Detailed description
    prediction_type = Column(String) # 'supervised' or 'unsupervised'
    confidence_score = Column(Float)
    
    # Relationships
    vehicle = relationship("Vehicle", back_populates="predictions")

# --- DATABASE SETUP ---

# Use the config path for the SQLite database
# Note: To migrate to PostgreSQL later, simply change this URL
# Example: DB_URL = "postgresql://user:password@localhost/bcscantool"
DB_URL = f"sqlite:///{config.DATABASE_PATH}"

# Create engine (connect_args used only for SQLite to allow multi-threading)
engine = create_engine(DB_URL, connect_args={"check_same_thread": False})

# Create a configured "Session" class
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def init_db():
    """Create all tables in the database."""
    Base.metadata.create_all(bind=engine)
    print(f"Database tables initialized at {config.DATABASE_PATH}")

def get_db():
    """Dependency generator for FastAPI to get DB sessions."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
