from fastapi import FastAPI, HTTPException, UploadFile, File, Security, Depends
from fastapi.security.api_key import APIKeyHeader
from fastapi.middleware.cors import CORSMiddleware
import pandas as pd
import json
import os
import shutil
import subprocess
import sys
import logging
from pydantic import BaseModel
import requests

from pathlib import Path

from src.core.database import SessionLocal, Vehicle, RepairLog, init_db
from datetime import datetime
from sqlalchemy import desc

from src import config
from src.core.diagnostic_engine import DiagnosticEngine
from src.core.predictive_analytics import PredictiveAnalytics
from src.core.gdrive_sync import backup_to_cloud
import joblib

logger = logging.getLogger("BCScanTool.API")

api_key_header = APIKeyHeader(name=config.API_KEY_NAME, auto_error=False)

async def get_api_key(api_key_header: str = Depends(api_key_header)):
    if api_key_header == config.API_KEY:
        return api_key_header
    else:
        raise HTTPException(status_code=403, detail="Could not validate API Key")

def sanitize_chat_input(text: str) -> str:
    """Basic sanitization for chat prompts."""
    # Remove common prompt injection markers
    forbidden = ["System:", "Assistant:", "User:", "###", "ignore previous instructions"]
    clean_text = text
    for word in forbidden:
        clean_text = clean_text.replace(word, "")
    return clean_text.strip()[:500]

# Allowed file extensions for upload
ALLOWED_EXTENSIONS = {'.x431', '.csv'}
MAX_UPLOAD_SIZE_MB = 50

def load_ml_models():
    """Load the trained machine learning models."""
    supervised_path = config.MODELS_DIR / "supervised_pipeline.joblib"
    anomaly_path = config.MODELS_DIR / "anomaly_pipeline.joblib"
    onnx_path = config.MODELS_DIR / "vehicle_lstm_model.onnx"
    keras_path = config.MODELS_DIR / "vehicle_lstm_model.keras"
    
    supervised = joblib.load(supervised_path) if supervised_path.exists() else None
    anomaly = joblib.load(anomaly_path) if anomaly_path.exists() else None
    
    onnx_session = None
    if onnx_path.exists():
        try:
            import onnxruntime as ort
            onnx_session = ort.InferenceSession(str(onnx_path))
            logger.info(f"Loaded MATLAB ONNX Model: {onnx_path.name}")
        except ImportError:
            logger.warning("ONNX file found but onnxruntime is not installed.")
        except Exception as e:
            logger.error(f"Failed to load ONNX model: {e}")
            
    keras_model = None
    if keras_path.exists():
        try:
            import tensorflow as tf
            keras_model = tf.keras.models.load_model(str(keras_path))
            logger.info(f"Loaded Python Keras Model: {keras_path.name}")
        except ImportError:
            logger.warning("TensorFlow not installed. Cannot load Keras model.")
        except Exception as e:
            logger.error(f"Failed to load Keras model: {e}")
            
    return supervised, anomaly, onnx_session, keras_model

SUPERVISED_MODEL, ANOMALY_MODEL, ONNX_MODEL, KERAS_MODEL = load_ml_models()
VEHICLE_SPECIFIC_MODELS = {}

app = FastAPI(title="BC Scan Tool API", version="1.0.0")

# CORS: restrict to local dashboard only (not wide-open *)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:8501", "http://127.0.0.1:8501"],  # Streamlit default
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

@app.get("/api/vehicles", dependencies=[Depends(get_api_key)])
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

@app.post("/api/upload", dependencies=[Depends(get_api_key)])
async def upload_diagnostic_file(file: UploadFile = File(...)):
    """Upload and process a raw .x431 or .csv diagnostic file."""
    # Validate file extension
    ext = Path(file.filename).suffix.lower()
    if ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(status_code=400,
                            detail=f"Invalid file type '{ext}'. Allowed: {ALLOWED_EXTENSIONS}")

    # Sanitize filename — strip path components to prevent directory traversal
    safe_filename = Path(file.filename).name
    if not safe_filename or safe_filename.startswith('.'):
        raise HTTPException(status_code=400, detail="Invalid filename")

    upload_dir = config.DATA_DIR / "raw"
    upload_dir.mkdir(parents=True, exist_ok=True)
    
    file_path = upload_dir / safe_filename
    with open(file_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

    logger.info(f"Uploaded file: {safe_filename} ({file_path.stat().st_size} bytes)")
        
    # If it's an x431 file, convert it to CSV first
    if ext == ".x431":
        try:
            from src.core.x431_parser import convert_file
            out_csv = upload_dir / f"{file_path.stem}.csv"
            convert_file(file_path, out_csv, clean=True)
        except Exception as e:
            logger.error(f"Failed to convert .x431: {e}")
            raise HTTPException(status_code=500, detail=f"Failed to convert .x431: {e}")
            
    # Trigger ML pipeline in background
    try:
        # Use subprocess.Popen without invalid timeout arg
        # The script itself should handle its own timeouts
        proc = subprocess.Popen(
            [sys.executable, str(config.PROJECT_ROOT / "scripts" / "run_full_analysis.py")]
        )
        logger.info(f"Triggered background ML pipeline (PID: {proc.pid})")
    except Exception as e:
        logger.error(f"Failed to trigger ML pipeline: {e}")
        
    return {"status": "success", "filename": safe_filename, "message": "File uploaded and ML processing started"}

@app.get("/api/vehicles/{vin}/diagnostics", dependencies=[Depends(get_api_key)])
def get_vehicle_diagnostics(vin: str):
    """Run diagnostics and predictions for a specific vehicle."""
    df = load_processed_data()
    if df.empty:
        raise HTTPException(status_code=404, detail="No diagnostic data found")
    
    vehicle_data = df[df['vin'] == vin].copy()
    if vehicle_data.empty:
        raise HTTPException(status_code=404, detail=f"No data for VIN {vin}")
        
    # --- DATA SEGMENTATION: Apply Repair Log Filter ---
    v_make = "Unknown"
    v_model = "Unknown"
    db = SessionLocal()
    try:
        vehicle = db.query(Vehicle).filter(Vehicle.vin == vin).first()
        if vehicle:
            v_make = vehicle.make
            v_model = vehicle.model
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
    # Fetch baseline confirmation date from DB
    baseline_dates = {}
    db = SessionLocal()
    try:
        vehicles = db.query(Vehicle).all()
        for v in vehicles:
            if v.baseline_confirmed_at:
                baseline_dates[v.vin] = v.baseline_confirmed_at
    finally:
        db.close()

    predictor = PredictiveAnalytics(vehicle_data, baseline_confirmed_dates=baseline_dates)
    predictions = predictor.analyze() or []
    health_scores = predictor.health_scores
    
    # --- ADD MACHINE LEARNING PREDICTIONS ---
    latest_scan = vehicle_data.iloc[-1:].copy()
    
    # 1. Supervised Random Forest
    if SUPERVISED_MODEL:
        try:
            feature_cols = SUPERVISED_MODEL.get('features', SUPERVISED_MODEL.get('feature_columns', []))
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
            logger.error(f"Supervised ML Error: {e}", exc_info=True)

    # 2. Unsupervised Isolation Forest
    if ANOMALY_MODEL:
        try:
            feature_cols = ANOMALY_MODEL.get('features', ANOMALY_MODEL.get('feature_columns', []))
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
            logger.error(f"Anomaly ML Error: {e}", exc_info=True)
            
    # 3. Deep Learning Models (MATLAB ONNX + Python Keras)
    numeric_cols = [
        'year', 'engine_speed_rpm', 'coolant_temp_f', 
        'misfire_current_cyl1', 'misfire_current_cyl2', 'misfire_current_cyl3', 'misfire_current_cyl4', 
        'misfire_current_cyl5', 'misfire_current_cyl6', 'misfire_current_cyl7', 'misfire_current_cyl8', 
        'misfire_history_cyl1', 'misfire_history_cyl2', 'misfire_history_cyl3', 'misfire_history_cyl4', 
        'misfire_history_cyl5', 'misfire_history_cyl6', 'misfire_history_cyl7', 'misfire_history_cyl8', 
        'total_misfire', 'misfire_cycles'
    ]
    
    if (ONNX_MODEL or KERAS_MODEL) and len(vehicle_data) > 0:
        try:
            import numpy as np
            
            # Align features
            X_lstm = vehicle_data.copy()
            for col in numeric_cols:
                if col not in X_lstm.columns:
                    X_lstm[col] = 0.0
            
            X_array = X_lstm[numeric_cols].fillna(0).values.astype(np.float32)
            
            # 3a. Run MATLAB ONNX Model
            if ONNX_MODEL:
                # Input expected: [SequenceLength, BatchSize=1, Features=21]
                X_onnx = np.expand_dims(X_array, axis=1)
                input_name = ONNX_MODEL.get_inputs()[0].name
                onnx_pred = ONNX_MODEL.run(None, {input_name: X_onnx})[0]
                # Output shape: [SequenceLength, 1, 1]
                latest_pred = float(onnx_pred[-1, 0, 0])
                
                if latest_pred > 20.0:
                    status = f"Critical: High Predicted Misfires ({latest_pred:.1f})"
                    severity = "CRITICAL"
                elif latest_pred > 5.0:
                    status = f"Warning: Moderate Predicted Misfires ({latest_pred:.1f})"
                    severity = "WARNING"
                else:
                    status = f"Healthy (Baseline) - Predicted misfires: {latest_pred:.2f}"
                    severity = "INFO"
                    
                predictions.append({
                    "severity": severity,
                    "issue": "Deep Learning (MATLAB ONNX)",
                    "details": f"The MATLAB-exported ONNX LSTM model predicted an anomaly rating of {latest_pred:.2f}.",
                    "prediction": status,
                    "confidence": "High"
                })
                
            # 3b. Run Python Keras Model
            if KERAS_MODEL:
                # Input expected: [BatchSize=1, SequenceLength, Features=21]
                X_keras = np.expand_dims(X_array, axis=0)
                keras_pred = KERAS_MODEL(X_keras, training=False).numpy()[0]
                # Output shape: [SequenceLength, 1]
                latest_k_pred = float(keras_pred[-1, 0])
                
                if latest_k_pred > 20.0:
                    status = f"Critical: High Predicted Misfires ({latest_k_pred:.1f})"
                    severity = "CRITICAL"
                elif latest_k_pred > 5.0:
                    status = f"Warning: Moderate Predicted Misfires ({latest_k_pred:.1f})"
                    severity = "WARNING"
                else:
                    status = f"Healthy (Baseline) - Predicted misfires: {latest_k_pred:.2f}"
                    severity = "INFO"
                    
                predictions.append({
                    "severity": severity,
                    "issue": "Deep Learning (Python Keras)",
                    "details": f"The native Python Keras LSTM model predicted an anomaly rating of {latest_k_pred:.2f}.",
                    "prediction": status,
                    "confidence": "High"
                })
        except Exception as e:
            logger.error(f"Deep Learning Inference Error: {e}", exc_info=True)
            
    # 4. Vehicle-Specific Deep Learning Autoencoder
    if v_make and v_model and v_make != "Unknown":
        vs_model_path = config.MODELS_DIR / f'vehicle_specific_lstm_{v_make}_{v_model}.keras'
        vs_features_path = config.MODELS_DIR / f'vehicle_features_{v_make}_{v_model}.json'
        vs_scaling_path = config.MODELS_DIR / f'vehicle_scaling_{v_make}_{v_model}.json'
        
        if vs_model_path.exists() and vs_features_path.exists() and vs_scaling_path.exists():
            try:
                import json
                import numpy as np
                import tensorflow as tf
                
                with open(vs_features_path) as f:
                    vs_features = json.load(f)
                with open(vs_scaling_path) as f:
                    vs_scaling = json.load(f)
                    
                model_key = f"{v_make}_{v_model}"
                if model_key not in VEHICLE_SPECIFIC_MODELS:
                    VEHICLE_SPECIFIC_MODELS[model_key] = tf.keras.models.load_model(str(vs_model_path))
                vs_model = VEHICLE_SPECIFIC_MODELS[model_key]
                
                raw_dir = config.DATA_DIR / 'csv' / 'Vehicle_make_model' / v_make / v_model
                if raw_dir.exists():
                    raw_files = sorted(raw_dir.glob("*_clean.csv"))
                    if raw_files:
                        latest_raw = raw_files[-1]
                        raw_df = pd.read_csv(latest_raw, low_memory=False)
                        
                        for col in vs_features:
                            if col not in raw_df.columns:
                                raw_df[col] = 0.0
                                
                        raw_sensor_data = raw_df[vs_features].fillna(0).values.astype(np.float32)
                        
                        if len(raw_sensor_data) >= 10:
                            recent_data = raw_sensor_data[-10:]
                            mins = np.array(vs_scaling['mins'], dtype=np.float32)
                            ranges = np.array(vs_scaling['ranges'], dtype=np.float32)
                            ranges[ranges == 0] = 1.0
                            recent_norm = (recent_data - mins) / ranges
                            
                            X_vs = np.expand_dims(recent_norm, axis=0)
                            reconstruction = vs_model(X_vs, training=False).numpy()
                            
                            mse = float(np.mean(np.square(X_vs - reconstruction)))
                            
                            if mse > 0.05:
                                status = f"Critical Sensor Anomaly Detected (MSE: {mse:.4f})"
                                severity = "CRITICAL"
                            elif mse > 0.02:
                                status = f"Warning: Sensor Drift (MSE: {mse:.4f})"
                                severity = "WARNING"
                            else:
                                status = f"Healthy (Baseline) - Signal MSE: {mse:.4f}"
                                severity = "INFO"
                                
                            predictions.append({
                                "severity": severity,
                                "issue": f"Autoencoder ({v_make} {v_model})",
                                "details": f"Analyzed {len(vs_features)} raw datastream sensors to compute an overall reconstruction anomaly score.",
                                "prediction": status,
                                "confidence": "High"
                            })
            except Exception as e:
                logger.error(f"Vehicle-Specific Autoencoder Error: {e}", exc_info=True)
    
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

@app.get("/api/vehicles/{vin}/topology", dependencies=[Depends(get_api_key)])
def get_vehicle_topology(vin: str):
    """Get the network topology status of all vehicle modules."""
    df = load_processed_data()
    if df.empty:
        raise HTTPException(status_code=404, detail="No diagnostic data found")
    
    vehicle_data = df[df['vin'] == vin].copy()
    if vehicle_data.empty:
        raise HTTPException(status_code=404, detail=f"No data for VIN {vin}")
        
    has_all_system = any(vehicle_data['source_file'].str.contains('AllSystemDTC', case=False, na=False))
    
    diag_engine = DiagnosticEngine(None, vehicle_data)
    issues = diag_engine.analyze()
    
    modules = [
        {"id": "ECM", "name": "Engine Control Module", "status": "OK", "codes": 0},
        {"id": "TCM", "name": "Transmission Control Module", "status": "OK", "codes": 0},
        {"id": "ABS", "name": "Anti-lock Braking System", "status": "OK", "codes": 0},
        {"id": "SRS", "name": "Supplemental Restraint System", "status": "OK", "codes": 0},
        {"id": "BCM", "name": "Body Control Module", "status": "OK", "codes": 0},
        {"id": "EPS", "name": "Electronic Power Steering", "status": "OK", "codes": 0},
    ]
    
    for issue in issues:
        cat = issue.get('category', '').lower()
        severity = issue.get('severity', 'INFO')
        
        if any(kw in cat for kw in ['engine', 'fuel', 'cooling', 'ignition', 'frequency', 'freeze frame']):
            status = "FAULT" if severity == 'CRITICAL' else "WARNING"
            if modules[0]['status'] != "FAULT":  
                modules[0]['status'] = status
            modules[0]['codes'] += 1
        elif 'transmission' in cat:
            modules[1]['status'] = "FAULT" if severity == 'CRITICAL' else "WARNING"
            modules[1]['codes'] += 1
            
    # If no full system scan, other modules are unknown
    if not has_all_system:
        for m in modules[1:]:
            m['status'] = "UNKNOWN"
            
    return {
        "vin": vin,
        "has_full_scan": has_all_system,
        "modules": modules
    }

class BaselineRequest(BaseModel):
    vin: str
    confirmed_at: datetime = None

@app.post("/api/vehicles/baseline", dependencies=[Depends(get_api_key)])
def confirm_baseline(request: BaselineRequest):
    """Confirm a healthy state for the vehicle to use as a baseline."""
    db = SessionLocal()
    try:
        vehicle = db.query(Vehicle).filter(Vehicle.vin == request.vin).first()
        if not vehicle:
            vehicle = Vehicle(vin=request.vin, make="Unknown", model="Unknown", year=0)
            db.add(vehicle)
        
        vehicle.baseline_confirmed_at = request.confirmed_at or datetime.utcnow()
        db.commit()
        return {"status": "success", "message": f"Baseline confirmed for {request.vin} at {vehicle.baseline_confirmed_at}"}
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        db.close()

class RepairLogRequest(BaseModel):
    vin: str
    description: str

@app.post("/api/repairs", dependencies=[Depends(get_api_key)])
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

@app.post("/api/chat", dependencies=[Depends(get_api_key)])
def chat_with_ai(request: ChatRequest):
    """Chat with the AI mechanic using Ollama."""
    # Build a context string from the diagnostics
    clean_message = sanitize_chat_input(request.message)
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
    prompt = f"{system_prompt}\\n\\nUser: {clean_message}\\nAssistant:"
    
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

@app.post("/api/cloud_sync", dependencies=[Depends(get_api_key)])
def sync_to_cloud():
    """Trigger a Google Drive backup sync of the database and processed data."""
    result = backup_to_cloud()
    if result.get("status") == "error":
        raise HTTPException(status_code=500, detail=result.get("message"))
    return result

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("src.api.main:app", host="127.0.0.1", port=8080, reload=True)
