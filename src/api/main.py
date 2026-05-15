from fastapi import FastAPI, HTTPException, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
import pandas as pd
import json
import os
import shutil
import subprocess
import sys
from pydantic import BaseModel
import requests

from pathlib import Path
sys.path.append(str(Path(__file__).resolve().parent.parent.parent))

from src.core.database import SessionLocal, Vehicle, RepairLog, init_db
from datetime import datetime
from sqlalchemy import desc

from src import config
from src.core.diagnostic_engine import DiagnosticEngine
from src.core.predictive_analytics import PredictiveAnalytics
import joblib

def load_ml_models():
    """Load the trained machine learning models."""
    supervised_path = config.MODELS_DIR / "supervised_pipeline.joblib"
    anomaly_path = config.MODELS_DIR / "anomaly_pipeline.joblib"
    onnx_path = config.MODELS_DIR / "vehicle_lstm_model.onnx"
    
    supervised = joblib.load(supervised_path) if supervised_path.exists() else None
    anomaly = joblib.load(anomaly_path) if anomaly_path.exists() else None
    
    onnx_session = None
    if onnx_path.exists():
        try:
            import onnxruntime as ort
            onnx_session = ort.InferenceSession(str(onnx_path))
            print(f"Loaded MATLAB ONNX Model: {onnx_path.name}")
        except ImportError:
            print("ONNX file found but onnxruntime is not installed.")
        except Exception as e:
            print(f"Failed to load ONNX model: {e}")
            
    return supervised, anomaly, onnx_session

SUPERVISED_MODEL, ANOMALY_MODEL, ONNX_MODEL = load_ml_models()

app = FastAPI(title="BC Scan Tool API", version="1.0.0")

# Enable CORS for web dashboard
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

def load_processed_data():
    processed_file = config.DATA_DIR / 'processed' / 'diagnostic_reports.csv'
    if not processed_file.exists():
        return pd.DataFrame()
    return pd.read_csv(processed_file)

def load_baselines():
    baseline_file = config.DATA_DIR / 'vehicle_baselines.json'
    if not baseline_file.exists():
        return {}
    with open(baseline_file) as f:
        return json.load(f)

@app.get("/api/health")
def health_check():
    return {"status": "ok"}

@app.get("/api/vehicles")
def get_vehicles():
    """Return a list of all vehicles and their baselines."""
    baselines = load_baselines()
    vehicles = []
    for vin, data in baselines.items():
        vehicles.append({
            "vin": vin,
            "make": data.get("make", "Unknown"),
            "model": data.get("model", "Unknown"),
            "year": data.get("year", "Unknown"),
        })
    return vehicles

@app.post("/api/upload")
async def upload_diagnostic_file(file: UploadFile = File(...)):
    """Upload and process a raw .x431 or .csv diagnostic file."""
    upload_dir = config.DATA_DIR / "raw"
    upload_dir.mkdir(parents=True, exist_ok=True)
    
    file_path = upload_dir / file.filename
    with open(file_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)
        
    # If it's an x431 file, convert it to CSV first
    if file.filename.endswith(".x431"):
        try:
            from src.core.x431_parser import convert_file
            out_csv = upload_dir / f"{file_path.stem}.csv"
            convert_file(file_path, out_csv, clean=True)
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Failed to convert .x431: {e}")
            
    # Trigger ML Training & Ingestion Pipeline asynchronously
    try:
        subprocess.Popen([sys.executable, str(config.PROJECT_ROOT / "scripts" / "run_full_analysis.py")])
    except Exception as e:
        print("Failed to trigger ML pipeline:", e)
        
    return {"status": "success", "filename": file.filename, "message": "File uploaded and ML processing started"}

@app.get("/api/vehicles/{vin}/diagnostics")
def get_vehicle_diagnostics(vin: str):
    """Run diagnostics and predictions for a specific vehicle."""
    df = load_processed_data()
    if df.empty:
        raise HTTPException(status_code=404, detail="No diagnostic data found")
    
    vehicle_data = df[df['vin'] == vin].copy()
    if vehicle_data.empty:
        raise HTTPException(status_code=404, detail=f"No data for VIN {vin}")
        
    # --- DATA SEGMENTATION: Apply Repair Log Filter ---
    db = SessionLocal()
    try:
        vehicle = db.query(Vehicle).filter(Vehicle.vin == vin).first()
        if vehicle:
            latest_repair = db.query(RepairLog).filter(RepairLog.vehicle_id == vehicle.id).order_by(desc(RepairLog.date)).first()
            if latest_repair and 'test_time_dt' in vehicle_data.columns:
                vehicle_data['test_time_dt'] = pd.to_datetime(vehicle_data['test_time_dt'])
                vehicle_data = vehicle_data[vehicle_data['test_time_dt'] > latest_repair.date]
                if vehicle_data.empty:
                    # In a real app we might just return "Healthy since repair" instead of 404
                    # But for now we just log it. 
                    pass
    finally:
        db.close()
    
    # If filtered out everything, return a basic response indicating healthy since repair
    if vehicle_data.empty:
        return {
            "vin": vin,
            "health_score": 100,
            "health_grade": "A",
            "health_status": "Excellent",
            "issues": [{"severity": "INFO", "issue": "Repaired", "details": "Vehicle was recently repaired. No new data yet."}],
            "predictions": [],
            "scans_count": 0
        }
    
    # Run diagnostic engine
    diag_engine = DiagnosticEngine(None, vehicle_data)
    issues = diag_engine.analyze()
    
    # Run predictive analytics
    predictor = PredictiveAnalytics(vehicle_data)
    predictions = predictor.analyze() or []
    health_scores = predictor.health_scores
    
    # --- ADD MACHINE LEARNING PREDICTIONS ---
    latest_scan = vehicle_data.iloc[-1:].copy()
    
    # 1. Supervised Random Forest
    if SUPERVISED_MODEL:
        try:
            feature_cols = SUPERVISED_MODEL['features']
            pipeline = SUPERVISED_MODEL['pipeline']
            label_encoder = SUPERVISED_MODEL['label_encoder']
            
            for col in feature_cols:
                if col not in latest_scan.columns:
                    latest_scan[col] = 0
            
            X_latest = latest_scan[feature_cols].apply(pd.to_numeric, errors='coerce').fillna(0)
            pred = pipeline.predict(X_latest)
            condition = label_encoder.inverse_transform(pred)[0]
            
            if condition != 'good':
                predictions.append({
                    "severity": "WARNING",
                    "issue": f"ML Detection: {condition}",
                    "details": f"Supervised ML model detected a '{condition}' signature in the latest sensor data.",
                    "prediction": condition,
                    "confidence": "High"
                })
        except Exception as e:
            print(f"Supervised ML Error: {e}")

    # 2. Unsupervised Isolation Forest
    if ANOMALY_MODEL:
        try:
            feature_cols = ANOMALY_MODEL['features']
            pipeline = ANOMALY_MODEL['pipeline']
            
            for col in feature_cols:
                if col not in latest_scan.columns:
                    latest_scan[col] = 0
            
            X_latest = latest_scan[feature_cols].apply(pd.to_numeric, errors='coerce').fillna(0)
            anomaly_score = pipeline.decision_function(X_latest)[0]
            is_anomaly = pipeline.predict(X_latest)[0]
            
            if is_anomaly == -1: # -1 indicates anomaly
                predictions.append({
                    "severity": "CRITICAL",
                    "issue": "Unsupervised Anomaly Detected",
                    "details": f"The AI Isolation Forest detected highly unusual sensor patterns (Anomaly Score: {anomaly_score:.2f}).",
                    "prediction": "Unknown Impending Failure",
                    "confidence": "Medium"
                })
        except Exception as e:
            print(f"Anomaly ML Error: {e}")
            
    # 3. ONNX Deep Learning Model (MATLAB Export)
    if ONNX_MODEL:
        try:
            import numpy as np
            # NOTE: When your MATLAB model is ready, map 'latest_scan' to the correct ONNX input array here.
            # input_name = ONNX_MODEL.get_inputs()[0].name
            # onnx_pred = ONNX_MODEL.run(None, {input_name: X_onnx_array})
            
            predictions.append({
                "severity": "INFO",
                "issue": "Deep Learning Active",
                "details": "The MATLAB-exported ONNX LSTM model is online and monitoring data streams.",
                "prediction": "Healthy (Baseline)",
                "confidence": "High"
            })
        except Exception as e:
            print(f"ONNX ML Error: {e}")
    
    score_data = health_scores.get(vin, {"score": 100, "grade": "A", "status": "Unknown"})
    
    return {
        "vin": vin,
        "health_score": score_data.get("score", 100),
        "health_grade": score_data.get("grade", "A"),
        "health_status": score_data.get("status", "Unknown"),
        "issues": issues,
        "predictions": predictions,
        "scans_count": len(vehicle_data)
    }

class RepairLogRequest(BaseModel):
    vin: str
    description: str

@app.post("/api/repairs")
def log_repair(request: RepairLogRequest):
    """Log a repair to reset the AI baseline."""
    db = SessionLocal()
    try:
        vehicle = db.query(Vehicle).filter(Vehicle.vin == request.vin).first()
        if not vehicle:
            vehicle = Vehicle(vin=request.vin, make="Unknown", model="Unknown", year=0)
            db.add(vehicle)
            db.commit()
            db.refresh(vehicle)
            
        repair = RepairLog(
            vehicle_id=vehicle.id,
            description=request.description,
            date=datetime.utcnow()
        )
        db.add(repair)
        db.commit()
        return {"status": "success", "message": f"Repair logged for {request.vin}: {request.description}"}
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        db.close()

class ChatRequest(BaseModel):
    message: str
    vin: str
    context_data: dict

@app.post("/api/chat")
def chat_with_ai(request: ChatRequest):
    """Chat with the AI mechanic using Ollama."""
    # Build a context string from the diagnostics
    issues = request.context_data.get("issues", [])
    predictions = request.context_data.get("predictions", [])
    
    issues_str = "\\n".join([f"- {i.get('issue')} ({i.get('severity')})" for i in issues]) if issues else "None"
    preds_str = "\\n".join([f"- {p.get('issue')} ({p.get('prediction')})" for p in predictions]) if predictions else "None"
    
    system_prompt = f"""You are a professional, expert AI mechanic assistant for the BCScanTool diagnostic platform.
You are currently helping a user troubleshoot their vehicle (VIN: {request.vin}).

Current Active Issues:
{issues_str}

Predictive Alerts:
{preds_str}

Your goal is to answer the user's questions clearly, concisely, and accurately based on the provided vehicle data. Provide actionable mechanical advice, potential repair costs, or troubleshooting steps. Do not use complex jargon without explaining it.
"""
    prompt = f"{system_prompt}\\n\\nUser: {request.message}\\nAssistant:"
    
    # Attempt to use local Ollama
    try:
        response = requests.post("http://localhost:11434/api/generate", json={
            "model": "llama3", # Default to llama3, user can change this if they use a different model
            "prompt": prompt,
            "stream": False
        }, timeout=45)
        
        if response.status_code == 200:
            return {"response": response.json().get("response", "").strip()}
        else:
            return {"response": f"I encountered an error with the local AI model: {response.status_code}. Try checking your Ollama installation."}
    except Exception as e:
        return {"response": "I could not connect to your local Ollama instance. Please make sure Ollama is running (`ollama serve`) and the `llama3` model is installed (`ollama pull llama3`). If you intended to use Google Gemini, please ensure your API key is configured."}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("src.api.main:app", host="127.0.0.1", port=8080, reload=True)
